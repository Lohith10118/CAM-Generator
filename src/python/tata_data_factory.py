import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import os

def generate_enterprise_data(records=1000):
    print("🏭 Starting Tata Motors Synthetic Data Factory...")
    
    # --- UPDATED PATH LOGIC FOR YOUR NEW FOLDER STRUCTURE ---
    # This jumps up from src/python -> src -> intelli-credit-ai to find the 'data' folder
    current_dir = os.path.dirname(os.path.abspath(__file__))
    src_dir = os.path.dirname(current_dir)
    base_dir = os.path.dirname(src_dir)
    
    data_dir = os.path.join(base_dir, 'data')
    os.makedirs(data_dir, exist_ok=True)
    # ---------------------------------------------------------
    
    # 1. GENERATE BANK STATEMENTS (Daily Transactions)
    print("⏳ Generating daily banking ledger...")
    start_date = datetime(2024, 4, 1)
    
    dates = [start_date + timedelta(days=np.random.randint(0, 365)) for _ in range(records)]
    dates.sort()
    
    descriptions = [
        "RTGS-DEALER-PAYMENT", "NEFT-SUBSIDIARY-TRANSFER", "VENDOR-PAYMENT-STEEL",
        "PAYROLL-AND-OPERATIONS", "TAX-OUTFLOW", "CAPEX-MACHINERY"
    ]
    
    bank_data = []
    balance = 50000000000  # Starting balance: 5,000 Crores
    total_inflows = 0
    
    for date in dates:
        desc = np.random.choice(descriptions)
        ref_no = f"{desc.split('-')[0]}{np.random.randint(100000, 999999)}"
        
        if "DEALER" in desc or "SUBSIDIARY" in desc:
            deposit = round(np.random.uniform(100000000, 500000000), 2)
            withdrawal = np.nan
            balance += deposit
            total_inflows += deposit
        else:
            deposit = np.nan
            withdrawal = round(np.random.uniform(50000000, 800000000), 2)
            balance -= withdrawal
            
        bank_data.append([date.strftime('%Y-%m-%d'), desc, ref_no, withdrawal, deposit, balance])

    bank_df = pd.DataFrame(bank_data, columns=['Date', 'Description', 'Reference_No', 'Withdrawal', 'Deposit', 'Balance'])
    bank_file = os.path.join(data_dir, 'tata_bank_statements_large.csv')
    bank_df.to_csv(bank_file, index=False)
    
    # 2. GENERATE GST RETURNS (Monthly)
    print("⏳ Generating monthly GST filings...")
    
    # THE FRAUD TRAP: Inflate actual inflows by 40%
    fake_annual_gst_revenue = total_inflows * 1.40 
    monthly_avg_sales = fake_annual_gst_revenue / 12
    
    gst_data = []
    for month in range(1, 13):
        monthly_sales = round(np.random.normal(monthly_avg_sales, monthly_avg_sales * 0.05), 2)
        tax_paid = round(monthly_sales * 0.18, 2)
        
        m = (month + 2) % 12 + 1
        y = 2024 if m >= 4 else 2025
        month_str = datetime(y, m, 1).strftime('%b-%Y')
        
        gst_data.append([month_str, monthly_sales, tax_paid, 'Filed'])

    gst_df = pd.DataFrame(gst_data, columns=['Month', 'Declared_Sales_INR', 'Tax_Paid', 'Filing_Status'])
    gst_file = os.path.join(data_dir, 'tata_gst_returns_large.csv')
    gst_df.to_csv(gst_file, index=False)
    
    print(f"\n✅ Success! Generated {records} banking transactions and 12 months of GST.")
    print(f"📊 Actual Bank Inflows: ₹{total_inflows:,.2f}")
    print(f"📊 Faked GST Declared Sales: ₹{gst_df['Declared_Sales_INR'].sum():,.2f}")
    print(f"🚨 The discrepancy trap is exactly: ₹{(gst_df['Declared_Sales_INR'].sum() - total_inflows):,.2f}")

if __name__ == "__main__":
    generate_enterprise_data(records=1500)