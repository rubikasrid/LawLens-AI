import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).resolve().parent / "lawlens.db"

def init_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Users table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            email TEXT UNIQUE NOT NULL,
            hashed_password TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # Uploads table with user_id foreign key
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS uploads (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            filename TEXT NOT NULL,
            summary TEXT NOT NULL,
            risk_count INTEGER NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
    """)
    conn.commit()
    conn.close()

def create_user(username: str, email: str, hashed_password: str):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    try:
        cursor.execute(
            "INSERT INTO users (username, email, hashed_password) VALUES (?, ?, ?)",
            (username, email, hashed_password)
        )
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        return False
    finally:
        conn.close()

def get_user_by_username(username: str):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT id, username, email, hashed_password FROM users WHERE username = ?", (username,))
    row = cursor.fetchone()
    conn.close()
    if row:
        return {"id": row[0], "username": row[1], "email": row[2], "hashed_password": row[3]}
    return None

def save_upload(filename: str, summary: str, risk_count: int, user_id: int):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO uploads (user_id, filename, summary, risk_count)
        VALUES (?, ?, ?, ?)
    """, (user_id, filename, summary, risk_count))
    conn.commit()
    conn.close()

def get_history(user_id: int):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        SELECT id, filename, summary, risk_count, created_at 
        FROM uploads 
        WHERE user_id = ?
        ORDER BY id DESC 
        LIMIT 10
    """, (user_id,))
    rows = cursor.fetchall()
    conn.close()

    return [
        {
            "id": r[0],
            "filename": r[1],
            "summary": r[2],
            "risk_count": r[3],
            "created_at": r[4]
        }
        for r in rows
    ]