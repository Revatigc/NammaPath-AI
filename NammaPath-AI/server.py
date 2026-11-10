"""NammaPath AI demo API. Local, deterministic workflows; no external AI claims."""
from __future__ import annotations
import json, sqlite3
import os
from contextlib import contextmanager
from datetime import date, timedelta
from pathlib import Path
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

ROOT = Path(__file__).parent
DB = Path(os.environ.get("NAMMAPATH_DB", ROOT / "nammapath.db"))
app = FastAPI(title="NammaPath AI Demo API", version="1.0.0")
cors_origins = [x.strip() for x in os.environ.get("NAMMAPATH_CORS_ORIGINS", "http://127.0.0.1:8000,http://localhost:8000").split(",") if x.strip()]
app.add_middleware(CORSMiddleware, allow_origins=cors_origins, allow_methods=["GET", "POST", "PATCH", "DELETE"], allow_headers=["Content-Type"])

OPPS = [
 {"id":"p1","title":"AI / ML Intern","company":"Northstar Labs","location":"Bengaluru","mode":"Hybrid","type":"Internship","pay":"₹20,000–₹30,000 / month","skills":["Python","Machine Learning","SQL"],"source":"Sample listing · fictional employer","verification":"Needs review"},
 {"id":"p2","title":"Data Science Intern","company":"Cedar Analytics","location":"Bengaluru","mode":"On-site","type":"Internship","pay":"₹18,000 / month","skills":["Python","SQL","Statistics"],"source":"Sample listing · fictional employer","verification":"Needs review"},
 {"id":"p3","title":"Graduate Software Engineer","company":"BluePeak Digital","location":"Bengaluru","mode":"Hybrid","type":"Graduate role","pay":"₹6–8 LPA","skills":["Python","APIs","Git"],"source":"Sample listing · fictional employer","verification":"Needs review"},
 {"id":"p4","title":"AI Product Apprentice","company":"Mitra Works","location":"Bengaluru","mode":"Hybrid","type":"Apprenticeship","pay":"₹15,000 / month","skills":["Python","Communication","SQL"],"source":"Sample listing · fictional employer","verification":"Needs review"},
 {"id":"p5","title":"Junior Data Analyst","company":"Orbit Retail Tech","location":"Bengaluru","mode":"On-site","type":"Graduate role","pay":"₹4.5–6 LPA","skills":["SQL","Python","Excel"],"source":"Sample listing · fictional employer","verification":"Needs review"},
 {"id":"p6","title":"Python Developer Trainee","company":"Kaveri Systems","location":"Bengaluru","mode":"Remote","type":"Apprenticeship","pay":"₹12,000 / month","skills":["Python","Git"],"source":"Sample listing · fictional employer","verification":"Needs review"},
]

def db():
    con = sqlite3.connect(DB); con.row_factory = sqlite3.Row
    con.execute("CREATE TABLE IF NOT EXISTS applications (id TEXT PRIMARY KEY, title TEXT NOT NULL, company TEXT NOT NULL, status TEXT NOT NULL DEFAULT 'Saved', created_at TEXT NOT NULL)")
    con.execute("CREATE TABLE IF NOT EXISTS reports (id INTEGER PRIMARY KEY AUTOINCREMENT, listing_id TEXT, details TEXT NOT NULL, created_at TEXT NOT NULL)")
    con.commit(); return con

@contextmanager
def connection():
    con = db()
    try:
        yield con
        con.commit()
    except Exception:
        con.rollback()
        raise
    finally:
        con.close()

class Application(BaseModel):
    opportunity_id: str
class StatusUpdate(BaseModel):
    status: str = Field(pattern="^(Saved|Preparing|Applied|Interview|Offer|Rejected)$")
class Report(BaseModel):
    listing_id: str = ""
    details: str = Field(min_length=5, max_length=2000)
class Chat(BaseModel):
    message: str = Field(min_length=1, max_length=2000)
    language: str = "English"
    skills: list[str] = Field(default_factory=list)

@app.get("/api/health")
def health(): return {"status":"ok","service":"NammaPath AI demo API","today":date.today().isoformat()}

def add_match_fields(item: dict, skills: list[str]):
    mine = {s.strip().casefold() for s in skills if s.strip()}
    required = item["skills"]
    matched = [skill for skill in required if skill.casefold() in mine]
    gaps = [skill for skill in required if skill.casefold() not in mine]
    result = {**item, "matched_skills": matched, "gaps": gaps,
              "score": round(len(matched) / len(required) * 100) if required else 0,
              "deadline": (date.today() + timedelta(days=14 + int(item["id"][1:]) * 3)).isoformat()}
    return result

@app.get("/api/opportunities")
def opportunities(q: str = "", type: str = "", mode: str = "", skills: str = ""):
    q = q.casefold()
    user_skills = [x.strip() for x in skills.split(",") if x.strip()]
    found = [o for o in OPPS if (not q or q in json.dumps(o, ensure_ascii=False).casefold()) and (not type or o["type"] == type) and (not mode or o["mode"] == mode)]
    return sorted((add_match_fields(o, user_skills) for o in found), key=lambda o: o["score"], reverse=True)

@app.get("/api/opportunities/{opportunity_id}")
def opportunity(opportunity_id: str, skills: str = ""):
    item = next((x for x in OPPS if x["id"] == opportunity_id), None)
    if not item: raise HTTPException(404, "Opportunity not found")
    return add_match_fields(item, [x.strip() for x in skills.split(",") if x.strip()])

@app.get("/api/roadmap")
def roadmap():
    return {"weeks":3,"items":[{"week":1,"goal":"FastAPI basics and REST APIs","task":"Create a small Python API and document two endpoints."},{"week":1,"goal":"SQL joins and data modeling","task":"Query a public dataset and explain three useful findings."},{"week":2,"goal":"Deploy a model with Docker","task":"Package a simple model behind an API."},{"week":2,"goal":"Publish a reproducible project","task":"Add a clear README, setup steps and sample output."},{"week":3,"goal":"Practice ML interview concepts","task":"Review evaluation metrics, overfitting and validation."},{"week":3,"goal":"Tailor your application","task":"Review your resume against one selected opportunity."}]}

def advice(message: str, language: str, skills: list[str]):
    text = message.casefold()
    if any(w in text for w in ("safe","scam","trust","fee","red flag")):
        intent = "trust"
    elif any(w in text for w in ("job","intern","role","opportun","find")):
        intent = "opportunities"
    elif any(w in text for w in ("skill","learn","gap","roadmap")):
        intent = "skills"
    elif any(w in text for w in ("resume","cover","application","apply")):
        intent = "application"
    else:
        intent = "general"
    catalog = {
      "English": {
        "trust":"These listings need review because the employer and vacancy are not independently verified. Check the official company domain and never pay an upfront application fee.",
        "opportunities":"I can show sample Bengaluru opportunities matched against the skills you provided. These are fictional demo listings, not verified vacancies.",
        "skills":"Share your skills in your profile to see computed overlaps and gaps. The roadmap suggests practice projects for missing skills.",
        "application":"I can offer application preparation guidance. Review every draft yourself; nothing is submitted automatically.",
        "general":"I can help explore sample roles, review skill matches, plan learning, or prepare an application."
      },
      "ಕನ್ನಡ": {
        "trust":"ಈ ಪಟ್ಟಿಗಳಿಗೆ ಪರಿಶೀಲನೆ ಅಗತ್ಯ: ಉದ್ಯೋಗದಾತ ಮತ್ತು ಹುದ್ದೆಯನ್ನು ಸ್ವತಂತ್ರವಾಗಿ ದೃಢಪಡಿಸಿಲ್ಲ. ಕಂಪನಿಯ ಅಧಿಕೃತ ವೆಬ್‌ಸೈಟ್ ಪರಿಶೀಲಿಸಿ; ಅರ್ಜಿ ಅಥವಾ ಸಂದರ್ಶನಕ್ಕಾಗಿ ಮುಂಗಡ ಶುಲ್ಕ ಪಾವತಿಸಬೇಡಿ.",
        "opportunities":"ನೀವು ನೀಡಿದ ಕೌಶಲ್ಯಗಳಿಗೆ ಹೊಂದುವ ಬೆಂಗಳೂರಿನ ಮಾದರಿ ಅವಕಾಶಗಳನ್ನು ತೋರಿಸಬಹುದು. ಇವು ಕಲ್ಪಿತ ಡೆಮೋ ಪಟ್ಟಿಗಳು; ದೃಢೀಕೃತ ಹುದ್ದೆಗಳಲ್ಲ.",
        "skills":"ನಿಮ್ಮ ಪ್ರೊಫೈಲ್‌ನಲ್ಲಿ ಕೌಶಲ್ಯಗಳನ್ನು ಸೇರಿಸಿ; ಹೊಂದಾಣಿಕೆ ಮತ್ತು ಕೊರತೆಗಳನ್ನು ಲೆಕ್ಕ ಹಾಕುತ್ತೇನೆ. ಕಲಿಕಾ ಯೋಜನೆಯಲ್ಲಿ ಅಭ್ಯಾಸ ಯೋಜನೆಗಳಿವೆ.",
        "application":"ಅರ್ಜಿ ತಯಾರಿಸಲು ಮಾರ್ಗದರ್ಶನ ನೀಡಬಹುದು. ಪ್ರತಿಯೊಂದು ಕರಡನ್ನು ನೀವೇ ಪರಿಶೀಲಿಸಿ; ಯಾವುದನ್ನೂ ಸ್ವಯಂಚಾಲಿತವಾಗಿ ಸಲ್ಲಿಸುವುದಿಲ್ಲ.",
        "general":"ಮಾದರಿ ಹುದ್ದೆಗಳನ್ನು ಹುಡುಕಲು, ಕೌಶಲ್ಯ ಹೊಂದಾಣಿಕೆ ನೋಡಲು, ಕಲಿಕೆ ಯೋಜಿಸಲು ಅಥವಾ ಅರ್ಜಿ ತಯಾರಿಸಲು ಸಹಾಯ ಮಾಡಬಹುದು."
      },
      "हिन्दी": {
        "trust":"इन सूचियों की जाँच ज़रूरी है: नियोक्ता और पद की स्वतंत्र पुष्टि नहीं हुई है। कंपनी की आधिकारिक वेबसाइट देखें और आवेदन या इंटरव्यू के लिए अग्रिम शुल्क न दें।",
        "opportunities":"आपके दिए कौशलों से मेल खाते बेंगलुरु के नमूना अवसर दिखा सकता हूँ। ये काल्पनिक डेमो सूचियाँ हैं, सत्यापित रिक्तियाँ नहीं।",
        "skills":"कौशलों को अपनी प्रोफ़ाइल में जोड़ें; मैं मेल और कमियों की गणना करूँगा। सीखने की योजना में अभ्यास परियोजनाएँ हैं।",
        "application":"आवेदन तैयार करने में मार्गदर्शन दे सकता हूँ। हर मसौदे की समीक्षा स्वयं करें; कुछ भी अपने आप जमा नहीं होगा।",
        "general":"मैं नमूना अवसर खोजने, कौशल मिलान देखने, सीखने की योजना बनाने या आवेदन तैयार करने में मदद कर सकता हूँ।"
      }
    }
    chosen = catalog.get(language, catalog["English"])[intent]
    if intent == "skills" and skills:
        chosen += " Skills on your profile: " + ", ".join(skills[:12]) + "."
    return chosen

@app.post("/api/pathfinder")
def pathfinder(payload: Chat):
    return {"mode":"rule-based demo assistant","reply":advice(payload.message, payload.language, payload.skills),"disclaimer":"This assistant uses keyword routing and prepared guidance, not a generative AI model. Demo listings are not verified."}

@app.get("/api/applications")
def applications():
    with connection() as con: return [dict(r) for r in con.execute("SELECT * FROM applications ORDER BY created_at DESC")]

@app.post("/api/applications", status_code=201)
def add_application(payload: Application):
    item = next((o for o in OPPS if o["id"] == payload.opportunity_id), None)
    if not item: raise HTTPException(404, "Opportunity not found")
    try:
        with connection() as con: con.execute("INSERT INTO applications VALUES (?,?,?,?,?)", (item["id"],item["title"],item["company"],"Saved",date.today().isoformat()))
    except sqlite3.IntegrityError: raise HTTPException(409, "Already tracked")
    return {"id":item["id"],"title":item["title"],"status":"Saved"}

@app.patch("/api/applications/{app_id}")
def update_application(app_id: str, payload: StatusUpdate):
    with connection() as con:
        cur = con.execute("UPDATE applications SET status=? WHERE id=?", (payload.status,app_id))
        if not cur.rowcount: raise HTTPException(404,"Application not found")
    return {"id":app_id,"status":payload.status}

@app.delete("/api/applications/{app_id}")
def delete_application(app_id: str):
    with connection() as con:
        cur=con.execute("DELETE FROM applications WHERE id=?",(app_id,))
        if not cur.rowcount: raise HTTPException(404,"Application not found")
    return {"deleted":True}

@app.post("/api/reports", status_code=201)
def report(payload: Report):
    with connection() as con: cur=con.execute("INSERT INTO reports (listing_id,details,created_at) VALUES (?,?,?)",(payload.listing_id,payload.details,date.today().isoformat())); ident=cur.lastrowid
    return {"id":ident,"status":"received","storage":"local demo database"}

@app.get("/")
def home(): return FileResponse(ROOT / "index.html")

@app.get("/app.js")
def frontend_script(): return FileResponse(ROOT / "frontend.js", media_type="text/javascript")
