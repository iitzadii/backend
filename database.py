import sqlite3
import json
import secrets
from datetime import datetime
import os

DB_PATH = os.path.join(os.path.dirname(__file__), "database.db")

def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Enable foreign keys
    cursor.execute("PRAGMA foreign_keys = ON;")
    
    # Create tables
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id TEXT PRIMARY KEY,
        name TEXT NOT NULL,
        email TEXT UNIQUE NOT NULL,
        password_hash TEXT NOT NULL,
        created_at TEXT NOT NULL
    );
    """)
    
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS sessions (
        token TEXT PRIMARY KEY,
        user_id TEXT NOT NULL,
        created_at TEXT NOT NULL,
        FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
    );
    """)
    
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS assessments (
        id TEXT PRIMARY KEY,
        user_id TEXT NOT NULL,
        answers TEXT NOT NULL,
        date TEXT NOT NULL,
        FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
    );
    """)
    
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS saved_careers (
        user_id TEXT NOT NULL,
        career_id TEXT NOT NULL,
        saved_at TEXT NOT NULL,
        PRIMARY KEY (user_id, career_id),
        FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
    );
    """)
    
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS activity (
        id TEXT PRIMARY KEY,
        user_id TEXT NOT NULL,
        message TEXT NOT NULL,
        at TEXT NOT NULL,
        FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
    );
    """)
    
    conn.commit()
    conn.close()

# User helpers
def get_user_by_email(email):
    conn = get_db_connection()
    user = conn.execute("SELECT * FROM users WHERE LOWER(email) = LOWER(?)", (email,)).fetchone()
    conn.close()
    return dict(user) if user else None

def get_user_by_id(user_id):
    conn = get_db_connection()
    user = conn.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
    conn.close()
    return dict(user) if user else None

def create_user(user_id, name, email, password_hash):
    conn = get_db_connection()
    created_at = datetime.utcnow().isoformat() + "Z"
    try:
        conn.execute(
            "INSERT INTO users (id, name, email, password_hash, created_at) VALUES (?, ?, ?, ?, ?)",
            (user_id, name, email, password_hash, created_at)
        )
        conn.commit()
        return {"id": user_id, "name": name, "email": email, "createdAt": created_at}
    finally:
        conn.close()

def update_user_profile(user_id, name):
    conn = get_db_connection()
    try:
        conn.execute("UPDATE users SET name = ? WHERE id = ?", (name, user_id))
        conn.commit()
        user = conn.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
        return dict(user) if user else None
    finally:
        conn.close()

# Session helpers
def create_session(user_id):
    token = secrets.token_hex(32)
    created_at = datetime.utcnow().isoformat() + "Z"
    conn = get_db_connection()
    try:
        conn.execute("INSERT INTO sessions (token, user_id, created_at) VALUES (?, ?, ?)", (token, user_id, created_at))
        conn.commit()
        return token
    finally:
        conn.close()

def get_user_by_token(token):
    conn = get_db_connection()
    # Join with users to fetch user data
    row = conn.execute(
        "SELECT u.* FROM users u JOIN sessions s ON u.id = s.user_id WHERE s.token = ?",
        (token,)
    ).fetchone()
    conn.close()
    return dict(row) if row else None

def delete_session(token):
    conn = get_db_connection()
    try:
        conn.execute("DELETE FROM sessions WHERE token = ?", (token,))
        conn.commit()
    finally:
        conn.close()

# Assessment helpers
def save_assessment(assessment_id, user_id, answers_dict):
    conn = get_db_connection()
    date_str = datetime.utcnow().isoformat() + "Z"
    answers_json = json.dumps(answers_dict)
    try:
        conn.execute(
            "INSERT INTO assessments (id, user_id, answers, date) VALUES (?, ?, ?, ?)",
            (assessment_id, user_id, answers_json, date_str)
        )
        conn.commit()
        return {"id": assessment_id, "user_id": user_id, "answers": answers_dict, "date": date_str}
    finally:
        conn.close()

def get_latest_assessment(user_id):
    conn = get_db_connection()
    row = conn.execute(
        "SELECT * FROM assessments WHERE user_id = ? ORDER BY date DESC LIMIT 1",
        (user_id,)
    ).fetchone()
    conn.close()
    if row:
        res = dict(row)
        res["answers"] = json.loads(res["answers"])
        return res
    return None

def get_assessment_history(user_id):
    conn = get_db_connection()
    rows = conn.execute(
        "SELECT * FROM assessments WHERE user_id = ? ORDER BY date DESC",
        (user_id,)
    ).fetchall()
    conn.close()
    history = []
    for r in rows:
        d = dict(r)
        d["answers"] = json.loads(d["answers"])
        history.append(d)
    return history

# Saved Careers helpers
def get_saved_careers(user_id):
    conn = get_db_connection()
    rows = conn.execute("SELECT career_id FROM saved_careers WHERE user_id = ?", (user_id,)).fetchall()
    conn.close()
    return [r["career_id"] for r in rows]

def toggle_saved_career(user_id, career_id):
    conn = get_db_connection()
    try:
        row = conn.execute(
            "SELECT 1 FROM saved_careers WHERE user_id = ? AND career_id = ?",
            (user_id, career_id)
        ).fetchone()
        
        if row:
            conn.execute(
                "DELETE FROM saved_careers WHERE user_id = ? AND career_id = ?",
                (user_id, career_id)
            )
        else:
            saved_at = datetime.utcnow().isoformat() + "Z"
            conn.execute(
                "INSERT INTO saved_careers (user_id, career_id, saved_at) VALUES (?, ?, ?)",
                (user_id, career_id, saved_at)
            )
        conn.commit()
    finally:
        conn.close()
    return get_saved_careers(user_id)

# Activity helpers
def log_activity(user_id, message):
    conn = get_db_connection()
    activity_id = secrets.token_hex(16)
    at_str = datetime.utcnow().isoformat() + "Z"
    try:
        conn.execute(
            "INSERT INTO activity (id, user_id, message, at) VALUES (?, ?, ?, ?)",
            (activity_id, user_id, message, at_str)
        )
        conn.commit()
    finally:
        conn.close()

def get_activity_log(user_id, limit=20):
    conn = get_db_connection()
    rows = conn.execute(
        "SELECT message, at FROM activity WHERE user_id = ? ORDER BY at DESC LIMIT ?",
        (user_id, limit)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]
