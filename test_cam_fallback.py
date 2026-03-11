import sys, os
import json
sys.path.append(os.path.join(os.getcwd(), 'src', 'python'))
from modules.cam_generator import generate_cam

risk_results = {
    "decision": "Review",
    "character_score": 25,
    "capacity_score": 10,
    "capital_score": 5,
    "collateral_score": 10,
    "conditions_score": 20,
    "total_score": 70,
    "limit": "₹15 Cr",
    "interest_rate": "10.0%",
    "explanation": "High mismatch detected."
}
financials = {
    "Net Profit": "81,309",
    "Organization Name": "Reliance Industries"
}
gst_bank = {
    "high_mismatch_months": ["2024-04"],
    "suspicious_counterparties": ["X"],
    "anomaly_months": []
}
news = {}

# Force fallback by passing bad API key internally or full_text being too large? 
# We can just mock the client. Wait, no need, let's just observe what happens if we pass empty text, 
# wait the API key is not in this shell, so it will fail immediately.
os.environ.pop("GEMINI_API_KEY", None)

res = generate_cam(risk_results, financials, gst_bank, news, "Test text")
print(res)
