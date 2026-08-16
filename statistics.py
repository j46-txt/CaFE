# statistics.py
# -*- coding: utf-8 -*-
import datetime
import csv
import io
import database
from typing import Dict, Any

def record_session(subject_id: int, duration_seconds: int, timer_mode: str) -> None:
    if duration_seconds <= 0:
        return
    end_dt = datetime.datetime.now(datetime.timezone.utc)
    start_dt = end_dt - datetime.timedelta(seconds=duration_seconds)
    database.save_or_update_focus_session(
        session_id=None,
        subject_id=subject_id,
        start_dt=start_dt,
        end_dt=end_dt,
        duration_seconds=duration_seconds,
        timer_mode=timer_mode
    )

def get_stats() -> Dict[str, Any]:
    """Calculates study statistics using environment local date and a rolling 14-day pace window."""
    today_date = datetime.datetime.now().astimezone().date()
    today_str = today_date.strftime('%Y-%m-%d')
    
    start_of_week_date = today_date - datetime.timedelta(days=today_date.weekday())
    start_of_week_str = start_of_week_date.strftime('%Y-%m-%d')
    
    fourteen_days_ago_date = today_date - datetime.timedelta(days=13)
    fourteen_days_ago_str = fourteen_days_ago_date.strftime('%Y-%m-%d')

    with database.get_db() as db:
        total_row = db.execute('SELECT TOTAL(duration_seconds) as total_sec FROM focus_sessions').fetchone()
        total_seconds = int(total_row['total_sec']) if total_row else 0

        today_row = db.execute('SELECT TOTAL(duration_seconds) as today_sec FROM focus_sessions WHERE start_date = ?', (today_str,)).fetchone()
        today_seconds = int(today_row['today_sec']) if today_row else 0

        week_row = db.execute('SELECT TOTAL(duration_seconds) as week_sec FROM focus_sessions WHERE start_date >= ? AND start_date <= ?', (start_of_week_str, today_str)).fetchone()
        week_seconds = int(week_row['week_sec']) if week_row else 0

        rolling_14d_row = db.execute('SELECT TOTAL(duration_seconds) as rolling_sec FROM focus_sessions WHERE start_date >= ?', (fourteen_days_ago_str,)).fetchone()
        rolling_14d_seconds = int(rolling_14d_row['rolling_sec']) if rolling_14d_row else 0

        days_row = db.execute('SELECT COUNT(DISTINCT start_date) as day_count FROM focus_sessions').fetchone()
        focus_days = int(days_row['day_count']) if days_row else 0

    # Pace is defined as average weekly hours studied in the rolling 14-day window
    avg_week_hours = (rolling_14d_seconds / 3600.0) / 2.0

    return {
        'today': today_seconds,
        'week': week_seconds,
        'total': total_seconds,
        'avg_week_hours': avg_week_hours,
        'focus_days': focus_days,
        'rolling_14d': rolling_14d_seconds
    }

def format_duration(seconds: int) -> str:
    hours, remainder = divmod(seconds, 3600)
    minutes, _ = divmod(remainder, 60)
    return f"{hours}h {minutes}m"

def export_history_csv() -> bytes:
    """Exports session history formatted directly in local environment time."""
    with database.get_db() as db:
        rows = db.execute('''
            SELECT fs.start_date, fs.start_time, fs.end_date, fs.end_time, 
                   fs.duration_seconds, fs.timer_mode, s.name as subject_name, fs.subject_id
            FROM focus_sessions fs
            LEFT JOIN subjects s ON fs.subject_id = s.id
            ORDER BY fs.id DESC
        ''').fetchall()
        
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(['Subject', 'Start Date', 'Start Time', 'End Date', 'End Time', 'Duration (Seconds)', 'Timer Mode', 'Weekday'])
    
    for row in rows:
        try:
            dt_obj = datetime.datetime.strptime(row['start_date'], '%Y-%m-%d')
            weekday = dt_obj.strftime('%A')
        except (ValueError, TypeError):
            weekday = 'Unknown'
            
        if row['subject_id'] is None:
            subject_display = ""
        else:
            subject_display = row['subject_name'] or "Deleted Subject"
            
        writer.writerow([
            subject_display, 
            row['start_date'], 
            row['start_time'], 
            row['end_date'], 
            row['end_time'], 
            row['duration_seconds'], 
            row['timer_mode'], 
            weekday
        ])
        
    return output.getvalue().encode('utf-8')
