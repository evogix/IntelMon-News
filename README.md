# ORACLE-INTEL-MON — Threat Intelligence Monitor → Telegram

Real-time cybersecurity intelligence aggregator. Every new article, CVE, or victim is delivered to Telegram with source link and timestamp.

**Cross-platform:** Linux · macOS · Windows (WSL) · Termux (Android) · Docker · VPS

## Monitored Sources

| Source | Data | Priority |
|---|---|---|
| **RSS Feeds (101)** | The Hacker News, BleepingComputer, KrebsOnSecurity, DarkReading, SecurityWeek, PortSwigger, The Record, CyberScoop, Ars Technica, Infosecurity Magazine, HelpNetSecurity, SANS ISC, CISA Advisories, NCSC UK, Schneier, SentinelOne, CrowdStrike, Rapid7, plus 80+ more | Scored by keywords |
| **CISA KEV** | Actively exploited CVEs (with ransomware campaign flag) | 🔴 CRITICAL |
| **NVD API** | New CVEs with CVSS ≥ 9.0 | 🔴 CRITICAL |
| **RansomWatch** | New ransomware victims (GitHub mirror) | 🔴 CRITICAL |
| **Exploit-DB** | New public exploits (last 48h) | 🟠 HIGH |

**Scoring engine:** Title/summary scan — `0day / RCE / actively exploited / ransomware / supply chain / backdoor` → CRITICAL, `exploit / POC / bypass / leak / hacked / malware` → HIGH, threat-group names (LockBit, Akira, Lazarus, etc.) → CRITICAL.

**Dedup:** SQLite-based with normalized title + 12-hour similarity check (Jaccard >0.6). No duplicate alerts. State persists across restarts.

**Filters:** Only articles from the last 3 days (`max_age_days: 3`). Older items are skipped. Short keywords (`rce`, `poc`) use word boundaries to avoid false positives (e.g., `percent`).

## Setup (5 minutes) — Any OS

```bash
git clone https://github.com/evogix/intel-monitor.git
cd intel-monitor
bash setup.sh                    # or: pip install -r requirements.txt

# 1. Create bot: @BotFather on Telegram → /newbot → copy token
# 2. Edit config.json → telegram.bot_token
# 3. Send a message to your bot, then:
curl https://api.telegram.org/bot<TOKEN>/getUpdates
# → copy chat.id from response
# 4. Edit config.json → telegram.chat_id

python3 monitor.py --test        # connectivity check
python3 monitor.py --once        # single cycle test
python3 monitor.py --loop 180    # continuous (every 3 min)
```

Copy `config.json.example` to `config.json` and fill your credentials. Never commit `config.json` with real tokens.

Works on **Python 3.10+** — `requests` + `feedparser` only.

## Alert Format

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

Timestamps are in IST (Asia/Kolkata, 12-hour with AM/PM).

## Configuration (`config.json`)

- `min_priority`: `"high"` (default, hides INFO), `"all"` or `"critical"`
- `cve_min_score`: `9.0` → lower to `7.0` for more CVEs
- `interval_sec`: `180` (3 min polling)
- `max_age_days`: `3` (only last 3 days)
- `heartbeat_cycles`: `0` (disabled; set to N to send heartbeat every N cycles)
- `keywords`: customize critical/high/group lists

## Running — Cross-Platform

**Linux / macOS / WSL:**
```bash
nohup python3 monitor.py --loop 180 > logs/nohup.log 2>&1 &
```

**Windows (PowerShell):**
```powershell
python monitor.py --loop 180
# or for background:
Start-Process python -ArgumentList "monitor.py --loop 180" -WindowStyle Hidden
```

**Docker (any OS):**
```bash
docker-compose up -d
# or
docker build -t intel-monitor . && docker run -d --restart unless-stopped -v $PWD/data:/app/data -v $PWD/logs:/app/logs -v $PWD/config.json:/app/config.json:ro intel-monitor
```

**Systemd (VPS — Linux):**
```bash
sudo cp intel-monitor.service /etc/systemd/system/
sudo systemctl enable --now intel-monitor
sudo journalctl -u intel-monitor -f
```

**Cron (VPS — alternative):**
```bash
*/3 * * * * cd /opt/intel-monitor && python3 monitor.py --once >> logs/cron.log 2>&1
```

**Termux (Android):**
```bash
termux-wake-lock
nohup python3 monitor.py --loop 180 > logs/nohup.log 2>&1 &
# Boot auto-start: ~/.termux/boot/intelmon-boot.sh
# Widget: ~/.shortcuts/IntelMon-Status.sh → Home → Widgets → Termux
```

## Project Structure

```
intel-monitor/
├── monitor.py              # main engine (cross-platform)
├── config.json             # sources + keywords + creds (gitignored)
├── config.json.example     # template
├── requirements.txt        # pip deps
├── setup.sh                # cross-platform installer
├── Dockerfile              # Docker build
├── docker-compose.yml      # Docker Compose
├── intel-monitor.service   # systemd service
├── data/intel.db           # dedup store (SQLite)
└── logs/                   # monitor.log, nohup.log
```

## Requirements

- Python 3.10+
- `pip install -r requirements.txt` (requests, feedparser)

## License

MIT
