import sqlite3
import os
from contextlib import contextmanager

DB_PATH = os.path.join(os.path.dirname(__file__), 'assets', 'database.sqlite')

@contextmanager
def get_db():
    """Provides a transactional database connection."""
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.commit()
        conn.close()

def init_db():
    """Initializes the database schema."""
    with get_db() as db:
        db.execute('''
            CREATE TABLE IF NOT EXISTS settings (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL
            )
        ''')
        db.execute('''
            CREATE TABLE IF NOT EXISTS subjects (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                is_active BOOLEAN NOT NULL DEFAULT 0,
                list_order INTEGER NOT NULL
            )
        ''')
        # Renamed study_sessions to focus_sessions
        db.execute('''
            CREATE TABLE IF NOT EXISTS focus_sessions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                subject_id INTEGER,
                start_date TEXT NOT NULL,
                start_time TEXT NOT NULL,
                end_date TEXT NOT NULL,
                end_time TEXT NOT NULL,
                duration_seconds INTEGER NOT NULL,
                timer_mode TEXT NOT NULL,
                FOREIGN KEY (subject_id) REFERENCES subjects(id)
            )
        ''')