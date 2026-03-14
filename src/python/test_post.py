import requests

url = "http://127.0.0.1:7860/process_documents"
data = {
    "entity_name": "Test",
    "entity_cin": "123",
    "entity_pan": "123",
    "entity_sector": "IT",
    "entity_turnover": "100",
    "loan_type": "Term Loan",
    "loan_amount": "100",
    "loan_tenure": "12",
}
files = {
    "unclassified_docs": ("dummy.txt", b"dummy content"),
}

try:
    response = requests.post(url, data=data, files=files)
    print(f"Status Code: {response.status_code}")
    print(f"Response: {response.text[:200]}")
except Exception as e:
    print(f"Error: {e}")
