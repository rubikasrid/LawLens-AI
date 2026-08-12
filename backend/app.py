import os
import sys

# Ensure backend folder is in Python search path to resolve local imports on Render
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from pydantic import BaseModel

# Local module imports
import models  # type: ignore
from database import engine, SessionLocal  # type: ignore

# Automatically create database tables on startup
models.Base.metadata.create_all(bind=engine)

# Initialize FastAPI Application
app = FastAPI(
    title="LawLens AI Backend API",
    description="API for LawLens AI application",
    version="1.0.0"
)

# Enable Cross-Origin Resource Sharing (CORS)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Database Session Dependency
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Request Schemas
class UserAuthSchema(BaseModel):
    username: str
    password: str

# API Endpoints
@app.get("/")
def root():
    return {"status": "ok", "message": "LawLens AI Backend API is operational"}

@app.get("/health")
def health_check():
    return {"status": "healthy"}

@app.post("/register")
def register(user: UserAuthSchema, db: Session = Depends(get_db)):
    # Check if user already exists
    existing_user = db.query(models.User).filter(models.User.username == user.username).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username already exists"
        )
    
    # Register new user
    new_user = models.User(username=user.username, password=user.password)
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    
    return {"message": "User registered successfully", "username": new_user.username}

@app.post("/login")
def login(user: UserAuthSchema, db: Session = Depends(get_db)):
    # Authenticate user credentials
    db_user = db.query(models.User).filter(
        models.User.username == user.username,
        models.User.password == user.password
    ).first()
    
    if not db_user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password"
        )
    
    return {"message": "Login successful", "username": db_user.username}