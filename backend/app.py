import io
import os
from typing import Optional
from fastapi import FastAPI, HTTPException, File, UploadFile, Form
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from pypdf import PdfReader
from deep_translator import GoogleTranslator
import openai

app = FastAPI(title="LawLens API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

users_db = {}

class UserAuth(BaseModel):
    username: str
    password: str
    email: Optional[str] = None

@app.get("/")
def read_root():
    return {"status": "LawLens API is running"}

@app.post("/register")
def register(user: UserAuth):
    if user.username in users_db:
        raise HTTPException(status_code=400, detail="Username already exists")
    users_db[user.username] = {"password": user.password, "email": user.email}
    return {"message": "User registered successfully!"}

@app.post("/login")
def login(user: UserAuth):
    stored_user = users_db.get(user.username)
    if not stored_user or stored_user["password"] != user.password:
        raise HTTPException(status_code=400, detail="Invalid username or password")
    return {"message": "Logged in successfully!"}

def generate_legal_summary(text: str) -> str:
    """Generates an executive legal summary using OpenAI API or key-phrase extraction fallback."""
    api_key = os.getenv("OPENAI_API_KEY")
    
    if api_key:
        try:
            client = openai.OpenAI(api_key=api_key)
            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {
                        "role": "system",
                        "content": "You are a legal AI assistant. Summarize key legal obligations, rights, liabilities, and important clauses in clean bullet points."
                    },
                    {"role": "user", "content": text[:4000]}  # Pass core document body
                ],
                max_tokens=350
            )
            return response.choices[0].message.content
        except Exception:
            pass  # Fallback to local extraction if API call fails
            
    # Key sentence extraction fallback (works completely offline without API keys)
    sentences = [s.strip() for s in text.split(".") if len(s.strip()) > 25]
    top_sentences = sentences[:4] if len(sentences) >= 4 else sentences
    if not top_sentences:
        return "No key clauses could be automatically extracted from this document."
    
    return "Executive Summary:\n" + "\n".join(f"• {s}." for s in top_sentences)

@app.post("/upload")
async def upload_document(
    file: UploadFile = File(...),
    target_lang: str = Form("en")
):
    if not file:
        raise HTTPException(status_code=400, detail="No file uploaded")
    
    contents = await file.read()
    extracted_text = ""

    # Extract text from PDF
    if file.filename.lower().endswith(".pdf"):
        try:
            pdf = PdfReader(io.BytesIO(contents))
            for page in pdf.pages:
                extracted_text += (page.extract_text() or "") + "\n"
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Failed to read PDF: {str(e)}")
    else:
        extracted_text = contents.decode("utf-8", errors="ignore")

    clean_text = extracted_text.strip()
    if not clean_text:
        raise HTTPException(status_code=400, detail="No readable text found in document.")

    # 1. Generate text summary
    english_summary = generate_legal_summary(clean_text)

    # 2. Translate summary if target language is Tamil ('ta') or Hindi ('hi')
    final_summary = english_summary
    if target_lang in ["ta", "hi"]:
        try:
            final_summary = GoogleTranslator(source="auto", target=target_lang).translate(english_summary)
        except Exception as e:
            final_summary = f"{english_summary}\n\n(Translation warning: {str(e)})"

    # Header tags by language
    lang_headers = {
        "en": "--- LAWLENS AI EXECUTIVE SUMMARY ---",
        "ta": "--- LAWLENS AI நிர்வாக சுருக்கம் ---",
        "hi": "--- LAWLENS AI कार्यकारी सारांश ---"
    }
    header = lang_headers.get(target_lang, "--- LAWLENS AI EXECUTIVE SUMMARY ---")

    formatted_output = (
        f"{header}\n"
        f"File Name: {file.filename}\n"
        f"Original Character Count: {len(clean_text)}\n"
        f"----------------------------------------\n\n"
        f"{final_summary}"
    )

    return {
        "message": "File analyzed and summarized successfully!",
        "filename": file.filename,
        "target_lang": target_lang,
        "summary": formatted_output
    }