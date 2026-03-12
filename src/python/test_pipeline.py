import os
import sys

# Ensure the local modules can be imported when running from different directories
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from modules.gst_bank_analysis import analyze_gst_bank
from reliance import generate_ril_enterprise_data

if not os.path.exists('data/ril_bank_statements_large.csv'):
    generate_ril_enterprise_data(100)

res = analyze_gst_bank('data/ril_gst_returns_large.csv', 'data/ril_bank_statements_large.csv')
for row in res.get('mismatch_table', [])[:5]:
    print(row)
