# ORACLE-INTEL-MON — Threat Intelligence Monitor → Telegram

Real-time cybersecurity intelligence aggregator. Every new article, CVE, or victim is delivered to Telegram with source link and timestamp.

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

## Setup (5 minutes)

```bash
cd intel-monitor
bash setup.sh                    # installs: requests feedparser

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

## Running

**Termux (background):**
```bash
termux-wake-lock
nohup python3 monitor.py --loop 180 > logs/nohup.log 2>&1 &
```

**With Boot/Widget (no need to open Termux):**
- Boot: `~/.termux/boot/intelmon-boot.sh` auto-starts on device boot
- Widget: add `~/.shortcuts/IntelMon-Status.sh` via home screen → Widgets → Termux

**VPS (24/7):**
```bash
# cron every 3 min
*/3 * * * * cd /opt/intel-monitor && python3 monitor.py --once >> logs/cron.log 2>&1
```
Or systemd with `Restart=always` and `--loop 180`.

## Project Structure

```
intel-monitor/
├── monitor.py           # main engine
├── config.json          # sources + keywords + creds (gitignored)
├── config.json.example  # template
├── setup.sh             # installer
├── data/intel.db        # dedup store (SQLite)
└── logs/                # monitor.log, nohup.log
```

## Requirements

- Python 3.10+
- `pip install requests feedparser`

## License

MIT
