# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Running the App

```bash
pip install -r requirements.txt
python pomodoro.py
```

On Windows you can also double-click `start.bat`. There is no build step, no test suite, and no linter configured.

## Architecture

The entire application lives in a single file, `pomodoro.py`, as one class: `PomodoroTimer(QMainWindow)`.

**Timer state machine** — two boolean flags drive all state transitions:
- `is_running`: whether `QTimer` is ticking
- `is_working`: whether the current phase is work (`True`) or break (`False`)

When `remaining_time` reaches zero, `timer_finished()` flips `is_working`, resets `remaining_time` to the appropriate duration, increments `total_sessions` (work→break only), and shows a `QMessageBox`. The timer does **not** auto-restart; the user must press Start again.

**Theme system** — `LIGHT_THEME` and `DARK_THEME` are class-level dicts with keys `bg`, `text`, `status_text`, `working`, `resting`, and a nested `buttons` dict. `current_theme` always points to whichever dict is active. `toggle_theme()` switches the pointer and calls `_apply_theme()` (window background) + `_update_all_colors()` (all widgets). Button styles are applied via inline Qt stylesheets; there is no external stylesheet file.

**Sound** — `play_sound()` is Windows-only. It tries to play `ringtone.mp3` via a PowerShell `MediaPlayer` subprocess with a fade-in loop, falling back to `winsound.Beep` if that fails or the file is missing. On non-Windows platforms both paths silently do nothing (the `winsound` import raises `ImportError` which is caught).

**Settings controls** — the work/break `QSpinBox` widgets are disabled while the timer is running. `update_work_time()` / `update_break_time()` only update `remaining_time` if the timer is stopped **and** the relevant phase is currently active.

## UI Language

All UI strings are in Traditional Chinese (繁體中文). Keep new UI text consistent with this convention.
