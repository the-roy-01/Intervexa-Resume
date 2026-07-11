import fitz
import pytesseract
from PIL import Image
from werkzeug.utils import secure_filename
from datetime import datetime
from flask import Flask, render_template, request, redirect, url_for, session
from pymongo import MongoClient
from dotenv import load_dotenv
import google.generativeai as genai
import os
import json 
import bcrypt
import random
from flask_mail import Mail, Message

if os.name == "nt":
    pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"
# Load environment variables
load_dotenv()

# Initialize Gemini client
genai.configure(api_key=os.getenv("GEMIN_API_KEY"))
print("Gemini API Key:", os.getenv("GEMIN_API_KEY"))

model = genai.GenerativeModel("gemini-2.5-flash")

app = Flask(__name__)

app.secret_key = "your_secret_key"
app.config["MAIL_SERVER"] = "smtp.gmail.com"
app.config["MAIL_PORT"] = 587
app.config["MAIL_USE_TLS"] = True
app.config["MAIL_USERNAME"] = "intervexaresume@gmail.com"
app.config["MAIL_PASSWORD"] = "ragqtpdzspmnyoki"

mail = Mail(app)
UPLOAD_FOLDER = "uploads"
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER
if not os.path.exists(app.config["UPLOAD_FOLDER"]):
    os.makedirs(app.config["UPLOAD_FOLDER"])

# MongoDB Connection
MONGO_URI = os.getenv("MONGO_URI")

client = MongoClient(MONGO_URI)

db = client["intervexa"]

users = db["users"]
feedbacks_collection = db["feedbacks"]
resumes_collection = db["resumes"]

# Test MongoDB Connection
try:
    client.admin.command("ping")
    print("✅ Connected to MongoDB Atlas")
except Exception as e:
    print("❌ Connection failed:", e)


def analyze_resume_with_ai(file_path):

    uploaded_file = genai.upload_file(file_path)

    prompt = """
You are an ATS Resume Analyzer.

Read the uploaded resume carefully, even if it is a scanned PDF.

Score the following from 0 to 100:

- Overall Score
- Resume Format
- Skills
- Keywords
- Experience
- Technical Skills
- Education
- Projects

Return ONLY valid JSON in this exact format:

{
    "overall_score": 85,
    "format_score": 90,
    "format_rating": "Excellent",
    "skills_score": 80,
    "skills_rating": "Good",
    "keyword_score": 75,
    "keyword_rating": "Average",
    "experience_score": 70,
    "experience_rating": "Average",
    "technical_score": 90,
    "technical_rating": "Excellent",
    "education_score": 95,
    "education_rating": "Excellent",
    "structure_score": 88,
    "structure_rating": "Good",
    "project_score": 82,
    "project_rating": "Good",
    "summary": "Write a short summary.",
    "technical_summary": "Write a short summary of technical skills.",
    "project_summary": "Write a short summary of projects.",
    "improvements": [
        "Improvement 1",
        "Improvement 2",
        "Improvement 3"
    ]
}
"""

    response = model.generate_content([uploaded_file, prompt])

    result = response.text.replace("```json", "").replace("```", "").strip()

    return json.loads(result)

# ---------- HOME PAGE ----------
@app.route("/")
def home():
    return render_template("index.html")

# Register Page
@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        fullname = request.form["fullname"]
        email = request.form["email"]
        password = request.form["password"]
        confirm_password = request.form["confirm_password"]

        if not fullname or not email or not password or not confirm_password:
            return "All fields are required"
        if password != confirm_password:
            return "Passwords do not match"

        existing_user = users.find_one({"email": email})
        if existing_user:
            return "Email already registered"

        hashed_password = bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt())
        users.insert_one({
            "fullname": fullname,
            "email": email,
            "password": hashed_password
        })
        print("✅ User Registered Successfully!")
        return redirect(url_for("login"))

    return render_template("register.html")

# Login Page
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form["email"]
        password = request.form["password"]

        user = users.find_one({"email": email})
        if user and bcrypt.checkpw(password.encode("utf-8"), user["password"]):
            session["email"] = user["email"]
            return render_template("homelog.html")

        return "Invalid Email or Password"
    return render_template("login.html")

# Upload Page
@app.route("/upload", methods=["GET", "POST"])
def upload():
    if request.method == "POST":
        if "resume" not in request.files:
            return "No file uploaded"

        file = request.files["resume"]
        if file.filename == "":
            return "Please select a file"

        filename = secure_filename(file.filename)
        filepath = os.path.join(app.config["UPLOAD_FOLDER"], filename)
        file.save(filepath)

        # Extract text from PDF
        text = ""
        if filename.lower().endswith(".pdf"):
            pdf = fitz.open(filepath)
            for page in pdf:
                page_text = page.get_text()
                if page_text.strip():
                    text += page_text
                else:
                    if os.name == "nt":
                        pix = page.get_pixmap(dpi=300)
                        image_path = "temp_page.png"
                        pix.save(image_path)
                        img = Image.open(image_path)
                        text += pytesseract.image_to_string(img)
                        os.remove(image_path)
                    else:
                        print("OCR skipped on Render")
            pdf.close()

        # ✅ Store in MongoDB (include filepath)
        resumes_collection.insert_one({
            "email": session.get("email"),
            "filename": filename,
            "filepath": filepath,   # ✅ Added this line
            "resume_text": text,
            "uploaded_at": datetime.utcnow()
        })

        print("✅ Resume uploaded successfully!")
        return redirect(url_for("loading"))

    return render_template("upload.html")

# Run AI Analysis
@app.route("/run_analysis")
def run_analysis():
    latest_resume = resumes_collection.find_one(
        {"email": session.get("email")},
        sort=[("uploaded_at", -1)]
    )

    if not latest_resume:
        return redirect(url_for("upload"))

    print("🤖 Sending resume to Gemini...")

    try:
        # ✅ Pass filepath instead of resume_text
        ai_result = analyze_resume_with_ai(latest_resume["filepath"])
        print(ai_result)

        resumes_collection.update_one(
            {"_id": latest_resume["_id"]},
            {"$set": {"ai_result": ai_result}}
        )

    except Exception as e:
        print("Gemini Error:", e)
        resumes_collection.update_one(
            {"_id": latest_resume["_id"]},
            {"$set": {
                "ai_result": {
                    "overall_score": 0,
                    "summary": "AI analysis failed.",
                    "improvements": [str(e)]
                }
            }}
        )

    return redirect(url_for("resume_analysis"))


if __name__ == "__main__":
    app.run(debug=True)
