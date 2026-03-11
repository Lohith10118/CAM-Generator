import os
import json
import re
from google import genai
from google.genai import types
from modules.document_processor import process_pdf
import pandas as pd

def classify_documents(file_paths):
    """
    Given a list of file paths, reads the first portion of each file
    and uses Gemini to classify its document type.
    Returns a dictionary mapping filename to its predicted category.
    """
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise ValueError("GEMINI_API_KEY environment variable is not set.")
        
    client = genai.Client(api_key=api_key)
    model_name = 'gemini-2.5-flash'
    
    categories = [
        "Annual Report",
        "GST Returns",
        "Bank Statements",
        "ALM",
        "Shareholding Pattern",
        "Borrowing Profile",
        "Portfolio Cuts",
        "Other"
    ]
    
    prompt = f"""
    You are an expert financial document classifier.
    Given the following extracted text from the beginning of a document, classify it into EXACTLY ONE of the following categories:
    {categories}
    
    Return ONLY a valid JSON object in the exact format below, with nothing else:
    {{
        "category": "..."
    }}
    
    Document Text:
    """

    results = {}
    
    for path in file_paths:
        filename = os.path.basename(path)
        ext = filename.lower().split('.')[-1]
        
        sample_text = ""
        try:
            if ext == 'pdf':
                # Try to process PDF, but we only need a small chunk
                extracted = process_pdf(path)
                if extracted.startswith("[{"):
                    parsed = json.loads(extracted)
                    sample_text = "\n".join([item['text'] for item in parsed[:3]]) # First 3 pages
                else:
                    sample_text = extracted[:4000]
            elif ext in ['csv']:
                df = pd.read_csv(path, nrows=10)
                sample_text = df.to_string()
            elif ext in ['xlsx', 'xls']:
                df = pd.read_excel(path, nrows=10)
                sample_text = df.to_string()
            else:
                sample_text = f"Filename: {filename}"
                
        except Exception as e:
            print(f"Failed to read {path} for classification: {e}")
            results[filename] = "Other"
            continue
            
        try:
            full_prompt = prompt + "\n" + sample_text[:4000]
            response = client.models.generate_content(
                model=model_name,
                contents=full_prompt,
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    temperature=0.0
                )
            )
            
            result_text = response.text.strip()
            if result_text.startswith('```'):
                result_text = re.sub(r'^```(?:json)?\s*', '', result_text)
                result_text = re.sub(r'\s*```$', '', result_text)
                
            match = re.search(r'\{.*\}', result_text, re.DOTALL)
            if match:
                result_text = match.group(0)
                
            data = json.loads(result_text)
            pred_cat = data.get('category', 'Other')
            if pred_cat not in categories:
                pred_cat = 'Other'
            results[filename] = pred_cat
            
        except Exception as e:
            print(f"Classification failed for {filename}: {e}")
            results[filename] = "Other"
            
    return results
