import pandas as pd
import numpy as np

# Test case 1: identical column names
df1 = pd.DataFrame({'month': ['2023-01'], 'amount': [118]})
df2 = pd.DataFrame({'month': ['2023-01'], 'amount': [100]})

gst_col_amt = 'amount'
bank_col_amt = 'amount'

merged = pd.merge(df1, df2, on='month', how='outer').fillna(0)
print("Columns after merge:", merged.columns)

try:
    merged.rename(columns={gst_col_amt: 'gst_revenue', bank_col_amt: 'bank_inflow'}, inplace=True)
    print("Columns after rename:", merged.columns)
    print(merged['gst_revenue'])
except Exception as e:
    print("Exception1:", e)

# Let's see if there's any scenario where it copies
