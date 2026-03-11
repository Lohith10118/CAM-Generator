import sys, os, json
import pandas as pd
from datetime import datetime
sys.path.append(os.path.join(os.getcwd(), 'src', 'python'))
from modules.gst_bank_analysis import analyze_gst_bank

gst_path = os.path.join(os.getcwd(), 'data', 'ril_gst_returns_large.csv')
bank_path = os.path.join(os.getcwd(), 'data', 'ril_bank_statements_large.csv')

res = analyze_gst_bank(gst_path, bank_path)
print(json.dumps(res, indent=2))
