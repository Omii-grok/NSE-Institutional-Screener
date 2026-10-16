# -*- coding: utf-8 -*-
"""
F&O Market Dashboard Module
Institutional derivative metrics, top movers, and delivery surges.
"""
import streamlit as st
import pandas as pd

def render_fno_dashboard(fno_df: pd.DataFrame | None = None):
    st.markdown("""
    <div class="sec-hdr blue" style="margin-top: 1.5rem;">
        <div class="title">📊 F&O MARKET DASHBOARD</div>
        <div class="chips">
            <span class="chip">~182 F&O Stocks</span>
            <span class="chip">Derivative Market Movers</span>
            <span class="chip">Institutional Delivery</span>
        </div>
    </div>
    """, unsafe_allow_html=True)

    if fno_df is None or fno_df.empty:
        st.info("No F&O data available for this session.")
        return

    # Key F&O summary statistics
    total_fno = len(fno_df)
    gainers = len(fno_df[fno_df["Change (%)"] > 0]) if "Change (%)" in fno_df.columns else 0
    losers = len(fno_df[fno_df["Change (%)"] < 0]) if "Change (%)" in fno_df.columns else 0
    high_deliv = len(fno_df[fno_df["Delivery (%)"] >= 50]) if "Delivery (%)" in fno_df.columns else 0

    m1, m2, m3, m4 = st.columns(4)
    with m1:
        st.metric("Total F&O Stocks", total_fno)
    with m2:
        st.metric("F&O Gainers", gainers, delta=f"+{gainers}" if gainers > 0 else None)
    with m3:
        st.metric("F&O Losers", losers, delta=f"-{losers}" if losers > 0 else None, delta_color="inverse")
    with m4:
        st.metric("High Delivery (≥50%)", high_deliv)

    # Sub-tabs for detailed F&O breakdown
    tab_all, tab_gainers, tab_losers, tab_delivery = st.tabs([
        "📋 All F&O Stocks",
        "🚀 Top Gainers",
        "🔻 Top Losers",
        "📦 High Delivery Volume"
    ])

    with tab_all:
        search = st.text_input("Filter symbol", placeholder="Type symbol (e.g. RELIANCE, INFY, SBIN)...", key="fno_dash_search")
        disp = fno_df
        if search.strip():
            disp = disp[disp["Symbol"].str.contains(search.strip().upper(), case=False, na=False)]
        st.dataframe(disp, use_container_width=True, hide_index=True, height=450)

    with tab_gainers:
        if "Change (%)" in fno_df.columns:
            top_gainers = fno_df.sort_values(by="Change (%)", ascending=False).head(20)
            st.dataframe(top_gainers, use_container_width=True, hide_index=True, height=450)

    with tab_losers:
        if "Change (%)" in fno_df.columns:
            top_losers = fno_df.sort_values(by="Change (%)", ascending=True).head(20)
            st.dataframe(top_losers, use_container_width=True, hide_index=True, height=450)

    with tab_delivery:
        if "Delivery (%)" in fno_df.columns:
            top_deliv = fno_df.sort_values(by="Delivery (%)", ascending=False).head(20)
            st.dataframe(top_deliv, use_container_width=True, hide_index=True, height=450)
