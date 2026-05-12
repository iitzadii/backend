import sqlite3

def get_db():
    conn = sqlite3.connect("notes.db")
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    db = get_db()
    db.execute("""
        CREATE TABLE IF NOT EXISTS notes (
            id INTEGER PRIMARY KEY,
            title TEXT,
            content TEXT,
            category TEXT,
            time TEXT,
            color TEXT
        )
    """)
    

    db.commit()
    db.close()
