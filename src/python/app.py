import os
import shutil
from flask import Flask, render_template, request, redirect, flash, send_file, url_for
from werkzeug.utils import secure_filename
from dotenv import load_dotenv, find_dotenv

# Load environment variables from .env file (looks in parent directories too)
load_dotenv(find_dotenv())

# Import from the newly structured modules
from modules.document_processor import process_pdf
from modules.financial_extractor import extract_financials
from modules.gst_bank_analysis import analyze_gst_bank
from modules.news_intelligence import process_news
from modules.risk_engine import compute_risk_score
from modules.cam_generator import generate_cam
from modules.pdf_report_generator import create_cam_pdf

app = Flask(__name__)
app.secret_key = 'supersecretkey'

basedir = os.path.abspath(os.path.dirname(__file__))
app.config['UPLOAD_FOLDER'] = os.path.join(basedir, 'uploads')
app.config['NEWS_FOLDER'] = os.path.join(basedir, 'uploads', 'news')

os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
os.makedirs(app.config['NEWS_FOLDER'], exist_ok=True)

@app.route("/", methods=['GET'])
def dashboard():
    return render_template("upload.html")

from modules.document_classifier import classify_documents

# --- Background Task Storage ---
import uuid
import threading

# Store background tasks: {task_id: {"status": "processing"|"success"|"error", "result": {...}, "message": "..."}}
background_tasks = {}

def background_process_documents(task_id, saved_doc_paths, entity_details, loan_details, officer_notes, dynamic_schema, app_config):
    """
    This function runs in a background thread so the HTTP request can return immediately.
    """
    try:
        background_tasks[task_id]['message'] = "Classifying documents..."
        print(f"[{task_id}] [1/3] Auto-classifying uploaded documents...")
        file_classes = classify_documents(saved_doc_paths)
        
        # 2. Find Annual Report
        annual_report_path = None
        for filename, category in file_classes.items():
            if category == "Annual Report":
                annual_report_path = os.path.join(app_config['UPLOAD_FOLDER'], filename)
                break
        
        if not annual_report_path:
             for path in saved_doc_paths:
                 if path.lower().endswith('.pdf'):
                     annual_report_path = path
                     file_classes[os.path.basename(path)] = "Annual Report"
                     break
                     
        if not annual_report_path:
            background_tasks[task_id]['status'] = 'error'
            background_tasks[task_id]['message'] = "Could not identify an Annual Report among the uploaded files."
            return

        background_tasks[task_id]['message'] = "Extracting text from Annual Report (this may take a few minutes)..."
        print(f"[{task_id}] [2/3] Processing PDF Document & chunking text...")
        extracted_text = process_pdf(annual_report_path)
        
        if not extracted_text or len(extracted_text.strip()) < 10:
            background_tasks[task_id]['status'] = 'error'
            background_tasks[task_id]['message'] = "The uploaded Annual Report PDF appears to be a scanned image or completely empty."
            return
            
        with open(os.path.join(app_config['UPLOAD_FOLDER'], 'extracted_text_cache.json'), 'w', encoding='utf-8') as f:
            f.write(extracted_text)
        
        background_tasks[task_id]['message'] = "AI extracting financial metrics from text..."
        print(f"[{task_id}] [3/3] Extracting Financials & applying Dynamic Schema from AI...")
        from modules.document_processor import extract_financial_tables
        financial_tables = extract_financial_tables(annual_report_path)
        
        financials = extract_financials(extracted_text, tables_data=financial_tables, dynamic_schema=dynamic_schema)
        
        print(f"[{task_id}] --- Processing complete! ---")
        
        # Save results securely so the browser can fetch them
        background_tasks[task_id]['status'] = 'success'
        background_tasks[task_id]['result'] = {
            "file_classes": file_classes,
            "financials": financials,
            "entity_details": entity_details,
            "loan_details": loan_details,
            "officer_notes": officer_notes
        }
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        background_tasks[task_id]['status'] = 'error'
        background_tasks[task_id]['message'] = f"Error during document processing: {str(e)}"

@app.route("/process_documents", methods=['POST'])
def process_documents():
    # Clear old uploads
    for folder in [app.config['UPLOAD_FOLDER'], app.config['NEWS_FOLDER']]:
        for filename in os.listdir(folder):
            file_path = os.path.join(folder, filename)
            try:
                if os.path.isfile(file_path) or os.path.islink(file_path):
                    os.unlink(file_path)
                elif os.path.isdir(file_path) and file_path != app.config['NEWS_FOLDER']:
                    shutil.rmtree(file_path)
            except Exception as e:
                pass

    unclassified_docs = request.files.getlist('unclassified_docs')
    news_files = request.files.getlist('news_files')
    officer_notes = request.form.get('officer_notes', '')
    dynamic_schema = request.form.get('dynamic_schema', '')

    # --- New Entity & Loan Details ---
    entity_details = {
        "name": request.form.get('entity_name', ''),
        "cin": request.form.get('entity_cin', ''),
        "pan": request.form.get('entity_pan', ''),
        "sector": request.form.get('entity_sector', ''),
        "turnover": request.form.get('entity_turnover', '')
    }
    
    loan_details = {
        "type": request.form.get('loan_type', ''),
        "amount": request.form.get('loan_amount', ''),
        "tenure": request.form.get('loan_tenure', ''),
        "interest": request.form.get('loan_interest', '')
    }

    if not unclassified_docs or not unclassified_docs[0].filename:
        flash("Please upload at least one financial document.")
        return redirect(url_for('dashboard'))

    saved_doc_paths = []
    for doc in unclassified_docs:
        if doc and doc.filename:
            filename = secure_filename(doc.filename)
            path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            doc.save(path)
            
            if filename.lower().endswith('.zip'):
                print(f"Extracting ZIP archive: {filename}")
                import zipfile
                try:
                    with zipfile.ZipFile(path, 'r') as zip_ref:
                        zip_ref.extractall(app.config['UPLOAD_FOLDER'])
                        for info in zip_ref.infolist():
                            if not info.is_dir() and not info.filename.startswith('__MACOSX') and not info.filename.startswith('.'):
                                extracted_path = os.path.join(app.config['UPLOAD_FOLDER'], info.filename)
                                if os.path.isfile(extracted_path):
                                    saved_doc_paths.append(extracted_path)
                except Exception as e:
                    print(f"Failed to extract zip file: {e}")
            else:
                saved_doc_paths.append(path)

    for news in news_files:
        if news and news.filename:
            news.save(os.path.join(app.config['NEWS_FOLDER'], secure_filename(news.filename)))

    # --- Start Background Processing Thread ---
    task_id = str(uuid.uuid4())
    background_tasks[task_id] = {
        "status": "processing",
        "message": "Starting processing...",
        "result": None
    }
    
    # We must pass app.config manually because threads don't share the current request context easily
    app_config = {
        'UPLOAD_FOLDER': app.config['UPLOAD_FOLDER'],
        'NEWS_FOLDER': app.config['NEWS_FOLDER']
    }
    
    thread = threading.Thread(target=background_process_documents, args=(
        task_id, saved_doc_paths, entity_details, loan_details, officer_notes, dynamic_schema, app_config
    ))
    thread.daemon = True # Allows app to exit even if thread is running
    thread.start()
    
    return render_template("processing.html", task_id=task_id)

from flask import jsonify

@app.route("/status/<task_id>", methods=['GET'])
def get_task_status(task_id):
    task = background_tasks.get(task_id)
    if not task:
        return jsonify({"status": "error", "message": "Task not found."}), 404
    return jsonify(task)

import json
@app.route("/review_staged", methods=['POST'])
def review_staged():
    """
    Renders the human-in-the-loop review screen after background processing completes.
    Data is submitted via a hidden form in processing.html.
    """
    try:
        entity_details = {
            "name": request.form.get('entity_name', ''),
            "cin": request.form.get('entity_cin', ''),
            "pan": request.form.get('entity_pan', ''),
            "sector": request.form.get('entity_sector', ''),
            "turnover": request.form.get('entity_turnover', '')
        }
        
        loan_details = {
            "type": request.form.get('loan_type', ''),
            "amount": request.form.get('loan_amount', ''),
            "tenure": request.form.get('loan_tenure', ''),
            "interest": request.form.get('loan_interest', '')
        }
        
        officer_notes = request.form.get('officer_notes', '')
        json_payload_str = request.form.get('json_payload', '{}')
        complex_data = json.loads(json_payload_str)
        
        file_classes = complex_data.get('file_classes', {})
        financials = complex_data.get('financials', {})
        
        return render_template(
            "review.html",
            file_classes=file_classes,
            financials=financials,
            entity_details=entity_details,
            loan_details=loan_details,
            officer_notes=officer_notes
        )
    except Exception as e:
        flash(f"Error loading review screen: {str(e)}")
        return redirect(url_for('dashboard'))


@app.route("/analyze_confirmed", methods=['POST'])
def analyze_confirmed():
    try:
        # Re-fetch state securely
        entity_details = {
            "name": request.form.get('entity_name', ''),
            "cin": request.form.get('entity_cin', ''),
            "pan": request.form.get('entity_pan', ''),
            "sector": request.form.get('entity_sector', ''),
            "turnover": request.form.get('entity_turnover', '')
        }
        
        loan_details = {
            "type": request.form.get('loan_type', ''),
            "amount": request.form.get('loan_amount', ''),
            "tenure": request.form.get('loan_tenure', ''),
            "interest": request.form.get('loan_interest', '')
        }
        
        officer_notes = request.form.get('officer_notes', '')

        # Re-fetch the financials as approved in the HITL review
        financials = {}
        for key in request.form:
            if key.startswith('fin_'):
                real_key = key[4:]
                financials[real_key] = request.form[key]

        # Re-fetch file classifications confirmed by user
        gst_path = None
        bank_path = None
        for key in request.form:
            if key.startswith('class_'):
                filename = key[6:]
                category = request.form[key]
                if category == "GST Returns":
                    gst_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                elif category == "Bank Statements":
                    bank_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)

        if not gst_path or not os.path.exists(gst_path) or not bank_path or not os.path.exists(bank_path):
            flash("Error: You must assign at least one document as 'GST Returns' and one as 'Bank Statements' in the review screen.")
            return redirect(url_for('dashboard'))

        try:
             with open(os.path.join(app.config['UPLOAD_FOLDER'], 'extracted_text_cache.json'), 'r', encoding='utf-8') as f:
                 extracted_text = f.read()
        except:
             extracted_text = ""

        # 4. Analyze GST and Bank mismatch
        print("[4/7] Running IsolationForest ML on GST vs Bank records...")
        gst_bank_results = analyze_gst_bank(gst_path, bank_path)
        
        # 5. Analyze News Intelligence
        print("[5/7] Crawling Web & Scanning for News Intelligence Risk...")
        organization_name = financials.get('Organization Name', 'Unknown Organization')
        news_insights = process_news(app.config['NEWS_FOLDER'], organization_name)
        
        # 6. Compute Risk Score (Five Cs)
        print("[6/7] Computing AI Five-Cs Risk Profile...")
        # Persist manually entered organization name into financials struct in case AI missed it
        if entity_details.get("name") and 'Organization Name' not in financials:
            financials['Organization Name'] = entity_details['name']
        risk_results = compute_risk_score(financials, gst_bank_results, news_insights, officer_notes, entity_details, loan_details)
        
        # 7. Generate CAM Report text
        print("[7/7] Structuring data and generating ReportLab PDF Payload...")
        ca_memo_text = generate_cam(risk_results, financials, gst_bank_results, news_insights, extracted_text, entity_details, loan_details)
        
        # 8. Create Downloadable PDF
        cam_pdf_path = os.path.join(app.config['UPLOAD_FOLDER'], "cam_report.pdf")
        organization_name = financials.get('Organization Name', 'Unknown Organization')
        create_cam_pdf(ca_memo_text, cam_pdf_path, borrower_name=organization_name, financials=financials)
        
        print("--- Final Analysis Complete! Rendering Dashboard ---")

        return render_template(
            "results.html",
            total_score=risk_results['total_score'],
            decision=risk_results['decision'],
            interest=risk_results['interest_rate'],
            limit=risk_results['limit'],
            explanation=risk_results['explanation'],
            character=risk_results['character_score'],
            capacity=risk_results['capacity_score'],
            capital=risk_results['capital_score'],
            collateral=risk_results['collateral_score'],
            conditions=risk_results['conditions_score'],
            financials=financials,
            gst_bank_results=gst_bank_results,
            news_insights=news_insights,
            organization_name=financials.get('Organization Name', 'Unknown Organization'),
            entity_details=entity_details,
            loan_details=loan_details
        )
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        flash(f"Error during final processing: {str(e)}")
        return redirect(url_for('dashboard'))

@app.route("/download_cam")
def download_cam():
    cam_pdf_path = os.path.join(app.config['UPLOAD_FOLDER'], "cam_report.pdf")
    if os.path.exists(cam_pdf_path):
        return send_file(cam_pdf_path, as_attachment=True, download_name="Credit_Appraisal_Memo.pdf")
    else:
        flash("No CAM generated yet. Please submit your files first.")
        return redirect(url_for("dashboard"))

if __name__ == "__main__":
    # host='0.0.0.0' makes it accessible to the internet
    # port=7860 is required by Hugging Face Spaces
    app.run(host='0.0.0.0', port=7860, debug=False)