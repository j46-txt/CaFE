# database.py
# -*- coding: utf-8 -*-
import sqlite3
import os
import psycopg2
import threading
import queue
import tempfile
import time
from contextlib import contextmanager

DB_PATH = os.path.join(os.path.dirname(__file__), 'assets', 'database.sqlite')
POSTGRES_URL = os.environ.get('DATABASE_URL')

BACKUP_QUEUE = queue.Queue(maxsize=1)

def load_cloud_backup():
    if not POSTGRES_URL:
        print("[Backup] DATABASE_URL not found. Running in ephemeral local-only mode.")
        return
    conn = None
    try:
        conn = psycopg2.connect(POSTGRES_URL, connect_timeout=5)
        with conn.cursor() as cur:
            cur.execute('''
                CREATE TABLE IF NOT EXISTS cafe_backup (
                    id INTEGER PRIMARY KEY,
                    file_data BYTEA,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            ''')
            conn.commit()
            
            cur.execute("SELECT file_data FROM cafe_backup WHERE id = 1;")
            row = cur.fetchone()
            if row and row[0]:
                os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
                
                for suffix in ['-wal', '-shm']:
                    stale_file = DB_PATH + suffix
                    if os.path.exists(stale_file):
                        try:
                            os.remove(stale_file)
                        except Exception as e:
                            print(f"[Backup Error] Aborting restore. Cannot clear WAL lock: {e}")
                            return 
                            
                with open(DB_PATH, 'wb') as f:
                    f.write(bytes(row[0]))
                print("[Backup] SQLite database successfully restored from the cloud!")
            else:
                print("[Backup] No remote backup found. Initializing a clean database.")
    except Exception as e:
        print(f"[Backup Error] Failed to load backup from cloud: {e}")
    finally:
        if conn:
            conn.close()

def save_cloud_backup(binary_data: bytes):
    if not POSTGRES_URL:
        return
    conn = None
    try:
        conn = psycopg2.connect(POSTGRES_URL, connect_timeout=5)
        with conn.cursor() as cur:
            cur.execute('''
                INSERT INTO cafe_backup (id, file_data, updated_at)
                VALUES (1, %s, CURRENT_TIMESTAMP)
                ON CONFLICT (id) DO UPDATE SET file_data = EXCLUDED.file_data, updated_at = CURRENT_TIMESTAMP;
            ''', (psycopg2.Binary(binary_data),))
            conn.commit()
        print("[Backup] Changes successfully synchronized to the cloud.")
    except Exception as e:
        print(f"[Backup Error] Failed to save backup to cloud: {e}")
    finally:
        if conn:
            conn.close()

def _backup_worker():
    while True:
        try:
            BACKUP_QUEUE.get()
            
            # BATCHING OPTIMIZATION: Wait 5 seconds to coalesce rapid consecutive writes (e.g., pausing/unpausing)
            time.sleep(5) 
            
            if os.path.exists(DB_PATH):
                tmp_path = None
                src_conn = None
                dst_conn = None
                try:
                    with tempfile.NamedTemporaryFile(suffix='.sqlite', delete=False) as tmp:
                        tmp_path = tmp.name
                    
                    src_conn = sqlite3.connect(DB_PATH, timeout=30.0)
                    dst_conn = sqlite3.connect(tmp_path)
                    src_conn.backup(dst_conn)
                    dst_conn.close()
                    dst_conn = None
                    src_conn.close()
                    src_conn = None
                    
                    with open(tmp_path, 'rb') as f:
                        binary_data = f.read()
                        
                    save_cloud_backup(binary_data)
                except Exception as e:
                    print(f"[Backup Error] Failed to generate consistent database snapshot: {e}")
                finally:
                    if dst_conn:
                        try: dst_conn.close()
                        except Exception: pass
                    if src_conn:
                        try: src_conn.close()
                        except Exception: pass
                    if tmp_path and os.path.exists(tmp_path):
                        try: os.remove(tmp_path)
                        except Exception: pass
        except Exception as e:
            print(f"[Backup Worker Error] Critical failure in background backup loop: {e}")
        finally:
            BACKUP_QUEUE.task_done()

threading.Thread(target=_backup_worker, daemon=True, name="CaFE-BackupWorker").start()

def save_cloud_backup_background():
    try:
        BACKUP_QUEUE.put_nowait(True)
    except queue.Full:
        pass

@contextmanager
def get_db():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = None
    tx_committed = False
    try:
        conn = sqlite3.connect(DB_PATH, timeout=5.0)
        conn.row_factory = sqlite3.Row
        conn.execute('PRAGMA synchronous=NORMAL;')
        
        yield conn
        conn.commit()
        tx_committed = True
    except Exception:
        if conn:
            conn.rollback()
        raise
    finally:
        if conn:
            try:
                changes = conn.total_changes
                # Removed PRAGMA wal_checkpoint(PASSIVE) here to eliminate main-thread disk I/O bottlenecks.
                # SQLite will auto-checkpoint, and our background worker copies the DB safely.
            except Exception as e:
                changes = 0
                
            conn.close()
            
            if tx_committed and changes > 0:
                save_cloud_backup_background()

def init_db():
    load_cloud_backup()
    with get_db() as db:
        db.execute('PRAGMA journal_mode=WAL;')
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
                list_order INTEGER NOT NULL,
                weight INTEGER NOT NULL DEFAULT 1,
                is_deleted BOOLEAN NOT NULL DEFAULT 0
            )
        ''')
        
        cursor = db.execute("PRAGMA table_info(subjects)")
        columns = [row['name'] for row in cursor.fetchall()]
        if 'weight' not in columns:
            db.execute("ALTER TABLE subjects ADD COLUMN weight INTEGER NOT NULL DEFAULT 1")
        if 'is_deleted' not in columns:
            db.execute("ALTER TABLE subjects ADD COLUMN is_deleted BOOLEAN NOT NULL DEFAULT 0")
        if 'tickets_remaining' not in columns:
            db.execute("ALTER TABLE subjects ADD COLUMN tickets_remaining INTEGER NOT NULL DEFAULT 0")
        if 'last_picked_turn' not in columns:
            db.execute("ALTER TABLE subjects ADD COLUMN last_picked_turn INTEGER NOT NULL DEFAULT 0")
            
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
        
        db.execute('CREATE INDEX IF NOT EXISTS idx_focus_sessions_start_date ON focus_sessions(start_date);')
        db.execute('CREATE INDEX IF NOT EXISTS idx_focus_sessions_subject_id ON focus_sessions(subject_id);')
