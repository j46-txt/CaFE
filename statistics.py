import datetime
import database
from typing import Dict

def record_session(subject_id: int, duration_seconds: int, timer_mode: str) -> None:
    """Saves a completed focus session to the database using UTC timestamps."""
    if duration_seconds <= 0:
        return

    end_dt = datetime.datetime.now(datetime.timezone.utc)
    start_dt = end_dt - datetime.timedelta(seconds=duration_seconds)

    with database.get_db() as db:
        db.execute('''
            INSERT INTO focus_sessions (subject_id, start_date, start_time, end_date, end_time, duration_seconds, timer_mode)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (
            subject_id,
            start_dt.strftime('%Y-%m-%d'),
            start_dt.strftime('%H:%M:%S'),
            end_dt.strftime('%Y-%m-%d'),
            end_dt.strftime('%H:%M:%S'),
            duration_seconds,
            timer_mode
        ))

def get_stats() -> Dict[str, int]:
    """Calculates today's, this week's, and total focus duration in seconds."""
    today_seconds = 0
    week_seconds = 0
    total_seconds = 0

    now = datetime.datetime.now().astimezone()
    today_date = now.date()
    start_of_week = today_date - datetime.timedelta(days=today_date.weekday())

    with database.get_db() as db:
        rows = db.execute('SELECT end_date, end_time, duration_seconds FROM focus_sessions').fetchall()

    for row in rows:
        duration = row['duration_seconds']
        total_seconds += duration

        utc_dt_str = f"{row['end_date']} {row['end_time']}"
        try:
            utc_dt = datetime.datetime.strptime(utc_dt_str, '%Y-%m-%d %H:%M:%S').replace(tzinfo=datetime.timezone.utc)
            local_dt = utc_dt.astimezone()
            local_date = local_dt.date()

            if local_date == today_date:
                today_seconds += duration

            if start_of_week <= local_date <= today_date:
                week_seconds += duration
        except ValueError:
            continue

    return {
        'today': today_seconds,
        'week': week_seconds,
        'total': total_seconds
    }

def format_duration(seconds: int) -> str:
    """Formats seconds into a readable 'Xh Ym' string."""
    hours, remainder = divmod(seconds, 3600)
    minutes, _ = divmod(remainder, 60)
    return f"{hours}h {minutes}m"