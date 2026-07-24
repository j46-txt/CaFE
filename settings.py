# settings.py
# -*- coding: utf-8 -*-
import database
import sqlite3
import threading

_SETTINGS_CACHE = {}
_CACHE_LOCK = threading.Lock()
_CACHE_INITIALIZED = False

def _ensure_cache_populated():
    global _CACHE_INITIALIZED
    if _CACHE_INITIALIZED:
        return
    with _CACHE_LOCK:
        if _CACHE_INITIALIZED:
            return
        try:
            with database.get_db() as db:
                rows = db.execute('SELECT key, value FROM settings').fetchall()
                for row in rows:
                    _SETTINGS_CACHE[row['key']] = row['value']
            _CACHE_INITIALIZED = True
        except sqlite3.Error:
            pass

def get_setting(key: str, default: str) -> str:
    _ensure_cache_populated()
    with _CACHE_LOCK:
        if key in _SETTINGS_CACHE:
            return _SETTINGS_CACHE[key]
        if _CACHE_INITIALIZED:
            return str(default)
            
    try:
        with database.get_db() as db:
            row = db.execute('SELECT value FROM settings WHERE key = ?', (key,)).fetchone()
            if row:
                with _CACHE_LOCK:
                    _SETTINGS_CACHE[key] = row['value']
                return row['value']
            return str(default)
    except sqlite3.Error:
        return str(default)

def set_setting(key: str, value: str) -> None:
    _ensure_cache_populated()
    val_str = str(value)
    with _CACHE_LOCK:
        _SETTINGS_CACHE[key] = val_str
        
    try:
        with database.get_db() as db:
            db.execute('REPLACE INTO settings (key, value) VALUES (?, ?)', (key, val_str))
    except sqlite3.Error:
        pass

def get_weekly_goal_hours() -> int:
    try:
        return int(get_setting('weekly_goal_hours', '10'))
    except (ValueError, TypeError):
        return 10

def get_pomodoro_minutes() -> int:
    try:
        return int(get_setting('pomodoro_minutes', '25'))
    except (ValueError, TypeError):
        return 25

def get_break_minutes() -> int:
    try:
        return int(get_setting('break_minutes', '5'))
    except (ValueError, TypeError):
        return 5

def get_auto_rotate() -> bool:
    return get_setting('auto_rotate', '1') == '1'

def set_auto_rotate(enabled: bool) -> None:
    set_setting('auto_rotate', '1' if enabled else '0')

def get_last_rotation_date() -> str:
    return get_setting('last_rotation_date', '')

def set_last_rotation_date(date_str: str) -> None:
    set_setting('last_rotation_date', date_str)
