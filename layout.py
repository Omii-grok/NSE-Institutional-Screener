import streamlit as st

def render_header(title: str = "NSE Institutional Screener"):
    """Render a consistent header with title and optional subtitle."""
    st.markdown(f"""
    <div class='hdr'>
        <h1>{title}</h1>
        <p>Professional market data terminal</p>
    </div>
    """, unsafe_allow_html=True)

def render_sidebar():
    """Render sidebar branding and optional quick filters placeholder."""
    with st.sidebar:
        st.markdown("""
        <div class='sb-logo'>
            <div class='ic'>📈</div>
            <h2>NSE Screener</h2>
            <small>Institutional Dashboard</small>
        </div>
        """, unsafe_allow_html=True)
        st.empty()

def render_footer():
    """Render a simple footer with last updated timestamp placeholder."""
    st.markdown("<div style='text-align:center; color:#6b7280; margin-top:2rem;'>Last Updated: --</div>", unsafe_allow_html=True)
