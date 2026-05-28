"""
fetch_daily.py
==============
Called by GitHub Actions every weekday at 7 PM IST.
Downloads sec_bhavdata_full.csv from NSE Archives and saves it locally.
GitHub Actions then commits the file back to the repo.

Exit codes:
  0  — CSV downloaded successfully
  0  — No new data (weekend / holiday / file not yet uploaded) — NOT an error
  1  — Hard network / server failure after all retries
"""

import datetime
import sys
import requests
import pytz

# ─────────────────────────────────────────────────────────────
# CONFIG
# ─────────────────────────────────────────────────────────────
IST = pytz.timezone("Asia/Kolkata")

NSE_HOLIDAYS: set[datetime.date] = {
    # 2025
    datetime.date(2025, 1, 26), datetime.date(2025, 2, 26),
    datetime.date(2025, 3, 14), datetime.date(2025, 3, 31),
    datetime.date(2025, 4, 14), datetime.date(2025, 4, 18),
    datetime.date(2025, 5, 1),  datetime.date(2025, 8, 15),
    datetime.date(2025, 8, 27), datetime.date(2025, 10, 2),
    datetime.date(2025, 10, 20),datetime.date(2025, 10, 21),
    datetime.date(2025, 11, 5), datetime.date(2025, 12, 25),
    # 2026
    datetime.date(2026, 1, 26), datetime.date(2026, 3, 3),
    datetime.date(2026, 3, 20), datetime.date(2026, 4, 3),
    datetime.date(2026, 4, 14), datetime.date(2026, 5, 1),
    datetime.date(2026, 8, 15), datetime.date(2026, 9, 16),
    datetime.date(2026, 10, 2), datetime.date(2026, 10, 9),
    datetime.date(2026, 11, 9), datetime.date(2026, 12, 25),
}

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept":          "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
    "Accept-Encoding": "gzip, deflate, br",
    "Referer":         "https://www.nseindia.com/",
    "Connection":      "keep-alive",
}

OUTPUT_FILE = "sec_bhavdata_full.csv"
LOOKBACK_DAYS = 10       # How many past trading days to search
MIN_FILE_SIZE = 10_000   # Bytes — anything smaller is an error page


# ─────────────────────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────────────────────
def is_trading_day(d: datetime.date) -> bool:
    return d.weekday() < 5 and d not in NSE_HOLIDAYS


def warm_session() -> requests.Session:
    """Get NSE session cookies (required to bypass anti-bot)."""
    session = requests.Session()
    try:
        session.get("https://www.nseindia.com", headers=HEADERS, timeout=15)
        print("✅ NSE session cookies obtained")
    except Exception as e:
        print(f"⚠️  Cookie warm-up failed (will try anyway): {e}")
    return session


def try_download(session: requests.Session, d: datetime.date) -> bool:
    """Attempt to download bhavcopy for date d. Returns True on success."""
    date_str = d.strftime("%d%m%Y")
    url = (
        f"https://nsearchives.nseindia.com/products/content/"
        f"sec_bhavdata_full_{date_str}.csv"
    )
    print(f"🔽 Trying: {url}")

    try:
        resp = session.get(url, headers=HEADERS, timeout=45)
        print(f"   HTTP {resp.status_code} | Size: {len(resp.content):,} bytes")

        if resp.status_code == 200 and len(resp.content) > MIN_FILE_SIZE:
            with open(OUTPUT_FILE, "wb") as f:
                f.write(resp.content)
            print(f"✅ Saved {OUTPUT_FILE} ({len(resp.content):,} bytes) for {d}")
            return True
        else:
            print(f"   ⚠️  File too small or bad status — skipping")
    except Exception as e:
        print(f"   ❌ Request error: {e}")

    return False


# ─────────────────────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────────────────────
def main() -> None:
    now_ist  = datetime.datetime.now(IST)
    today    = now_ist.date()
    weekday  = today.strftime("%A")

    print(f"\n{'='*60}")
    print(f"  NSE Bhavcopy Downloader")
    print(f"  IST Time : {now_ist.strftime('%Y-%m-%d %H:%M:%S %Z')}")
    print(f"  Today    : {today} ({weekday})")
    print(f"{'='*60}\n")

    session = warm_session()
    found   = 0

    for offset in range(LOOKBACK_DAYS):
        candidate = today - datetime.timedelta(days=offset)

        if not is_trading_day(candidate):
            reason = "weekend" if candidate.weekday() >= 5 else "holiday"
            print(f"⏭️  Skipping {candidate} ({reason})")
            continue

        if try_download(session, candidate):
            found = offset  # 0 = today, 1 = yesterday, etc.
            break
        else:
            print(f"   File not available for {candidate} yet\n")

    if found == 0 and try_download.__name__:  # check if file was actually written
        import pathlib
        if pathlib.Path(OUTPUT_FILE).exists():
            size = pathlib.Path(OUTPUT_FILE).stat().st_size
            if size > MIN_FILE_SIZE:
                print(f"\n🎉 Download complete! File size: {size:,} bytes")
                print(f"   GitHub Actions will now commit to the repo.\n")
                sys.exit(0)

    # Recheck if file was saved from any iteration
    import pathlib
    csv_path = pathlib.Path(OUTPUT_FILE)
    if csv_path.exists() and csv_path.stat().st_size > MIN_FILE_SIZE:
        print(f"\n🎉 Download complete! File size: {csv_path.stat().st_size:,} bytes")
        sys.exit(0)

    # If today is weekend / holiday, exit cleanly (not an error)
    if not is_trading_day(today):
        print(f"\n✅ Today ({today}) is a non-trading day. Nothing to download. Exiting cleanly.")
        sys.exit(0)

    # Genuine failure
    print(f"\n🚨 FAILED: Could not download NSE data for any of the last {LOOKBACK_DAYS} days.")
    print("   NSE servers may be temporarily unavailable.")
    sys.exit(1)


if __name__ == "__main__":
    main()
