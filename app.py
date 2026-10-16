import streamlit as st
import sys
import pathlib

# Add the original repo path to sys.path so we can import the existing screener module
repo_path = pathlib.Path(r"C:/Users/ompra/Desktop/NSE/repo_clone")
sys.path.append(str(repo_path))

# Import the existing screener script (its top‑level code runs on import)
import screener as original

# Load external CSS for a clean, maintainable style
with open(r"C:/Users/ompra/Desktop/NSE/New folder/style.css") as f:
    st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

# Render the original UI – the original script uses session_state to control views
# After the original rendering we add our new F&O Market button
if st.button("F&O Market", key="fno_btn"):
    import fno_dashboard
    fno_dashboard.render_fno_dashboard()
