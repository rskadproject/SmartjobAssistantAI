import os
import json
import requests
import PyPDF2
import docx
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

API_KEY = os.getenv("GEMINI_API_KEY")
URL = "https://generativelanguage.googleapis.com/v1beta/models/gemini-flash-latest:generateContent"

def call_gemini(text):
    if not API_KEY: return "Error: No API Key found in .env"
    headers = {'Content-Type': 'application/json'}
    data = {"contents": [{"parts": [{"text": text}]}]}
    # Simple Retry Logic
    for attempt in range(2):
        try:
            resp = requests.post(f"{URL}?key={API_KEY}", headers=headers, json=data, timeout=60)
            
            if resp.status_code != 200:
                return f"Error {resp.status_code}: {resp.text}"
                
            res_json = resp.json()
            if 'candidates' not in res_json or not res_json['candidates']:
                return "Error: No response candidates (Possible Safety Block)."
                
            return res_json['candidates'][0]['content']['parts'][0]['text']
        except Exception as e:
            if attempt == 1: # Last attempt
                return f"Error connecting to AI: {str(e)}"

# Extractors
def extract_text_from_pdf(file_path):
    text = ""
    try:
        with open(file_path, 'rb') as file:
            reader = PyPDF2.PdfReader(file)
            for page in reader.pages:
                text += page.extract_text() + "\n"
    except Exception as e:
        print(f"Error reading PDF: {e}")
    return text

def extract_text_from_docx(file_path):
    text = ""
    try:
        doc = docx.Document(file_path)
        for para in doc.paragraphs:
            text += para.text + "\n"
    except Exception as e:
        print(f"Error reading DOCX: {e}")
    return text

# AI Functions
def analyze_with_ai(text):
    prompt = f"""
    You are an expert ATS (Applicant Tracking System) scanner and career coach. Analyze the resume text below.
    Resume Text:
    {text[:4000]}
    Tasks:
    1. Extract specific Technical Skills (programming, tools, hard skills).
    2. Extract specific Soft Skills (communication, leadership, etc.).
    3. Suggest 3 suitable job roles containing a title and description.
    4. Calculate an estimated ATS Score (0-100).
    5. Provide 3 specific tips to improve the resume.
    6. Identify 3 critical MISSING skills for the suggested roles and provide a brief recommendation on how to verify/learn them.
    Return ONLY a JSON object with this structure:
    {{
        "technical_skills": {{
            "Languages": [],
            "Frameworks_and_Libraries": [],
            "Tools_and_Platforms": [],
            "Databases_and_Cloud": []
        }},
        "soft_skills": [],
        "job_roles": [{{"title": "", "description": ""}}],
        "ats_score": 0, "ats_tips": [],
        "missing_skills": [{{"skill": "", "recommendation": ""}}]
    }}
    """
    res = call_gemini(prompt)
    try:
        if "```json" in res: res = res.split("```json")[1].split("```")[0]
        elif "```" in res: res = res.split("```")[1].split("```")[0]
        return json.loads(res.strip())
    except:
        return {"error": f"Failed to parse AI response: {res}"}

def analyze_with_ai_ats(text, jd_text):
    prompt = f"""
    You are an expert ATS (Applicant Tracking System) scanner and career coach. Analyze the resume against the job description below.
    
    Job Description:
    {jd_text[:3000] if jd_text else 'N/A (Provide general analysis)'}
    
    Resume Text:
    {text[:4000]}
    
    Tasks:
    1. Extract specific Technical Skills (programming, tools, hard skills) found in the Resume.
    2. Extract specific Soft Skills found in the Resume.
    3. Suggest 3 suitable job roles containing a title and description.
    4. Provide 6 specific tips to improve the resume, particularly referencing the Job Description if provided.
    5. Identify 3 critical MISSING skills (found in JD but not in Resume, or general recommendations for the suggested roles if no JD is provided) and provide a brief recommendation on how to learn/showcase them.
    
    Return ONLY a JSON object with this exact structure:
    {{
        "technical_skills": {{
            "Languages": [],
            "Frameworks_and_Libraries": [],
            "Tools_and_Platforms": [],
            "Databases_and_Cloud": []
        }},
        "soft_skills": [],
        "job_roles": [{{"title": "", "description": ""}}],
        "ats_tips": [],
        "missing_skills": [{{"skill": "", "recommendation": ""}}]
    }}
    """
    res = call_gemini(prompt)
    try:
        if "```json" in res: res = res.split("```json")[1].split("```")[0]
        elif "```" in res: res = res.split("```")[1].split("```")[0]
        return json.loads(res.strip())
    except:
        return {"error": f"Failed to parse AI response: {res}"}

def generate_summary_ai(role, skills):
    prompt = f"Write a concise, professional resume summary (3-4 sentences) for a {role} with skills: {skills}."
    return call_gemini(prompt)

def improve_sentence_ai(sentence):
    prompt = f"""
    You are an expert resume writer. Rewrite the following sentence to sound much more professional, impactful, and action-oriented for a resume experience section.
    Original: "{sentence}"
    Return ONLY the improved sentence, nothing else. Avoid quotes.
    """
    return call_gemini(prompt)
