# Web偵察ツール チートシート: theHarvester vs Gobuster vs ffuf vs feroxbuster vs katana

5つのツール、5つの役割。どれが「最高」かではなく、エンゲージメントのどのフェーズにどのツールを当てるかが重要です。

---

## クイック判断マトリクス

| タスク | 第一選択 | 理由 |
|---|---|---|
| 公開情報からのOSINT（メール、サブドメイン、ホスト） | **theHarvester** | パッシブ収集、ターゲットへ直接通信しない |
| 高速でシンプルなディレクトリ探索 | **Gobuster** | 構文が単純、信頼性高い、Kaliに標準搭載 |
| パラメータファジング、vhost発見、複数位置ファジング | **ffuf** | `FUZZ` キーワードがURL・ヘッダ・ボディどこにでも置ける |
| 深い再帰的ディレクトリマッピング | **feroxbuster** | 自動再帰、リンク抽出、ワイルドカード除去 |
| モダンWebアプリ（SPA/React/Angular）のクロール＋エンドポイント発見 | **katana** | ヘッドレスブラウジング、JS解析、XHR抽出 |

---

## theHarvester — パッシブOSINT収集

**何をするか:** 公開ソース（検索エンジン、証明書透明性ログ、PGP鍵サーバー、Shodanなど）からメールアドレス、サブドメイン、ホスト名、従業員名を収集します。ターゲットに直接触れない、純粋にパッシブなツールです。

**いつ使うか:** 外部偵察の最初のステップ。ターゲットのWebサーバーを見る前に、すでに公開されている情報を収集します。

**基本構文:**
```bash
theHarvester -d <domain> -l <limit> -b <source>
```

**フラグ:**

| フラグ | 意味 |
|---|---|
| `-d` | 対象ドメインまたは企業名 |
| `-l` | ソースごとの結果上限（デフォルト500） |
| `-b` | データソース: `google`, `bing`, `duckduckgo`, `dnsdumpster`, `crtsh`, `virustotal`, `shodan`, `all` |
| `-f` | 出力をファイルに保存（HTML/XML） |
| `-c` | DNSブルートフォースを実行 |
| `-n` | DNSサーバールックアップを有効化 |

**例:**

```bash
# DuckDuckGoからの基本的なメール＋サブドメイン収集
theHarvester -d kali.org -l 500 -b duckduckgo

# 全ソースを横断した包括的スキャン
theHarvester -d example.com -l 500 -b all -f results

# 証明書透明性を使ったサブドメイン重視
theHarvester -d example.com -l 300 -b crtsh

# メール収集のみ、ファイル保存
theHarvester -d example.com -l 100 -b google,bing -f emails
```

**実運用の注意:** GoogleはしばしばCAPTCHAやボット検出でtheHarvesterをブロックします。`-b google` が失敗したら `duckduckgo`、`crtsh`、`dnsdumpster` に切り替えてください。

---

## Gobuster — 高速・シンプル・マルチモード

**何をするか:** URI（ディレクトリ/ファイル）、DNSサブドメイン、仮想ホスト、S3/GCSバケット、TFTPファイルをブルートフォースします。モードベースで、各モードが1つのことをうまくやります。

**いつ使うか:** 設定を考えずに素早く信頼できる結果が欲しいとき。DNSサブドメイン列挙や、再帰が不要なシンプルなディレクトリスキャンに最適です。

**構文:**
```bash
gobuster <mode> <flags>
```

**モード:** `dir`, `dns`, `vhost`, `s3`, `gcs`, `fuzz`, `tftp`

**主要フラグ:**

| フラグ | 意味 |
|---|---|
| `-u` | 対象URL |
| `-w` | ワードリストのパス |
| `-t` | スレッド数（デフォルト10） |
| `-x` | 拡張子（例: `.php,.html`） |
| `-o` | 出力ファイル |
| `-q` | 静音モード |
| `-s` | 表示するステータスコード |

**例:**

```bash
# 拡張子付きディレクトリブルートフォース
gobuster dir -u https://target.com -w /usr/share/wordlists/dirb/common.txt -x php,html,js,txt -t 50

# DNSサブドメイン列挙
gobuster dns -d target.com -w /usr/share/wordlists/subdomains.txt -t 50

# 仮想ホスト発見
gobuster vhost -u https://target.com -w vhosts.txt --append-domain

# S3バケット列挙
gobuster s3 -w bucket-names.txt

# クエリパラメータのファジング
gobuster fuzz -u https://example.com?FUZZ=test -w parameter-names.txt
```

**重要な制限:** Gobusterは**再帰をネイティブサポートしていません**。`/admin/` を見つけても、そのディレクトリを手動で再スキャンする必要があります。

---

## ffuf — 柔軟なファザー

**何をするか:** 汎用HTTPファザー。リテラルキーワード `FUZZ` をリクエストのどこにでも置けます — URLパス、クエリパラメータ、POSTボディ、ヘッダ、さらには `Host` ヘッダまで。これにより純粋なディレクトリスキャナよりはるかに versatile です。

**いつ使うか:** パラメータファジング、仮想ホスト発見、APIエンドポイント発見、生リクエストインポートによる認証済みエンドポイントのテスト、そして外科的な精度が必要なあらゆるシナリオ。

**構文:**
```bash
ffuf -w <wordlist> -u <URL with FUZZ> [options]
```

**主要フラグ:**

| フラグ | 意味 |
|---|---|
| `-w` | ワードリストのパス |
| `-u` | 対象URL（`FUZZ` を含む） |
| `-H` | カスタムヘッダ（`FUZZ` を含められる） |
| `-X` | HTTPメソッド |
| `-d` | POSTデータ |
| `-mc` | マッチするステータスコード（デフォルト: 200,204,301,302,307,401,403） |
| `-fc` | フィルタするステータスコード |
| `-fs` | レスポンスサイズでフィルタ |
| `-fw` | ワード数でフィルタ |
| `-fl` | 行数でフィルタ |
| `-t` | スレッド数（デフォルト40） |
| `-ac` | 自動キャリブレーション（ワイルドカード応答を自動フィルタ） |
| `-recursion` | 再帰スキャンを有効化 |
| `-o` | 出力ファイル |

**例:**

```bash
# 基本的なディレクトリ発見
ffuf -u https://target.com/FUZZ -w wordlist.txt

# 404を除外し、200/301/302のみ表示
ffuf -u https://target.com/FUZZ -w wordlist.txt -mc 200,301,302 -fc 404

# 仮想ホストファジング（Hostヘッダ）
ffuf -u https://target.com -H "Host: FUZZ.target.com" -w vhosts.txt -fs 612

# パラメータファジング
ffuf -u "https://target.com/api?FUZZ=test" -w params.txt -mc 200

# POSTデータファジング（ログインブルートフォース）
ffuf -u https://target.com/login -X POST -d "user=admin&pass=FUZZ" -w passwords.txt

# 再帰的ディレクトリスキャン
ffuf -u https://target.com/FUZZ -w wordlist.txt -recursion -recursion-depth 3

# 複数位置ファジング（2つのワードリストを同時に）
ffuf -u https://FUZZ.target.com/FUZZ2 \
     -w subdomains.txt:FUZZ -w dirs.txt:FUZZ2

# 生リクエストファイル経由の認証済みファジング
ffuf --request req.txt -w wordlist.txt -ac
```

**`-ac` フラグが重要:** 自動キャリブレーションはターゲットの「見つからない」応答を分析し、類似した応答を自動でフィルタします。手動で `-fs` の値を探す手間が省けます。

---

## feroxbuster — 再帰的ディレクトリの獣

**何をするか:** Rustで書かれた再帰的コンテンツ発見ツール。最大の特徴は**自動再帰** — ディレクトリを見つけると即座にそのスキャンをキューに入れ、手動介入なしに完全なサイトマップを構築します。

**いつ使うか:** 徹底的で深いディレクトリマッピングが必要なとき。バグバウンティの偵察、大規模アセット列挙、手動再帰が面倒なあらゆるシナリオ。

**構文:**
```bash
feroxbuster -u <URL> -w <wordlist> [options]
```

**主要フラグ:**

| フラグ | 意味 |
|---|---|
| `-u` | 対象URL |
| `-w` | ワードリストのパス |
| `-x` | 拡張子（例: `php,html,txt`） |
| `-d` / `--depth` | 最大再帰深度 |
| `-t` | スレッド数 |
| `--extract-links` | レスポンスボディから追加リンクを解析 |
| `--filter-status` | ステータスコードでフィルタ |
| `--filter-similar-to` | 指定例に類似したページをフィルタ |
| `--dont-scan` | 再帰から除外するパス |
| `--silent` | プログレスバーを抑制 |
| `-o` | 出力ファイル |

**例:**

```bash
# 基本的な再帰スキャン（再帰はデフォルトでON）
feroxbuster -u https://target.com -w wordlist.txt

# 拡張子と深度制限付き
feroxbuster -u https://target.com -w wordlist.txt -x php,html,txt -d 3 -t 50

# レスポンスからリンクを抽出してさらなるエンドポイントを発見
feroxbuster -u https://target.com -w wordlist.txt --extract-links

# ノイズの多いパスを再帰から除外
feroxbuster -u https://target.com -w wordlist.txt --dont-scan /static /assets /js

# /register に類似したページをフィルタ（動的CSRFトークンに対応）
feroxbuster -u https://target.com -w wordlist.txt --filter-similar-to https://target.com/register
```

**ワイルドカード処理:** feroxbusterはデフォルトでワイルドカード応答を自動フィルタします。ランダムなパスがすべて同じページで200を返す場合、それを検出して自動的に除外します。

---

## katana — モダンWebクローラー

**何をするか:** ProjectDiscoveryによってGoで書かれた次世代クローリング＆スパイダーフレームワーク。静的なHTMLリンクだけを追う従来のクローラーとは異なり、katanaはJavaScriptを解析し、JSファイルからエンドポイントを抽出し、ヘッドレスブラウジングを実行してReact、Angular、Vueで構築されたシングルページアプリケーション（SPA）をクロールできます。静的解析では見逃す隠れたエンドポイント、APIルート、XHR呼び出し、フォームアクションを発見するように設計されています。

**いつ使うか:** モダンWebアプリケーションの攻撃面をマッピングする必要があるとき。特に、従来のクローラーがほとんど何も見えないSPAで有用です。katanaは、ffufやferoxbusterでファジングを始める前に、エンドポイントインベントリを構築するために最初に実行するツールです。

**構文:**
```bash
katana -u <URL> [options]
```

**主要フラグ:**

| フラグ | 意味 |
|---|---|
| `-u` | 対象URL |
| `-list` | 対象URLのリストを含むファイル |
| `-d` | 最大クロール深度（デフォルト3） |
| `-jc` | JavaScriptファイルの解析と発見されたエンドポイントのクロールを有効化 |
| `-jsl` | JavaScriptファイル内でjsluice解析を有効化（メモリ消費大） |
| `-hl` | ヘッドレスハイブリッドクローリングを有効化（SPA/React/Angular用） |
| `-xhr` | JSONL出力でXHRリクエストURLとメソッドを抽出 |
| `-kf` | 既知のファイルをクロール（`all`, `robotstxt`, `sitemapxml`） |
| `-cs` | クローラーが追跡するインスコープURL正規表現 |
| `-fs` | 事前定義スコープフィールド（`dn`, `rdn`, `fqdn`）またはカスタム正規表現（デフォルト "rdn"） |
| `-f` | 出力に表示するフィールド（`url`, `qurl`, `qpath`, `path`, `fqdn` など） |
| `-o` | 出力ファイル |
| `-c` | 同時フェッチャー数（デフォルト10） |
| `-rl` | 1秒あたりの最大リクエスト数（デフォルト150） |

**例:**

```bash
# 基本的なクロール（標準モード、JSなし）
katana -u https://target.com

# JavaScript解析付きクロール（JSファイルからエンドポイントを抽出）
katana -u https://target.com -jc

# ヘッドレスモード（SPA/React/Angularアプリに必須）
katana -u https://target.com -hl -jc

# ヘッドレス＋XHR抽出＋JSONL出力
katana -u https://target.com -hl -sc -nos -xhr -j -o katana_headless.jsonl

# クエリパラメータを含むURLのみ抽出
katana -u https://target.com -jc -f qurl

# JS＋XHR/fetch呼び出しトレース付きクロール
katana -u https://target.com -jc -xhr

# 同一ドメインに限定（デフォルト動作）
katana -u https://target.com -jc -cs target.com

# 深度制御（最大深度5）
katana -u https://target.com -jc -d 5

# レート制限（1秒あたりのリクエスト数）
katana -u https://target.com -jc -rl 50

# 認証済みクロール — セッションCookieを提供
katana -u https://target.com -hl -H "Cookie: session=<token>" -jc

# ファイルから複数ターゲット
katana -list urls.txt -jc -o all_endpoints.txt
```

**フィールド抽出 — キラー機能:** Katanaは `-f` フラグを使ってクロール出力から特定のフィールドを抽出できます。利用可能なフィールドには `url`, `path`, `fqdn`, `rdn`, `rurl`, `qurl`, `qpath`, `file`, `ufile`, `key`, `value`, `kv`, `dir`, `udir` があります。これによりノイズをフィルタし、クリーンなエンドポイントを他のツールに直接パイプできます。

```bash
# クエリパラメータ付きURLのみ抽出（パラメータファジングに有用）
katana -u https://target.com -f qurl -silent

# JSファイルURLのみ抽出
katana -u https://target.com -jc | grep "\.js$" > js_files.txt

# APIパスをフィルタ
katana -u https://target.com -jc | grep -E "(/api/|/v[0-9]+/|/graphql|/rest/)"

# JSから発見されたエンドポイントを表示（静的アセットを除外）
katana -u https://target.com -jc | grep -v "\.(png|jpg|gif|svg|ico|woff|css)$"
```

**パイプライン統合:** Katanaは他のProjectDiscoveryツールや標準Unixパイプラインに投入されるように設計されています。典型的な偵察ワークフローでは、katanaの出力をファジングツールに直接チェーンします。

```bash
# クロールしてからファズ
katana -u https://target.com -jc | sort -u > endpoints.txt
# その後 endpoints.txt を ffuf や feroxbuster に投入
```

---

## プロフェッショナルなワークフロー

実際のエンゲージメントでは1つのツールだけを使いません。標準的なマルチフェーズアプローチはこちら:

**フェーズ1 — パッシブ偵察 (theHarvester)**
```bash
theHarvester -d target.com -l 500 -b all -f recon
```
ターゲットに触れる前に、メール、サブドメイン、ホスト名を収集。

**フェーズ2 — エンドポイント発見 (katana)**
```bash
katana -u https://target.com -jc -hl -d 3 -o endpoints.txt
```
アプリケーションをクロールし、JavaScriptを解析し、完全なエンドポイントインベントリを構築。SPAの場合、`-hl` は必須です。

**フェーズ3 — 広範な再帰マッピング (feroxbuster)**
```bash
feroxbuster -u https://target.com -w /usr/share/seclists/Discovery/Web-Content/raft-medium-directories.txt -x php,html,txt --depth 3
```
1パスでディレクトリ構造の完全なマップを取得。

**フェーズ4 — 外科的ファジング (ffuf)**
```bash
# 発見されたパラメータをテスト
ffuf -u https://target.com/admin/panel.php?accessID=FUZZ -w ids.txt -mc 200 -fs 58

# vhostをテスト
ffuf -u https://target.com -H "Host: FUZZ.target.com" -w vhosts.txt
```
feroxbusterやkatanaが発見した特定のエンドポイント、パラメータ、ヘッダを掘り下げる。

**Gobusterは信頼できる代替**としてフェーズ3に位置します — 再帰なしの速度が欲しいとき、あるいはWebターゲットすら見つける前のDNSサブドメイン列挙に。

---

## まとめ

| ツール | 言語 | 最適用途 | 再帰 | FUZZ配置 | 主な特徴 |
|---|---|---|---|---|---|
| **theHarvester** | Python | OSINT、パッシブ偵察 | N/A | N/A | ターゲットに直接通信しない |
| **Gobuster** | Go | 高速dir/DNS/vhostスキャン | ❌ 手動 | URLパスのみ | シンプル、信頼性、高速 |
| **ffuf** | Go | パラメータ/vhost/カスタムファジング | ✅ 手動フラグ | どこでも | 最も versatile なファザー |
| **feroxbuster** | Rust | 深い再帰ディレクトリマッピング | ✅ 自動 | URLパス | 自動再帰の獣 |
| **katana** | Go | SPAクロール、JSエンドポイント発見 | ✅ 設定可能な深度 | N/A（クローラー、ファザーではない） | ヘッドレス＋JS解析 |

**経験則:**
- ターゲットに触れずにメールとサブドメインが欲しい？ → **theHarvester**
- 素早いディレクトリスキャンやDNS列挙が欲しい？ → **Gobuster**
- パラメータ、ヘッダ、POSTボディをファズしたい？ → **ffuf**
- すべてのディレクトリを再帰的にマップしたい？ → **feroxbuster**
- モダンSPAをクロールしてJSエンドポイントを抽出したい？ → **katana**
