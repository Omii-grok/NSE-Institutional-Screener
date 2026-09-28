"""
Drop-in Streamlit module: institutional chart scans on the Nifty 500.

Usage in your existing app:
    from scanner_tab import render_chart_scans_tab
    ...
    with tab_scans:            # or a page / sidebar option
        render_chart_scans_tab()

Requires: pip install streamlit yfinance pandas requests
"""
import io

import pandas as pd
import requests
import streamlit as st
import yfinance as yf

NIFTY500_URL = "https://nsearchives.nseindia.com/content/indices/ind_nifty500list.csv"


# ---------- data ----------
@st.cache_data(ttl=24 * 3600, show_spinner=False)
def load_universe() -> pd.DataFrame:
    r = requests.get(NIFTY500_URL, headers={"User-Agent": "Mozilla/5.0"}, timeout=20)
    r.raise_for_status()
    df = pd.read_csv(io.StringIO(r.text))
    return df[["Symbol", "Industry"]].dropna(subset=["Symbol"])


@st.cache_data(ttl=3600, show_spinner=False)
def download_prices(symbols: tuple) -> pd.DataFrame:
    tickers = [f"{s}.NS" for s in symbols]
    return yf.download(
        tickers, period="2y", interval="1d", group_by="ticker",
        auto_adjust=True, threads=True, progress=False,
    )


# ---------- scan logic ----------
def scan_stock(df: pd.DataFrame, min_price: float, min_avg_vol: float):
    df = df.dropna()
    if len(df) < 260:
        return None

    c, h, l, v = df["Close"], df["High"], df["Low"], df["Volume"]
    sma50, sma150, sma200 = c.rolling(50).mean(), c.rolling(150).mean(), c.rolling(200).mean()
    avgvol = v.rolling(20).mean()

    close = c.iloc[-1]
    hi250_close = c.iloc[-250:].max()
    lo250_close = c.iloc[-250:].min()
    prior_hi250 = h.iloc[-251:-1].max()
    range10 = h.iloc[-10:].max() - l.iloc[-10:].min()

    liquid = close > min_price and avgvol.iloc[-1] > min_avg_vol

    stage2 = (
        liquid
        and close > sma150.iloc[-1]
        and close > sma200.iloc[-1]
        and sma150.iloc[-1] > sma200.iloc[-1]
        and sma200.iloc[-1] > sma200.iloc[-22]
        and sma50.iloc[-1] > sma150.iloc[-1]
        and close > sma50.iloc[-1]
        and close >= 1.3 * lo250_close
        and close >= 0.75 * hi250_close
    )
    breakout = (
        liquid
        and close > prior_hi250
        and v.iloc[-1] > 1.5 * avgvol.iloc[-1]
        and close > sma200.iloc[-1]
    )
    tight_base = (
        liquid
        and close >= 0.90 * hi250_close
        and close > sma50.iloc[-1]
        and sma50.iloc[-1] > sma200.iloc[-1]
        and range10 < 0.08 * close
        and v.iloc[-1] < avgvol.iloc[-1]
    )

    return {
        "Close": round(float(close), 2),
        "% from 52W High": round((close / hi250_close - 1) * 100, 1),
        "Vol / 20D Avg": round(float(v.iloc[-1] / avgvol.iloc[-1]), 2),
        "Stage 2": bool(stage2),
        "Breakout": bool(breakout),
        "Tight Base": bool(tight_base),
    }


@st.cache_data(ttl=3600, show_spinner=False)
def run_scans(min_price: float, min_avg_vol: float) -> pd.DataFrame:
    uni = load_universe()
    data = download_prices(tuple(uni["Symbol"]))
    rows = []
    for sym, industry in zip(uni["Symbol"], uni["Industry"]):
        try:
            res = scan_stock(data[f"{sym}.NS"], min_price, min_avg_vol)
        except Exception:
            continue
        if res:
            res["Symbol"] = sym
            res["Industry"] = industry
            rows.append(res)
    out = pd.DataFrame(rows)
    if out.empty:
        return out
    out["Score"] = out[["Stage 2", "Breakout", "Tight Base"]].sum(axis=1)
    cols = ["Symbol", "Industry", "Close", "% from 52W High", "Vol / 20D Avg",
            "Stage 2", "Breakout", "Tight Base", "Score"]
    return out[cols]


# ---------- UI ----------
def render_chart_scans_tab():
    st.subheader("Institutional Chart Scans (Nifty 500)")

    c1, c2, c3 = st.columns([1, 1, 1])
    min_price = c1.number_input("Min price (Rs)", value=100, step=10)
    min_avg_vol = c2.number_input("Min 20D avg volume", value=300_000, step=50_000)
    if c3.button("Refresh data", use_container_width=True):
        st.cache_data.clear()

    with st.spinner("Downloading prices and running scans (first run takes 1-2 min)..."):
        try:
            results = run_scans(float(min_price), float(min_avg_vol))
        except Exception as e:
            st.error(f"Scan failed: {e}")
            return

    if results.empty:
        st.warning("No data returned.")
        return

    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Stage 2 Uptrend", int(results["Stage 2"].sum()))
    m2.metric("52W Breakout", int(results["Breakout"].sum()))
    m3.metric("Tight Base", int(results["Tight Base"].sum()))
    m4.metric("High conviction (2+)", int((results["Score"] >= 2).sum()))

    t_top, t1, t2, t3 = st.tabs(["High Conviction", "Stage 2", "Breakout", "Tight Base"])

    def show(df, key):
        df = df.sort_values(["Score", "% from 52W High"], ascending=[False, False])
        st.dataframe(df, use_container_width=True, hide_index=True)
        st.download_button(
            "Download CSV", df.to_csv(index=False).encode(),
            file_name=f"{key}.csv", mime="text/csv", key=f"dl_{key}",
        )

    with t_top:
        show(results[results["Score"] >= 2], "high_conviction")
    with t1:
        show(results[results["Stage 2"]], "stage2")
    with t2:
        show(results[results["Breakout"]], "breakout")
    with t3:
        show(results[results["Tight Base"]], "tight_base")


if __name__ == "__main__":
    st.set_page_config(page_title="NSE Institutional Scanner", layout="wide")
    render_chart_scans_tab()
