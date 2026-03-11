import os
from google import genai
from google.genai import types
import json
import re

def generate_cam(risk_results, financials, gst_bank_results, news_insights, full_text, entity_details=None, loan_details=None):
    """
    Use Gemini to generate a structured JSON Credit Appraisal Memo for tabular display.
    """
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        return '{"error": "GEMINI_API_KEY missing. AI unable to generate CAM."}'
        
    client = genai.Client(api_key=api_key)
    model_name = 'gemini-2.5-flash'
    
    entity_details = entity_details or {}
    loan_details = loan_details or {}
    
    prompt = f"""
    You are an expert Credit Analyst. Please extract and infer information to populate the following Credit Appraisal Memorandum.
    Use the provided data (financials, UI inputs, GST analysis, risk scoring) to complete the fields.
    If exact data is missing, make a highly plausible, professional estimate based on the context, or write "Not available in provided docs".
    
    CRITICAL RULE: Never say 'Not available in provided docs'. If specific collateral or capital details are missing, you MUST generate an estimated justification based on the company's Total Assets and Net Worth.
    CRITICAL RULE 2: Format all financial numbers cleanly (e.g., '1,022,401 Crore'). Do not write 'C in crore'.
    
    Do NOT include markdown formatting. Return ONLY a valid JSON object matching this exact schema:
    
    {{
      "applicant_name": "Organization Name (Use {financials.get('Organization Name', 'Unknown')} or contextual info)",
      "entity_identifiers": {{
        "cin": "CIN Note",
        "pan": "PAN Note",
        "sector": "Sector classification"
      }},
      "borrower_overview": {{
        "description": "Brief summary of the borrower's business",
        "industry": "Industry sector",
        "key_activities": "Main business activities"
      }},
      "financial_performance": {{
        "net_profit": "Extracted Net Profit",
        "roa": "Return on Assets",
        "npa": "Net NPA",
        "capital_adequacy": "Capital Adequacy Ratio"
      }},
      "revenue_validation": {{
        "gst_bank_mismatch_status": "Summary of mismatch (>15% months)",
        "suspicious_counterparties": "Number/details of suspicious parties",
        "ml_anomalies": "Summary of IsolationForest anomalies"
      }},
      "external_intelligence": {{
        "news_sentiment": "Positive/Neutral/Negative",
        "litigation_found": "Yes/No with brief details",
        "key_risks": "Summary of news risk keywords"
      }},
      "risk_assessment_five_cs": {{
        "character": "Score and brief justification",
        "capacity": "Score and brief justification",
        "capital": "Score and brief justification",
        "collateral": "Score and brief justification",
        "conditions": "Score and brief justification"
      }},
      "credit_recommendation": {{
        "decision": "Approve/Review/Reject",
        "requested_facility": "The user requested facility type and amount",
        "ai_suggested_limit": "AI Proposed Limit",
        "interest_rate": "Proposed Rate",
        "rationale": "The exact AI generated rationale"
      }}
    }}
    
    DATA PROVIDED:
    
    Executive Text Context (Truncated):
    {full_text[:15000]}
    
    Entity Details provided via UI:
    {json.dumps(entity_details, indent=2)}
    
    Loan Request Details provided via UI:
    {json.dumps(loan_details, indent=2)}
    
    Financial Metrics:
    {json.dumps(financials, indent=2)}
    
    GST vs Bank Analysis:
    - High Mismatch Months (>15% variance): {', '.join(gst_bank_results.get('high_mismatch_months', [])) or 'None recorded.'}
    - Suspicious Repeated Counterparties Formally Identified: {len(gst_bank_results.get('suspicious_parties', []))}
    - Bank Statement Anomalous Transactions flagged by ML: {len(gst_bank_results.get('anomalies', []))}
    
    External Intelligence Findings:
    {json.dumps(news_insights, indent=2)}
    
    Total Risk Engine Decision Outputs:
    {json.dumps(risk_results, indent=2)}
    
    Please return ONLY the raw JSON string matching the specified schema.
    """
    
    try:
        response = client.models.generate_content(
            model=model_name,
            contents=prompt,
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                temperature=0.0
            )
        )
        # Parse output to ensure strictly JSON
        result_text = response.text.strip()
        if result_text.startswith('```'):
            result_text = re.sub(r'^```(?:json)?\s*', '', result_text)
            result_text = re.sub(r'\s*```$', '', result_text)
        
        # Additional fallback regex if there's text before/after JSON
        match = re.search(r'\{.*\}', result_text, re.DOTALL)
        if match:
            result_text = match.group(0)
            
        data = json.loads(result_text)
        return json.dumps(data)
    except Exception as e:
        print(f"Error communicating with AI CAM generator: {str(e)}")
        # Fallback JSON structure if generation fails
        fallback = {
            "applicant_name": financials.get("Organization Name", "Unknown") if financials else "Unknown",
            "entity_identifiers": {
                "cin": entity_details.get("cin", "N/A"),
                "pan": entity_details.get("pan", "N/A"),
                "sector": entity_details.get("sector", "N/A")
            },
            "borrower_overview": {"description": "Error generating AI summary.", "industry": entity_details.get("sector", "N/A"), "key_activities": "Data Unavailable"},
            "financial_performance": {
                "net_profit": financials.get("Net Profit", "N/A") if financials else "N/A", 
                "roa": financials.get("ROA", "N/A") if financials else "N/A", 
                "npa": financials.get("Net NPA", "N/A") if financials else "N/A", 
                "capital_adequacy": financials.get("Capital Adequacy Ratio", "N/A") if financials else "N/A"
            },
            "revenue_validation": {
                "gst_bank_mismatch_status": f"High mismatch in {len(gst_bank_results.get('high_mismatch_months', []))} months" if gst_bank_results else "N/A", 
                "suspicious_counterparties": str(len(gst_bank_results.get('suspicious_counterparties', []))) if gst_bank_results else "N/A", 
                "ml_anomalies": f"Detected in {len(gst_bank_results.get('anomaly_months', []))} months" if gst_bank_results else "N/A"
            },
            "external_intelligence": {
                "news_sentiment": str(news_insights.get("sentiment_score", "N/A")) if news_insights else "N/A", 
                "litigation_found": "Yes" if news_insights and news_insights.get("litigation_detected") else "No", 
                "key_risks": ", ".join(news_insights.get("risk_keywords", [])) if news_insights and news_insights.get("risk_keywords") else "None detected"
            },
            "risk_assessment_five_cs": {
                "character": str(risk_results.get("character_score", "N/A")) if risk_results else "N/A", 
                "capacity": str(risk_results.get("capacity_score", "N/A")) if risk_results else "N/A", 
                "capital": str(risk_results.get("capital_score", "N/A")) if risk_results else "N/A", 
                "collateral": str(risk_results.get("collateral_score", "N/A")) if risk_results else "N/A", 
                "conditions": str(risk_results.get("conditions_score", "N/A")) if risk_results else "N/A"
            },
            "credit_recommendation": {
                "decision": risk_results.get("decision", "Error") if risk_results else "Error",
                "requested_facility": f"{loan_details.get('type', 'N/A')} - {loan_details.get('amount', 'N/A')} Cr" if loan_details else "N/A",
                "ai_suggested_limit": risk_results.get("limit", "N/A") if risk_results else "N/A",
                "interest_rate": risk_results.get("interest_rate", "N/A") if risk_results else "N/A",
                "rationale": risk_results.get("explanation", "API/Timeout Error fallback generated. See core scores.") if risk_results else "API Error fallback"
            }
        }
        return json.dumps(fallback)
