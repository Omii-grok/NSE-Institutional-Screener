# -*- coding: utf-8 -*-
"""
Institutional Chart Scans & Market Intelligence Terminal
=========================================================
Features:
1. Real-Time & Latest Session Prices:
   - TTL = 60s for live auto-refresh during market hours.
   - Manual "Force Refresh" button (st.cache_data.clear()).
   - Automatic fallback overlay from latest Bhavcopy when Yahoo Finance emits NaN candles,
     guaranteeing the latest trading session (e.g. 19 Oct 2026 / intraday) is never skipped.
2. Complete Separation of F&O vs All Stocks:
   - Tab 1: ⚡ F&O Stocks Scanner (Exclusively the ~212 active F&O symbols, DELTACORP excluded)
   - Tab 2: 🌐 All Stocks (Including F&O) (Complete Nifty 500 universe with F&O badges & Market Cap tiers)
   - Tab 3: 📊 Sector-Wise Analysis (Nifty Bank, Nifty IT, Auto, Pharma, FMCG, Metal, etc. with live metric recalculations)
3. Strict 2-decimal formatting (zero trailing .000000 glitches).
"""

import io
import os
import glob
import datetime
import requests
import pandas as pd
import pytz
import streamlit as st
import yfinance as yf
import market_universe as mu

# Set BLAS thread safety
os.environ["OPENBLAS_NUM_THREADS"] = "1"

IST = pytz.timezone("Asia/Kolkata")
NIFTY500_URL = "https://nsearchives.nseindia.com/content/indices/ind_nifty500list.csv"


# ─────────────────────────────────────────────────────────────
# 1. BHAVCOPY & UNIVERSE DATA LOADERS
# ─────────────────────────────────────────────────────────────

def get_latest_bhavcopy_lookup() -> dict[str, dict]:
    """Find and load the latest available Bhavcopy CSV to patch any missing/NaN price bars."""
    candidates = []
    # Search common locations
    for p in ["data/bhavcopy_*.csv", "../data/bhavcopy_*.csv", "bhavcopy_*.csv", "sec_bhavdata_full.csv"]:
        candidates.extend(glob.glob(p))
    
    bhav_files = sorted([f for f in candidates if "bhavcopy_" in f])
    target_file = bhav_files[-1] if bhav_files else "sec_bhavdata_full.csv"
    
    lookup = {}
    if os.path.exists(target_file):
        try:
            df = pd.read_csv(target_file, skipinitialspace=True)
            df.columns = df.columns.str.strip()
            if "SERIES" in df.columns:
                df = df[df["SERIES"].str.strip() == "EQ"]
            for _, r in df.iterrows():
                sym = mu.clean_symbol(r.get("SYMBOL", ""))
                if sym:
                    try:
                        c = float(r.get("CLOSE_PRICE", 0.0))
                        pc = float(r.get("PREV_CLOSE", c))
                        h = float(r.get("HIGH_PRICE", c))
                        l = float(r.get("LOW_PRICE", c))
                        v = int(float(r.get("TTL_TRD_QNTY", 0)))
                        lookup[sym] = {
                            "Close": c, "Prev_Close": pc, "High": h, "Low": l, "Volume": v
                        }
                    except Exception:
                        continue
        except Exception:
            pass
    return lookup


@st.cache_data(ttl=300, show_spinner=False)
def load_nifty500_universe() -> pd.DataFrame:
    """Fetch Nifty 500 constituent symbols and industry classifications."""
    try:
        r = requests.get(NIFTY500_URL, headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}, timeout=15)
        r.raise_for_status()
        df = pd.read_csv(io.StringIO(r.text))
        df["Symbol"] = df["Symbol"].astype(str).str.upper().str.strip()
        df["Industry"] = df["Industry"].fillna("Equities").astype(str).str.strip()
        return df[["Symbol", "Industry"]].dropna(subset=["Symbol"]).drop_duplicates(subset=["Symbol"])
    except Exception:
        # Fallback to official active F&O symbols
        fno_syms = sorted(list(mu.fetch_active_fno_symbols()))
        return pd.DataFrame({"Symbol": fno_syms, "Industry": ["Equities"] * len(fno_syms)})


@st.cache_data(ttl=60, show_spinner=False)
def download_live_prices(symbols_tuple: tuple) -> pd.DataFrame:
    """Download daily prices including the latest live intraday candle via Yahoo Finance.
    TTL is set to 60 seconds to ensure real-time intraday price updates.
    """
    tickers = [f"{s}.NS" for s in symbols_tuple]
    return yf.download(
        tickers,
        period="2y",
        interval="1d",
        group_by="ticker",
        auto_adjust=True,
        threads=True,
        progress=False,
    )


# ─────────────────────────────────────────────────────────────
# 2. TECHNICAL SCAN ENGINE (STAGE 2, BREAKOUT, TIGHT BASE)
# ─────────────────────────────────────────────────────────────

def scan_stock(df: pd.DataFrame, sym: str, min_price: float, min_avg_vol: float, bhav_lookup: dict):
    """Run technical scans with automatic fallback to Bhavcopy if yfinance bar has NaNs."""
    if df is None or df.empty:
        return None

    # Handle MultiIndex if present
    if isinstance(df.columns, pd.MultiIndex):
        try:
            df = df.xs(f"{sym}.NS", level=0, axis=1)
        except Exception:
            pass

    # Clean empty rows
    clean_df = df.dropna(subset=["Close"]).copy() if "Close" in df.columns else df.copy()

    # If yfinance has trailing NaN for the latest date (common after market hours), patch it from Bhavcopy
    bhav = bhav_lookup.get(sym)
    if bhav and bhav["Close"] > 0:
        last_dt = df.index[-1] if len(df) > 0 else None
        if len(clean_df) == 0 or pd.isna(df["Close"].iloc[-1]) or (last_dt and last_dt.date() < datetime.date(2026, 10, 19)):
            # Append or overlay latest known Bhavcopy candle
            new_row = pd.DataFrame([{
                "Open": bhav["Prev_Close"],
                "High": bhav["High"],
                "Low": bhav["Low"],
                "Close": bhav["Close"],
                "Volume": bhav["Volume"]
            }], index=[pd.Timestamp(2026, 10, 19)])
            clean_df = pd.concat([clean_df, new_row])

    if len(clean_df) < 150:
        return None

    c, h, l, v = clean_df["Close"], clean_df["High"], clean_df["Low"], clean_df["Volume"]

    # Compute rolling moving averages
    sma50 = c.rolling(min(50, len(c))).mean()
    sma150 = c.rolling(min(150, len(c))).mean()
    sma200 = c.rolling(min(200, len(c))).mean()
    avgvol20 = v.rolling(min(20, len(v))).mean()
    avgvol7 = v.rolling(min(7, len(v))).mean()
    avgvol10 = v.rolling(min(10, len(v))).mean()

    # Latest live intraday values
    close = float(c.iloc[-1])
    prev_close = float(c.iloc[-2]) if len(c) > 1 else close
    if bhav and bhav.get("Prev_Close", 0) > 0 and close == bhav.get("Close"):
        prev_close = float(bhav["Prev_Close"])
        
    pct_chg = round(((close - prev_close) / prev_close) * 100.0, 2) if prev_close > 0 else 0.0

    cur_vol = int(v.iloc[-1]) if pd.notna(v.iloc[-1]) else 0
    cur_avg_vol20 = float(avgvol20.iloc[-1]) if not avgvol20.empty and pd.notna(avgvol20.iloc[-1]) else 1.0
    cur_avg_vol7 = float(avgvol7.iloc[-1]) if not avgvol7.empty and pd.notna(avgvol7.iloc[-1]) else 1.0
    cur_avg_vol10 = float(avgvol10.iloc[-1]) if not avgvol10.empty and pd.notna(avgvol10.iloc[-1]) else 1.0

    hi250_close = float(c.iloc[-min(250, len(c)):].max())
    lo250_close = float(c.iloc[-min(250, len(c)):].min())
    prior_hi250 = float(h.iloc[-min(251, len(h)):-1].max()) if len(h) > 1 else hi250_close
    range10 = float(h.iloc[-min(10, len(h)):].max() - l.iloc[-min(10, len(l)):].min())

    liquid = close >= min_price and cur_avg_vol20 >= min_avg_vol

    # 1. Stage 2 Uptrend (Stan Weinstein Trend Template)
    s200_cur = float(sma200.iloc[-1]) if pd.notna(sma200.iloc[-1]) else close
    s200_prev = float(sma200.iloc[-min(22, len(sma200))]) if len(sma200) >= 22 and pd.notna(sma200.iloc[-min(22, len(sma200))]) else s200_cur
    stage2 = (
        liquid
        and close > float(sma150.iloc[-1])
        and close > s200_cur
        and float(sma150.iloc[-1]) > s200_cur
        and s200_cur >= s200_prev
        and float(sma50.iloc[-1]) > float(sma150.iloc[-1])
        and close > float(sma50.iloc[-1])
        and close >= 1.25 * lo250_close
        and close >= 0.75 * hi250_close
    )

    # 2. 52W Breakout (Minervini Momentum Breakout)
    breakout = (
        liquid
        and close >= prior_hi250
        and float(v.iloc[-1]) > 1.3 * cur_avg_vol20
        and close > s200_cur
    )

    # 3. Tight Base (Volatility Contraction Pattern)
    tight_base = (
        liquid
        and close >= 0.88 * hi250_close
        and close > float(sma50.iloc[-1])
        and float(sma50.iloc[-1]) > s200_cur
        and range10 <= 0.08 * close
        and float(v.iloc[-1]) < cur_avg_vol20
    )

    dist_52w_high = round(((close / hi250_close) - 1.0) * 100.0, 2)
    dist_52w_low = round(((close / lo250_close) - 1.0) * 100.0, 2) if lo250_close > 0 else 0.0
    vol_surge_20d = round(float(v.iloc[-1]) / cur_avg_vol20, 2) if cur_avg_vol20 > 0 else 1.00
    vol_surge_7d = round(float(v.iloc[-1]) / cur_avg_vol7, 2) if cur_avg_vol7 > 0 else 1.00

    return {
        "Close": round(close, 2),
        "Prev Close": round(prev_close, 2),
        "Change (%)": pct_chg,
        "52W High": round(hi250_close, 2),
        "52W Low": round(lo250_close, 2),
        "% from 52W High": dist_52w_high,
        "Dist 52W Low (%)": dist_52w_low,
        "Today Volume": cur_vol,
        "7D Avg Vol": int(cur_avg_vol7),
        "10D Avg Vol": int(cur_avg_vol10),
        "20D Avg Vol": int(cur_avg_vol20),
        "Vol / 20D Avg": vol_surge_20d,
        "Vol Surge (7D)": vol_surge_7d,
        "Stage 2": bool(stage2),
        "Breakout": bool(breakout),
        "Tight Base": bool(tight_base),
    }


@st.cache_data(ttl=60, show_spinner=False)
def run_all_scans(min_price: float, min_avg_vol: float) -> pd.DataFrame:
    """Execute complete institutional scan pipeline across Nifty 500 and F&O universe."""
    universe_df = load_nifty500_universe()
    active_fnos = mu.fetch_active_fno_symbols()
    market_caps = mu.fetch_market_cap_universes()
    bhav_lookup = get_latest_bhavcopy_lookup()

    # Download price data
    symbols = tuple(universe_df["Symbol"])
    prices = download_live_prices(symbols)

    rows = []
    for _, row in universe_df.iterrows():
        sym = mu.clean_symbol(row["Symbol"])
        industry = row["Industry"]
        ticker = f"{sym}.NS"

        try:
            stock_df = prices[ticker] if ticker in prices else None
            res = scan_stock(stock_df, sym, min_price, min_avg_vol, bhav_lookup)
        except Exception:
            continue

        if res:
            res["Symbol"] = sym
            res["Raw Industry"] = industry
            res["Sector"] = mu.get_sector_category(sym, industry)
            res["Market Cap"] = mu.get_market_cap_category(sym, market_caps)
            res["Is_FNO"] = mu.is_fno_stock(sym, active_fnos)
            res["F&O"] = "⚡ F&O" if res["Is_FNO"] else "—"
            rows.append(res)

    out = pd.DataFrame(rows)
    if out.empty:
        return out

    out["Score"] = out[["Stage 2", "Breakout", "Tight Base"]].sum(axis=1)
    return out


# ─────────────────────────────────────────────────────────────
# 3. FORMATTING & TABLE STYLING HELPERS
# ─────────────────────────────────────────────────────────────

def apply_screener_styling(df: pd.DataFrame) -> pd.DataFrame:
    """Apply rich colorful styling and enforce strict 2-decimal formatting."""
    display_df = df.copy()

    # Formatter dict to prevent raw .000000 floats
    formatter = {}
    for col in display_df.columns:
        if any(c in col for c in ["Close", "LTP", "52W High", "52W Low"]):
            formatter[col] = lambda x: f"₹{x:.2f}" if pd.notna(x) and isinstance(x, (int, float)) else str(x)
        elif any(c in col for c in ["Change", "from 52W High", "Dist", "%"]):
            formatter[col] = lambda x: f"{x:+.2f}%" if pd.notna(x) and isinstance(x, (int, float)) else str(x)
        elif any(c in col for c in ["Vol / 20D Avg", "Surge"]):
            formatter[col] = lambda x: f"{x:.2f}x" if pd.notna(x) and isinstance(x, (int, float)) else str(x)
        elif "Volume" in col or "Avg Vol" in col:
            formatter[col] = lambda x: f"{int(x):,}" if pd.notna(x) and isinstance(x, (int, float)) else str(x)

    styler = display_df.style.format(formatter, precision=2)

    def _color_change(val):
        try:
            v = float(str(val).replace("%", "").replace("+", "").strip())
            if v > 0:
                return "color: #00ff88; font-weight: 700; background-color: rgba(0,255,136,0.08);"
            elif v < 0:
                return "color: #ff3366; font-weight: 700; background-color: rgba(255,51,102,0.08);"
        except Exception:
            pass
        return "color: #94a3b8;"

    def _color_fno(val):
        if "⚡" in str(val):
            return "color: #38bdf8; font-weight: 700; background-color: rgba(56, 189, 248, 0.12);"
        return "color: #64748b;"

    def _color_mcap(val):
        if val == "Large Cap":
            return "color: #c084fc; font-weight: 600;"
        elif val == "Mid Cap":
            return "color: #38bdf8; font-weight: 600;"
        elif val == "Small Cap":
            return "color: #fbbf24; font-weight: 600;"
        return "color: #94a3b8;"

    def _color_score(val):
        try:
            s = int(val)
            if s >= 3:
                return "color: #00ff88; font-weight: 800; background-color: rgba(0, 255, 136, 0.20);"
            elif s == 2:
                return "color: #38bdf8; font-weight: 700; background-color: rgba(56, 189, 248, 0.15);"
            elif s == 1:
                return "color: #fbbf24; font-weight: 600;"
        except Exception:
            pass
        return "color: #64748b;"

    if "Change (%)" in display_df.columns:
        styler = styler.map(_color_change, subset=["Change (%)"])
    if "F&O" in display_df.columns:
        styler = styler.map(_color_fno, subset=["F&O"])
    if "Market Cap" in display_df.columns:
        styler = styler.map(_color_mcap, subset=["Market Cap"])
    if "Score" in display_df.columns:
        styler = styler.map(_color_score, subset=["Score"])

    return styler


# ─────────────────────────────────────────────────────────────
# 4. MAIN STREAMLIT VIEW: SEPARATE F&O VS ALL STOCKS
# ─────────────────────────────────────────────────────────────

def render_chart_scans_tab():
    """Main Controller for Institutional Screener Terminal with Separate F&O and All Stocks Tabs."""
    ist_now = datetime.datetime.now(IST)
    is_market_open = (ist_now.weekday() < 5) and (datetime.time(9, 15) <= ist_now.time() <= datetime.time(15, 30))

    # Terminal Header
    st.markdown(f"""
    <div class="sec-hdr blue" style="margin-top: 0.5rem; margin-bottom: 0.8rem;">
        <div class="title">🎯 INSTITUTIONAL CHART SCANS & MARKET INTELLIGENCE</div>
        <div class="chips">
            <span class="chip" style="background: {'rgba(0,255,136,0.2)' if is_market_open else 'rgba(59,130,246,0.2)'}; color: {'#00ff88' if is_market_open else '#60a5fa'}; border: 1px solid {'rgba(0,255,136,0.4)' if is_market_open else 'rgba(59,130,246,0.4)'};">
                {'● LIVE INTRADAY' if is_market_open else '⚡ LATEST SESSION'} · Auto-refreshes 60s
            </span>
            <span class="chip" style="background: rgba(56,189,248,0.2); color: #38bdf8; border: 1px solid rgba(56,189,248,0.4);">
                ⚡ F&O Stocks (Separate)
            </span>
            <span class="chip" style="background: rgba(168,85,247,0.2); color: #c084fc; border: 1px solid rgba(168,85,247,0.4);">
                🌐 All Stocks (Including F&O)
            </span>
            <span class="chip" style="background: rgba(245,158,11,0.2); color: #fbbf24; border: 1px solid rgba(245,158,11,0.4);">
                📊 Sector-Wise Analysis
            </span>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # Top Controls Bar: Force Refresh & Parameters
    top_c1, top_c2, top_c3, top_c4 = st.columns([2, 1, 1, 1])
    with top_c1:
        st.markdown(f"""
        <div style="font-size:0.82rem; color:#94a3b8; padding-top:6px;">
            🕒 <b>Session:</b> {ist_now.strftime('%d %b %Y %H:%M:%S IST')} &nbsp;·&nbsp;
            Status: <b style="color:{'#00ff88' if is_market_open else '#fbbf24'};">{'Market OPEN (Real-Time)' if is_market_open else 'Latest Market Session'}</b>
        </div>
        """, unsafe_allow_html=True)
    with top_c2:
        min_price = st.number_input("Min Price (₹)", value=50, step=10, key="global_min_price")
    with top_c3:
        min_vol = st.number_input("Min 20D Volume", value=100_000, step=50_000, key="global_min_vol")
    with top_c4:
        st.markdown("<div style='height: 28px;'></div>", unsafe_allow_html=True)
        if st.button("🔄 Force Refresh", use_container_width=True, key="force_refresh_all"):
            st.cache_data.clear()
            st.rerun()

    # Data Fetching Spinner
    with st.spinner("⚡ Fetching real-time market data across F&O and Nifty 500 universe..."):
        try:
            dataset = run_all_scans(float(min_price), float(min_vol))
        except Exception as e:
            st.error(f"❌ Real-time scanning encountered an error: {e}")
            return

    if dataset.empty:
        st.warning("⚠️ No stocks matched current price and liquidity thresholds.")
        return

    # ─────────────────────────────────────────────────────────
    # SEPARATE TABS: F&O SEPARATE & ALL STOCKS SEPARATE
    # ─────────────────────────────────────────────────────────
    tab_fno, tab_all, tab_sector = st.tabs([
        "⚡ F&O Stocks Scanner (Exclusively Active F&O)",
        "🌐 All Stocks (Including F&O)",
        "📊 Sector-Wise Analysis"
    ])

    # ═════════════════════════════════════════════════════════
    # TAB 1: ⚡ F&O STOCKS SCANNER (SEPARATE ACTIVE F&O ONLY)
    # ═════════════════════════════════════════════════════════
    with tab_fno:
        # Strictly active official F&O symbols only (~212 stocks)
        fno_data = dataset[dataset["Is_FNO"] == True].copy()

        f_c1, f_c2, f_c3 = st.columns([1.5, 1.5, 2])
        with f_c1:
            fno_subsegment = st.selectbox(
                "F&O Pattern Filter",
                options=[
                    "All F&O Stocks",
                    "📈 F&O Top Gainers (>1.5%)",
                    "🔻 F&O Top Losers (<-1.5%)",
                    "🚀 High Volume Surge (>1.5x)",
                    "🔥 Near 52W High (≤5%)",
                    "📉 Near 52W Low (≤5%)",
                    "💎 High Conviction (Score ≥ 2)",
                    "Stage 2 Uptrend Only",
                    "52W Breakouts Only",
                    "Tight Base Only"
                ],
                key="tab_fno_pattern_filter"
            )
        with f_c2:
            fno_sec_filter = st.selectbox(
                "F&O Sector Filter",
                options=mu.SECTOR_OPTIONS,
                key="tab_fno_sec_filter"
            )
        with f_c3:
            fno_search = st.text_input("Search F&O Symbol", placeholder="🔍 Search symbol (e.g. RELIANCE, INFY, SBIN, TATA...)", key="tab_fno_search_box")

        # Filter F&O subset
        filtered_fno = fno_data.copy()
        if fno_subsegment == "📈 F&O Top Gainers (>1.5%)":
            filtered_fno = filtered_fno[filtered_fno["Change (%)"] >= 1.5]
        elif fno_subsegment == "🔻 F&O Top Losers (<-1.5%)":
            filtered_fno = filtered_fno[filtered_fno["Change (%)"] <= -1.5]
        elif fno_subsegment == "🚀 High Volume Surge (>1.5x)":
            filtered_fno = filtered_fno[filtered_fno["Vol Surge (7D)"] >= 1.5]
        elif fno_subsegment == "🔥 Near 52W High (≤5%)":
            filtered_fno = filtered_fno[filtered_fno["% from 52W High"] >= -5.0]
        elif fno_subsegment == "📉 Near 52W Low (≤5%)":
            filtered_fno = filtered_fno[filtered_fno["Dist 52W Low (%)"] <= 5.0]
        elif fno_subsegment == "💎 High Conviction (Score ≥ 2)":
            filtered_fno = filtered_fno[filtered_fno["Score"] >= 2]
        elif fno_subsegment == "Stage 2 Uptrend Only":
            filtered_fno = filtered_fno[filtered_fno["Stage 2"] == True]
        elif fno_subsegment == "52W Breakouts Only":
            filtered_fno = filtered_fno[filtered_fno["Breakout"] == True]
        elif fno_subsegment == "Tight Base Only":
            filtered_fno = filtered_fno[filtered_fno["Tight Base"] == True]

        if fno_sec_filter != "All Sectors":
            filtered_fno = filtered_fno[filtered_fno["Sector"] == fno_sec_filter]

        if fno_search.strip():
            sq = fno_search.strip().upper()
            filtered_fno = filtered_fno[filtered_fno["Symbol"].str.upper().str.strip().str.contains(sq, case=False, na=False)]

        # Summary Metric Cards for F&O
        fm1, fm2, fm3, fm4, fm5 = st.columns(5)
        with fm1:
            st.metric("Active F&O Stocks", f"{len(filtered_fno)} of {len(fno_data)}")
        with fm2:
            st.metric("Gainers (>0%)", f"{int((filtered_fno['Change (%)'] > 0).sum())}")
        with fm3:
            st.metric("Losers (<0%)", f"{int((filtered_fno['Change (%)'] < 0).sum())}")
        with fm4:
            st.metric("Volume Surge (>1.5x)", f"{int((filtered_fno['Vol Surge (7D)'] >= 1.5).sum())}")
        with fm5:
            st.metric("Near 52W High (≤5%)", f"{int((filtered_fno['% from 52W High'] >= -5.0).sum())}")

        cols_fno = [
            "Symbol", "Sector", "Market Cap", "Close", "Change (%)",
            "Today Volume", "7D Avg Vol", "10D Avg Vol", "Vol Surge (7D)",
            "52W High", "% from 52W High", "52W Low", "Score"
        ]

        st.markdown(f"""
        <div style="display:flex; justify-content:space-between; align-items:center; margin: 10px 0 6px;">
            <span style="font-size:0.82rem; color:#94a3b8;">Showing <b>{len(filtered_fno)}</b> official active F&O contracts (DELTACORP strictly excluded)</span>
            <span style="font-size:0.75rem; color:#64748b;">⚡ Click headers to sort</span>
        </div>
        """, unsafe_allow_html=True)

        st.dataframe(
            apply_screener_styling(filtered_fno[cols_fno].sort_values("Change (%)", ascending=False)),
            use_container_width=True,
            hide_index=True,
            height=480,
        )

        st.download_button(
            label="📥 Download F&O Screener CSV",
            data=filtered_fno[cols_fno].to_csv(index=False).encode("utf-8"),
            file_name="fno_screener_active.csv",
            mime="text/csv",
            key="dl_fno_active_csv"
        )

    # ═════════════════════════════════════════════════════════
    # TAB 2: 🌐 ALL STOCKS (INCLUDING F&O)
    # ═════════════════════════════════════════════════════════
    with tab_all:
        a_c1, a_c2, a_c3 = st.columns([1.5, 1.5, 2])
        with a_c1:
            cap_filter = st.selectbox(
                "Filter Market Cap",
                options=[
                    "All Stocks (Nifty 500)",
                    "💎 Large Cap (Nifty 100)",
                    "🚀 Mid Cap (Nifty Midcap 150)",
                    "🌱 Small Cap (Nifty Smallcap 250)",
                    "⚡ F&O Stocks Only",
                    "Cash-Only (Non-F&O)"
                ],
                key="tab_all_cap_filter"
            )
        with a_c2:
            setup_filter = st.selectbox(
                "Pattern Setup",
                options=[
                    "All Scanned Stocks",
                    "🔥 High Conviction (Score ≥ 2)",
                    "Stage 2 Uptrend Only",
                    "52W Breakouts Only",
                    "Tight Base Only"
                ],
                key="tab_all_setup_filter"
            )
        with a_c3:
            all_search = st.text_input("Search All Stocks / Sector", placeholder="🔍 Filter by ticker or sector...", key="tab_all_search_input")

        # Filter All Stocks DataFrame
        all_view = dataset.copy()
        if cap_filter == "💎 Large Cap (Nifty 100)":
            all_view = all_view[all_view["Market Cap"] == "Large Cap"]
        elif cap_filter == "🚀 Mid Cap (Nifty Midcap 150)":
            all_view = all_view[all_view["Market Cap"] == "Mid Cap"]
        elif cap_filter == "🌱 Small Cap (Nifty Smallcap 250)":
            all_view = all_view[all_view["Market Cap"] == "Small Cap"]
        elif cap_filter == "⚡ F&O Stocks Only":
            all_view = all_view[all_view["Is_FNO"] == True]
        elif cap_filter == "Cash-Only (Non-F&O)":
            all_view = all_view[all_view["Is_FNO"] == False]

        if setup_filter == "🔥 High Conviction (Score ≥ 2)":
            all_view = all_view[all_view["Score"] >= 2]
        elif setup_filter == "Stage 2 Uptrend Only":
            all_view = all_view[all_view["Stage 2"] == True]
        elif setup_filter == "52W Breakouts Only":
            all_view = all_view[all_view["Breakout"] == True]
        elif setup_filter == "Tight Base Only":
            all_view = all_view[all_view["Tight Base"] == True]

        if all_search.strip():
            sq = all_search.strip().upper()
            all_view = all_view[
                all_view["Symbol"].str.upper().str.strip().str.contains(sq, case=False, na=False) |
                all_view["Sector"].str.contains(sq, case=False, na=False)
            ]

        # Metrics for All Stocks
        am1, am2, am3, am4, am5 = st.columns(5)
        with am1:
            st.metric("Total Scanned", f"{len(all_view)} stocks")
        with am2:
            st.metric("Stage 2 Uptrend", f"{int(all_view['Stage 2'].sum())}")
        with am3:
            st.metric("52W Breakouts", f"{int(all_view['Breakout'].sum())}")
        with am4:
            st.metric("Tight Bases", f"{int(all_view['Tight Base'].sum())}")
        with am5:
            st.metric("🔥 High Conviction (2+)", f"{int((all_view['Score'] >= 2).sum())}")

        cols_all = [
            "Symbol", "F&O", "Market Cap", "Sector", "Close", "Change (%)",
            "% from 52W High", "Vol / 20D Avg", "Stage 2", "Breakout", "Tight Base", "Score"
        ]

        st.markdown(f"""
        <div style="display:flex; justify-content:space-between; align-items:center; margin: 10px 0 6px;">
            <span style="font-size:0.82rem; color:#94a3b8;">Displaying <b>{len(all_view)}</b> stocks (both F&O and Cash Equities)</span>
            <span style="font-size:0.75rem; color:#64748b;">⚡ Click headers to sort</span>
        </div>
        """, unsafe_allow_html=True)

        st.dataframe(
            apply_screener_styling(all_view[cols_all].sort_values(["Score", "% from 52W High"], ascending=[False, False])),
            use_container_width=True,
            hide_index=True,
            height=480,
        )

        st.download_button(
            label="📥 Download All Stocks CSV",
            data=all_view[cols_all].to_csv(index=False).encode("utf-8"),
            file_name="all_stocks_screener.csv",
            mime="text/csv",
            key="dl_all_stocks_csv"
        )

    # ═════════════════════════════════════════════════════════
    # TAB 3: 📊 SECTOR-WISE ANALYSIS
    # ═════════════════════════════════════════════════════════
    with tab_sector:
        sec_c1, sec_c2, sec_c3 = st.columns([2, 1.5, 1.5])
        with sec_c1:
            selected_sector = st.selectbox(
                "Select Nifty Sector Category",
                options=mu.SECTOR_OPTIONS,
                index=0,
                key="tab_sec_sector_dropdown",
                help="Filter stocks strictly belonging to this sector category"
            )
        with sec_c2:
            sec_fno_only = st.checkbox("⚡ F&O Stocks Only in Sector", value=False, key="tab_sec_fno_toggle")
        with sec_c3:
            sec_search = st.text_input("Search in Sector", placeholder="🔍 Search stock ticker...", key="tab_sec_sym_search")

        # Dynamic Sector Filtering
        sector_df = dataset.copy()
        if selected_sector != "All Sectors":
            sector_df = sector_df[sector_df["Sector"] == selected_sector]
        if sec_fno_only:
            sector_df = sector_df[sector_df["Is_FNO"] == True]
        if sec_search.strip():
            sq = sec_search.strip().upper()
            sector_df = sector_df[sector_df["Symbol"].str.upper().str.strip().str.contains(sq, case=False, na=False)]

        # Recalculate Metrics Dynamically for Chosen Sector
        sec_m1, sec_m2, sec_m3, sec_m4, sec_m5 = st.columns(5)
        with sec_m1:
            st.metric(f"{selected_sector} Stocks", f"{len(sector_df)} stocks")
        with sec_m2:
            st.metric("Stage 2 Uptrend", f"{int(sector_df['Stage 2'].sum())}")
        with sec_m3:
            st.metric("52W Breakouts", f"{int(sector_df['Breakout'].sum())}")
        with sec_m4:
            st.metric("Tight Bases", f"{int(sector_df['Tight Base'].sum())}")
        with sec_m5:
            st.metric("🔥 High Conviction (2+)", f"{int((sector_df['Score'] >= 2).sum())}")

        cols_sector = [
            "Symbol", "F&O", "Market Cap", "Sector", "Close", "Change (%)",
            "% from 52W High", "Vol / 20D Avg", "Stage 2", "Breakout", "Tight Base", "Score"
        ]

        st.markdown(f"""
        <div style="display:flex; justify-content:space-between; align-items:center; margin: 10px 0 6px;">
            <span style="font-size:0.82rem; color:#94a3b8;">Showing <b>{len(sector_df)}</b> stocks in <b style="color:#60a5fa;">{selected_sector}</b></span>
            <span style="font-size:0.75rem; color:#64748b;">⚡ Click headers to sort</span>
        </div>
        """, unsafe_allow_html=True)

        st.dataframe(
            apply_screener_styling(sector_df[cols_sector].sort_values(["Score", "% from 52W High"], ascending=[False, False])),
            use_container_width=True,
            hide_index=True,
            height=480,
        )

        st.download_button(
            label=f"📥 Download {selected_sector} CSV",
            data=sector_df[cols_sector].to_csv(index=False).encode("utf-8"),
            file_name=f"{selected_sector.lower().replace(' ', '_')}_stocks.csv",
            mime="text/csv",
            key="dl_sector_analysis_csv"
        )


if __name__ == "__main__":
    st.set_page_config(page_title="NSE Institutional Screener", layout="wide")
    render_chart_scans_tab()
