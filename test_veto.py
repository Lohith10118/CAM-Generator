import sys, os
import json
sys.path.append(os.path.join(os.getcwd(), 'src', 'python'))
from modules.risk_engine import compute_risk_score

financials = {
    "Net Profit": 81309, 
    "ROA": 6.8,
    "Capital Adequacy Ratio": 18.0,
    "Net NPA": 0.5
}
gst_bank = {
    "high_mismatch_months": ["2024-01", "2024-02", "2024-03", "2024-04", "2024-05", "2024-06"],
    "suspicious_parties": ["FraudCo"],
    "anomaly_months": ["2024-05"]
}
loan_details = {
    "amount": "2000"
}
news = {}
os.environ.pop("GEMINI_API_KEY", None)
os.environ.pop("GEMINI_API_KEY_1", None)
os.environ.pop("GEMINI_API_KEY_2", None)

res = compute_risk_score(financials, gst_bank, news, entity_details={}, loan_details=loan_details)
print(json.dumps(res, indent=2))
