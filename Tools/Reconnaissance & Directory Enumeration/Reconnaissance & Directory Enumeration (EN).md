# Web Reconnaissance Tool Cheat Sheet: theHarvester vs Gobuster vs ffuf vs feroxbuster

Four tools, four different jobs. Picking the right one isn't about which is "best" — it's about matching the tool to the phase of your engagement. Here's the breakdown.

---

## Quick Decision Matrix

| Task | First Choice | Why |
|---|---|---|
| OSINT (emails, subdomains, hosts) from public sources | **theHarvester** | Passive collection, no direct traffic to target |
| Fast, no-nonsense directory scanning | **Gobuster** | Simple syntax, reliable, pre-installed on Kali |
| Parameter fuzzing, vhost discovery, multi-position fuzzing | **ffuf** | The `FUZZ` keyword works anywhere — URL, headers, body |
| Deep recursive directory mapping | **feroxbuster** | Auto-recursion, link extraction, wildcard filtering |

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

## The Professional Workflow

Real engagements don't use just one tool. Here's the standard three-phase approach:

**Phase 1 — Passive Recon (theHarvester)**
```bash
theHarvester -d target.com -l 500 -b all -f recon
```
Collect emails, subdomains, and hostnames before touching the target.

**Phase 2 — Broad Recursive Mapping (feroxbuster)**
```bash
feroxbuster -u https://target.com -w /usr/share/seclists/Discovery/Web-Content/raft-medium-directories.txt -x php,html,txt --depth 3
```
Get a complete map of the directory structure in one pass.

**Phase 3 — Surgical Fuzzing (ffuf)**
```bash
# Test discovered parameters
ffuf -u https://target.com/admin/panel.php?accessID=FUZZ -w ids.txt -mc 200 -fs 58

# Test vhosts
ffuf -u https://target.com -H "Host: FUZZ.target.com" -w vhosts.txt
```
Drill into specific endpoints, parameters, or headers that feroxbuster discovered.

**Gobuster sits as a reliable alternative** for Phase 2 when you want speed without recursion, or for DNS subdomain enumeration before you even have a web target.

---

## Summary

| Tool | Language | Best For | Recursion | FUZZ Placement |
|---|---|---|---|---|
| **theHarvester** | Python | OSINT, passive recon | N/A | N/A |
| **Gobuster** | Go | Fast dir/DNS/vhost scans | ❌ Manual | URL path only |
| **ffuf** | Go | Parameter/vhost/custom fuzzing | ✅ Manual flag | Anywhere |
| **feroxbuster** | Rust | Deep recursive mapping | ✅ Automatic | URL path |

**Rule of thumb:**
- Need emails and subdomains without touching the target? → **theHarvester**
- Need a quick directory scan or DNS enumeration? → **Gobuster**
- Need to fuzz a parameter, header, or POST body? → **ffuf**
- Need to map every directory recursively? → **feroxbuster**
