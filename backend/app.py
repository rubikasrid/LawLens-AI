import os
from pathlib import Path
from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import create_engine, Column, Integer, String
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from pydantic import BaseModel

# --- 1. DATABASE CONFIGURATION ---
BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "lawlens.db"
SQLALCHEMY_DATABASE_URL = f"sqlite:///{DB_PATH}"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL, 
    connect_args={"check_same_thread": False}
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# --- 2. DATABASE MODELS (Embedded directly to avoid import errors) ---
class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True, nullable=False)
    password = Column(String, nullable=False)

# Create Database Tables Automatically
Base.metadata.create_all(bind=engine)

# --- 3. FASTAPI APP SETUP ---
app = FastAPI(
    title="LawLens AI Backend API",
    description="API for LawLens AI application",
    version="1.0.0"
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Dependency to get DB session
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Request Schema
class UserAuthSchema(BaseModel):
    username: str
    password: str
    email: str | None = None

# --- 4. API ROUTES ---
@app.get("/")
def root():
    return {"status": "ok", "message": "LawLens AI Backend API is operational"}

@app.get("/health")
def health_check():
    return {"status": "healthy"}

@app.post("/register")
def register(user: UserAuthSchema, db: Session = Depends(get_db)):
    existing_user = db.query(User).filter(User.username == user.username).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username already exists"
        )
    
    new_user = User(username=user.username, password=user.password)
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return {"message": "User registered successfully", "username": new_user.username}

@app.post("/login")
def login(user: UserAuthSchema, db: Session = Depends(get_db)):
    db_user = db.query(User).filter(
        User.username == user.username,
        User.password == user.password
    ).first()
    
    if not db_user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password"
        )
    
    return {"message": "Login successful", "username": db_user.username}