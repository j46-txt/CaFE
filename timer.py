# timer.py
# -*- coding: utf-8 -*-
import time
from dataclasses import dataclass
from typing import Callable, Optional
from datetime import datetime, timezone
import settings

PAUSE_LONG_THRESHOLD_SECONDS = 300

@dataclass
class TimerState:
    mode: str = 'pomodoro'  # 'pomodoro', 'break', 'stopwatch'
    status: str = 'idle'    # 'idle', 'running', 'paused'
    seconds_remaining: int = 25 * 60
    seconds_elapsed: int = 0
    seconds_focused_in_turn: int = 0

class FocusTimer:
    def __init__(
        self,
        on_tick: Callable[[], None],
        on_complete: Callable[[int, str, Optional[int], Optional[datetime]], Optional[int]],
        on_sound_alert: Optional[Callable[[str], None]] = None,
        on_long_pause_prompt: Optional[Callable[[int], str]] = None
    ):
        """
        :param on_tick: Callback triggered on every timer step.
        :param on_complete: Callback to log/update study session in DB.
        :param on_sound_alert: Optional audio trigger ('pomodoro' or 'break').
        :param on_long_pause_prompt: Optional callback returning 'continue' or 'new_session' after 5+ min pause.
        """
        self.state = TimerState()
        self.on_tick = on_tick
        self.on_complete = on_complete
        self.on_sound_alert = on_sound_alert
        self.on_long_pause_prompt = on_long_pause_prompt
        
        self._last_tick_time: float = 0.0
        
        self.current_session_id: Optional[int] = None
        self.accumulated_seconds: int = 0
        self.session_start_time: Optional[datetime] = None
        self.last_pause_monotonic: Optional[float] = None
        
        self.sync_durations()

    def sync_durations(self) -> None:
        self.pomodoro_duration = settings.get_pomodoro_minutes() * 60
        self.break_duration = settings.get_break_minutes() * 60
        if self.state.status == 'idle':
            if self.state.mode == 'pomodoro':
                self.state.seconds_remaining = self.pomodoro_duration
            elif self.state.mode == 'break':
                self.state.seconds_remaining = self.break_duration

    def start(self) -> None:
        now_mono = time.monotonic()
        
        if self.state.status in ('idle', 'paused'):
            if self.last_pause_monotonic is not None:
                pause_duration = int(now_mono - self.last_pause_monotonic)
                
                # Check for long pause threshold without destroying user progress
                if pause_duration >= PAUSE_LONG_THRESHOLD_SECONDS and self.current_session_id is not None:
                    user_choice = 'continue'
                    if self.on_long_pause_prompt:
                        user_choice = self.on_long_pause_prompt(pause_duration)
                    
                    if user_choice == 'new_session':
                        self._clear_session_state()

            if self.current_session_id is None:
                self.accumulated_seconds = 0
                self.session_start_time = datetime.now(timezone.utc)

            if self.state.status == 'idle':
                self.sync_durations()
                if self.state.mode == 'stopwatch':
                    self.state.seconds_elapsed = 0
                self.state.seconds_focused_in_turn = 0

        self.last_pause_monotonic = None
        self.state.status = 'running'
        self._last_tick_time = now_mono
        self.on_tick()

    def pause(self) -> None:
        if self.state.status == 'running':
            self.state.status = 'paused'
            total_focused = self.accumulated_seconds + self.state.seconds_focused_in_turn
            
            if self.state.mode in ('pomodoro', 'stopwatch') and total_focused > 0:
                if self.session_start_time is None:
                    self.session_start_time = datetime.now(timezone.utc)
                
                new_session_id = self.on_complete(
                    total_focused,
                    self.state.mode,
                    self.current_session_id,
                    self.session_start_time
                )
                if new_session_id:
                    self.current_session_id = new_session_id
                
                self.accumulated_seconds = total_focused
                self.state.seconds_focused_in_turn = 0
                
            self.last_pause_monotonic = time.monotonic()
        self.on_tick()

    def handle_disconnect(self) -> None:
        pass

    def skip(self) -> None:
        if self.state.mode == 'break':
            self.state.mode = 'pomodoro'
            self._clear_session_state()
            self._reset()
            self.on_tick()

    def reset(self) -> None:
        self._flush_current_session_if_running()
        self._clear_session_state()
        self._reset()
        self.on_tick()

    def stop(self) -> None:
        if self.state.mode == 'stopwatch':
            self._flush_current_session_if_running()
            self._clear_session_state()
            self._reset()
            self.on_tick()

    def set_mode(self, new_mode: str) -> None:
        new_mode = new_mode.lower()
        if new_mode not in ('pomodoro', 'stopwatch'):
            return
        self._flush_current_session_if_running()
        self._clear_session_state()
        self.state.mode = new_mode
        self._reset()
        self.on_tick()

    def tick(self) -> None:
        if self.state.status != 'running':
            return
        now = time.monotonic()
        delta = int(now - self._last_tick_time)
        if delta > 0:
            if delta > 10:  # OS sleep safeguard
                self.pause()
                self._last_tick_time = now
                return 

            self._last_tick_time += delta  
            
            if self.state.mode in ('pomodoro', 'stopwatch'):
                self.state.seconds_focused_in_turn += delta

            if self.state.mode in ('pomodoro', 'break'):
                self.state.seconds_remaining -= delta
                if self.state.seconds_remaining <= 0:
                    is_pomodoro = self.state.mode == 'pomodoro'
                    total_focused = self.accumulated_seconds + self.state.seconds_focused_in_turn
                    
                    if is_pomodoro:
                        if total_focused > 0:
                            if self.session_start_time is None:
                                self.session_start_time = datetime.now(timezone.utc)
                            self.on_complete(
                                total_focused,
                                'pomodoro',
                                self.current_session_id,
                                self.session_start_time
                            )
                        if self.on_sound_alert:
                            self.on_sound_alert('pomodoro')
                        self._clear_session_state()
                        self.state.mode = 'break'
                        self._reset()
                        self.start()  # Auto-starts Break timer
                    else:
                        if self.on_sound_alert:
                            self.on_sound_alert('break')
                        self._clear_session_state()
                        self.state.mode = 'pomodoro'
                        self._reset()
                        self.start()  # Auto-starts next Focus timer
                    return
            elif self.state.mode == 'stopwatch':
                self.state.seconds_elapsed += delta
            self.on_tick()

    def _flush_current_session_if_running(self) -> None:
        total_focused = self.accumulated_seconds + self.state.seconds_focused_in_turn
        if self.state.mode in ('pomodoro', 'stopwatch') and total_focused > 0:
            if self.session_start_time is None:
                self.session_start_time = datetime.now(timezone.utc)
            self.on_complete(
                total_focused,
                self.state.mode,
                self.current_session_id,
                self.session_start_time
            )

    def _clear_session_state(self) -> None:
        self.current_session_id = None
        self.accumulated_seconds = 0
        self.state.seconds_focused_in_turn = 0
        self.session_start_time = None
        self.last_pause_monotonic = None

    def _reset(self) -> None:
        self.state.status = 'idle'
        self.sync_durations()
        if self.state.mode == 'pomodoro':
            self.state.seconds_remaining = self.pomodoro_duration
        elif self.state.mode == 'break':
            self.state.seconds_remaining = self.break_duration
        else:
            self.state.seconds_elapsed = 0

    @property
    def display_time(self) -> str:
        secs = max(0, self.state.seconds_remaining if self.state.mode in ('pomodoro', 'break') else self.state.seconds_elapsed)
        mins, secs = divmod(secs, 60)
        hours, mins = divmod(mins, 60)
        if hours > 0:
            return f"{hours:02d}:{mins:02d}:{secs:02d}"
        return f"{mins:02d}:{secs:02d}"
