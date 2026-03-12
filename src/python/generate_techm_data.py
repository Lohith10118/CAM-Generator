import pandas as pd
from datetime import datetime, timedelta
import random
import os

# Create the data/processed directory if it doesn't exist
output_dir = os.path.join("data", "processed")
os.makedirs(output_dir, exist_ok=True)

# Tech Mahindra FY 24-25 Actuals (from uploaded consolidated results)
# Annual Revenue: 529,883 Million INR (approx 52,988 Crores) -> ~4,415 Crore Monthly
MONTHLY_REVENUE_BASE = 44150000000 

def generate_gst_returns():
    months = ["Apr-2024", "May-2024", "Jun-2024", "Jul-2024", "Aug-2024", "Sep-2024", 
              "Oct-2024", "Nov-2024", "Dec-2024", "Jan-2025", "Feb-2025", "Mar-2025"]
    
    gst_data = []
    for month in months:
        # Add a little randomness (± 5%) to monthly revenue
        variation = random.uniform(0.95, 1.05)
        total_sales = MONTHLY_REVENUE_BASE * variation
        
        # IT Services: ~80% Exports (Zero Rated), 20% Domestic (Taxable)
        export_sales = total_sales * 0.80
        domestic_sales = total_sales * 0.20
        
        # 18% GST on Domestic IT Services
        total_tax = domestic_sales * 0.18
        igst = total_tax * 0.70 # Mostly inter-state client billing
        cgst = total_tax * 0.15
        sgst = total_tax * 0.15

        gst_data.append([
            month, 
            round(total_sales, 2), 
            round(domestic_sales, 2), 
            round(export_sales, 2),
            round(igst, 2), 
            round(cgst, 2), 
            round(sgst, 2)
        ])
        
    df = pd.DataFrame(gst_data, columns=[
        "Month", "Total_Declared_Sales", "Domestic_Taxable_Sales", 
        "Export_Zero_Rated_Sales", "IGST_Paid", "CGST_Paid", "SGST_Paid"
    ])
    
    file_path = os.path.join(output_dir, "techm_gst_returns.csv")
    df.to_csv(file_path, index=False)
    print(f"✅ GST Returns saved successfully to: {file_path}")

def generate_bank_statements():
    start_date = datetime(2024, 4, 1)
    end_date = datetime(2025, 3, 31)
    current_date = start_date
    
    # Start with a massive, healthy balance (5000 Crores)
    running_balance = 50000000000.00 
    
    bank_data = []
    
    while current_date <= end_date:
        # Skip weekends for major corporate transactions
        if current_date.weekday() >= 5:
            current_date += timedelta(days=1)
            continue
            
        # 1. INFLOWS (Client Payments - matching GST approx)
        # Daily revenue is roughly 200 Crore
        daily_inflow = (MONTHLY_REVENUE_BASE / 22) * random.uniform(0.8, 1.2)
        running_balance += daily_inflow
        bank_data.append([
            current_date.strftime("%Y-%m-%d"), 
            "NEFT/RTGS Client Payment - IT Services", 
            0.0, 
            round(daily_inflow, 2), 
            round(running_balance, 2)
        ])
        
        # 2. OUTFLOWS (Payroll, Server Costs, Operations)
        # TechM has high payroll (148,000+ employees). 
        daily_outflow = (MONTHLY_REVENUE_BASE / 24) * random.uniform(0.7, 1.1)
        running_balance -= daily_outflow
        bank_data.append([
            current_date.strftime("%Y-%m-%d"), 
            "RTGS/NEFT Vendor Payment / Payroll / Cloud Hosting", 
            round(daily_outflow, 2), 
            0.0, 
            round(running_balance, 2)
        ])
        
        current_date += timedelta(days=1)
        
    df = pd.DataFrame(bank_data, columns=["Date", "Narration", "Withdrawal", "Deposit", "Balance"])
    
    file_path = os.path.join(output_dir, "techm_bank_statements.csv")
    df.to_csv(file_path, index=False)
    print(f"✅ Bank Statements saved successfully to: {file_path}")

if __name__ == "__main__":
    generate_gst_returns()
    generate_bank_statements()