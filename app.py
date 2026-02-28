import os
import json
import requests
import logging
import tempfile
from flask import Flask, render_template, request, jsonify, redirect, url_for, flash, send_file
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from dotenv import load_dotenv
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
import PyPDF2
import docx
from io import BytesIO
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter

from ai_helpers import extract_text_from_pdf, extract_text_from_docx, analyze_with_ai, analyze_with_ai_ats, improve_sentence_ai
from ats_engine import ATSScanner

# Setup Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()
api_key = os.getenv("GEMINI_API_KEY")


app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'dev_warning_change_me_in_prod')
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Initialize DB
db = SQLAlchemy(app)

# Initialize Login Manager
login_manager = LoginManager()
login_manager.login_view = 'login'
login_manager.init_app(app)

# Database Model
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(150), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# Create tables
with app.app_context():
    db.create_all()

# Use system temp directory for uploads
app.config['UPLOAD_FOLDER'] = tempfile.gettempdir() 
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB limit

ALLOWED_EXTENSIONS = {'pdf', 'docx'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# Routes
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/ats')
@login_required
def ats_analyzer():
    return render_template('ats.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
        
    if request.method == 'POST':
        data = request.json
        email = data.get('email')
        password = data.get('password')
        
        user = User.query.filter_by(email=email).first()
        if user and check_password_hash(user.password_hash, password):
            login_user(user, remember=True)
            return jsonify({"success": True})
        else:
            return jsonify({"error": "Invalid email or password"}), 401
            
    return render_template('login.html')

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
        
    if request.method == 'POST':
        data = request.json
        email = data.get('email')
        password = data.get('password')
        
        user = User.query.filter_by(email=email).first()
        if user:
            return jsonify({"error": "Email already exists"}), 400
            
        if len(password) < 6:
            return jsonify({"error": "Password must be at least 6 characters"}), 400
            
        new_user = User(email=email, password_hash=generate_password_hash(password, method='pbkdf2:sha256'))
        db.session.add(new_user)
        db.session.commit()
        
        login_user(new_user, remember=True)
        return jsonify({"success": True})
        
    return render_template('signup.html')

@app.route('/logout', methods=['POST'])
@login_required
def logout():
    logout_user()
    return jsonify({"success": True})



@app.route('/analyze', methods=['POST'])
@login_required
def analyze():
    if 'resume' not in request.files:
        return jsonify({"error": "No file uploaded"}), 400
    
    file = request.files['resume']
    
    if file.filename == '':
        return jsonify({"error": "No file selected"}), 400
        
    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)
        
        text = ""
        if filename.endswith('.pdf'):
            text = extract_text_from_pdf(filepath)
        elif filename.endswith('.docx'):
            text = extract_text_from_docx(filepath)
            
        if not text.strip():
            return jsonify({"error": "Could not extract text from file."}), 400
            
        # Basic AI Analysis (Original Behavior)
        try:
            ai_analysis = analyze_with_ai(text, jd_text="")
        except:
             ai_analysis = {"error": "Failed to analyze resume"}

        try:
            os.remove(filepath)
        except:
            pass
            
        return jsonify(ai_analysis)
    
    return jsonify({"error": "Invalid file type"}), 400


@app.route('/analyze_ats', methods=['POST'])
@login_required
def analyze_ats():
    if 'resume' not in request.files:
        return jsonify({"error": "No file uploaded"}), 400
    
    file = request.files['resume']
    jd_text = request.form.get('job_description', '')
    
    if file.filename == '':
        return jsonify({"error": "No file selected"}), 400
        
    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)
        
        # Extract Text
        text = ""
        if filename.endswith('.pdf'):
            text = extract_text_from_pdf(filepath)
        elif filename.endswith('.docx'):
            text = extract_text_from_docx(filepath)
            
        if not text.strip():
            return jsonify({"error": "Could not extract text from file."}), 400
            
        # ATS Engine Scanning
        scanner = ATSScanner()
        info_dict = scanner.parse_resume_info(text)
        sections_dict = scanner.detect_sections(text)
        resume_kws = scanner.extract_keywords(text)
        jd_kws = scanner.extract_keywords(jd_text)
        
        keyword_analysis = scanner.compare_keywords(resume_kws, jd_kws)
        ats_score = scanner.calculate_score(keyword_analysis, sections_dict, info_dict)
            
        # AI Analysis
        ai_analysis = analyze_with_ai_ats(text, jd_text)

        final_report = {
            "info": info_dict,
            "sections": sections_dict,
            "keywords": keyword_analysis,
            "score": ats_score,
            "ai_analysis": ai_analysis
        }

        # Cleanup
        try:
            os.remove(filepath)
        except:
            pass
            
        return jsonify(final_report)
    
    return jsonify({"error": "Invalid file type"}), 400

@app.route('/improve_sentence', methods=['POST'])
@login_required
def improve_sentence():
    data = request.json
    sentence = data.get('sentence')
    if not sentence:
        return jsonify({"error": "No sentence provided"}), 400
    
    improved = improve_sentence_ai(sentence)
    return jsonify({"original": sentence, "improved": improved})

@app.route('/download_report', methods=['POST'])
@login_required
def download_report():
    data = request.json
    if not data:
        return jsonify({"error": "No report data provided"}), 400
        
    buffer = BytesIO()
    p = canvas.Canvas(buffer, pagesize=letter)
    p.setFont("Helvetica-Bold", 18)
    p.drawString(50, 750, "ATS Resume Analysis Report")
    
    p.setFont("Helvetica-Bold", 14)
    y = 710
    score_info = data.get('score', {})
    total_score = score_info.get('total_score', 'N/A')
    p.drawString(50, y, f"Overall ATS Score: {total_score}/100")
    
    y -= 30
    p.setFont("Helvetica", 12)
    p.drawString(50, y, "Keyword Match Analysis:")
    y -= 20
    kws = data.get('keywords', {}).get('matched', [])
    kw_text = ", ".join(kws[:15]) + ("..." if len(kws)>15 else "")
    p.drawString(70, y, f"Matches: {kw_text}")
    
    p.showPage()
    p.save()
    
    buffer.seek(0)
    return send_file(buffer, as_attachment=True, download_name="ATS_Report.pdf", mimetype='application/pdf')

if __name__ == '__main__':
    app.run(debug=True)
