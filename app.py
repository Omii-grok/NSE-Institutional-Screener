# -*- coding: utf-8 -*-
"""
Streamlit entry point wrapper.
Runs the main institutional screener application.
"""
import os
import sys
import pathlib

# Ensure current repository directory is on sys.path
root_dir = pathlib.Path(__file__).parent.resolve()
if str(root_dir) not in sys.path:
    sys.path.insert(0, str(root_dir))

# Execute screener main logic
import screener

if __name__ == "__main__":
    screener.main()
