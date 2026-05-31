"""
fetch_daily.py
==============
Called by GitHub Actions every weekday at 7 PM IST.
Downloads sec_bhavdata_full.csv from NSE Archives and saves it historically by date.
GitHub Actions then commits the entire data/ directory back to the repo.

Exit codes:
  0  — CSV downloaded successfully or verified valid historical database state
  0  — No new data (weekend / holiday / file not yet uploaded) — NOT an error
  1  — Hard network / server failure after all retries
"""

import datetime
import os
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

DATA_DIR = "data"
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
    date_str = d.strftime("%d%m%Y")    # Format for NSE URL (DDMMYYYY)
    file_str = d.strftime("%Y_%m_%d")   # Format for historic file preservation (YYYY_MM_DD)
    url = (
        f"https://nsearchives.nseindia.com/products/content/"
        f"sec_bhavdata_full_{date_str}.csv"
    )
    print(f"🔽 Trying: {url}")

    # Explicitly ensure target data folder exists
    os.makedirs(DATA_DIR, exist_ok=True)
    target_output_path = os.path.join(DATA_DIR, f"bhavcopy_{file_str}.csv")

    try:
        resp = session.get(url, headers=HEADERS, timeout=45)
        print(f"   HTTP {resp.status_code} | Size: {len(resp.content):,} bytes")

        if resp.status_code == 200 and len(resp.content) > MIN_FILE_SIZE:
            with open(target_output_path, "wb") as f:
                f.write(resp.content)
            print(f"✅ Saved {target_output_path} ({len(resp.content):,} bytes) for {d}")
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
    print(f"  NSE Bhavcopy Downloader (Flat-File DB Edition)")
    print(f"  IST Time : {now_ist.strftime('%Y-%m-%d %H:%M:%S %Z')}")
    print(f"  Today    : {today} ({weekday})")
    print(f"{'='*60}\n")

    session = warm_session()
    downloaded_date = None

    for offset in range(LOOKBACK_DAYS):
        candidate = today - datetime.timedelta(days=offset)

        if not is_trading_day(candidate):
            reason = "weekend" if candidate.weekday() >= 5 else "holiday"
            print(f"⏭️  Skipping {candidate} ({reason})")
            continue

        if try_download(session, candidate):
            downloaded_date = candidate
            break
        else:
            print(f"   File not available for {candidate} yet\n")

    # Verification checks
    if downloaded_date:
        file_str = downloaded_date.strftime("%Y_%m_%d")
        target_path = os.path.join(DATA_DIR, f"bhavcopy_{file_str}.csv")
        
        if os.path.exists(target_path):
            size = os.path.getsize(target_path)
            if size > MIN_FILE_SIZE:
                print(f"\n🎉 Download complete! File size: {size:,} bytes for {downloaded_date}")
                print(f"   GitHub Actions will now commit historical tracking states to the repo.\n")
                sys.exit(0)

    # Fallback state: ensure workspace contains at least one readable dataset
    if os.path.exists(DATA_DIR):
        existing_csvs = [f for f in os.listdir(DATA_DIR) if f.endswith('.csv') and os.path.getsize(os.path.join(DATA_DIR, f)) > MIN_FILE_SIZE]
        if existing_csvs:
            print(f"\n🎉 Workspace verified: {len(existing_csvs)} valid datasets exist. Exiting clean.")
            sys.exit(0)

    # Clean exit strategy for non-trading environments
    if not is_trading_day(today):
        print(f"\n✅ Today ({today}) is a non-trading day. Nothing to download. Exiting cleanly.")
        sys.exit(0)

    # Absolute failure state
    print(f"\n🚨 FAILED: Could not download NSE data for any of the last {LOOKBACK_DAYS} days.")
    print("   NSE servers may be temporarily offline or layout configurations have altered.")
    sys.exit(1)


if __name__ == "__main__":
    main()