"""
fetch_daily.py
==============
Run by GitHub Actions every weekday at 7 PM IST.
Downloads the latest NSE sec_bhavdata_full.csv and saves it locally
so Streamlit Cloud can read it even if NSE blocks the live fetch.
"""

import datetime
import sys
import requests
import pytz

IST = pytz.timezone("Asia/Kolkata")

NSE_HOLIDAYS = {
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
    "Referer":         "https://www.nseindia.com/",
}


def is_trading_day(d: datetime.date) -> bool:
    return d.weekday() < 5 and d not in NSE_HOLIDAYS


def main() -> None:
    today = datetime.datetime.now(IST).date()

    # Warm up session cookies (NSE anti-bot)
    session = requests.Session()
    try:
        session.get("https://www.nseindia.com", headers=HEADERS, timeout=15)
        print("✅ NSE session warmed up")
    except Exception as e:
        print(f"⚠️  Cookie warm-up failed: {e}")

    # Walk backwards to find the most recent trading day with available data
    for offset in range(10):
        candidate = today - datetime.timedelta(days=offset)
        if not is_trading_day(candidate):
            print(f"⏭  Skipping {candidate} (weekend or holiday)")
            continue

        date_str = candidate.strftime("%d%m%Y")
        url = (
            f"https://nsearchives.nseindia.com/products/content/"
            f"sec_bhavdata_full_{date_str}.csv"
        )
        print(f"🔽 Trying {url}")

        try:
            resp = session.get(url, headers=HEADERS, timeout=30)
            if resp.status_code == 200 and len(resp.content) > 10_000:
                with open("sec_bhavdata_full.csv", "wb") as f:
                    f.write(resp.content)
                print(
                    f"✅ Saved sec_bhavdata_full.csv "
                    f"({len(resp.content):,} bytes) for {candidate}"
                )
                sys.exit(0)
            else:
                print(
                    f"❌ Got HTTP {resp.status_code}, "
                    f"size={len(resp.content)} — skipping"
                )
        except Exception as e:
            print(f"❌ Request failed for {candidate}: {e}")

    print("🚨 Could not download NSE data for any of the last 10 days.")
    sys.exit(1)


if __name__ == "__main__":
    main()
