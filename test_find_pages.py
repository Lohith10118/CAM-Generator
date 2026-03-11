import fitz

def _find_financial_pages(pdf_path):
    try:
        doc = fitz.open(pdf_path)
        keywords = ['balance sheet', 'statement of profit and loss', 'cash flow', 'financial results', 'income statement', 'standalone financial']
        relevant_pages = []
        for page_num in range(len(doc)):
            text = doc.load_page(page_num).get_text("text").lower()
            if any(k in text for k in keywords) and any(c in text for c in ['crore', 'lakh', 'million', 'thousand', 'in \u20b9', 'in rs']):
                relevant_pages.append(str(page_num + 1))
        
        if len(relevant_pages) > 20:
            relevant_pages = relevant_pages[:20]
            
        if not relevant_pages:
            return '1-20'
            
        return ",".join(relevant_pages)
    except Exception as e:
        return f"Error: {e}"

# If there's an actual PDF uploaded we could test it, but we can just syntax check this.
print("Syntax OK")
