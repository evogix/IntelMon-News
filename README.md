# 🛰️ ORACLE-INTEL-MON — Full Internet Threat Monitor → Telegram

Real-time cybersecurity intel aggregator. Jo bhi naya hoga — Telegram pe alert milega source ke saath.

## Kya-Kya Monitor Hota Hai

| Source | Data | Priority |
|---|---|---|
| **Ransomware.live API** | Har naya ransomware victim (LockBit, Akira, Cl0p...) | 🔴 CRITICAL |
| **CISA KEV** | Actively-exploited CVEs (+ransomware campaign flag) | 🔴 CRITICAL |
| **NVD API** | Naye CVEs with CVSS ≥ 9.0 | 🔴 CRITICAL |
| **RSS Feeds** (8 sources) | Hacker News, BleepingComputer, Krebs, DarkReading, SecurityWeek, PortSwigger, r/netsec, GBHackers | Keyword-scored |
| **Exploit-DB** | Naye public exploits (last 48h) | 🟠 HIGH |

**Keyword engine:** title/summary scan → `0day/RCE/ransomware/APT/supply chain` = CRITICAL, `exploit/POC/bypass/breach` = HIGH, threat-group names (LockBit, Lazarus, Scattered Spider...) = CRITICAL.

## Setup (5 min)

```bash
cd intel-monitor
bash setup.sh                    # deps install
# 1. @BotFather → /newbot → token copy
# 2. config.json → telegram.bot_token
# 3. Bot ko DM bhejo, phir: curl api.telegram.org/bot<TOKEN>/getUpdates → chat.id
# 4. config.json → telegram.chat_id

python3 monitor.py --test        # ✅ connectivity check
python3 monitor.py --once        # single cycle test
python3 monitor.py --loop 600    # continuous — har 10 min poll
```

## Alert Format

```
🔴 CRITICAL 🚨 RANSOMWARE-VICTIM
Acme Logistics Ltd
• 🤖 Group: akira
• 🌍 Country: IN
• 📅 Discovered: 2026-08-24
• 🔗 Source: https://ransomware.live/...
• ⏰ 2026-08-24 14:32 UTC
```

```
🟠 HIGH 🚨 NEWS
New bypass technique disclosed for popular VPN appliance
• 📰 BleepingComputer
• 🎯 match: kw:bypass
• 🔗 Source: https://...
```

## Tuning (`config.json`)

- `min_priority`: `"high"` (default — INFO chhupata hai) ya `"all"` ya `"critical"`
- `cve_min_score`: `9.0` → kam karke `7.0` = zyada CVE alerts
- `keywords`: apne hisaab se add/remove karo
- `interval_sec` / `--loop 300`: har 5 min poll

## Background Run (Termux)

```bash
termux-wake-lock
nohup python3 monitor.py --loop 600 > logs/nohup.log 2>&1 &
```

## VPS Run (24/7 recommended)

```bash
*/10 * * * * cd /opt/intel-monitor && python3 monitor.py --once >> logs/cron.log 2>&1
```
Ya systemd: `Restart=always` ke saath `--loop 600`.

## Advanced Add-ons (next level)

1. **Hacker-group Telegram channels** — Telethon userbot se channels scrape karo (many groups announce via TG)
2. **Twitter/X** — Nitter RSS instances se @vxunderground etc.
3. **Zone-H defacements** — mirror archive polling for "hacked by" claims
4. **GitHub advisories** — GHSA GraphQL API
5. **Dark-web leak sites** — ransomware.live already covers; direct .onion needs Tor proxy + custom fetchers

## Files

```
intel-monitor/
├── monitor.py      # main engine
├── config.json     # sources + keywords + creds
├── setup.sh        # installer
├── data/intel.db   # dedup store (SQLite)
└── logs/           # monitor.log, cron.log
```

Dedup SQLite-based hai — same news dobara alert NAHI hogi. State persist hoti hai restarts ke across.
