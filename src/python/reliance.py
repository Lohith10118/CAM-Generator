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
    
    # THE FRAUD TRAP: We inflate the GST declared sales to be 18% higher than actual bank cash.
    # This creates a massive, multi-thousand crore black hole for the AI to find.
    fake_annual_gst_revenue = total_inflows * 1.18 
    monthly_avg_sales = fake_annual_gst_revenue / 12
    
    gst_data = []
    for month in range(1, 13):
        monthly_sales = round(np.random.normal(monthly_avg_sales, monthly_avg_sales * 0.03), 2)
        tax_paid = round(monthly_sales * 0.18, 2) # Assuming 18% GST bracket
        
        m = (month + 2) % 12 + 1
        y = 2024 if m >= 4 else 2025
        month_str = datetime(y, m, 1).strftime('%b-%Y')
        
        gst_data.append([month_str, monthly_sales, tax_paid, 'Filed'])

    gst_df = pd.DataFrame(gst_data, columns=['Month', 'Declared_Sales_INR', 'Tax_Paid', 'Filing_Status'])
    gst_file = os.path.join(data_dir, 'ril_gst_returns_large.csv')
    gst_df.to_csv(gst_file, index=False)
    
    # ---------------------------------------------------------
    print(f"\nSuccess! Generated {records} Reliance banking transactions and 12 months of GST.")
    print(f"Actual Bank Inflows: Rs. {total_inflows:,.2f}")
    print(f"Faked GST Declared Sales: Rs. {gst_df['Declared_Sales_INR'].sum():,.2f}")
    print(f"The massive missing cash trap is exactly: Rs. {(gst_df['Declared_Sales_INR'].sum() - total_inflows):,.2f}")

if __name__ == "__main__":
    generate_ril_enterprise_data(records=2500)