# IntelMon-News — Real-Time Threat Intelligence → Telegram

<p align="center">
  <img src="https://img.shields.io/badge/Python-3.10%2B-blue?style=flat-square&logo=python" alt="Python">
  <img src="https://img.shields.io/badge/Platform-Linux%20%7C%20macOS%20%7C%20Windows%20%7C%20Termux%20%7C%20Docker-lightgrey?style=flat-square" alt="Platform">
  <img src="https://img.shields.io/badge/Feeds-200%2B-orange?style=flat-square" alt="Feeds">
  <img src="https://img.shields.io/badge/Interval-5min-green?style=flat-square" alt="Interval">
  <img src="https://img.shields.io/badge/License-MIT-yellow?style=flat-square" alt="License">
</p>

<p align="center">
  <b>200+ curated security feeds → Telegram in 5 minutes. No duplicates. No spam. Just signal.</b><br>
  Monitors news, CVEs, ransomware victims, exploits and dark web leaks — 24/7.
</p>

---

## ✨ Features

- **200+ RSS Feeds** — News, vendor blogs, CERTs, research — all scored and deduped
- **CISA KEV + NVD** — Actively exploited CVEs and CVSS ≥9.0 criticals
- **RansomWatch + Dark Web** — Ransomware victims and dark web leak sites (`darkweb.py` separate module)
- **Exploit-DB** — New public exploits (last 48h)
- **Smart Scoring** — `rce`/`poc` use word boundaries (no `percent` false positive), group names auto-CRITICAL
- **Dedup Engine** — Normalized title + 12h similarity (Jaccard >0.6), SQLite persistent
- **Date Filter** — Only last 3 days (`max_age_days`), older items skipped
- **Cross-Platform** — Linux, macOS, Windows/WSL, Termux, Docker, Systemd, Cron
- **IST Timestamps** — 12-hour with AM/PM (`24-Aug-2026 05:35:56 PM IST`)

## 📡 Monitored Sources

| Category | Sources | Priority |
|----------|---------|----------|
| **News (200)** | The Hacker News, BleepingComputer, KrebsOnSecurity, DarkReading, SecurityWeek, PortSwigger, The Record, CyberScoop, HelpNetSecurity, SANS ISC, CISA Advisories, NCSC UK, Schneier, SentinelOne, CrowdStrike, Rapid7 and 180+ more — see [`feeds.json`](feeds.json) | Scored |
| **CISA KEV** | Known Exploited Vulnerabilities (with ransomware flag) | 🔴 CRITICAL |
| **NVD** | New CVEs `CVSS ≥9.0` (NVD API v2) | 🔴 CRITICAL |
| **RansomWatch** | Ransomware victims (GitHub mirror, 80+ groups) | 🔴 CRITICAL |
| **Dark Web** | Leak-site monitoring via `darkweb.py` (Tor fallback) — enable with `darkweb.services: true` | 🔴 CRITICAL |
| **Exploit-DB** | New exploits from GitLab CSV | 🟠 HIGH |

Full feed list: [`feeds.json`](feeds.json) — 200 curated, categorized, enabled/disabled per feed.

## 🚀 Quick Start (5 min)

```bash
git clone https://github.com/evogix/IntelMon-News.git
cd IntelMon-News
bash setup.sh                  # installs requests + feedparser, creates data/logs

cp config.json.example config.json
# Edit config.json:
# 1. @BotFather → /newbot → copy token → telegram.bot_token
# 2. Send a message to your bot, then:
#    curl https://api.telegram.org/bot<TOKEN>/getUpdates  # copy chat.id
# 3. telegram.chat_id

python3 monitor.py --test      # should say TEST OK in Telegram
python3 monitor.py --once      # single cycle (dry run)
python3 monitor.py --loop 300  # every 5 min (or --loop for config interval)
```

> **Requires:** Python 3.10+, `pip install -r requirements.txt` (only `requests`, `feedparser`)

## 🔔 Alert Format

```
🔴 CRITICAL 🚨 NEWS

PeopleSoft Pre-Auth RCE: PSIGW SSRF Chain → RCE

• 📰 The Record

🔗 Source

⏰ 24-Aug-2026 05:35:56 PM IST
```

```
🔴 CRITICAL 🚨 NEW-CVE

CVE-2026-78167 — CVSS 10.0

• Remote code execution in XYZ
• Vector: CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:C/C:H/I:H/A:H
• Severity: CRITICAL

🔗 Source

⏰ 24-Aug-2026 05:31:29 PM IST
```

```
🔴 CRITICAL 🚨 DARKWEB LEAK

victim-company.com — LockBit

• 🕸️ Dark Web Leak Site
• 👥 Group: lockbit
• 🎯 Victim: victim-company.com

🔗 Source

⏰ 24-Aug-2026 05:40:00 PM IST
```

## ⚙️ Configuration

`config.json` holds **only sensitive settings** — feeds are in [`feeds.json`](feeds.json):

```json
{
  "telegram": {
    "bot_token": "PUT_YOUR_BOT_TOKEN_HERE",
    "chat_id": "PUT_YOUR_CHAT_ID_HERE"
  },
  "settings": {
    "min_priority": "high",
    "interval_sec": 300,
    "heartbeat_cycles": 0,
    "max_age_days": 3,
    "cve_min_score": 9.0
  },
  "keywords": { "critical": [...], "high": [...], "groups": [...] },
  "sources": {
    "enable_kev": true,
    "enable_nvd": true,
    "enable_ransomware": true,
    "enable_exploitdb": true,
    "enable_darkweb": false
  },
  "darkweb": {
    "services": false,
    "tor_proxy": "socks5h://127.0.0.1:9050",
    "use_tor": false
  }
}
```

| Key | Default | Description |
|-----|---------|-------------|
| `min_priority` | `high` | `high` hides INFO, `all` shows everything, `critical` only |
| `interval_sec` | `300` | Poll every 300s (5 min). Also used when running `python3 monitor.py --loop` without value |
| `heartbeat_cycles` | `0` | `0` disabled; `N` sends `💓 alive` every N cycles if no alerts |
| `max_age_days` | `3` | Only articles from last 3 days (22-24 Aug) |
| `cve_min_score` | `9.0` | Minimum CVSS to alert (lower to 7.0 for more) |
| `darkweb.services` | `false` | Set `true` to enable `darkweb.py` (separate module, Tor optional) |

Enable dark web: set `darkweb.services: true` **and** `sources.enable_darkweb: true`, then restart.

`feeds.json` is the professional feed store — 200 feeds, each with `name`, `url`, `category`, `enabled`. Edit it to add/remove feeds without touching config.

## ▶️ Running — Cross-Platform

**Linux / macOS / WSL:**
```bash
nohup python3 monitor.py --loop 300 > logs/nohup.log 2>&1 &
# or use config interval:
nohup python3 monitor.py --loop > logs/nohup.log 2>&1 &
```

**Windows (PowerShell):**
```powershell
python monitor.py --loop 300
# background:
Start-Process python -ArgumentList "monitor.py --loop 300" -WindowStyle Hidden
```

**Docker:**
```bash
docker-compose up -d
# logs:
docker logs -f intel-monitor
```

**Systemd (VPS):**
```bash
sudo cp intel-monitor.service /etc/systemd/system/
sudo systemctl enable --now intel-monitor
sudo journalctl -u intel-monitor -f
```

**Cron:**
```bash
*/5 * * * * cd /opt/IntelMon-News && python3 monitor.py --once >> logs/cron.log 2>&1
```

**Termux (Android):**
```bash
termux-wake-lock
nohup python3 monitor.py --loop 300 > logs/nohup.log 2>&1 &
# Boot auto-start: ~/.termux/boot/intelmon-boot.sh
# Widget: ~/.shortcuts/IntelMon-Status.sh → Home → Widgets → Termux
```

`--loop` without value uses `config.json` interval. `--loop 60` overrides config.

## 🏗️ Architecture

```
feeds.json (200) ─┐
config.json ──────┤→ monitor.py ─→ scoring → dedup (SQLite) → Telegram
CISA KEV ─────────┤                     ↑
NVD API ──────────┤              darkweb.py (if enabled, Tor fallback)
RansomWatch ──────┘
Exploit-DB ───────┘
```

- **Parallel fetch:** 20 threads, 30s timeout, Session pooling, retry on 403/530
- **Scoring:** Word-boundary for short keywords (`rce`, `poc`) to avoid `percent` false positive
- **Dedup:** Normalized title (no link) + 12h Jaccard similarity >0.6
- **Storage:** `data/intel.db` (seen hashes, meta), `logs/monitor.log`

## 📁 Project Structure

```
IntelMon-News/
├── monitor.py              # main engine
├── darkweb.py              # dark web module (separate, Tor optional)
├── feeds.json              # 200 curated feeds (professional split)
├── config.json             # sensitive settings only (gitignored)
├── config.json.example     # template
├── requirements.txt        # requests, feedparser
├── setup.sh                # cross-platform installer
├── Dockerfile              # Docker
├── docker-compose.yml      # Compose
├── intel-monitor.service   # systemd
├── data/intel.db           # SQLite dedup
└── logs/                   # monitor.log, nohup.log
```

## 🔧 Troubleshooting

- **403/530/Connection refused** — Rate-limited/WAF or slow origin. Handled with retry + backoff, not spammed. Check `logs/monitor.log` (debug level).
- **No alerts for 5 min** — No new HIGH/CRITICAL in that window (normal). Check `logs/monitor.log` for `cycle done` and `seen` count. Enable `heartbeat_cycles` or set `min_priority: all` for more.
- **Duplicate alerts** — Fixed via title dedup + similarity. If still seen, check `data/intel.db` `seen` table.
- **Old news** — `max_age_days: 3` filters older than 3 days.

## 📄 License

MIT — see [LICENSE](LICENSE) if present.

---

<p align="center">Built for hunters who need signal, not noise.</p>
