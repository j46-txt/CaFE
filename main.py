from nicegui import app, ui
import database
import subjects
import ui as user_interface

def startup():
    """Runs on application startup to ensure database and default data are ready."""
    database.init_db()
    subjects.seed_default_subjects()

app.on_startup(startup)

@ui.page('/')
def main_page():
    """Renders the main application page."""
    user_interface.build_ui()

if __name__ in {"__main__", "__mp_main__"}:
    # Dark mode set by default to reduce eye strain
    ui.run(title="FocusFlow", port=8080, dark=True, show=False)