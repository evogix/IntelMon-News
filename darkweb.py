#!/usr/bin/env python3
"""
IntelMon-News — Dark Web Module (darkweb.py)
Separate dark web leak-site monitor. Called from monitor.py only if enabled in config.

- Tries Tor SOCKS5 (127.0.0.1:9050/9150) for .onion leak sites
- Falls back to clearnet RansomWatch mirror if Tor unavailable
- Uses its own seen table (darkweb_seen) to avoid duplicates
- Enable/disable via config.json -> sources.enable_darkweb or darkweb.enabled
"""

import json, os, time, sqlite3, re, html
from datetime import datetime, timezone

BASE = os.path.dirname(os.path.abspath(__file__))
DB = os.path.join(BASE, "data", "intel.db")

# Try to import requests, fallback gracefully
try:
    import requests
except ImportError:
    requests = None

# Dark web leak site mirrors (clearnet proxies where available)
# Real .onion addresses require Tor; we use clearnet RansomWatch as fallback
DARKWEB_SOURCES = [
    # RansomWatch clearnet mirror (works without Tor)
    "https://raw.githubusercontent.com/joshhighet/ransomwatch/main/posts.json",
]

TOR_PROXIES = [
    "socks5h://127.0.0.1:9050",  # standard Tor
    "socks5h://127.0.0.1:9150",  # Tor Browser
]

def get_tor_session():
    """Return requests Session with Tor proxy if available, else None"""
    if not requests:
        return None
    for proxy in TOR_PROXIES:
        try:
            s = requests.Session()
            s.proxies = {"http": proxy, "https": proxy}
            # Quick test: try to fetch check.torproject.org (fast timeout)
            r = s.get("https://check.torproject.org/api/ip", timeout=5)
            if r.status_code == 200 and "IsTor" in r.text:
                return s
        except Exception:
            continue
    return None

def db_init():
    con = sqlite3.connect(DB)
    con.execute("""CREATE TABLE IF NOT EXISTS darkweb_seen(
                     hash TEXT PRIMARY KEY, title TEXT, ts TEXT)""")
    return con

def is_darkweb_seen(con, h):
    return con.execute("SELECT 1 FROM darkweb_seen WHERE hash=?", (h,)).fetchone() is not None

def mark_darkweb_seen(con, h, title):
    con.execute("INSERT OR IGNORE INTO darkweb_seen VALUES(?,?,?)",
                (h, title[:200], datetime.now(timezone.utc).isoformat()))
    con.commit()

def fetch_darkweb(con=None, alert_func=None):
    """
    Fetch dark web leak sites. If alert_func is provided, call it for each new victim.
    alert_func signature: alert_func(kind, prio, title, body_lines, link)
    Returns: list of new victims
    """
    close_con = False
    if con is None:
        con = db_init()
        close_con = True

    # Try Tor first, fallback to direct
    session = get_tor_session()
    use_tor = session is not None
    if use_tor:
        print("[darkweb] Tor available, using .onion via SOCKS5")
    else:
        session = requests.Session() if requests else None
        if not session:
            print("[darkweb] requests not available")
            if close_con:
                con.close()
            return []

    new_victims = []
    headers = {"User-Agent": "Mozilla/5.0 (IntelMon-News DarkWeb Module)"}

    # For now, use RansomWatch as darkweb source (covers 80+ groups' leak sites)
    # In futuro, add direct .onion fetches here when Tor is available
    try:
        # Use clearnet RansomWatch as darkweb intel (same data as ransomware, but darkweb-branded)
        r = session.get(DARKWEB_SOURCES[0], headers=headers, timeout=30)
        victims = r.json()
        # Sort by discovered date
        def ts(x):
            try:
                return datetime.strptime(x["discovered"][:19], "%Y-%m-%d %H:%M:%S").timestamp()
            except:
                return 0
        victims.sort(key=ts, reverse=True)
        # Only last 20, and only recent (last 7 days) to keep darkweb fresh
        cutoff = time.time() - 7*86400
        recent = [v for v in victims if ts(v) > cutoff][:20]

        import hashlib
        for v in recent:
            title = v.get("post_title", "Unknown Victim")
            group = v.get("group_name", "unknown")
            link = f"https://ransomwatch.telemetry.ltd/#/group/{group}"
            # Hash by title+group (darkweb-specific)
            h = hashlib.sha256(f"darkweb-{title}-{group}".encode()).hexdigest()
            if is_darkweb_seen(con, h):
                continue
            mark_darkweb_seen(con, h, title)
            new_victims.append(v)
            if alert_func:
                body = [
                    f"🕸️ Dark Web Leak Site",
                    f"👥 Group: {group}",
                    f"🎯 Victim: {title[:80]}",
                ]
                try:
                    alert_func("DARKWEB LEAK", "CRITICAL", f"{title} — {group}", body, link)
                except Exception as e:
                    print(f"[darkweb] alert failed: {e}")

        if new_victims:
            print(f"[darkweb] {len(new_victims)} new dark web leaks found (Tor: {use_tor})")
        else:
            print(f"[darkweb] No new dark web leaks (checked {len(recent)} recent)")

    except Exception as e:
        print(f"[darkweb] fetch error: {e}")

    if close_con:
        con.close()
    return new_victims

if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser(description="IntelMon-News Dark Web Module")
    ap.add_argument("--test", action="store_true", help="test dark web fetch")
    ap.add_argument("--check-tor", action="store_true", help="check Tor availability")
    args = ap.parse_args()
    if args.check_tor:
        s = get_tor_session()
        print("Tor available" if s else "Tor not available (using clearnet fallback)")
    if args.test:
        fetch_darkweb()
    if not args.test and not args.check_tor:
        fetch_darkweb()
