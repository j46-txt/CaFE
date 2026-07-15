# subjects.py
# -*- coding: utf-8 -*-
import datetime
import random
import threading
from dataclasses import dataclass
from typing import Optional, List
import database
import settings

LOCAL_TZ = datetime.timezone(datetime.timedelta(hours=-3))

@dataclass
class Subject:
    id: int
    name: str
    is_active: bool
    list_order: int
    weight: int = 1
    is_deleted: int = 0
    tickets_remaining: int = 0
    last_picked_turn: int = 0

rotation_lock = threading.RLock()

def seed_default_subjects() -> None:
    pass

def get_all_subjects() -> List[Subject]:
    with database.get_db() as db:
        rows = db.execute('SELECT * FROM subjects WHERE is_deleted = 0 ORDER BY list_order ASC').fetchall()
        return [Subject(**dict(row)) for row in rows]

def add_subject(name: str, weight: int = 1) -> None:
    if not name.strip():
        return
    with database.get_db() as db:
        max_order = db.execute('SELECT MAX(list_order) as max_ord FROM subjects').fetchone()['max_ord']
        new_order = 0 if max_order is None else max_order + 1
        safe_weight = max(1, min(weight, 10))
        
        db.execute(
            '''INSERT INTO subjects 
               (name, is_active, list_order, weight, is_deleted, tickets_remaining, last_picked_turn) 
               VALUES (?, ?, ?, ?, 0, ?, 0)''',
            (name.strip(), 0, new_order, safe_weight, safe_weight)
        )
        
        count = db.execute('SELECT COUNT(*) as count FROM subjects WHERE is_deleted = 0').fetchone()['count']
        if count == 1:
            db.execute('UPDATE subjects SET is_active = 1 WHERE name = ? AND is_deleted = 0', (name.strip(),))

def update_subject(subject_id: int, name: str, weight: int) -> None:
    if not name.strip():
        return
    with database.get_db() as db:
        safe_weight = max(1, min(weight, 10))
        old_sub = db.execute('SELECT weight, tickets_remaining FROM subjects WHERE id = ?', (subject_id,)).fetchone()
        
        if old_sub:
            old_weight = old_sub['weight']
            tickets = old_sub['tickets_remaining']
            delta = safe_weight - old_weight
            new_tickets = max(0, tickets + delta)
        else:
            new_tickets = safe_weight

        db.execute('''
            UPDATE subjects 
            SET name = ?, weight = ?, tickets_remaining = ? 
            WHERE id = ?
        ''', (name.strip(), safe_weight, new_tickets, subject_id))

def delete_subject(subject_id: int) -> None:
    with database.get_db() as db:
        current = db.execute('SELECT is_active FROM subjects WHERE id = ?', (subject_id,)).fetchone()
        db.execute('UPDATE subjects SET is_deleted = 1, is_active = 0 WHERE id = ?', (subject_id,))
        if current and current['is_active']:
            fallback = db.execute('SELECT id FROM subjects WHERE is_deleted = 0 ORDER BY list_order ASC LIMIT 1').fetchone()
            if fallback:
                db.execute('UPDATE subjects SET is_active = 1 WHERE id = ?', (fallback['id'],))

def set_active_subject(subject_id: int) -> None:
    with database.get_db() as db:
        db.execute('UPDATE subjects SET is_active = 0')
        db.execute('UPDATE subjects SET is_active = 1 WHERE id = ?', (subject_id,))

def get_active_subject() -> Optional[Subject]:
    with database.get_db() as db:
        row = db.execute('SELECT * FROM subjects WHERE is_active = 1 AND is_deleted = 0 LIMIT 1').fetchone()
        if row:
            return Subject(**dict(row))
        row = db.execute('SELECT * FROM subjects WHERE is_deleted = 0 ORDER BY list_order ASC LIMIT 1').fetchone()
        if row:
            db.execute('UPDATE subjects SET is_active = 1 WHERE id = ?', (row['id'],))
            return Subject(**dict(row))
    return None

def rotate_subject() -> None:
    with rotation_lock:
        with database.get_db() as db:
            all_subs = db.execute('SELECT * FROM subjects WHERE is_deleted = 0').fetchall()
            if not all_subs:
                return
            if len(all_subs) == 1:
                db.execute('UPDATE subjects SET is_active = 1 WHERE id = ?', (all_subs[0]['id'],))
                return

            total_tickets = sum(s['tickets_remaining'] for s in all_subs)
            if total_tickets <= 0:
                for s in all_subs:
                    db.execute('UPDATE subjects SET tickets_remaining = weight WHERE id = ?', (s['id'],))
                all_subs = db.execute('SELECT * FROM subjects WHERE is_deleted = 0').fetchall()

            max_turn_row = db.execute('SELECT MAX(last_picked_turn) as max_t FROM subjects').fetchone()
            current_turn = max_turn_row['max_t'] if max_turn_row and max_turn_row['max_t'] else 0

            active_subs_count = len(all_subs)
            cooldown = max(0, active_subs_count // 2)

            candidates = []
            while cooldown >= 0:
                candidates = [
                    s for s in all_subs 
                    if s['tickets_remaining'] > 0 and 
                       (current_turn - s['last_picked_turn'] >= cooldown or s['last_picked_turn'] == 0)
                ]
                if candidates:
                    break
                cooldown -= 1

            if not candidates:
                candidates = [s for s in all_subs if s['tickets_remaining'] > 0]
            if not candidates:
                candidates = all_subs

            weights = [max(1, s['tickets_remaining']) for s in candidates]
            chosen = random.choices(candidates, weights=weights, k=1)[0]

            db.execute('UPDATE subjects SET is_active = 0')
            db.execute('''
                UPDATE subjects 
                SET is_active = 1, 
                    tickets_remaining = MAX(0, tickets_remaining - 1), 
                    last_picked_turn = ? 
                WHERE id = ?
            ''', (current_turn + 1, chosen['id']))

def ensure_daily_rotation() -> None:
    if not settings.get_auto_rotate():
        return
    with rotation_lock:
        today_str = datetime.datetime.now(LOCAL_TZ).strftime('%Y-%m-%d')
        last_date = settings.get_last_rotation_date()
        if not last_date:
            settings.set_last_rotation_date(today_str)
            return
        if last_date < today_str:
            rotate_subject()
            settings.set_last_rotation_date(today_str)
