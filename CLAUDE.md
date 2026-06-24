# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Running the App

```bash
pip install -r requirements.txt
python pomodoro.py
```

On Windows you can also double-click `start.bat`. There is no build step, no test suite, and no linter configured.

## Packaging as Windows Executable

```bat
build.bat          # runs PyInstaller, outputs dist\番茄鐘.exe
```

Development dependencies (PyInstaller) are in `requirements-dev.txt`.

## Architecture

The application lives in two classes in `pomodoro.py`:

**`TimerDisplay(QWidget)`** — custom widget that paints a circular arc progress ring using `QPainter` in `paintEvent`. The arc draws from the top (90°) clockwise, shrinking as `_progress` (0.0–1.0) decreases. The centered time label is a `QLabel` child resized to fill the widget in `resizeEvent`.

**`PomodoroTimer(QMainWindow)`** — the main window. Key design choices:

- **Frameless always-on-top window** — uses `FramelessWindowHint | WindowStaysOnTopHint` + `WA_TranslucentBackground`. The central `QFrame#container` carries the `border-radius: 16px` rounded background. The title bar (`QWidget#titleBar`) is draggable via `mousePressEvent`/`mouseMoveEvent` overrides.

- **Timer state machine** — three booleans drive all transitions:
  - `is_running`: whether `QTimer` is ticking
  - `is_working`: work phase (`True`) or break phase (`False`)
  - `is_long_break`: whether the current break is a long break

- **Long break logic** — `sessions_since_long_break` increments each time a work phase ends. When it reaches `LONG_BREAK_INTERVAL` (4), `is_long_break` is set and `long_break_time` is used instead of `break_time`, then the counter resets.

- **Auto-start countdown** — `_phase_finished()` does not auto-start immediately. It starts a second `QTimer` (`auto_start_timer`) that counts down `AUTO_START_DELAY` (5) seconds, updating the status label each second. When the countdown expires, `start_timer()` is called automatically. Pressing Space or clicking Start during the countdown cancels it and starts immediately.

- **Phase color** — `_phase_color()` returns `working`, `resting`, or `long_break` color from `current_theme` based on the three state booleans. This color drives both the arc and the status/time labels.

- **Theme system** — `LIGHT_THEME` and `DARK_THEME` are class-level dicts with keys: `bg`, `text`, `status_text`, `track`, `working`, `resting`, `long_break`, `titlebar`, `input_bg`, `input_border`, and a nested `buttons` dict. `_apply_container_style()` rebuilds the entire container stylesheet from `current_theme`; `_update_all_colors()` calls it then re-applies each button's inline stylesheet.

- **History** — `_save_session()` appends a JSON record to `history.json` (same directory as the script) each time a work phase completes. Schema: `{date, time, task, type, duration_min}`. `_show_history()` opens a `QDialog` with a `QTableWidget` showing the 20 most recent entries.

- **Keyboard shortcuts** — handled in `keyPressEvent`: Space (Start/Pause or skip countdown), R (Reset), Escape (minimize).

- **Sound** — Windows-only. Tries PowerShell `MediaPlayer` with `ringtone.mp3`, falls back to `winsound.Beep`. Non-Windows platforms silently do nothing.

- **Task input** — `QLineEdit` above the arc display. Locked while the timer is running; its text is captured by `_save_session()` when the work phase ends.

- **Settings controls** — all three `QSpinBox` widgets (work / break / long break minutes) are disabled while `is_running` is True or during the auto-start countdown. `update_*_time()` methods only update `remaining_time` if the timer is stopped and the matching phase is currently active.

## UI Language

All UI strings are in Traditional Chinese (繁體中文). Keep new UI text consistent with this convention.
