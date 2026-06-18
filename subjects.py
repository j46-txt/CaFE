import datetime
from dataclasses import dataclass
from typing import Optional
import database

@dataclass
class Subject:
    id: int
    name: str
    is_active: bool
    list_order: int

def seed_default_subjects() -> None:
    """Seeds the database with default subjects if the table is empty."""
    with database.get_db() as db:
        count = db.execute('SELECT COUNT(*) as count FROM subjects').fetchone()['count']
        if count == 0:
            defaults = [
                "Constitutional Law", "Administrative Law", "Civil Procedure",
                "Criminal Procedure", "Civil Law", "Criminal Law", 
                "Portuguese", "Logic"
            ]
            for idx, name in enumerate(defaults):
                is_active = 1 if idx == 0 else 0
                db.execute(
                    'INSERT INTO subjects (name, is_active, list_order) VALUES (?, ?, ?)',
                    (name, is_active, idx)
                )

def get_active_subject() -> Optional[Subject]:
    """Retrieves the currently active subject from the database."""
    with database.get_db() as db:
        row = db.execute('SELECT * FROM subjects WHERE is_active = 1 LIMIT 1').fetchone()
        
        if row:
            return Subject(**dict(row))
        
        row = db.execute('SELECT * FROM subjects ORDER BY list_order ASC LIMIT 1').fetchone()
        if row:
            db.execute('UPDATE subjects SET is_active = 1 WHERE id = ?', (row['id'],))
            return Subject(**dict(row))
            
    return None

def rotate_subject() -> None:
    """Rotates the active status to the next subject in the ordered list."""
    with database.get_db() as db:
        current = db.execute('SELECT * FROM subjects WHERE is_active = 1 LIMIT 1').fetchone()
        if not current:
            return

        next_sub = db.execute(
            'SELECT * FROM subjects WHERE list_order > ? ORDER BY list_order ASC LIMIT 1',
            (current['list_order'],)
        ).fetchone()

        if not next_sub:
            next_sub = db.execute('SELECT * FROM subjects ORDER BY list_order ASC LIMIT 1').fetchone()

        if next_sub and current['id'] != next_sub['id']:
            db.execute('UPDATE subjects SET is_active = 0 WHERE id = ?', (current['id'],))
            db.execute('UPDATE subjects SET is_active = 1 WHERE id = ?', (next_sub['id'],))

def ensure_daily_rotation() -> None:
    """
    Checks if the currently active subject had a session on a previous calendar day,
    but no session today. If so, it fulfills the condition to rotate to the next subject.
    """
    current = get_active_subject()
    if not current:
        return

    now = datetime.datetime.now().astimezone()
    today_date = now.date()

    with database.get_db() as db:
        rows = db.execute('SELECT end_date, end_time FROM focus_sessions WHERE subject_id = ? ORDER BY id DESC', (current.id,)).fetchall()

    if not rows:
        return

    last_session_date = None
    for row in rows:
        utc_dt_str = f"{row['end_date']} {row['end_time']}"
        try:
            utc_dt = datetime.datetime.strptime(utc_dt_str, '%Y-%m-%d %H:%M:%S').replace(tzinfo=datetime.timezone.utc)
            local_date = utc_dt.astimezone().date()
            if last_session_date is None or local_date > last_session_date:
                last_session_date = local_date
        except ValueError:
            continue

    if last_session_date is not None and last_session_date < today_date:
        rotate_subject()