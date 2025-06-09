#!/bin/bash
cd "$(dirname "$0")/app"
source ../venv/bin/activate 2>/dev/null || echo "Consider activating your venv manually."
streamlit run location_take_home_pay_app.py
