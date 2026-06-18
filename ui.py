from nicegui import ui
from timer import FocusTimer
import subjects
import statistics
import settings

def build_ui():
    """Builds the minimalist FocusFlow user interface."""
    
    subjects.ensure_daily_rotation()
    active_subject = subjects.get_active_subject()
    subject_name = active_subject.name if active_subject else "No Subject Available"
    
    def refresh_stats():
        """Fetches the latest metrics and updates the UI labels."""
        goal_hours = settings.get_weekly_goal_hours()
        goal_seconds = goal_hours * 3600
        
        new_stats = statistics.get_stats()
        today_label.text = statistics.format_duration(new_stats['today'])
        week_label.text = f"{statistics.format_duration(new_stats['week'])} / {goal_hours}h"
        
        progress_val = min(1.0, new_stats['week'] / goal_seconds) if goal_seconds > 0 else 0
        week_progress.value = progress_val
        total_label.text = f"{new_stats['total'] // 3600}h"

    def open_settings():
        """Opens a minimalist configuration dialog."""
        with ui.dialog() as dialog, ui.card().classes('w-80 bg-neutral-900 border border-neutral-800'):
            ui.label('Settings').classes('text-xl font-bold text-gray-200 mb-4')
            
            pomo_input = ui.number('Focus Duration (min)', value=settings.get_pomodoro_minutes(), format='%.0f').classes('w-full mb-2')
            break_input = ui.number('Break Duration (min)', value=settings.get_break_minutes(), format='%.0f').classes('w-full mb-2')
            goal_input = ui.number('Weekly Goal (hours)', value=settings.get_weekly_goal_hours(), format='%.0f').classes('w-full mb-6')
            
            def save_settings():
                settings.set_setting('pomodoro_minutes', int(pomo_input.value))
                settings.set_setting('break_minutes', int(break_input.value))
                settings.set_setting('weekly_goal_hours', int(goal_input.value))
                focus_timer.sync_durations()
                refresh_stats()
                dialog.close()
                
            ui.button('Save', on_click=save_settings).classes('w-full bg-blue-600 text-white')
        dialog.open()

    def update_display():
        """Updates the UI components based on the current timer state."""
        timer_label.text = focus_timer.display_time
        
        # Colorize timer based on mode
        is_break = focus_timer.state.mode == 'break'
        timer_label.classes(replace=f"text-7xl font-mono {'text-green-400' if is_break else 'text-gray-100'} mb-8")
        
        mode_text = {
            'pomodoro': 'Focus',
            'break': 'Break',
            'stopwatch': 'Stopwatch'
        }.get(focus_timer.state.mode, '')
        
        timer_status_label.text = mode_text
        mode_btn.text = 'Switch to Stopwatch' if focus_timer.state.mode in ('pomodoro', 'break') else 'Switch to Pomodoro'

        # Button visibility logic
        is_pomo_mode = focus_timer.state.mode in ('pomodoro', 'break')
        
        if focus_timer.state.status == 'idle':
            start_btn.text = 'Start'
            start_btn.set_visibility(True)
            pause_btn.set_visibility(False)
            skip_btn.set_visibility(False)
            reset_btn.set_visibility(False)
            stop_btn.set_visibility(False)
        else:
            start_btn.text = 'Resume'
            start_btn.set_visibility(focus_timer.state.status == 'paused')
            pause_btn.set_visibility(focus_timer.state.status == 'running')
            
            skip_btn.set_visibility(is_pomo_mode)
            reset_btn.set_visibility(is_pomo_mode)
            stop_btn.set_visibility(not is_pomo_mode)

    def on_session_complete(duration_seconds: int, mode: str):
        """Handles the completion of a focus timer session."""
        if active_subject:
            statistics.record_session(active_subject.id, duration_seconds, mode)
            
        minutes = duration_seconds // 60
        ui.notify(f"Session recorded: {minutes} minutes.", color='positive', position='top')
        refresh_stats()

    focus_timer = FocusTimer(on_tick=update_display, on_complete=on_session_complete)
    ui.timer(1.0, focus_timer.tick)

    with ui.column().classes('w-full max-w-xl mx-auto items-center p-4 mt-8'):
        
        # Header
        with ui.row().classes('w-full justify-between items-center mb-8'):
            ui.label('FocusFlow').classes('text-3xl font-bold text-gray-200')
            ui.button(icon='settings', on_click=open_settings).props('flat round color=grey')
        
        # Timer Section
        with ui.card().classes('w-full items-center p-8 bg-neutral-900 border border-neutral-800 shadow-none'):
            with ui.row().classes('w-full justify-between items-center mb-4'):
                timer_status_label = ui.label('Focus').classes('text-sm uppercase tracking-wider text-gray-500')
                mode_btn = ui.button(on_click=focus_timer.toggle_mode).props('flat size=sm color=grey')

            ui.label(subject_name).classes('text-2xl font-bold text-gray-200 mb-8 text-center')
            
            timer_label = ui.label(focus_timer.display_time)
            
            with ui.row().classes('gap-4 h-10'):
                start_btn = ui.button('Start', icon='play_arrow', on_click=focus_timer.start).classes('px-6 py-2 bg-blue-600 text-white')
                pause_btn = ui.button('Pause', icon='pause', on_click=focus_timer.pause).classes('px-6 py-2').props('outline color=grey')
                skip_btn = ui.button('Skip', icon='skip_next', on_click=focus_timer.skip).classes('px-6 py-2').props('outline color=grey')
                reset_btn = ui.button('Reset', icon='refresh', on_click=focus_timer.reset).classes('px-6 py-2').props('outline color=grey')
                stop_btn = ui.button('Stop', icon='stop', on_click=focus_timer.stop).classes('px-6 py-2').props('outline color=grey')

        # Statistics Section
        with ui.card().classes('w-full p-6 mt-6 bg-neutral-900 border border-neutral-800 shadow-none'):
            with ui.row().classes('w-full justify-between items-center mb-2'):
                ui.label('Today').classes('text-gray-400')
                today_label = ui.label('0h 0m').classes('text-gray-200 font-medium')
            
            ui.separator().classes('my-2 bg-neutral-800')
            
            with ui.row().classes('w-full justify-between items-center mb-2'):
                ui.label('Week').classes('text-gray-400')
                week_label = ui.label('0h 0m / 18h').classes('text-gray-200 font-medium')
            week_progress = ui.linear_progress(value=0.0, color='blue').classes('w-full h-2 rounded')

        # Global Footer Stats
        with ui.column().classes('w-full items-center mt-8 text-gray-500'):
            ui.label('Total Accumulated Time').classes('text-xs uppercase tracking-wider')
            total_label = ui.label('0h').classes('text-lg font-medium')

    # Initial states
    update_display()
    refresh_stats()