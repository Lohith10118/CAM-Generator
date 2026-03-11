import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import os

def generate_ril_enterprise_data(records=2500):
    print("Starting Reliance Industries Synthetic Data Factory...")
    
    # Setup paths matching your project structure
    current_dir = os.path.dirname(os.path.abspath(__file__))
    src_dir = os.path.dirname(current_dir)
    base_dir = os.path.dirname(src_dir)
    
    data_dir = os.path.join(base_dir, 'data')
    os.makedirs(data_dir, exist_ok=True)
    
    # ---------------------------------------------------------
    # 1. GENERATE BANK STATEMENTS (Reliance specific daily transactions)
    # ---------------------------------------------------------
    print("Generating daily banking ledger...")
    start_date = datetime(2024, 4, 1)
    
    dates = [start_date + timedelta(days=np.random.randint(0, 365)) for _ in range(records)]
    dates.sort()
    
    # Reliance-specific transaction descriptions
    descriptions = [
        "RTGS-JIO-TELECOM-REVENUE", "NEFT-RETAIL-STORE-DEPOSIT", "VENDOR-PAYMENT-CRUDE-OIL",
        "PAYROLL-AND-OPERATIONS", "TAX-OUTFLOW-ADVANCE", "NEFT-PETROCHEM-EXPORT"
    ]
    
    bank_data = []
    balance = 150000000000  # Starting balance: 15,000 Crores
    total_inflows = 0
    
    for date in dates:
        desc = np.random.choice(descriptions)
        ref_no = f"{desc.split('-')[0]}{np.random.randint(100000, 999999)}"
        
        # Determine if inflow or outflow based on description
        if "REVENUE" in desc or "DEPOSIT" in desc or "EXPORT" in desc:
            # Massive daily deposits (₹50 Cr to ₹500 Cr per transaction)
            deposit = round(np.random.uniform(500000000, 5000000000), 2)
            withdrawal = np.nan
            balance += deposit
            total_inflows += deposit
        else:
            # Massive daily withdrawals for operations/crude
            deposit = np.nan
            withdrawal = round(np.random.uniform(300000000, 2000000000), 2)
            balance -= withdrawal
            
        bank_data.append([date.strftime('%Y-%m-%d'), desc, ref_no, withdrawal, deposit, balance])

    bank_df = pd.DataFrame(bank_data, columns=['Date', 'Description', 'Reference_No', 'Withdrawal', 'Deposit', 'Balance'])
    bank_file = os.path.join(data_dir, 'ril_bank_statements_large.csv')
    bank_df.to_csv(bank_file, index=False)
    
    # ---------------------------------------------------------
    # 2. GENERATE GST RETURNS (Monthly)
    # ---------------------------------------------------------
    print("Generating monthly GST filings...")
    
    # THE FRAUD TRAP: Make the first 9 months clean to train the ML model.
    # Then spike Jan, Feb, March 2025 by 40% to test the anomaly detector.
    
    bank_df['MonthStr'] = pd.to_datetime(bank_df['Date']).dt.strftime('%b-%Y')
    monthly_inflows = bank_df.groupby('MonthStr')['Deposit'].sum().fillna(0).to_dict()
    
    gst_data = []
    for month in range(1, 13):
        m = (month + 2) % 12 + 1
        y = 2024 if m >= 4 else 2025
        month_str = datetime(y, m, 1).strftime('%b-%Y')
        
        actual_inflow = monthly_inflows.get(month_str, 0.0)
        
        # Q4 Fraud Spike (Jan, Feb, Mar 2025)
        if m in [1, 2, 3] and y == 2025:
            monthly_sales = round(actual_inflow * 1.40, 2) # 40% Fake Inflation
        else:
            monthly_sales = round(actual_inflow, 2) # Perfect Match
            
        tax_paid = round(monthly_sales * 0.18, 2)
        gst_data.append([month_str, monthly_sales, tax_paid, 'Filed'])

    gst_df = pd.DataFrame(gst_data, columns=['Month', 'Declared_Sales_INR', 'Tax_Paid', 'Filing_Status'])
    gst_file = os.path.join(data_dir, 'ril_gst_returns_large.csv')
    gst_df.to_csv(gst_file, index=False)
    
    bank_df.drop(columns=['MonthStr'], inplace=True, errors='ignore')

    # ---------------------------------------------------------
    print(f"\nSuccess! Generated {records} Reliance banking transactions and 12 months of GST.")
    print(f"Actual Bank Inflows: Rs. {total_inflows:,.2f}")
    print(f"Faked GST Declared Sales: Rs. {gst_df['Declared_Sales_INR'].sum():,.2f}")
    print(f"The massive missing cash trap is exactly: Rs. {(gst_df['Declared_Sales_INR'].sum() - total_inflows):,.2f}")

if __name__ == "__main__":
    generate_ril_enterprise_data(records=2500)