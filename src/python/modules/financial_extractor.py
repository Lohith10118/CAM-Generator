import json
import re
import time
from modules.gemini_client import generate_content_with_fallback
from google.genai import types
from modules.document_processor import split_document_into_chunks

def extract_regex_fallbacks(text):
    """Fallback regex extraction for known financial patterns."""
    data = {}
    
    patterns = {
        "Net Profit": r"(?i)Net Profit.*?([\d,\.]+)",
        "Profit After Tax": r"(?i)Profit After Tax.*?([\d,\.]+)",
        "ROA": r"(?i)Return on Assets.*?([\d,\.]+)",
        "Capital Adequacy Ratio": r"(?i)Capital Adequacy Ratio.*?([\d,\.]+)",
        "Net NPA": r"(?i)Net NPA.*?([\d,\.]+)"
    }
    
    for key, pattern in patterns.items():
        match = re.search(pattern, text)
        if match:
            data[key] = match.group(1)
            
    return data

def extract_financials(text, tables_data=None, dynamic_schema=None):
    """
    Use Gemini API to analyze the annual report text and extract structured financial metrics.
    """
    # Using gemini-2.5-flash for fast and cost-effective extraction
    model_name = 'gemini-2.5-flash'
    
    base_schema = {
        "Organization Name": "...",
        "Net Profit": "...",
        "Profit After Tax": "...",
        "Total Assets": "...",
        "ROA": "...",
        "Capital Adequacy Ratio": "...",
        "Net NPA": "..."
    }
    
    aggregated_data = {
        "Organization Name": "Unknown",
        "Net Profit": "N/A",
        "Profit After Tax": "N/A",
        "Total Assets": "N/A",
        "ROA": "N/A",
        "Capital Adequacy Ratio": "N/A",
        "Net NPA": "N/A"
    }
    
    if dynamic_schema:
        custom_fields = [f.strip() for f in dynamic_schema.split(',') if f.strip()]
        for cf in custom_fields:
            if cf not in base_schema:
                base_schema[cf] = "..."
                aggregated_data[cf] = "N/A"
                
    schema_str = json.dumps(base_schema, indent=2)
    

    try:
        # Get raw combined text for regex
        if text.startswith("[{"):
            parsed_data = json.loads(text)
            combined_text = "\n".join([item['text'] for item in parsed_data])
        else:
             combined_text = text
    except Exception:
        combined_text = text

    # 1. Regex Fallback Baseline
    aggregated_data.update(extract_regex_fallbacks(combined_text))

    # Incorporate tables_data if present
    table_context = ""
    if tables_data:
        table_context = "Extracted Tables from Document:\n"
        for i, df in enumerate(tables_data):
            table_context += f"Table {i+1}:\n{df.head(10).to_csv(index=False)}\n"
    
    # 2. Semantic Document Vector Search for relevant chunks
    from modules.document_indexer import get_indexer
    indexer = get_indexer()
    indexer.build_index(text, chunk_size=4000)
    
    queries = ["Net Profit Revenue", "Return on Assets ROA", "Total Assets", "Capital Adequacy Ratio", "Non Performing Assets NPA"]
    relevant_chunks_set = set()
    for q in queries:
        results = indexer.search(q, top_k=1)
        for res in results:
            relevant_chunks_set.add(res)
            
    # Fallback if search returns nothing
    all_chunks = split_document_into_chunks(text, chunk_size=4000)
    relevant_chunks = list(relevant_chunks_set) if relevant_chunks_set else all_chunks[:3]
    chunks_to_process = relevant_chunks[:3]
    
    prompt = f"""
    You are an expert financial analyst. Extract the following financial metrics from the provided annual report text chunk.
    If a metric is not explicitly found, attempt to calculate it (e.g., ROA = Net Profit / Total Assets, or CAR = Tier 1 + Tier 2 Capital / Risk-Weighted Assets) if its component mathematical parts are available in the chunk.
    If a metric is completely unavailable and cannot be calculated, return 'N/A'.
    
    Return ONLY a valid JSON object in the EXACT format below, with no additional markdown formatting, comments, or extra text:
{schema_str}
    """
    
    for i, chunk_text in enumerate(chunks_to_process):
        try:
            full_prompt = prompt + "\nChunk Text:\n" + chunk_text
            if i == 0 and table_context:
                full_prompt += "\n" + table_context

            response = generate_content_with_fallback(
                model_name=model_name,
                contents=full_prompt,
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    temperature=0.0
                ),
                timeout_seconds=20
            )
            
            result_text = response.text.strip()
            if result_text.startswith('```'):
                result_text = re.sub(r'^```(?:json)?\s*', '', result_text)
                result_text = re.sub(r'\s*```$', '', result_text)
                
            match = re.search(r'\{.*\}', result_text, re.DOTALL)
            if match:
                result_text = match.group(0)
                
            chunk_data = json.loads(result_text)
            
            # Aggregate results
            for key in aggregated_data.keys():
                if aggregated_data[key] in ["N/A", "Unknown"] and key in chunk_data and str(chunk_data[key]).strip() not in ["N/A", "Unknown", ""]:
                    aggregated_data[key] = chunk_data[key]
                    
            if i < len(chunks_to_process) - 1:
                time.sleep(1) # Prevent rate limits
        except Exception as e:
            print(f"Error processing chunk {i}: {e}")
            continue

    # Cross-fill PAT and Net Profit if one is missing
    if aggregated_data.get("Profit After Tax") in ["N/A", "Unknown", None] and aggregated_data.get("Net Profit") not in ["N/A", "Unknown", None]:
        aggregated_data["Profit After Tax"] = aggregated_data["Net Profit"]
    elif aggregated_data.get("Net Profit") in ["N/A", "Unknown", None] and aggregated_data.get("Profit After Tax") not in ["N/A", "Unknown", None]:
        aggregated_data["Net Profit"] = aggregated_data["Profit After Tax"]
        
    # Calculate ROA if missing but we have Net Profit and Total Assets
    if aggregated_data.get("ROA") in ["N/A", "Unknown", None] and aggregated_data.get("Net Profit") not in ["N/A", "Unknown", None] and aggregated_data.get("Total Assets") not in ["N/A", "Unknown", None]:
        try:
            np_val = float(re.sub(r'[^\d.-]', '', str(aggregated_data["Net Profit"])))
            ta_val = float(re.sub(r'[^\d.-]', '', str(aggregated_data["Total Assets"])))
            if ta_val != 0:
                aggregated_data["ROA"] = f"{round((np_val / ta_val) * 100, 2)}%"
        except Exception:
            pass

    return aggregated_data
