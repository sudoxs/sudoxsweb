# Web Reconnaissance Tool Cheat Sheet: theHarvester vs Gobuster vs ffuf vs feroxbuster vs katana

Five tools, five different jobs. Picking the right one isn't about which is "best" — it's about matching the tool to the phase of your engagement. Here's the breakdown.

---

## Quick Decision Matrix

| Task | First Choice | Why |
|---|---|---|
| OSINT (emails, subdomains, hosts) from public sources | **theHarvester** | Passive collection, no direct traffic to target |
| Fast, no-nonsense directory scanning | **Gobuster** | Simple syntax, reliable, pre-installed on Kali |
| Parameter fuzzing, vhost discovery, multi-position fuzzing | **ffuf** | The `FUZZ` keyword works anywhere — URL, headers, body |
| Deep recursive directory mapping | **feroxbuster** | Auto-recursion, link extraction, wildcard filtering |
| Crawling modern web apps (SPA/React/Angular) + endpoint discovery | **katana** | Headless browsing, JS parsing, XHR extraction  |

---

## theHarvester — Passive OSINT Collection

**What it does:** Gathers email addresses, subdomains, hostnames, and employee names from public sources (search engines, certificate transparency logs, PGP key servers, Shodan, etc.). It never touches the target directly — purely passive.

**When to use it:** The very first step of external recon. Before you even look at the target's web server, harvest what's already publicly exposed.

**Basic syntax:**
```bash
theHarvester -d <domain> -l <limit> -b <source>
```

**Flags:**

| Flag | Meaning |
|---|---|
| `-d` | Target domain or company name |
| `-l` | Limit results per source (default 500) |
| `-b` | Data source: `google`, `bing`, `duckduckgo`, `dnsdumpster`, `crtsh`, `virustotal`, `shodan`, `all` |
| `-f` | Save output to file (HTML/XML) |
| `-c` | Perform DNS brute force |
| `-n` | Enable DNS server lookup |

**Examples:**

```bash
# Basic email + subdomain harvest from DuckDuckGo
theHarvester -d kali.org -l 500 -b duckduckgo

# Comprehensive scan across all sources
theHarvester -d example.com -l 500 -b all -f results

# Subdomain-focused using certificate transparency
theHarvester -d example.com -l 300 -b crtsh

# Email harvesting only, save to file
theHarvester -d example.com -l 100 -b google,bing -f emails
```

**Real-world note:** Google often blocks theHarvester with CAPTCHAs or bot detection. If `-b google` fails, switch to `duckduckgo`, `crtsh`, or `dnsdumpster`.

---

## Gobuster — Fast, Simple, Multi-Mode

**What it does:** Brute-forces URIs (directories/files), DNS subdomains, virtual hosts, S3/GCS buckets, and TFTP files. Mode-based — each mode does one thing well.

**When to use it:** When you want quick, reliable results without thinking about configuration. Excellent for DNS subdomain enumeration and simple directory scans where recursion isn't needed.

**Syntax:**
```bash
gobuster <mode> <flags>
```

**Modes:** `dir`, `dns`, `vhost`, `s3`, `gcs`, `fuzz`, `tftp`

**Key flags:**

| Flag | Meaning |
|---|---|
| `-u` | Target URL |
| `-w` | Wordlist path |
| `-t` | Threads (default 10) |
| `-x` | File extensions (e.g. `.php,.html`) |
| `-o` | Output file |
| `-q` | Quiet mode |
| `-s` | Status codes to show |

**Examples:**

```bash
# Directory brute-force with extensions
gobuster dir -u https://target.com -w /usr/share/wordlists/dirb/common.txt -x php,html,js,txt -t 50

# DNS subdomain enumeration
gobuster dns -d target.com -w /usr/share/wordlists/subdomains.txt -t 50

# Virtual host discovery
gobuster vhost -u https://target.com -w vhosts.txt --append-domain

# S3 bucket enumeration
gobuster s3 -w bucket-names.txt

# Fuzzing a query parameter
gobuster fuzz -u https://example.com?FUZZ=test -w parameter-names.txt
```

**Important limitation:** Gobuster does **not** support recursion natively. If it finds `/admin/`, you must manually re-scan that directory.

---

## ffuf — The Flexible Fuzzer

**What it does:** A general-purpose HTTP fuzzer. The literal keyword `FUZZ` can be placed anywhere in the request — URL path, query parameter, POST body, headers, even the `Host` header. This makes it far more versatile than pure directory scanners.

**When to use it:** Parameter fuzzing, virtual host discovery, API endpoint discovery, testing authenticated endpoints (via raw request import), and any scenario where you need surgical precision.

**Syntax:**
```bash
ffuf -w <wordlist> -u <URL with FUZZ> [options]
```

**Key flags:**

| Flag | Meaning |
|---|---|
| `-w` | Wordlist path |
| `-u` | Target URL (contains `FUZZ`) |
| `-H` | Custom header (can contain `FUZZ`) |
| `-X` | HTTP method |
| `-d` | POST data |
| `-mc` | Match status codes (default: 200,204,301,302,307,401,403) |
| `-fc` | Filter status codes |
| `-fs` | Filter by response size |
| `-fw` | Filter by word count |
| `-fl` | Filter by line count |
| `-t` | Threads (default 40) |
| `-ac` | Auto-calibrate (auto-filter wildcard responses) |
| `-recursion` | Enable recursive scanning |
| `-o` | Output file |

**Examples:**

```bash
# Basic directory discovery
ffuf -u https://target.com/FUZZ -w wordlist.txt

# Filter out 404s and show only 200/301/302
ffuf -u https://target.com/FUZZ -w wordlist.txt -mc 200,301,302 -fc 404

# Virtual host fuzzing (Host header)
ffuf -u https://target.com -H "Host: FUZZ.target.com" -w vhosts.txt -fs 612

# Parameter fuzzing
ffuf -u "https://target.com/api?FUZZ=test" -w params.txt -mc 200

# POST data fuzzing (login brute-force)
ffuf -u https://target.com/login -X POST -d "user=admin&pass=FUZZ" -w passwords.txt

# Recursive directory scan
ffuf -u https://target.com/FUZZ -w wordlist.txt -recursion -recursion-depth 3

# Multi-position fuzzing (two wordlists simultaneously)
ffuf -u https://FUZZ.target.com/FUZZ2 \
     -w subdomains.txt:FUZZ -w dirs.txt:FUZZ2

# Authenticated fuzzing via raw request file
ffuf --request req.txt -w wordlist.txt -ac
```

**The `-ac` flag matters:** Auto-calibration analyzes the target's "not found" response and automatically filters out similar responses. This saves you from manually figuring out the right `-fs` value.

---

## feroxbuster — Recursive Directory Beast

**What it does:** A recursive content discovery tool written in Rust. Its defining feature is **automatic recursion** — when it finds a directory, it immediately queues it for its own scan, building a complete site map without manual intervention.

**When to use it:** When you need thorough, deep directory mapping. Bug bounty recon, large-scale asset enumeration, or any scenario where manual recursion would be tedious.

**Syntax:**
```bash
feroxbuster -u <URL> -w <wordlist> [options]
```

**Key flags:**

| Flag | Meaning |
|---|---|
| `-u` | Target URL |
| `-w` | Wordlist path |
| `-x` | Extensions (e.g. `php,html,txt`) |
| `-d` / `--depth` | Max recursion depth |
| `-t` | Threads |
| `--extract-links` | Parse response bodies for additional links |
| `--filter-status` | Filter by status code |
| `--filter-similar-to` | Filter pages similar to a given example |
| `--dont-scan` | Exclude paths from recursion |
| `--silent` | Suppress progress bars |
| `-o` | Output file |

**Examples:**

```bash
# Basic recursive scan (recursion is ON by default)
feroxbuster -u https://target.com -w wordlist.txt

# With extensions and depth limit
feroxbuster -u https://target.com -w wordlist.txt -x php,html,txt -d 3 -t 50

# Extract links from responses to find more endpoints
feroxbuster -u https://target.com -w wordlist.txt --extract-links

# Exclude noisy paths from recursion
feroxbuster -u https://target.com -w wordlist.txt --dont-scan /static /assets /js

# Filter out pages similar to /register (handles dynamic CSRF tokens)
feroxbuster -u https://target.com -w wordlist.txt --filter-similar-to https://target.com/register
```

**Wildcard handling:** feroxbuster auto-filters wildcard responses by default. If every random path returns a 200 with the same page, it detects and filters that automatically.

---

## katana — Modern Web Crawler

**What it does:** A next-generation crawling and spidering framework written in Go by ProjectDiscovery. Unlike traditional crawlers that only follow static HTML links, katana can parse JavaScript, extract endpoints from JS files, and execute headless browsing to crawl Single-Page Applications (SPAs) built with React, Angular, or Vue . It's designed to uncover hidden endpoints, API routes, XHR calls, and form actions that static analysis would miss .

**When to use it:** When you need to map out a modern web application's attack surface. This is especially useful for SPAs where traditional crawlers see almost nothing. Katana is the first tool you run to build an endpoint inventory before you start fuzzing with ffuf or feroxbuster.

**Syntax:**
```bash
katana -u <URL> [options]
```

**Key flags:**

| Flag | Meaning |
|---|---|
| `-u` | Target URL |
| `-list` | File containing list of target URLs |
| `-d` | Maximum crawl depth (default 3)  |
| `-jc` | Enable JavaScript file parsing and crawling of discovered endpoints  |
| `-jsl` | Enable jsluice parsing in JavaScript files (memory intensive)  |
| `-hl` | Enable headless hybrid crawling (for SPA/React/Angular)  |
| `-xhr` | Extract XHR request URL and method in JSONL output  |
| `-kf` | Crawl known files (`all`, `robotstxt`, `sitemapxml`)  |
| `-cs` | In-scope URL regex to be followed by crawler  |
| `-fs` | Pre-defined scope field (`dn`, `rdn`, `fqdn`) or custom regex (default "rdn")  |
| `-f` | Field to display in output (`url`, `qurl`, `qpath`, `path`, `fqdn`, etc.)  |
| `-o` | Output file  |
| `-c` | Number of concurrent fetchers (default 10)  |
| `-rl` | Maximum requests per second (default 150)  |

**Examples:**

```bash
# Basic crawl (standard mode, no JS)
katana -u https://target.com

# Crawl with JavaScript parsing (extract endpoints from JS files)
katana -u https://target.com -jc

# Headless mode (required for SPA/React/Angular apps)
katana -u https://target.com -hl -jc

# Headless with XHR extraction and JSONL output
katana -u https://target.com -hl -sc -nos -xhr -j -o katana_headless.jsonl

# Extract only URLs that contain query parameters
katana -u https://target.com -jc -f qurl

# Crawl with JS + XHR/fetch call tracing
katana -u https://target.com -jc -xhr

# Limit to same domain (default behavior)
katana -u https://target.com -jc -cs target.com

# Depth control (max depth 5)
katana -u https://target.com -jc -d 5

# Rate limit (requests per second)
katana -u https://target.com -jc -rl 50

# Authenticated crawl — provide session cookie
katana -u https://target.com -hl -H "Cookie: session=<token>" -jc

# Multiple targets from file
katana -list urls.txt -jc -o all_endpoints.txt
```

**Field extraction — the killer feature:** Katana can extract specific fields from crawl output using the `-f` flag. Available fields include `url`, `path`, `fqdn`, `rdn`, `rurl`, `qurl`, `qpath`, `file`, `ufile`, `key`, `value`, `kv`, `dir`, `udir` . This lets you filter out noise and pipe clean endpoints directly into other tools.

```bash
# Extract only URLs with query parameters (useful for parameter fuzzing)
katana -u https://target.com -f qurl -silent

# Extract only JS file URLs
katana -u https://target.com -jc | grep "\.js$" > js_files.txt

# Filter for API paths
katana -u https://target.com -jc | grep -E "(/api/|/v[0-9]+/|/graphql|/rest/)"

# Show discovered endpoints from JS (exclude static assets)
katana -u https://target.com -jc | grep -v "\.(png|jpg|gif|svg|ico|woff|css)$"
```

**Pipeline integration:** Katana is designed to feed into other ProjectDiscovery tools and standard Unix pipelines. A typical recon workflow chains katana's output directly into fuzzing tools :

```bash
# Crawl then fuzz
katana -u https://target.com -jc | sort -u > endpoints.txt
# Then feed endpoints.txt into ffuf or feroxbuster
```

---

## The Professional Workflow

Real engagements don't use just one tool. Here's the standard multi-phase approach:

**Phase 1 — Passive Recon (theHarvester)**
```bash
theHarvester -d target.com -l 500 -b all -f recon
```
Collect emails, subdomains, and hostnames before touching the target.

**Phase 2 — Endpoint Discovery (katana)**
```bash
katana -u https://target.com -jc -hl -d 3 -o endpoints.txt
```
Crawl the application, parse JavaScript, and build a complete endpoint inventory. For SPAs, `-hl` is mandatory.

**Phase 3 — Broad Recursive Mapping (feroxbuster)**
```bash
feroxbuster -u https://target.com -w /usr/share/seclists/Discovery/Web-Content/raft-medium-directories.txt -x php,html,txt --depth 3
```
Get a complete map of the directory structure in one pass.

**Phase 4 — Surgical Fuzzing (ffuf)**
```bash
# Test discovered parameters
ffuf -u https://target.com/admin/panel.php?accessID=FUZZ -w ids.txt -mc 200 -fs 58

# Test vhosts
ffuf -u https://target.com -H "Host: FUZZ.target.com" -w vhosts.txt
```
Drill into specific endpoints, parameters, or headers that feroxbuster or katana discovered.

**Gobuster sits as a reliable alternative** for Phase 3 when you want speed without recursion, or for DNS subdomain enumeration before you even have a web target.

---

## Summary

| Tool | Language | Best For | Recursion | FUZZ Placement | Key Distinction |
|---|---|---|---|---|---|
| **theHarvester** | Python | OSINT, passive recon | N/A | N/A | No direct traffic to target |
| **Gobuster** | Go | Fast dir/DNS/vhost scans | ❌ Manual | URL path only | Simple, reliable, fast |
| **ffuf** | Go | Parameter/vhost/custom fuzzing | ✅ Manual flag | Anywhere | Most versatile fuzzer |
| **feroxbuster** | Rust | Deep recursive directory mapping | ✅ Automatic | URL path | Auto-recursion beast |
| **katana** | Go | SPA crawling, JS endpoint discovery | ✅ Configurable depth | N/A (crawler, not fuzzer) | Headless + JS parsing  |

**Rule of thumb:**
- Need emails and subdomains without touching the target? → **theHarvester**
- Need a quick directory scan or DNS enumeration? → **Gobuster**
- Need to fuzz a parameter, header, or POST body? → **ffuf**
- Need to map every directory recursively? → **feroxbuster**
- Need to crawl a modern SPA and extract JS endpoints? → **katana**
