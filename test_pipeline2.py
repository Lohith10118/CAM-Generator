import sys, os
import pandas as pd
from datetime import datetime

# Setup
os.makedirs('data', exist_ok=True)
try:
    from src.python.reliance import generate_ril_enterprise_data
    generate_ril_enterprise_data(50)
except Exception as e:
    print('Failed generate:', e)

sys.path.append(os.path.join(os.getcwd(), 'src', 'python'))
from modules.gst_bank_analysis import analyze_gst_bank
from reliance import generate_ril_enterprise_data

basedir = os.path.dirname(os.path.abspath(__file__))
r_gst = os.path.join(basedir, 'data', 'ril_gst_returns_large.csv')
r_bank = os.path.join(basedir, 'data', 'ril_bank_statements_large.csv')

res = analyze_gst_bank(r_gst, r_bank)
import json
print(json.dumps(res, indent=2))
