from modules.gemini_client import generate_content_with_fallback
from google.genai import types

def compute_risk_score(financials, gst_bank_results, news_insights, officer_notes="", entity_details=None, loan_details=None):
    """
    Implement a credit risk scoring model based on the Five Cs:
    Character (25), Capacity (20), Capital (15), Collateral (15), Conditions (25).
    """
    
    # Defaults
    entity_details = entity_details or {}
    loan_details = loan_details or {}
    requested_amount = _parse_val(loan_details.get("amount"))
    
    # Check if this is a massive conglomerate (e.g. Net Profit > 500 Cr)
    net_profit = _parse_val(financials.get("Net Profit"))
    is_large_corporate = net_profit is not None and net_profit > 500
    
    # Scale factor for penalties (large corporates have standard litigation and accounting variances)
    penalty_scale = 0.3 if is_large_corporate else 1.0
    
    # 1. CHARACTER (Max 25)
    # Based on news sentiment, litigation, and repeated counterparties
    character_score = 25
    if news_insights:
        sentiment = str(news_insights.get("sentiment_score", "")).lower()
        litigation_flag = news_insights.get("litigation_detected", False)
        
        if "negative" in sentiment:
            character_score -= (10 * penalty_scale)
        elif "neutral" in sentiment:
            character_score -= (3 * penalty_scale)
            
        if litigation_flag:
            character_score -= (15 * penalty_scale)
            
    if gst_bank_results and gst_bank_results.get("suspicious_parties"):
        # Penalty for too many repeated unknown counterparties (potential shell companies)
        character_score -= min(5, len(gst_bank_results["suspicious_parties"]) * penalty_scale)
        
    character_score = max(0, character_score)
    
    # 2. CAPACITY (Max 20)
    # Based on GST-Bank mismatch and Profitability
    capacity_score = 20
    if gst_bank_results:
        high_mismatch = len(gst_bank_results.get("high_mismatch_months", []))
        anomaly_months = len(gst_bank_results.get("anomaly_months", []))
        
        if is_large_corporate:
            # Massive companies have expected timing differences across subsidiaries
            if high_mismatch > 6:
                capacity_score -= 5
            if anomaly_months > 6:
                capacity_score -= 5
        else:
            capacity_score -= (high_mismatch * 2) # -2 for every month with >15% mismatch
            if anomaly_months > 2:
                capacity_score -= 10
    
    
    if net_profit is not None:
        if net_profit <= 0:
            capacity_score -= 10
        elif net_profit < 10:
            capacity_score -= 5 # Arbitrary small threshold logic
    else:
        capacity_score -= 10 # Heavy penalty for lack of profit clarity
        
    capacity_score = max(0, capacity_score)
    
    # 3. CAPITAL (Max 15)
    # Based on Capital Adequacy Ratio (CAR) and Net NPA
    capital_score = 15
    car_val = _parse_val(financials.get("Capital Adequacy Ratio"))
    npa_val = _parse_val(financials.get("Net NPA"))
    
    if car_val is not None:
        if car_val < 9:
            capital_score -= 10 # Below Basel norm roughly
        elif car_val < 12:
            capital_score -= 5
    else:
        capital_score -= 5
        
    if npa_val is not None:
        if npa_val > 5:
            capital_score -= 10 # High NPA
        elif npa_val > 2:
            capital_score -= 5
    else:
        capital_score -= 5
        
    capital_score = max(0, capital_score)
    
    # 4. COLLATERAL (Max 15)
    # Since collateral is often not explicitly clear in basic annual reports unless specified, 
    # we assign a moderate default or estimate based on ROA and total assets context.
    collateral_score = 15
    roa_val = _parse_val(financials.get("ROA"))
    if roa_val is not None:
        if roa_val < 0.5:
            # Low return on assets implies assets might be heavily encumbered or unproductive
            collateral_score -= 5
    else:
        collateral_score -= 5
        
    # 5. CONDITIONS (Max 25)
    # Industry conditions, anomaly presence
    conditions_score = 25
    if gst_bank_results and gst_bank_results.get("anomaly_months"):
        # Volatility or anomalies in bank statements
        num_anomalies = len(gst_bank_results["anomaly_months"])
        
        if is_large_corporate:
            conditions_score -= min(5.0, num_anomalies * penalty_scale)
        else:
            conditions_score -= min(15.0, num_anomalies * 2)
            
    # Apply Officer Notes dynamically via Gemini
    if officer_notes and officer_notes.strip():
        adjustment = __analyze_officer_notes(officer_notes)
        conditions_score += adjustment
        
    conditions_score = max(0, conditions_score)
    
    # CALCULATE PRELIMINARY TOTAL
    total_score = character_score + capacity_score + capital_score + collateral_score + conditions_score
    
    # CALCULATE CAPACITY LIMIT
    net_profit = _parse_val(financials.get("Net Profit"))
    if total_score > 70:
        multiplier = 4.0
    elif total_score >= 50:
        multiplier = 1.5
    else:
        multiplier = 0.0
    calculated_capacity_limit = (net_profit * multiplier) if net_profit and net_profit > 0 else 0
    
    # ADJUST FOR REQUESTED LOAN VS CAPACITY
    if requested_amount and calculated_capacity_limit > 0:
        if calculated_capacity_limit > requested_amount:
            # Cap the AI suggested limit safely at what they actually requested
            # A bank never suggests ₹300,000 Cr just because they can afford it when they only asked for ₹2,000 Cr.
            calculated_capacity_limit = requested_amount
            
        if requested_amount > (calculated_capacity_limit * 1.5):
            # Applying for way more than they can safely handle drops the capacity/total score
            capacity_score = max(0, capacity_score - 10)
            total_score = character_score + capacity_score + capital_score + collateral_score + conditions_score

    # AUTO-REJECT VETO FOR FINANCIAL FRAUD/MISMATCH
    has_critical_veto = False
    if gst_bank_results:
        mismatched_months = len(gst_bank_results.get("high_mismatch_months", []))
        ml_anomalies_detected = len(gst_bank_results.get("anomaly_months", []))
        
        if ml_anomalies_detected > 0 or mismatched_months > 3:
            has_critical_veto = True
            total_score = min(total_score, 40)  # Force score down to a failing grade

    # FINAL DECISION LOGIC
    if total_score > 70:
        decision = "Approve"
        interest_rate = loan_details.get("interest") or "8.5% - 10.0%"
    elif total_score >= 50:
        decision = "Review"
        interest_rate = loan_details.get("interest") or "10.5% - 13.0%"
    else:
        decision = "Reject"
        interest_rate = "N/A"
        
    # Format Limit properly
    if decision == "Reject":
        limit = "Rs. 0"
    elif calculated_capacity_limit > 0:
        limit = f"₹{round(calculated_capacity_limit, 2)} Cr"
    else:
        limit = "Requires Collateral Assessment"

    # Generate Explainable Decision Rationale
    if has_critical_veto:
        explanation = "CRITICAL WARNING: Loan rejected despite strong profitability due to severe discrepancies between declared GST returns and actual Bank Cash inflows. ML algorithms have flagged potential circular trading or revenue inflation."
    else:
        explanation = __generate_rationale(total_score, decision, limit, financials, gst_bank_results, news_insights, notes=officer_notes, requested_amount=requested_amount)
        
    return {
        "character_score": round(character_score, 2),
        "capacity_score": round(capacity_score, 2),
        "capital_score": round(capital_score, 2),
        "collateral_score": round(collateral_score, 2),
        "conditions_score": round(conditions_score, 2),
        "total_score": round(total_score, 2),
        "decision": decision,
        "interest_rate": interest_rate,
        "limit": limit,
        "explanation": explanation
    }

def _parse_val(val_str):
    if not val_str or str(val_str).upper() == "N/A":
        return None
    try:
        import re
        # Remove non-numeric characters except decimals and minus
        clean_str = re.sub(r'[^\d.-]', '', str(val_str))
        if clean_str:
            return float(clean_str)
        return None
    except Exception:
        return None

def __analyze_officer_notes(notes):
    prompt = f"""You are a scoring assistant. Read these Credit Officer qualitative notes: "{notes}"
Based on these notes, output ONLY a single integer representing a risk score adjustment from -20 (severe risk) to +10 (strong positive mitigate). Do not include any text, just the integer.
"""
    try:
        response = generate_content_with_fallback(
            model_name='gemini-2.5-flash',
            contents=prompt,
            config=types.GenerateContentConfig(temperature=0.0),
            timeout_seconds=15
        )
        import re
        val = re.sub(r'[^\d-]', '', response.text)
        return int(val)
    except Exception:
        return 0

def __generate_rationale(score, decision, limit, financials, gst_bank_results, news_insights, notes, requested_amount=None):
    news_summary = ""
    if news_insights:
        news_summary = f"Sentiment: {news_insights.get('sentiment_score', 'Neutral')}. Keywords: {', '.join(news_insights.get('risk_keywords', []))}."
        if news_insights.get('litigation_detected'):
            news_summary += " Litigation detected."
            
    mismatch = "Yes" if gst_bank_results and gst_bank_results.get('high_mismatch_months') else "No"
    anomalies = len(gst_bank_results.get('anomaly_months', [])) if gst_bank_results else 0
    req_context = f"Requested Loan Amount: {requested_amount} Cr. " if requested_amount else ""
    
    prompt = f"""You are an automated Credit Manager. Explain the loan {decision} in exactly two clear, professional sentences. 
Data: Score is {score}/100. AI Suggested Limit is {limit}. {req_context}
Officer Notes provided: "{notes}". 
High GST/Bank Mismatch: {mismatch}. 
Machine Learning Anomalies Detected: {anomalies} months.
News/Litigation Risks: {news_summary}
Make sure to explain WHY it was approved, reviewed, or rejected. If the requested amount is drastically higher than the AI suggested limit, mention that capacity is insufficient.
"""
    try:
        response = generate_content_with_fallback(
            model_name='gemini-2.5-flash',
            contents=prompt,
            config=types.GenerateContentConfig(temperature=0.0),
            timeout_seconds=15
        )
        return response.text.strip()
    except Exception:
        return f"{decision} based on score {score}."
