from flask import Flask, request, send_file
import pytesseract
from PIL import Image
from reportlab.pdfgen import canvas
import requests
from datetime import datetime
import os

app = Flask(__name__)

UPLOAD_FOLDER = "uploads"

if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

# Tesseract OCR path
pytesseract.pytesseract.tesseract_cmd = (
    r"C:\Program Files\Tesseract-OCR\tesseract.exe"
)

# Store latest report
latest_result = ""
latest_score = 0
latest_reasons = []
latest_advice = ""
latest_website = ""


# Scam detection
def calculate_scam_score(text):

    score = 0
    reasons = []

    text = text.lower()

    keyword_reasons = {
        "pay fee":
        "🚩 Payment request detected",

        "registration fee":
        "🚩 Registration fee detected",

        "urgent":
        "🚩 Urgent wording found",

        "limited seats":
        "🚩 Limited seats pressure found",

        "guaranteed job":
        "🚩 Unrealistic promise detected",

        "pay ₹":
        "🚩 Money request found",

        "payment required":
        "🚩 Payment required detected",

        "confirm seat":
        "🚩 Seat confirmation pressure",

        "processing fee":
        "🚩 Processing fee found"
    }

    for word, reason in keyword_reasons.items():

        if word in text:
            score += 15
            reasons.append(reason)

    if score > 100:
        score = 100

    return score, reasons


# Website checker
def check_website(url):

    risk = 0
    reasons = []

    url = url.lower()

    suspicious_domains = [
        ".xyz",
        ".top",
        ".click",
        ".loan",
        ".buzz"
    ]

    if url and not url.startswith(
        "https://"
    ):

        risk += 20

        reasons.append(
            "🚩 HTTPS missing"
        )

    for domain in suspicious_domains:

        if domain in url:

            risk += 20

            reasons.append(
                f"🚩 Suspicious domain: {domain}"
            )

    return risk, reasons


@app.route("/")
def home():

    return """
    <html>

    <head>

    <title>
    Smart Internship Scam Detector
    </title>

    <style>
*{
    margin:0;
    padding:0;
    box-sizing:border-box;
    font-family: 'Segoe UI', sans-serif;
}

body{
    background: linear-gradient(135deg, #0f2027, #203a43, #2c5364);
    min-height:100vh;
    display:flex;
    justify-content:center;
    align-items:center;
    padding:30px;
}

.container{
    width:90%;
    max-width:900px;
    background: rgba(255,255,255,0.12);
    backdrop-filter: blur(18px);
    border-radius:25px;
    padding:40px;
    color:white;
    box-shadow: 0 8px 32px rgba(0,0,0,0.3);
    border:1px solid rgba(255,255,255,0.2);
    text-align:center;
}

h1{
    font-size:48px;
    color:#ff6b6b;
    margin-bottom:10px;
}

h2{
    margin-top:20px;
    margin-bottom:15px;
    color:#ffffff;
}

.score{
    font-size:32px;
    font-weight:bold;
    margin:20px 0;
}

.progress-bar{
    width:100%;
    height:24px;
    background:#dcdcdc;
    border-radius:50px;
    overflow:hidden;
    margin:20px 0;
}

.progress{
    height:100%;
    background: linear-gradient(to right, #ff416c, #ff4b2b);
    border-radius:50px;
    transition:1s ease;
}

ul{
    list-style:none;
    margin-top:10px;
}

ul li{
    background: rgba(255,255,255,0.1);
    padding:12px;
    border-radius:12px;
    margin:10px 0;
    font-size:18px;
}

.advice{
    background: rgba(255,255,255,0.1);
    padding:20px;
    border-radius:20px;
    margin-top:25px;
}

button, .btn{
    box-shadow: 0 0 20px rgba(255,75,43,0.5);
    font-weight:bold;
    border:none;
    outline:none;
    background: linear-gradient(to right, #ff416c, #ff4b2b);
    color:white;
    padding:14px 28px;
    border-radius:50px;
    font-size:18px;
    cursor:pointer;
    margin-top:20px;
    transition:0.3s;
    text-decoration:none;
    display:inline-block;
}

button:hover, .btn:hover{
    transform:scale(1.05);
}

input, textarea{
    width:100%;
    padding:16px;
    border:none;
    border-radius:15px;
    margin:12px 0;
    font-size:16px;
    background: rgba(255,255,255,0.15);
    color:white;
}
input[type="file"]{
    background: rgba(255,255,255,0.12);
    padding:12px;
    border-radius:15px;
    color:white;
    border:1px solid rgba(255,255,255,0.2);

input::placeholder,
textarea::placeholder{
    color:#ddd;
}

label{
    font-size:18px;
    font-weight:bold;
    display:block;
    margin-top:15px;
    text-align:left;
}

.risk-high{
    color:#ff4b5c;
}

.risk-medium{
    color:#ffc107;
}

.risk-safe{
    color:#4caf50;
}
</style>

    </head>

    <body>

    <div class="container">

    <h1>
    🛡 Smart Internship Scam Detector
    </h1>

    <p>
    Protecting Students from Fake Internships 🚀
    </p>

    <form
    method="POST"
    action="/check"
    enctype="multipart/form-data">

    <h3>
    Paste Internship Message
    </h3>

    <textarea
    name="message"
    placeholder=
    "Paste internship message here">
    </textarea>

    <h3>
    Company Website
    </h3>

    <input
    type="text"
    name="website"
    placeholder=
    "https://company.com">

    <h3>
    Upload Screenshot
    </h3>

    <input
    type="file"
    name="screenshot">

    <button type="submit" id="chechBtn">
    Check Scam Risk
    </button>

    </form>

    </div>
    <script>
document.querySelector("form").addEventListener("submit", function() {
    let btn = document.getElementById("checkBtn");

    btn.innerHTML = "⏳ Checking...";
    btn.disabled = true;
    btn.style.opacity = "0.8";

    setTimeout(() => {
        btn.innerHTML = "🔍 Analyzing...";
    }, 700);
});
</script>
    </body>
    </html>
    """
@app.route("/check", methods=["POST"])
def check():

    global latest_result
    global latest_score
    global latest_reasons
    global latest_advice
    global latest_website

    message = request.form["message"]
    website = request.form["website"]

    uploaded_file = request.files["screenshot"]

    # OCR Screenshot Reading
    if uploaded_file.filename != "":

        filepath = os.path.join(
            UPLOAD_FOLDER,
            uploaded_file.filename
        )

        uploaded_file.save(filepath)

        extracted_text = (
            pytesseract.image_to_string(
                Image.open(filepath)
            )
        )

        message += extracted_text

    # Scam score
    score, reasons = (
        calculate_scam_score(
            message
        )
    )

    website_risk, website_reasons = (
        check_website(
            website
        )
    )

    final_score = (
        score +
        website_risk
    )

    if final_score > 100:
        final_score = 100

    reasons.extend(
        website_reasons
    )

    # AI Advice
    if final_score >= 70:

        result = (
            "🚨 High Scam Risk"
        )

        color = "#ff3b30"

        advice = """
        ❌ Avoid This Internship.
        High chance of scam.
        Do not pay money.
        """

    elif final_score >= 40:

        result = (
            "⚠️ Suspicious"
        )

        color = "#ff9500"

        advice = """
        ⚠️ Be Careful.
        Verify company details.
        """

    else:

        result = "✅ Safe"

        color = "#34c759"

        advice = """
        ✅ Looks Safe.
        Still verify company profile.
        """

    # Save latest report
    latest_result = result
    latest_score = final_score
    latest_reasons = reasons
    latest_advice = advice
    latest_website = website

    reasons_html = "".join(
        f"<li>{reason}</li>"
        for reason in reasons
    )
            # Smart Company Check
    company_status = "⚠️ Suspicious"

    try:
        fake_domains = [".xyz", ".top", ".click", ".buzz", ".loan"]

        if website:
            if any(domain in website for domain in fake_domains):
                company_status = "❌ Fake / Suspicious Domain"

            else:
                check_url = website

                if not website.startswith("http"):
                    check_url = "https://" + website

                response = requests.get(check_url, timeout=5)

                if response.status_code == 200:
                    company_status = "✅ Real / Active Company Website"
                else:
                    company_status = "⚠️ Suspicious Website"

    except:
        company_status = "❌ Fake or Website Not Working"

    return f"""

    <html>

    <head>

    <style>

    body{{
        background:
        linear-gradient(
        135deg,
        #0f2027,
        #203a43,
        #2c5364
        );

        min-height:100vh;

        display:flex;
        justify-content:center;
        align-items:center;

        font-family:Arial;
    }}

    .box{{
        background:white;

        width:60%;

        padding:40px;

        border-radius:25px;

        text-align:center;
    }}

    h1{{
        color:{color};
        font-size:45px;
        text-shadow: 0 0 20px rgba(255, 80, 80, 0.5);
    }}

    .bar-container{{
        width:100%;
        height:30px;
        background:#ddd;
        border-radius:30px;
    }}

    .bar{{
        width:{final_score}%;
        height:30px;
        background:{color};
        border-radius:30px;
    }}

    ul{{
        list-style:none;
    }}

    li{{
        margin:10px;
        font-size:18px;
    }}

    .advice{{
        background:#f2f2f2;
        padding:20px;
        border-radius:15px;
        margin-top:20px;
        font-size:18px;
    }}

    a{{
        text-decoration:none;
        color:white;
        background:#ff512f;
        padding:15px 30px;
        border-radius:15px;
    }}

    </style>

    </head>

    <body>

    <div class="box">

    <h1>{result}</h1>

    <h2>
    Risk Score:
    {final_score}%
    </h2>

    <div class="bar-container">
    <div class="bar"></div>
    </div>

    <br>

    <h2>
    Why Suspicious?
    </h2>

    <ul>
    {reasons_html}
    </ul>

    <div class="advice">

    <h2>
    🤖 AI Advice
    </h2>

    {advice}
    <h3>🌐 Company Check:</h3>
    <p>{company_status}</p>

    </div>

    <br><br>

    <a href="/download-report">
    📄 Download PDF Report
    </a>

    <br><br>

    <a href="/">
    Check Again
    </a>

    </div>

    </body>
    </html>
    """


@app.route("/download-report")
def download_report():

    file_name = (
        "scam_report.pdf"
    )

    c = canvas.Canvas(
        file_name
    )

    c.setFont(
        "Helvetica-Bold",
        18
    )

    c.drawString(
        170,
        800,
        "Internship Scam Report"
    )

    c.setFont(
        "Helvetica",
        12
    )

    c.drawString(
        50,
        760,
        f"Generated: {datetime.now()}"
    )

    c.drawString(
        50,
        730,
        f"Result: {latest_result}"
    )

    c.drawString(
        50,
        700,
        f"Risk Score: {latest_score}%"
    )

    c.drawString(
        50,
        670,
        f"Website: {latest_website}"
    )

    c.drawString(
        50,
        640,
        "Reasons:"
    )

    y = 620

    for reason in latest_reasons:

        c.drawString(
            70,
            y,
            f"- {reason}"
        )

        y -= 20

    c.drawString(
        50,
        y - 20,
        "AI Advice:"
    )

    c.drawString(
        70,
        y - 40,
        latest_advice
    )

    c.save()

    return send_file(
        file_name,
        as_attachment=True
    )


if __name__ == "__main__":
    app.run(debug=True)