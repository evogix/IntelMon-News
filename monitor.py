#!/usr/bin/env python3
"""
IntelMon-News v1.0
Full-internet cybersecurity threat monitor -> Telegram alerts.
Sources: RSS news feeds | CISA KEV | NVD critical CVEs | Ransomware.live victims | Exploit-DB

Usage:
  python3 monitor.py --test          # send test message to Telegram
  python3 monitor.py --once          # single fetch cycle (for cron)
  python3 monitor.py --loop 600      # continuous mode, poll every 600s
"""

import sys, os, json, time, sqlite3, hashlib, html, re, argparse, logging
from datetime import datetime, timedelta, timezone
from concurrent.futures import ThreadPoolExecutor, as_completed

try:
    import requests
except ImportError:
    print("[!] pip install requests"); sys.exit(1)
try:
    import feedparser
except ImportError:
    feedparser = None
    print("[!] pip install feedparser  (RSS disabled until installed)")

BASE = os.path.dirname(os.path.abspath(__file__))
CFG = json.load(open(os.path.join(BASE, "config.json")))
DB = os.path.join(BASE, "data", "intel.db")
LOG = os.path.join(BASE, "logs", "monitor.log")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.FileHandler(LOG), logging.StreamHandler()],
)
log = logging.getLogger("intelmon")

UA = {"User-Agent": "Mozilla/5.0 (IntelMon; security-research)"}
TIMEOUT = 25

# ─────────────────────────── Timezone: IST ────────────────────────────────
try:
    from zoneinfo import ZoneInfo
    TZ = ZoneInfo("Asia/Kolkata")
except Exception:
    TZ = timezone(timedelta(hours=5, minutes=30))   # fallback: fixed +05:30

def now_str():
    return datetime.now(TZ).strftime("%d-%b-%Y %I:%M:%S %p IST")

# ─────────────────────────── DB (dedup + state) ───────────────────────────
def db():
    con = sqlite3.connect(DB)
    con.execute("""CREATE TABLE IF NOT EXISTS seen(
                     hash TEXT PRIMARY KEY, kind TEXT, title TEXT,
                     priority TEXT, ts TEXT)""")
    con.execute("""CREATE TABLE IF NOT EXISTS meta(
                     key TEXT PRIMARY KEY, value TEXT)""")
    return con

def is_seen(con, h):
    return con.execute("SELECT 1 FROM seen WHERE hash=?", (h,)).fetchone() is not None

def mark_seen(con, h, kind, title, prio):
    con.execute("INSERT OR IGNORE INTO seen VALUES(?,?,?,?,?)",
                (h, kind, title[:200], prio, datetime.now(timezone.utc).isoformat()))
    con.commit()

def get_meta(con, key, default):
    r = con.execute("SELECT value FROM meta WHERE key=?", (key,)).fetchone()
    if not r:
        return default
    try:
        return float(r[0])
    except ValueError:
        return default

def set_meta(con, key, val):
    con.execute("INSERT OR REPLACE INTO meta VALUES(?,?)", (key, str(val)))
    con.commit()

# ─────────────────────────── Scoring engine ──────────────────────────────
def score(text):
    t = text.lower()
    kw = CFG["keywords"]
    for g in kw["groups"]:
        if g in t: return "CRITICAL", f"threat-group:{g}"
    for k in kw["critical"]:
        # short keywords (rce/poc) substring se false positive: "percent" me "rce" na pakde
        if k in ("rce", "poc"):
            if re.search(r'\b' + re.escape(k) + r'\b', t):
                return "CRITICAL", f"kw:{k}"
        elif k in t:
            return "CRITICAL", f"kw:{k}"
    for k in kw["high"]:
        if k in ("rce", "poc"):
            if re.search(r'\b' + re.escape(k) + r'\b', t):
                return "HIGH", f"kw:{k}"
        elif k in t:
            return "HIGH", f"kw:{k}"
    return "INFO", ""

ICON = {"CRITICAL": "🔴 CRITICAL", "HIGH": "🟠 HIGH", "INFO": "🟡 INFO"}

def esc(s):  # telegram HTML escape
    s = html.escape(s or "", quote=False)
    return s[:900]

# ─────────────────────────── Telegram sender ─────────────────────────────
TG = "https://api.telegram.org/bot{}/{}".format(CFG["telegram"]["bot_token"], "{}")

def tg_send(text):
    """Send HTML text to Telegram; auto-chunks >4096 chars; retries on flood."""
    chunks = [text[i:i+3900] for i in range(0, len(text), 3900)] or ["(empty)"]
    ok = True
    for ch in chunks:
        for attempt in range(4):
            try:
                r = requests.post(TG.format("sendMessage"), data={
                    "chat_id": CFG["telegram"]["chat_id"],
                    "text": ch, "parse_mode": "HTML",
                    "disable_web_page_preview": "false",
                }, timeout=TIMEOUT).json()
                if r.get("ok"):
                    break
                # retry_after from Telegram rate-limit
                wait = r.get("parameters", {}).get("retry_after", 2 ** attempt * 2)
                log.warning(f"TG retry in {wait}s: {r.get('description')}")
                time.sleep(wait)
            except Exception as e:
                log.warning(f"TG error: {e}"); time.sleep(2 ** attempt)
        else:
            ok = False
        time.sleep(1.1)  # ~20 msg/min safe limit
    return ok

def is_similar_recent(con, title):
    # 12h me same story alag title se aaye to bhi duplicate samjho (Jaccard >0.6)
    try:
        norm = set(re.sub(r'\W+', ' ', title.lower()).split())
        if len(norm) < 4:
            return False
        rows = con.execute("SELECT title FROM seen WHERE ts > datetime('now','-12 hours')").fetchall()
        for (rt,) in rows:
            rnorm = set(re.sub(r'\W+', ' ', rt.lower()).split())
            if not rnorm:
                continue
            inter = len(norm & rnorm)
            union = len(norm | rnorm)
            if union and inter/union > 0.6:
                return True
    except Exception:
        pass
    return False

def alert(kind, prio, title, body_lines, link):
    body = "\n".join(f"• {esc(l)}" for l in body_lines)
    msg = (
        f'{ICON[prio]} 🚨 <b>{esc(kind)}</b>\n\n'
        f'<b>{esc(title)}</b>\n\n'
        f'{body}\n\n'
        f'🔗 <a href="{html.escape(link, quote=True)}">Source</a>\n\n'
        f'⏰ <code>{now_str()}</code>'
    )
    con = db()
    # dedup by normalized title (link alag ho to bhi same story = duplicate)
    norm_title = re.sub(r'\W+', ' ', title.lower()).strip()[:80]
    h = hashlib.sha256((kind + norm_title).encode()).hexdigest()
    if is_seen(con, h) or is_similar_recent(con, title):
        # mark seen bhi karo taaki dobara check na ho
        if not is_seen(con, h):
            mark_seen(con, h, kind, title, prio)
        return False
    if BOOTSTRAP:                        # first-ever cycle -> silent baseline
        mark_seen(con, h, kind, title, prio)
        log.info(f"[BASELINE] {kind}: {title[:70]}")
        return False
    if prio == "INFO" and CFG["min_priority"] in ("high", "critical"):
        mark_seen(con, h, kind, title, prio); return False   # skip but remember
    if prio == "HIGH" and CFG["min_priority"] == "critical":
        mark_seen(con, h, kind, title, prio); return False
    if tg_send(msg):
        mark_seen(con, h, kind, title, prio)
        global SENT_THIS_CYCLE
        SENT_THIS_CYCLE += 1
        log.info(f"[SENT] [{prio}] {kind}: {title[:80]}")
        return True
    log.error(f"[FAILED] {title[:80]}")
    return False

# ─────────────────────────── Source: RSS feeds ───────────────────────────
MAX_AGE_DAYS = int(CFG.get("max_age_days", 3))  # sirf latest 3 din ka news
def fetch_rss(con):
    """20-thread parallel fetch + date filter (only last 3 days) + seeding."""
    if not feedparser:
        return
    def _fetch_one(src):
        try:
            r = requests.get(src["url"], headers=UA, timeout=20)
            if r.status_code == 200 and r.content:
                return (src, r.content)
            log.warning(f"RSS {src['name']}: HTTP {r.status_code}")
            return (src, None)
        except Exception as ex:
            log.error(f"RSS {src['name']}: {ex}")
            return (src, None)
    srcs = CFG["sources"]["rss"]
    results = {}
    with ThreadPoolExecutor(max_workers=20) as ex:
        futs = {ex.submit(_fetch_one, s): s for s in srcs}
        for fut in as_completed(futs):
            src, content = fut.result()
            results[src["url"]] = (src, content)
    for src in srcs:  # config order preserve karo
        _, raw = results.get(src["url"], (src, None))
        if not raw:
            continue
        try:
            fp = feedparser.parse(raw)
            seedkey = f"rss_seeded::{src['url']}"
            seeded = get_meta(con, seedkey, 0)
            seeded_count = 0
            for e in fp.entries[:15]:
                title = e.get("title", "").strip()
                link = e.get("link", "")
                summary = re.sub(r"<[^>]+>", " ", e.get("summary", ""))[:400]
                if not title:
                    continue
                # date filter: only last MAX_AGE_DAYS (default 3) ka article
                pub = None
                try:
                    if getattr(e, 'published_parsed', None):
                        pub = datetime(*e.published_parsed[:6], tzinfo=timezone.utc)
                    elif getattr(e, 'updated_parsed', None):
                        pub = datetime(*e.updated_parsed[:6], tzinfo=timezone.utc)
                except Exception:
                    pub = None
                if pub and (datetime.now(timezone.utc) - pub).total_seconds() > MAX_AGE_DAYS*86400:
                    continue
                is_zoneh = "zone-h" in src["url"]
                if is_zoneh:
                    m = re.search(r'notified by\s+([^\s<]+)', e.get("summary",""), re.I)
                    hacker = m.group(1) if m else "unknown"
                    prio, kind, body = "CRITICAL", "ZONE-H DEFACEMENT", [f"\U0001F575 Hacked by: {hacker}"]
                else:
                    prio, hit = score(title + " " + summary)
                    kind, body = "NEWS", [f"\U0001F4F0 {src['name']}"]
                if not seeded:
                    if prio == "INFO":
                        norm = re.sub(r'\W+', ' ', title.lower()).strip()[:80]
                        h = hashlib.sha256((kind + norm).encode()).hexdigest()
                        if not is_seen(con, h):
                            mark_seen(con, h, kind, title, prio)
                            seeded_count += 1
                        continue
                    alert(kind, prio, title, body, link)
                    seeded_count += 1
                    continue
                alert(kind, prio, title, body, link)
            if not seeded:
                set_meta(con, seedkey, 1)
                log.info(f"[RSS SEEDED] {src['name']}: {seeded_count} items baselined")
        except Exception as ex:
            log.error(f"RSS parse {src['name']}: {ex}")

# ───────────── Source: CISA KEV (actively exploited CVEs) ────────────────
def fetch_kev(con):
    try:
        j = requests.get("https://www.cisa.gov/sites/default/files/feeds/"
                         "known_exploited_vulnerabilities.json",
                         headers=UA, timeout=TIMEOUT).json()
        for v in j.get("vulnerabilities", [])[-25:]:
            cve = v.get("cveID"); name = v.get("vulnerabilityName")
            ransom = v.get("knownRansomwareCampaignUse", "") == "Known"
            prio = "CRITICAL"
            alert("KEV-ACTIVE-EXPLOIT", prio,
                  f"{cve} — {name}",
                  [f"\U0001F3C6 CISA Known Exploited Vuln",
                   f"\U0001F462 Vendor: {v.get('vendorProject','?')} / {v.get('product','?')}",
                   *( ["\U0001F916 Used in RANSOMWARE campaigns!"] if ransom else [] ),
                   f"\U0001F4C5 Added: {v.get('dateAdded')}"],
                  f"https://nvd.nist.gov/vuln/detail/{cve}")
    except Exception as ex:
        log.error(f"KEV: {ex}")

# ───────────── Source: NVD (new high/critical CVEs) ──────────────────────
def fetch_nvd(con):
    """NVD API v2 rule: pubStartDate + pubEndDate REQUIRED TOGETHER (max 120d)."""
    last = get_meta(con, "nvd_last", time.time() - 86400)
    def iso(ts):
        return datetime.fromtimestamp(ts, timezone.utc) \
                       .strftime("%Y-%m-%dT%H:%M:%S.") + f"{ts%1*1000:03.0f}".zfill(3) + "+00:00"
    params = {
        "pubStartDate": iso(max(last, time.time() - 86400 * 2)),
        "pubEndDate":   iso(time.time()),
        "resultsPerPage": 50,
    }
    minscore = CFG.get("cve_min_score", 9.0)
    try:
        r = requests.get("https://services.nvd.nist.gov/rest/json/cves/2.0",
                         params=params, headers=UA, timeout=40)
        if r.status_code != 200 or not r.content.strip():
            log.warning(f"NVD skip: HTTP {r.status_code} empty={not r.content}")
            return
        j = r.json()
        set_meta(con, "nvd_last", time.time())
        for item in j.get("vulnerabilities", []):
            c = item["cve"]
            cid = c["id"]
            desc = next((d["value"] for d in c["descriptions"] if d["lang"] == "en"), "")
            metrics = c.get("metrics", {})
            cvss = None; vec = ""
            for keyname in ("cvssMetricV31", "cvssMetricV30", "cvssMetricV2"):
                if keyname in metrics:
                    d = metrics[keyname][0]["cvssData"]
                    if cvss is None or d["baseScore"] > cvss:
                        cvss = d["baseScore"]; vec = d.get("vectorString", "")
            if cvss is None or cvss < minscore:
                continue
            alert("NEW-CVE", "CRITICAL" if cvss >= 9 else "HIGH",
                  f"{cid} — CVSS {cvss}",
                  [f"\U0001F4DD {desc[:300]}",
                   f"\U0001F39A Vector: {vec}",
                   f"\u26A1 Severity: {'CRITICAL' if cvss>=9 else 'HIGH'}"],
                  f"https://nvd.nist.gov/vuln/detail/{cid}")
    except Exception as ex:
        log.error(f"NVD: {ex}")

# ───────────── Source: RansomWatch (fresh victims) ────────────────────────
def fetch_ransomware(con):
    """ransomwatch GitHub mirror — tracks all major leak-site groups.
    Bootstrap-safe: pehli baar sirf baseline set hota hai, alerts nahi jaate."""
    try:
        r = requests.get("https://raw.githubusercontent.com/joshhighet/ransomwatch/"
                         "main/posts.json", headers=UA, timeout=60)
        victims = r.json()
        def ts(x):  # '2020-01-12 00:00:00.000000' -> epoch
            try:
                return datetime.strptime(x["discovered"][:19],
                                         "%Y-%m-%d %H:%M:%S").timestamp()
            except Exception:
                return 0
        victims.sort(key=ts, reverse=True)
        newest = ts(victims[0]) if victims else time.time()
        last = get_meta(con, "rw_last", 0)
        set_meta(con, "rw_last", newest)
        if last == 0:
            log.info(f"RansomWatch baseline set: {len(victims)} victims, "
                     f"newest={victims[0]['discovered'][:10] if victims else '?'}")
            return                       # first run -> no alert flood
        fresh = [v for v in victims if ts(v) > last][:20]
        for v in fresh:
            group = v.get("group_name", "?")
            victim = v.get("post_title", "?")
            when = v.get("discovered", "?")[:16]
            alert("RANSOMWARE-VICTIM", "CRITICAL", f"{victim}",
                  [f"\U0001F916 Group: {group}",
                   f"\U0001F4C5 Discovered: {when}"],
                  "https://ransomwatch.telemetry.ltd/")
    except Exception as ex:
        log.error(f"RansomWatch: {ex}")

# ───────────── Source: Exploit-DB (new public exploits) ──────────────────
def fetch_exploitdb(con):
    try:
        txt = requests.get("https://gitlab.com/exploit-database/exploitdb/-/raw/main/"
                           "files_exploits.csv", headers=UA, timeout=60).text
        rows = txt.strip().split("\n")[1:]
        cutoff = (datetime.now(timezone.utc) - timedelta(days=2)).strftime("%Y-%m-%d")
        for line in reversed(rows):           # newest first (file is date-sorted)
            parts = line.split('","')
            if len(parts) < 5:
                continue
            eid, _, _, date_p, etype, platform, _desc = (parts + [""]*7)[:7]
            if date_p.strip('"') < cutoff:
                break
            eid = eid.strip('"')
            alert("EXPLOIT-PUBLISHED", "HIGH", f"{_desc.strip(chr(34))[:120]}",
                  [f"\U0001F9E9 Type: {etype}", f"\U0001F4BB Platform: {platform}"],
                  f"https://www.exploit-db.com/exploits/{eid}")
    except Exception as ex:
        log.error(f"ExploitDB: {ex}")

# ─────────────────────────── Main loop ───────────────────────────────────
BOOTSTRAP = False
CYCLE_COUNT = 0
SENT_THIS_CYCLE = 0

def cycle():
    global BOOTSTRAP, CYCLE_COUNT, SENT_THIS_CYCLE
    SENT_THIS_CYCLE = 0
    CYCLE_COUNT += 1
    con = db()
    BOOTSTRAP = not get_meta(con, "bootstrapped", 0)
    if BOOTSTRAP:
        log.info("BOOTSTRAP MODE: pehli cycle — sirf baseline, koi alert nahi")
    t0 = time.time()
    log.info("=== intel cycle start ===")
    if CFG["sources"].get("enable_ransomware"): fetch_ransomware(con)
    if CFG["sources"].get("enable_kev"):        fetch_kev(con)
    if CFG["sources"].get("enable_nvd"):        fetch_nvd(con)
    if CFG["sources"].get("enable_exploitdb"):  fetch_exploitdb(con)
    fetch_rss(con)
    set_meta(con, "bootstrapped", 1)
    n = con.execute("SELECT COUNT(*) FROM seen").fetchone()[0]
    log.info(f"=== cycle done in {time.time()-t0:.1f}s | total seen items: {n} ===")
    con.close()
    # Heartbeat: har N cycles pe ek "alive" ping jab tak koi alert nahi gaya ho
    hb = int(CFG.get("heartbeat_cycles", 0) or 0)
    if hb > 0 and not BOOTSTRAP and SENT_THIS_CYCLE == 0 and CYCLE_COUNT % hb == 0:
        tg_send(f"\U0001F493 IntelMon alive \u2014 cycle #{CYCLE_COUNT} \u00b7 "
                f"{n} items tracked \u00b7 is ghante mein 0 new alerts")
        log.info("[HEARTBEAT] sent")

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--once", action="store_true", help="single cycle (cron mode)")
    ap.add_argument("--loop", type=int, metavar="SEC", help="continuous mode")
    ap.add_argument("--test", action="store_true", help="send test alert")
    a = ap.parse_args()

    if a.test:
        ok = tg_send(f"\u2705 \U0001F916 <b>IntelMon-News online!</b>\nMonitoring: "
                     f"RSS \u00B7 KEV \u00B7 NVD \u00B7 Ransomware.live \u00B7 Exploit-DB\n"
                     f"min_priority={CFG['min_priority']} interval={CFG.get('interval_sec',600)}s")
        print("TEST OK" if ok else "TEST FAILED"); sys.exit(0)

    if a.loop:
        log.info(f"loop mode: every {a.loop}s — Ctrl+C to stop")
        while True:
            try: cycle()
            except Exception as e: log.exception(f"cycle crash: {e}")
            time.sleep(a.loop)
    else:
        cycle()
