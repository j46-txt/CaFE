import database

def get_setting(key: str, default: str) -> str:
    """Retrieves a configuration value from the database."""
    with database.get_db() as db:
        row = db.execute('SELECT value FROM settings WHERE key = ?', (key,)).fetchone()
        return row['value'] if row else str(default)

def set_setting(key: str, value: str) -> None:
    """Saves or updates a configuration value in the database."""
    with database.get_db() as db:
        db.execute('''
            REPLACE INTO settings (key, value)
            VALUES (?, ?)
        ''', (key, str(value)))

def get_weekly_goal_hours() -> int:
    """Gets the weekly goal target in hours."""
    return int(get_setting('weekly_goal_hours', '18'))

def get_pomodoro_minutes() -> int:
    """Gets the Pomodoro duration in minutes."""
    return int(get_setting('pomodoro_minutes', '25'))

def get_break_minutes() -> int:
    """Gets the Break duration in minutes."""
    return int(get_setting('break_minutes', '5'))