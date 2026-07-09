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

pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"

# Load environment variables
load_dotenv()

# Initialize Gemini client
genai.configure(api_key=os.getenv("GEMIN_API_KEY"))

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


# ---------- AI FUNCTION ----------

def analyze_resume_with_ai(resume_text):
    prompt = f"""
You are an ATS Resume Analyzer.

Analyze the following resume.

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

{{
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
    "technical_summary": "Write a short summary of your technical skills.",
    "project_summary": "Write a short summary of your projects.",

    "improvements": [
        "Improvement 1",
        "Improvement 2",
        "Improvement 3"
    ]
}}

Resume:

{resume_text}
"""
    response = model.generate_content(prompt)

    result = response.text

    # Remove markdown if Gemini returns ```json ... ```
    result = result.replace("```json", "").replace("```", "").strip()

    return json.loads(result)

def generate_interview_questions(role, experience, interview_type, difficulty, total_questions):

    prompt = f"""
You are an AI Interviewer.

Generate {total_questions} interview questions.

Job Role: {role}
Experience: {experience}
Interview Type: {interview_type}
Difficulty: {difficulty}

Return ONLY a JSON array.

Example:

[
"Question 1",
"Question 2",
"Question 3"
]
"""

    response = model.generate_content(prompt)

    result = response.text.replace("```json", "").replace("```", "").strip()

    return json.loads(result)

def analyze_interview_performance(questions, answers):

    prompt = f"""
You are an expert HR interviewer.

Analyze the interview based on these questions and answers.

Questions:
{questions}

Answers:
{answers}

Return ONLY valid JSON in this format:

{{
    "overall_score": 85,
    "communication": 90,
    "technical": 82,
    "confidence": 88,
    "problem_solving": 84,
    "grade": "A",

    "summary": "Overall interview performance summary.",

    "strengths": [
        "Strength 1",
        "Strength 2",
        "Strength 3"
    ],

    "improvements": [
        "Improvement 1",
        "Improvement 2",
        "Improvement 3"
    ],

    "recommendations": [
        "Recommendation 1",
        "Recommendation 2",
        "Recommendation 3"
    ]
}}
"""

    response = model.generate_content(prompt)

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

        # Check empty fields
        if not fullname or not email or not password or not confirm_password:
            return "All fields are required"

        # Check password match
        if password != confirm_password:
            return "Passwords do not match"

        # Check if email already exists
        existing_user = users.find_one({"email": email})

        if existing_user:
            return "Email already registered"

        # Hash password
        hashed_password = bcrypt.hashpw(
            password.encode("utf-8"),
            bcrypt.gensalt()
        )

        # Insert user
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

        # Find user
        user = users.find_one({"email": email})

        # Verify password
        if user and bcrypt.checkpw(
            password.encode("utf-8"),
            user["password"]
        ):
            session["email"] = user["email"]
            return render_template("homelog.html")

        return "Invalid Email or Password"

    return render_template("login.html")


# Privacy Policy
@app.route("/privacy")
def privacy():
    return render_template("privacy.html")


# Terms of Service
@app.route("/termsofservice")
def termsofservice():
    return render_template("termsofservice.html")


# Contact
@app.route("/contact")
def contact():
    return render_template("contact.html")


# Feedback
@app.route("/feedback", methods=["GET", "POST"])
def feedback():

    if request.method == "POST":

        suggestion = request.form.get("suggestion")

        feedbacks_collection.insert_one({
            "suggestion": suggestion
        })

        print("✅ Feedback Submitted Successfully!")

        return redirect(url_for("thankyou"))

    return render_template("feedback.html")


# Thank You
@app.route("/thankyou")
def thankyou():
    return render_template("thankyou.html")


# Get Started
@app.route("/getstarted")
def getstarted():
    return render_template("getstarted.html")


# Home After Login
@app.route("/homelog")
def homelog():
    return render_template("homelog.html")

#logout
@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("home"))

#Upload Page
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

                # If normal PDF
                if page_text.strip():
                    text += page_text

                # If scanned PDF
                else:
                    pix = page.get_pixmap(dpi=300)

                    image_path = "temp_page.png"

                    pix.save(image_path)

                    img = Image.open(image_path)

                    text += pytesseract.image_to_string(img)

                    os.remove(image_path)

        pdf.close()
        # Analyze resume using AI


        # Store in MongoDB
        resumes_collection.insert_one({
            "email": session.get("email"),

            "filename": filename,

            "resume_text": text,

            "uploaded_at": datetime.utcnow()

        })

        print("✅ Resume uploaded successfully!")

        return redirect(url_for("loading"))

    return render_template("upload.html")

#Interview Preparation Page

@app.route("/interview")
def interview():
    return render_template("interview.html")
    
#loading Page
@app.route("/loading")
def loading():
    return render_template("analysis.html")
       
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

    ai_result = analyze_resume_with_ai(
        latest_resume["resume_text"]
    )

    print(ai_result)

    resumes_collection.update_one(
        {"_id": latest_resume["_id"]},
        {
            "$set": {
                "ai_result": ai_result
            }
        }
    )

    return redirect(url_for("resume_analysis"))

# User Profile Page
@app.route("/profile")
def profile():

    user_email = session.get("email")

    if not user_email:
        return redirect(url_for("login"))

    user = users.find_one({"email": user_email})

    return render_template("profile.html", user=user)


# Update Profile
@app.route("/update_profile", methods=["POST"])
def update_profile():

    user_email = session.get("email")

    if not user_email:
        return redirect(url_for("login"))

    users.update_one(
        {"email": user_email},
        {
            "$set": {
                "fullname": request.form["fullname"],
                "phone": request.form["phone"],
                "username": request.form["username"],
                "job_role": request.form["job_role"],
                "location": request.form["location"],
                "about": request.form["about"],
                "linkedin": request.form["linkedin"]
            }
        }
    )

    return redirect(url_for("homelog"))
# Resume Analysis Report
@app.route("/resume_analysis")
def resume_analysis():

    latest_resume = resumes_collection.find_one(
        {"email": session.get("email")},
        sort=[("uploaded_at", -1)]
    )

    if not latest_resume:
        return redirect(url_for("upload"))

    return render_template(
        "resume analysis.html",
        resume=latest_resume,
        ai=latest_resume.get("ai_result")
    )

#interview questions
@app.route("/interviewquestion")
def interviewquestion():
    return render_template("interviewquestion.html")

#interview Guide
@app.route("/interviewguide")
def interviewguide():
    return render_template("interviewguide.html")

#Mock
@app.route("/mock")
def mock():

    questions = session.get("questions", [])

    return render_template(
        "mock.html",
        questions=questions
    )
# AI Mock
@app.route("/aimock", methods=["GET", "POST"])
def aimock():

    if request.method == "POST":

        role = request.form["role"]
        experience = request.form["experience"]
        interview_type = request.form["interview_type"]
        difficulty = request.form["difficulty"]
        total_questions = int(request.form["total_questions"])

        questions = generate_interview_questions(
            role,
            experience,
            interview_type,
            difficulty,
            total_questions
        )

        session["questions"] = questions
        session["current_question"] = 0

        return redirect(url_for("logolod"))

    return render_template("aimock.html")

#voicelod
@app.route("/voicelod")
def voicelod():
    return render_template("voicelod.html")    

#logolod
@app.route("/logolod")
def logolod():
    return render_template("logolod.html")

@app.route("/save_answers", methods=["POST"])
def save_answers():
    data = request.get_json()

    session["answers"] = data.get("answers", [])
    session["questions"] = data.get("questions", [])

    print("Questions:", session["questions"])
    print("Answers:", session["answers"])

    return {"status": "success"}

#performance
@app.route("/performance")
def performance():

    questions = session.get("questions", [])
    answers = session.get("answers", [])

    if not questions or not answers:
        return redirect(url_for("mock"))

    try:
        ai = analyze_interview_performance(
            questions,
            answers
        )

        return render_template(
            "performance.html",
            ai=ai
        )

    except Exception as e:
        print("Gemini Error:", e)

        return render_template(
            "performance.html",
            ai={
                "overall_score": 0,
                "communication": 0,
                "technical": 0,
                "confidence": 0,
                "problem_solving": 0,
                "grade": "N/A",
                "summary": "AI analysis unavailable.",
                "strengths": [],
                "improvements": [],
                "recommendations": []
            }
        )
# fone
@app.route("/fone", methods=["GET", "POST"])
def fone():

    if request.method == "POST":

        email = request.form["email"]

        # Check if email exists
        user = users.find_one({"email": email})

        if not user:
            return "Email not found"

        # Generate 4-digit OTP
        otp = str(random.randint(1000, 9999))

        # Save OTP and email in session
        session["otp"] = otp
        session["reset_email"] = email

        # Send OTP email
        try:

            msg = Message(
                "Intervexa Password Reset OTP",
                sender=app.config["MAIL_USERNAME"],
                recipients=[email]
            )

            msg.body = f"""
Hello,

Your OTP for password reset is:

{otp}

This OTP will be used to reset your password.

Regards,
Intervexa Team
"""

            mail.send(msg)

            print("✅ OTP SENT:", otp)

        except Exception as e:

            print("❌ EMAIL ERROR:", e)

            return f"Email Error: {e}"

        return redirect(url_for("ftwo"))

    return render_template("fone.html")

#ftwo
@app.route("/ftwo", methods=["GET", "POST"])
def ftwo():

    if request.method == "POST":

        entered_otp = request.form["otp"]

        if entered_otp == session.get("otp"):
            return redirect(url_for("fthree"))

        return "Invalid OTP"

    return render_template("ftwo.html")

#fthree
@app.route("/fthree", methods=["GET", "POST"])
def fthree():

    if request.method == "POST":

        password = request.form["password"]

        email = session.get("reset_email")

        if not email:
            return redirect(url_for("login"))

        hashed_password = bcrypt.hashpw(
            password.encode("utf-8"),
            bcrypt.gensalt()
        )

        users.update_one(
            {"email": email},
            {
                "$set": {
                    "password": hashed_password
                }
            }
        )

        session.pop("otp", None)
        session.pop("reset_email", None)

        return redirect(url_for("login"))

    return render_template("fthree.html")

if __name__ == "__main__":
    app.run(debug=True)