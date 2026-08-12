import os
import io
import re
import json
import uuid
import urllib.request
import urllib.parse
from pathlib import Path
from typing import Optional, Any, Dict, List
from pathlib import Path
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi import FastAPI, HTTPException, UploadFile, File, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse

from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

try:
    from deep_translator import GoogleTranslator
    HAS_DEEP_TRANSLATOR = True
except ImportError:
    HAS_DEEP_TRANSLATOR = False

# Initialize FastAPI App
app = FastAPI(title="LawLens AI Backend API")

import sys
from pathlib import Path
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Ensure the backend directory is in Python's search path
BACKEND_DIR = Path(__file__).resolve().parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

# Import local modules
import models  # type: ignore
from database import engine

# Initialize FastAPI App
app = FastAPI(title="LawLens AI Backend API")

# Automatically create database tables on startup
models.Base.metadata.create_all(bind=engine)

# CORS Configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Folder Setup
BASE_DIR = Path(__file__).resolve().parent
ASSETS_FOLDER = BASE_DIR / "assets"
REPORT_FOLDER = BASE_DIR / "reports"
FONTS_FOLDER = BASE_DIR / "fonts"

ASSETS_FOLDER.mkdir(parents=True, exist_ok=True)
REPORT_FOLDER.mkdir(parents=True, exist_ok=True)
FONTS_FOLDER.mkdir(parents=True, exist_ok=True)

# Static Font File Paths
FONT_HINDI = FONTS_FOLDER / "NotoSansDevanagari-Regular.ttf"
FONT_TAMIL = FONTS_FOLDER / "NotoSansTamil-Regular.ttf"


def is_valid_ttf(path: Path) -> bool:
    """Checks if file exists, is over 50KB, and has valid TTF/OTF magic bytes."""
    if not path.exists() or path.stat().st_size < 50000:
        return False
    try:
        with open(path, "rb") as f:
            header = f.read(4)
            return header in [b"\x00\x01\x00\x00", b"OTTO", b"true", b"typ1"]
    except Exception:
        return False


def ensure_unicode_fonts():
    """Downloads valid static TTF fonts for Devanagari and Tamil scripts."""
    font_sources = {
        FONT_HINDI: [
            "https://github.com/googlefonts/noto-fonts/raw/main/hinted/ttf/NotoSansDevanagari/NotoSansDevanagari-Regular.ttf",
            "https://raw.githubusercontent.com/google/fonts/main/ofl/notosansdevanagari/static/NotoSansDevanagari-Regular.ttf"
        ],
        FONT_TAMIL: [
            "https://github.com/googlefonts/noto-fonts/raw/main/hinted/ttf/NotoSansTamil/NotoSansTamil-Regular.ttf",
            "https://raw.githubusercontent.com/google/fonts/main/ofl/notosanstamil/static/NotoSansTamil-Regular.ttf"
        ]
    }

    for font_path, urls in font_sources.items():
        if not is_valid_ttf(font_path):
            if font_path.exists():
                try:
                    font_path.unlink()
                except Exception:
                    pass

            for url in urls:
                try:
                    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
                    with urllib.request.urlopen(req, timeout=15) as response:
                        content = response.read()
                        if len(content) > 50000 and content[:4] in [b"\x00\x01\x00\x00", b"OTTO", b"true"]:
                            with open(font_path, "wb") as out_file:
                                out_file.write(content)
                            print(f"Successfully downloaded {font_path.name}")
                            break
                except Exception as e:
                    print(f"Download attempt failed for {font_path.name} from {url}: {e}")


ensure_unicode_fonts()


def register_reportlab_fonts():
    """Registers TTF fonts in ReportLab."""
    if is_valid_ttf(FONT_HINDI):
        try:
            pdfmetrics.registerFont(TTFont("HindiFont", str(FONT_HINDI)))
        except Exception as e:
            print(f"HindiFont registration error: {e}")

    if is_valid_ttf(FONT_TAMIL):
        try:
            pdfmetrics.registerFont(TTFont("TamilFont", str(FONT_TAMIL)))
        except Exception as e:
            print(f"TamilFont registration error: {e}")


register_reportlab_fonts()

# In-memory storage
HISTORY_DB: List[Dict[str, Any]] = []
USERS_DB: Dict[str, str] = {"rubikasrid": "password123"}


# --- CREDENTIAL PARSER ---

async def extract_credentials(request: Request) -> tuple:
    username = "rubikasrid"
    password = "password123"
    try:
        raw_body = await request.body()
        if raw_body:
            try:
                data = json.loads(raw_body.decode("utf-8"))
                if isinstance(data, dict):
                    username = data.get("username") or data.get("email") or data.get("user") or username
                    password = data.get("password") or data.get("pass") or password
                    return str(username), str(password)
            except Exception:
                pass

            try:
                parsed = urllib.parse.parse_qs(raw_body.decode("utf-8"))
                if parsed:
                    if "username" in parsed: username = parsed["username"][0]
                    elif "email" in parsed: username = parsed["email"][0]
                    elif "user" in parsed: username = parsed["user"][0]

                    if "password" in parsed: password = parsed["password"][0]
                    elif "pass" in parsed: password = parsed["pass"][0]
                    return str(username), str(password)
            except Exception:
                pass

        query_params = dict(request.query_params)
        if query_params:
            username = query_params.get("username") or query_params.get("email") or query_params.get("user") or username
            password = query_params.get("password") or query_params.get("pass") or password

    except Exception as e:
        print(f"Credential parsing notice: {e}")

    return str(username), str(password)


# --- AUTHENTICATION ENDPOINTS ---

@app.api_route("/login", methods=["GET", "POST", "OPTIONS"])
@app.api_route("/auth/login", methods=["GET", "POST", "OPTIONS"])
@app.api_route("/api/login", methods=["GET", "POST", "OPTIONS"])
@app.api_route("/token", methods=["GET", "POST", "OPTIONS"])
async def login_user(request: Request):
    username, password = await extract_credentials(request)
    USERS_DB[username] = password
    return JSONResponse(
        status_code=200,
        content={
            "status": "success",
            "access_token": "mock-jwt-token-12345",
            "token": "mock-jwt-token-12345",
            "token_type": "bearer",
            "user": {"id": 1, "username": username, "email": f"{username}@example.com"}
        }
    )


@app.api_route("/register", methods=["GET", "POST", "OPTIONS"])
@app.api_route("/auth/register", methods=["GET", "POST", "OPTIONS"])
async def register_user(request: Request):
    username, password = await extract_credentials(request)
    USERS_DB[username] = password
    return JSONResponse(
        status_code=200,
        content={
            "status": "success",
            "access_token": "mock-jwt-token-12345",
            "token": "mock-jwt-token-12345",
            "token_type": "bearer",
            "user": {"id": 1, "username": username, "email": f"{username}@example.com"}
        }
    )


# --- SCRIPT FORMATTER FOR REPORTLAB ---

def prepare_paragraph_markup(text: str, indic_font_name: str) -> str:
    if not text:
        return ""

    text = text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    text = text.replace("\u200b", "").replace("\xa0", " ")

    if indic_font_name == "Helvetica":
        return text

    tokens = re.split(r'([\u0900-\u097F\u0B80-\u0BFF]+)', text)
    formatted_chunks = []
    for token in tokens:
        if not token:
            continue
        if re.search(r'[\u0900-\u097F\u0B80-\u0BFF]', token):
            formatted_chunks.append(f'<font name="{indic_font_name}">{token}</font>')
        else:
            formatted_chunks.append(f'<font name="Helvetica">{token}</font>')

    return "".join(formatted_chunks)


# --- LANGUAGE TRANSLATION ENGINE ---

def get_language_code(target_lang: str) -> str:
    if not target_lang:
        return "en"
    clean = str(target_lang).lower().strip()
    if "tamil" in clean or "தமிழ்" in clean or clean == "ta": return "ta"
    if "hindi" in clean or "हिन्दी" in clean or "हिंदी" in clean or clean == "hi": return "hi"
    if "telugu" in clean or clean == "te": return "te"
    if "kannada" in clean or clean == "kn": return "kn"
    if "marathi" in clean or clean == "mr": return "mr"
    if "bengali" in clean or clean == "bn": return "bn"
    if "malayalam" in clean or clean == "ml": return "ml"
    if "spanish" in clean or clean == "es": return "es"
    if "french" in clean or clean == "fr": return "fr"
    if "german" in clean or clean == "de": return "de"
    return "en"


def translate_text(text: str, target_lang: str = "en") -> str:
    code = get_language_code(target_lang)
    if not text or code == "en":
        return text

    clean_input = " ".join(text.split())
    if not clean_input:
        return text

    CHUNK_SIZE = 350
    words = clean_input.split()
    chunks, current_chunk, current_len = [], [], 0

    for word in words:
        if current_len + len(word) + 1 > CHUNK_SIZE:
            chunks.append(" ".join(current_chunk))
            current_chunk = [word]
            current_len = len(word)
        else:
            current_chunk.append(word)
            current_len += len(word) + 1
    if current_chunk:
        chunks.append(" ".join(current_chunk))

    translated_chunks = []
    for chunk in chunks:
        translated_chunk = None
        if HAS_DEEP_TRANSLATOR:
            try:
                translated_chunk = GoogleTranslator(source="auto", target=code).translate(chunk)
            except Exception:
                pass

        if not translated_chunk:
            try:
                url = f"https://translate.googleapis.com/translate_a/single?client=gtx&sl=auto&tl={code}&dt=t&q=" + urllib.parse.quote(chunk)
                req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
                with urllib.request.urlopen(req, timeout=10) as resp:
                    data = json.loads(resp.read().decode("utf-8"))
                    translated_chunk = "".join([item[0] for item in data[0] if item and item[0]])
            except Exception:
                translated_chunk = chunk

        translated_chunks.append(translated_chunk or chunk)

    return " ".join(translated_chunks)


# --- DOCUMENT PARSER & ANALYZER ---

def extract_text_from_bytes(file_bytes: bytes, filename: str = "document.pdf") -> str:
    ext = os.path.splitext(filename)[1].lower()
    extracted = ""

    if ext == ".pdf":
        try:
            import pypdf
            reader = pypdf.PdfReader(io.BytesIO(file_bytes))
            extracted = " ".join([page.extract_text() or "" for page in reader.pages])
        except Exception:
            pass

    elif ext in [".docx", ".doc"]:
        try:
            import docx
            doc = docx.Document(io.BytesIO(file_bytes))
            extracted = " ".join([p.text for p in doc.paragraphs if p.text.strip()])
        except Exception:
            pass

    if not extracted.strip():
        try:
            extracted = file_bytes.decode("utf-8", errors="ignore")
        except Exception:
            extracted = ""

    return " ".join(extracted.split())


def analyze_document_text(text: str, target_language: str = "EN") -> Dict[str, Any]:
    clean_txt = " ".join(text.split())
    base_summary = clean_txt[:2000] if len(clean_txt) >= 10 else "Document uploaded successfully. Content analysis complete."

    risk_keywords = {
        "Termination Clause": (["terminate", "termination", "cancel"], "HIGH", "Ensure standard notice periods apply."),
        "Liability & Indemnity": (["indemnify", "indemnification", "liability"], "HIGH", "Ensure liability caps are clearly defined."),
        "Payment & Penalty Terms": (["penalty", "interest rate", "late fee"], "MEDIUM", "Verify payment terms and penalty rates."),
        "Confidentiality": (["confidential", "non-disclosure"], "LOW", "Confirm scope of non-disclosure terms.")
    }

    flagged_clauses = []
    for category, (keywords, risk_level, rec) in risk_keywords.items():
        if any(kw in clean_txt.lower() for kw in keywords):
            flagged_clauses.append({
                "category": translate_text(category, target_language),
                "risk_level": risk_level,
                "clause_text": translate_text(clean_txt[:200], target_language),
                "recommendation": translate_text(rec, target_language)
            })

    translated_summary = translate_text(base_summary, target_language)
    return {"summary": translated_summary, "risk_clauses": flagged_clauses}


# --- REPORTLAB PDF GENERATOR ---

def generate_pdf_file(summary_text: str) -> Path:
    pdf_path = REPORT_FOLDER / f"Report_{uuid.uuid4().hex[:8]}.pdf"
    
    doc = SimpleDocTemplate(
        str(pdf_path),
        pagesize=letter,
        rightMargin=36,
        leftMargin=36,
        topMargin=36,
        bottomMargin=36
    )

    styles = getSampleStyleSheet()
    
    indic_font = "Helvetica"
    if any("\u0900" <= c <= "\u097F" for c in summary_text) and is_valid_ttf(FONT_HINDI):
        indic_font = "HindiFont"
    elif any("\u0B80" <= c <= "\u0BFF" for c in summary_text) and is_valid_ttf(FONT_TAMIL):
        indic_font = "TamilFont"

    title_style = ParagraphStyle(
        'DocTitle',
        parent=styles['Heading1'],
        fontName='Helvetica-Bold',
        fontSize=18,
        leading=22,
        alignment=1,
        spaceAfter=15
    )
    
    header_style = ParagraphStyle(
        'SectionHeader',
        parent=styles['Heading2'],
        fontName='Helvetica-Bold',
        fontSize=14,
        leading=18,
        spaceAfter=10
    )
    
    body_style = ParagraphStyle(
        'BodyTextCustom',
        parent=styles['Normal'],
        fontName=indic_font if indic_font != "Helvetica" else 'Helvetica',
        fontSize=10,
        leading=15,
        spaceAfter=8
    )

    formatted_summary = prepare_paragraph_markup(summary_text, indic_font)

    story = [
        Paragraph("LawLens AI - Executive Report", title_style),
        Spacer(1, 10),
        Paragraph("Executive Summary:", header_style),
        Spacer(1, 5),
        Paragraph(formatted_summary, body_style)
    ]

    doc.build(story)
    return pdf_path


# --- API ENDPOINTS ---

BASE_DIR = Path(__file__).resolve().parent
FRONTEND_DIR = BASE_DIR.parent / "frontend"

@app.get("/")
def read_root():
    index_path = FRONTEND_DIR / "index.html"
    if index_path.exists():
        return FileResponse(index_path)
    return {"status": "ok", "message": "LawLens Backend API Running"}

if FRONTEND_DIR.exists():
    app.mount("/", StaticFiles(directory=str(FRONTEND_DIR), html=True), name="static")

@app.get("/history")
def get_history():
    return {"status": "success", "history": HISTORY_DB}


@app.post("/upload")
async def upload_document(
    request: Request,
    file: Optional[UploadFile] = File(None),
    document: Optional[UploadFile] = File(None),
    upload_file: Optional[UploadFile] = File(None),
):
    try:
        uploaded_file = file or document or upload_file
        
        form_data = {}
        try:
            form = await request.form()
            form_data = dict(form)
        except Exception:
            pass

        query_params = dict(request.query_params)
        all_params = {**query_params, **form_data}

        lang_keys = [
            "output_language", "target_language", "language", "lang",
            "target_lang", "output_lang", "targetLanguage", "outputLanguage"
        ]
        
        selected_lang = "EN"
        for key in lang_keys:
            if key in all_params and all_params[key]:
                selected_lang = str(all_params[key])
                break

        if not uploaded_file:
            for val in form_data.values():
                if isinstance(val, UploadFile):
                    uploaded_file = val
                    break

        if not uploaded_file:
            raise HTTPException(status_code=400, detail="No file uploaded.")

        filename = uploaded_file.filename or "uploaded_document.pdf"
        content = await uploaded_file.read()
        extracted_text = extract_text_from_bytes(content, filename)

        analysis = analyze_document_text(extracted_text, target_language=selected_lang)

        record = {
            "filename": filename,
            "status": "success",
            "language": selected_lang,
            "summary": analysis["summary"],
            "executive_summary": analysis["summary"],
            "risk_clauses": analysis["risk_clauses"],
            "risks": analysis["risk_clauses"],
            "risk_count": len(analysis["risk_clauses"])
        }

        HISTORY_DB.append(record)
        return record

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Upload processing failed: {str(e)}")


@app.api_route("/export-pdf", methods=["GET", "POST"])
@app.api_route("/export_pdf", methods=["GET", "POST"])
@app.api_route("/download-pdf", methods=["GET", "POST"])
@app.api_route("/download_pdf", methods=["GET", "POST"])
@app.api_route("/export", methods=["GET", "POST"])
async def export_pdf_report(request: Request):
    try:
        summary_text = ""
        try:
            body = await request.json()
            summary_text = body.get("summary") or body.get("executive_summary") or ""
        except Exception:
            pass

        if not summary_text:
            try:
                form = await request.form()
                summary_text = form.get("summary") or form.get("executive_summary") or ""
            except Exception:
                pass

        if not summary_text and HISTORY_DB:
            summary_text = HISTORY_DB[-1].get("summary", "")

        if not summary_text:
            summary_text = "LawLens Document Analysis Report - Content generated successfully."

        pdf_path = generate_pdf_file(summary_text)

        return FileResponse(
            path=str(pdf_path),
            media_type="application/pdf",
            filename="LawLens_Analysis_Report.pdf"
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"PDF Generation Failed: {str(e)}")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8001)