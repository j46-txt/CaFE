import time
from dataclasses import dataclass
from typing import Callable
import settings

@dataclass
class TimerState:
    mode: str = 'pomodoro'  # 'pomodoro', 'break', 'stopwatch'
    status: str = 'idle'    # 'idle', 'running', 'paused'
    seconds_remaining: int = 25 * 60
    seconds_elapsed: int = 0

class FocusTimer:
    def __init__(self, on_tick: Callable[[], None], on_complete: Callable[[int, str], None]):
        """
        Manages the timer state machine for FocusFlow.
        """
        self.state = TimerState()
        self.on_tick = on_tick
        self.on_complete = on_complete
        self._last_tick_time: float = 0.0
        self.sync_durations()

    def sync_durations(self) -> None:
        """Fetches the latest durations from settings."""
        self.pomodoro_duration = settings.get_pomodoro_minutes() * 60
        self.break_duration = settings.get_break_minutes() * 60
        if self.state.status == 'idle':
            if self.state.mode == 'pomodoro':
                self.state.seconds_remaining = self.pomodoro_duration
            elif self.state.mode == 'break':
                self.state.seconds_remaining = self.break_duration

    def start(self) -> None:
        """Starts or resumes the timer."""
        if self.state.status == 'idle':
            self.sync_durations()
            if self.state.mode == 'stopwatch':
                self.state.seconds_elapsed = 0
        
        self.state.status = 'running'
        self._last_tick_time = time.time()
        self.on_tick()

    def pause(self) -> None:
        """Pauses the timer."""
        self.state.status = 'paused'
        self.on_tick()

    def skip(self) -> None:
        """Skips the current phase (Focus or Break) and automatically transitions to the next."""
        if self.state.mode == 'pomodoro':
            elapsed = self.pomodoro_duration - self.state.seconds_remaining
            if elapsed > 0:
                self.on_complete(elapsed, self.state.mode)
            self.state.mode = 'break'
            self._reset()
            self.start()
        elif self.state.mode == 'break':
            self.state.mode = 'pomodoro'
            self._reset()
            self.start()

    def reset(self) -> None:
        """Resets the Pomodoro/Break back to the start without saving."""
        self._reset()
        self.on_tick()

    def stop(self) -> None:
        """Stops the Stopwatch, logs the time, and resets."""
        if self.state.mode == 'stopwatch':
            if self.state.seconds_elapsed > 0:
                self.on_complete(self.state.seconds_elapsed, self.state.mode)
            self._reset()
            self.on_tick()

    def toggle_mode(self) -> None:
        """Switches between Pomodoro and Stopwatch modes."""
        if self.state.mode in ('pomodoro', 'break'):
            self.state.mode = 'stopwatch'
        else:
            self.state.mode = 'pomodoro'
        self._reset()
        self.on_tick()

    def tick(self) -> None:
        """Calculates time deltas and updates the state. Must be called frequently."""
        if self.state.status != 'running':
            return

        now = time.time()
        delta = int(now - self._last_tick_time)
        
        if delta > 0:
            self._last_tick_time = now
            
            if self.state.mode in ('pomodoro', 'break'):
                self.state.seconds_remaining -= delta
                if self.state.seconds_remaining <= 0:
                    is_pomodoro = self.state.mode == 'pomodoro'
                    duration = self.pomodoro_duration if is_pomodoro else self.break_duration
                    
                    if is_pomodoro:
                        self.on_complete(duration, self.state.mode)
                        self.state.mode = 'break'
                    else:
                        self.state.mode = 'pomodoro'
                    
                    self._reset()
                    self.start()  # Infinite cycle automation
                    return
            elif self.state.mode == 'stopwatch':
                self.state.seconds_elapsed += delta
                
            self.on_tick()

    def _reset(self) -> None:
        """Internal reset method."""
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
        """Returns the formatted time string (MM:SS or HH:MM:SS) for the UI."""
        secs = max(0, self.state.seconds_remaining if self.state.mode in ('pomodoro', 'break') else self.state.seconds_elapsed)
        mins, secs = divmod(secs, 60)
        hours, mins = divmod(mins, 60)
        
        if hours > 0:
            return f"{hours:02d}:{mins:02d}:{secs:02d}"
        return f"{mins:02d}:{secs:02d}"