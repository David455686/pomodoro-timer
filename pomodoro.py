import sys
import os
import json
from datetime import datetime
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QSpinBox, QLineEdit, QDialog, QTableWidget,
    QTableWidgetItem, QHeaderView, QFrame, QListWidget, QListWidgetItem
)
from PyQt6.QtCore import QTimer, Qt, QRectF
from PyQt6.QtGui import QFont, QPainter, QPen, QColor, QCursor


def _get_app_data_dir():
    if sys.platform == 'win32':
        base = os.environ.get('APPDATA', os.path.expanduser('~'))
    else:
        base = os.path.expanduser('~')
    path = os.path.join(base, '番茄鐘')
    os.makedirs(path, exist_ok=True)
    return path


# ── Timer display ─────────────────────────────────────────────────────────────

class TimerDisplay(QWidget):
    """Circular arc progress ring with centered time label."""

    ARC_WIDTH = 10

    def __init__(self, parent=None):
        super().__init__(parent)
        self._progress = 1.0
        self._arc_color = '#ff6b6b'
        self._track_color = '#2a2a3a'
        self.setMinimumSize(180, 180)

        self._label = QLabel('25:00', self)
        self._label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        font = QFont('Courier New', 42, QFont.Weight.Bold)
        self._label.setFont(font)

    def update_display(self, time_text, color, progress, track_color):
        self._progress = max(0.0, min(1.0, progress))
        self._arc_color = color
        self._track_color = track_color
        self._label.setText(time_text)
        self._label.setStyleSheet(f'color: {color}; background: transparent;')
        self.update()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._label.setGeometry(0, 0, self.width(), self.height())

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        w, h = self.width(), self.height()
        margin = 18
        size = min(w, h) - 2 * margin
        rect = QRectF((w - size) / 2, (h - size) / 2, size, size)

        pen = QPen(QColor(self._track_color), self.ARC_WIDTH)
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        painter.setPen(pen)
        painter.drawArc(rect, 0, 360 * 16)

        if self._progress > 0.005:
            pen.setColor(QColor(self._arc_color))
            painter.setPen(pen)
            painter.drawArc(rect, 90 * 16, -int(360 * 16 * self._progress))
        painter.end()


# ── Task list dialog ──────────────────────────────────────────────────────────

class TaskListDialog(QDialog):
    """Floating task list panel that stays on top alongside the timer."""

    TASKS_FILE = 'tasks.json'

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle('任務清單')
        self.setWindowFlags(
            Qt.WindowType.Window |
            Qt.WindowType.WindowStaysOnTopHint
        )
        self.resize(280, 360)
        self._tasks = []
        self._load_tasks()
        self._init_ui()

    def _tasks_path(self):
        return os.path.join(_get_app_data_dir(), self.TASKS_FILE)

    def _load_tasks(self):
        path = self._tasks_path()
        try:
            if os.path.isfile(path):
                with open(path, 'r', encoding='utf-8') as f:
                    self._tasks = json.load(f)
        except Exception:
            self._tasks = []

    def _save_tasks(self):
        try:
            with open(self._tasks_path(), 'w', encoding='utf-8') as f:
                json.dump(self._tasks, f, ensure_ascii=False, indent=2)
        except Exception:
            pass

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(8)

        self.list_widget = QListWidget()
        self.list_widget.setAlternatingRowColors(True)
        self.list_widget.itemChanged.connect(self._on_item_changed)
        layout.addWidget(self.list_widget)

        add_row = QHBoxLayout()
        self.add_input = QLineEdit()
        self.add_input.setPlaceholderText('新增任務，按 Enter...')
        self.add_input.returnPressed.connect(self._add_task)
        add_row.addWidget(self.add_input)
        add_btn = QPushButton('新增')
        add_btn.setFixedWidth(52)
        add_btn.clicked.connect(self._add_task)
        add_row.addWidget(add_btn)
        layout.addLayout(add_row)

        del_btn = QPushButton('刪除選取')
        del_btn.clicked.connect(self._delete_selected)
        layout.addWidget(del_btn)

        self._refresh_list()

    def _refresh_list(self):
        self.list_widget.blockSignals(True)
        self.list_widget.clear()
        for task in self._tasks:
            item = QListWidgetItem(task['text'])
            item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
            item.setCheckState(
                Qt.CheckState.Checked if task.get('done') else Qt.CheckState.Unchecked
            )
            self.list_widget.addItem(item)
        self.list_widget.blockSignals(False)

    def _on_item_changed(self, item):
        row = self.list_widget.row(item)
        if 0 <= row < len(self._tasks):
            self._tasks[row]['done'] = (item.checkState() == Qt.CheckState.Checked)
            self._save_tasks()

    def _add_task(self):
        text = self.add_input.text().strip()
        if not text:
            return
        self._tasks.append({'text': text, 'done': False})
        self._save_tasks()
        self._refresh_list()
        self.add_input.clear()
        self.list_widget.scrollToBottom()

    def _delete_selected(self):
        selected = self.list_widget.selectedItems()
        if not selected:
            return
        rows = sorted([self.list_widget.row(i) for i in selected], reverse=True)
        for row in rows:
            if 0 <= row < len(self._tasks):
                self._tasks.pop(row)
        self._save_tasks()
        self._refresh_list()

    def show(self):
        self._load_tasks()
        self._refresh_list()
        super().show()


# ── Main window ───────────────────────────────────────────────────────────────

class PomodoroTimer(QMainWindow):
    DEFAULT_WORK_TIME = 25 * 60
    DEFAULT_BREAK_TIME = 5 * 60
    DEFAULT_LONG_BREAK_TIME = 15 * 60
    LONG_BREAK_INTERVAL = 4
    AUTO_START_DELAY = 5

    WINDOW_WIDTH = 360
    WINDOW_HEIGHT = 480
    TIMER_INTERVAL_MS = 1000

    LIGHT_THEME = {
        'bg': 'rgba(245, 245, 250, 230)',
        'text': '#1a1a2e',
        'status_text': '#666680',
        'track': '#dcdce8',
        'working': '#e05252',
        'resting': '#3da84a',
        'long_break': '#4a8fd4',
        'titlebar': 'rgba(235, 235, 242, 230)',
        'input_bg': '#ffffff',
        'input_border': '#d0d0e0',
        'buttons': {
            'start':   {'bg': '#3da84a', 'hover': '#2d8a3a'},
            'pause':   {'bg': '#e08a30', 'hover': '#c87820'},
            'reset':   {'bg': '#5a9fd4', 'hover': '#4a8fc4'},
            'close':   {'bg': '#e05252', 'hover': '#c04040'},
            'minimize':{'bg': '#aaaaaa', 'hover': '#888888'},
            'history': {'bg': '#7878b0', 'hover': '#6060a0'},
            'tasks':   {'bg': '#4a8fd4', 'hover': '#3a7fc4'},
            'theme':   {'bg': '#9090a8', 'hover': '#787890'},
        },
    }

    DARK_THEME = {
        'bg': 'rgba(18, 18, 28, 220)',
        'text': '#e8e8f0',
        'status_text': '#9090b0',
        'track': '#2a2a3a',
        'working': '#ff6b6b',
        'resting': '#51cf66',
        'long_break': '#74b9ff',
        'titlebar': 'rgba(28, 28, 42, 220)',
        'input_bg': '#1e1e2e',
        'input_border': '#3a3a5a',
        'buttons': {
            'start':   {'bg': '#51cf66', 'hover': '#40c057'},
            'pause':   {'bg': '#ffa94d', 'hover': '#ff922b'},
            'reset':   {'bg': '#74c0fc', 'hover': '#4dabf7'},
            'close':   {'bg': '#ff6b6b', 'hover': '#e05252'},
            'minimize':{'bg': '#555570', 'hover': '#444460'},
            'history': {'bg': '#8888cc', 'hover': '#6666aa'},
            'tasks':   {'bg': '#74b9ff', 'hover': '#4dabf7'},
            'theme':   {'bg': '#4a4a6a', 'hover': '#383858'},
        },
    }

    def __init__(self):
        super().__init__()
        self.work_time = self.DEFAULT_WORK_TIME
        self.break_time = self.DEFAULT_BREAK_TIME
        self.long_break_time = self.DEFAULT_LONG_BREAK_TIME
        self.remaining_time = self.work_time
        self.current_phase_total = self.work_time
        self.is_working = True
        self.is_long_break = False
        self.is_running = False
        self.total_sessions = 0
        self.sessions_since_long_break = 0
        self.is_dark_mode = False
        self.current_theme = self.LIGHT_THEME
        self.auto_start_countdown = 0
        self._countdown_base_msg = ''
        self._drag_pos = None
        self._task_dialog = None

        self.timer = QTimer()
        self.timer.timeout.connect(self._tick)
        self.auto_start_timer = QTimer()
        self.auto_start_timer.timeout.connect(self._auto_start_tick)

        self._setup_fonts()
        self._init_window()
        self.init_ui()

    def _setup_fonts(self):
        def f(size, bold=False):
            font = QFont()
            font.setPointSize(size)
            if bold:
                font.setBold(True)
            return font

        self.font_title = f(12, bold=True)
        self.font_status = f(11)
        self.font_button = f(10, bold=True)
        self.font_label = f(9)
        self.font_stats = f(10)

    def _init_window(self):
        self.setWindowTitle('番茄鐘')
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.WindowStaysOnTopHint
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setFixedSize(self.WINDOW_WIDTH, self.WINDOW_HEIGHT)

    def init_ui(self):
        container = QFrame()
        container.setObjectName('container')
        self.setCentralWidget(container)

        root = QVBoxLayout(container)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)
        root.addWidget(self._create_title_bar())

        body = QVBoxLayout()
        body.setContentsMargins(20, 12, 20, 16)
        body.setSpacing(8)

        self.task_input = QLineEdit()
        self.task_input.setPlaceholderText('輸入任務名稱...')
        self.task_input.setFont(self.font_status)
        self.task_input.setFixedHeight(34)
        body.addWidget(self.task_input)

        self.timer_display = TimerDisplay()
        self.timer_display.setMinimumHeight(180)
        body.addWidget(self.timer_display, stretch=1)

        self.status_label = QLabel('準備工作')
        self.status_label.setFont(self.font_status)
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.status_label.setWordWrap(True)
        body.addWidget(self.status_label)

        body.addLayout(self._create_button_layout())
        body.addLayout(self._create_settings_layout())
        body.addLayout(self._create_stats_row())

        root.addLayout(body)
        self._apply_container_style()
        self._update_all_colors()
        self._refresh_display()

    def _create_title_bar(self):
        bar = QWidget()
        bar.setObjectName('titleBar')
        bar.setFixedHeight(40)

        layout = QHBoxLayout(bar)
        layout.setContentsMargins(14, 0, 8, 0)
        layout.setSpacing(4)

        self.title_label = QLabel('🍅 番茄鐘')
        self.title_label.setFont(self.font_title)
        layout.addWidget(self.title_label)
        layout.addStretch()

        self.tasks_btn   = self._make_icon_btn('📝', 'tasks',   self._toggle_tasks)
        self.history_btn = self._make_icon_btn('📋', 'history', self._show_history)
        self.theme_btn   = self._make_icon_btn('🌙', 'theme',   self.toggle_theme)
        self.minimize_btn= self._make_icon_btn('—',  'minimize', self.showMinimized)
        self.close_btn   = self._make_icon_btn('✕',  'close',    self.close)

        for btn in [self.tasks_btn, self.history_btn, self.theme_btn,
                    self.minimize_btn, self.close_btn]:
            layout.addWidget(btn)

        bar.mousePressEvent = self._title_press
        bar.mouseMoveEvent  = self._title_move
        return bar

    def _make_icon_btn(self, text, style_key, callback):
        btn = QPushButton(text)
        btn.setFont(self.font_button)
        btn.setFixedSize(28, 28)
        btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        btn.clicked.connect(callback)
        self._apply_icon_style(btn, style_key)
        return btn

    def _apply_icon_style(self, btn, key):
        s = self.current_theme['buttons'][key]
        btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {s['bg']}; color: white;
                border: none; border-radius: 6px; font-size: 12px;
            }}
            QPushButton:hover {{ background-color: {s['hover']}; }}
        """)

    def _create_button_layout(self):
        layout = QHBoxLayout()
        layout.setSpacing(8)
        self.start_btn = self._make_action_btn('開始', 'start', self.start_timer)
        self.pause_btn = self._make_action_btn('暫停', 'pause', self.pause_timer)
        self.reset_btn = self._make_action_btn('重置', 'reset', self.reset_timer)
        self.pause_btn.setEnabled(False)
        for btn in [self.start_btn, self.pause_btn, self.reset_btn]:
            layout.addWidget(btn)
        return layout

    def _make_action_btn(self, text, style_key, callback):
        btn = QPushButton(text)
        btn.setFont(self.font_button)
        btn.setFixedHeight(36)
        btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        btn.clicked.connect(callback)
        self._apply_action_style(btn, style_key)
        return btn

    def _apply_action_style(self, btn, key):
        s = self.current_theme['buttons'][key]
        btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {s['bg']}; color: white;
                border: none; border-radius: 10px;
                padding: 6px 12px; font-weight: bold;
            }}
            QPushButton:hover:enabled {{ background-color: {s['hover']}; }}
            QPushButton:disabled {{ background-color: #888; color: #ccc; }}
        """)

    def _create_settings_layout(self):
        layout = QHBoxLayout()
        layout.setSpacing(6)
        layout.addWidget(self._lbl('工作'))
        self.work_spinbox = self._spinbox(25, 1, 60, self.update_work_time)
        layout.addWidget(self.work_spinbox)
        layout.addWidget(self._lbl('休息'))
        self.break_spinbox = self._spinbox(5, 1, 30, self.update_break_time)
        layout.addWidget(self.break_spinbox)
        layout.addWidget(self._lbl('長休'))
        self.long_break_spinbox = self._spinbox(15, 5, 60, self.update_long_break_time)
        layout.addWidget(self.long_break_spinbox)
        return layout

    def _lbl(self, text):
        lbl = QLabel(text)
        lbl.setFont(self.font_label)
        return lbl

    def _spinbox(self, default, lo, hi, slot):
        sb = QSpinBox()
        sb.setValue(default)
        sb.setRange(lo, hi)
        sb.setMaximumWidth(54)
        sb.setFixedHeight(26)
        sb.valueChanged.connect(slot)
        return sb

    def _create_stats_row(self):
        layout = QHBoxLayout()
        self.stats_label = QLabel('🍅 × 0  今日完成')
        self.stats_label.setFont(self.font_stats)
        layout.addWidget(self.stats_label)
        layout.addStretch()
        return layout

    # ── Drag ─────────────────────────────────────────────────────────────────

    def _title_press(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_pos = event.globalPosition().toPoint() - self.frameGeometry().topLeft()

    def _title_move(self, event):
        if self._drag_pos and event.buttons() == Qt.MouseButton.LeftButton:
            self.move(event.globalPosition().toPoint() - self._drag_pos)

    # ── Keyboard ──────────────────────────────────────────────────────────────

    def keyPressEvent(self, event):
        k = event.key()
        if k == Qt.Key.Key_Space:
            if self.is_running:
                self.pause_timer()
            elif self.auto_start_countdown > 0:
                self._cancel_auto_start()
                self.start_timer()
            else:
                self.start_timer()
        elif k == Qt.Key.Key_R:
            self.reset_timer()
        elif k == Qt.Key.Key_Escape:
            self.showMinimized()

    # ── Timer control ─────────────────────────────────────────────────────────

    def start_timer(self):
        if not self.is_running:
            self._cancel_auto_start()
            self.is_running = True
            self._set_controls(start=False, pause=True, spinboxes=False)
            self.task_input.setEnabled(False)
            self.timer.start(self.TIMER_INTERVAL_MS)

    def pause_timer(self):
        self.is_running = False
        self._set_controls(start=True, pause=False, spinboxes=False)
        self.timer.stop()

    def reset_timer(self):
        self._cancel_auto_start()
        self.timer.stop()
        self.is_running = False
        self.is_working = True
        self.is_long_break = False
        self.remaining_time = self.work_time
        self.current_phase_total = self.work_time
        self._set_controls()
        self.task_input.setEnabled(True)
        self._refresh_display()

    def _set_controls(self, start=True, pause=False, spinboxes=True):
        self.start_btn.setEnabled(start)
        self.pause_btn.setEnabled(pause)
        self.work_spinbox.setEnabled(spinboxes)
        self.break_spinbox.setEnabled(spinboxes)
        self.long_break_spinbox.setEnabled(spinboxes)

    def _tick(self):
        self.remaining_time -= 1
        self._refresh_display()
        if self.remaining_time <= 0:
            self._phase_finished()

    def _phase_finished(self):
        self.timer.stop()
        self.is_running = False
        self.play_sound()

        if self.is_working:
            self._save_session()
            self.total_sessions += 1
            self.sessions_since_long_break += 1
            self.stats_label.setText(f'🍅 × {self.total_sessions}  今日完成')
            self.is_working = False

            if self.sessions_since_long_break >= self.LONG_BREAK_INTERVAL:
                self.is_long_break = True
                self.sessions_since_long_break = 0
                self.remaining_time = self.long_break_time
                self.current_phase_total = self.long_break_time
                msg = f'🎉 完成 {self.total_sessions} 個番茄！長休息開始...'
            else:
                self.is_long_break = False
                self.remaining_time = self.break_time
                self.current_phase_total = self.break_time
                msg = '✅ 工作結束！準備休息...'
        else:
            self.is_working = True
            self.is_long_break = False
            self.remaining_time = self.work_time
            self.current_phase_total = self.work_time
            msg = '🚀 休息結束！準備開始下一輪...'

        self._set_controls(start=False, pause=False, spinboxes=False)
        self.task_input.setEnabled(False)
        self._refresh_display()
        self._start_auto_countdown(msg)

    def _start_auto_countdown(self, msg):
        self.auto_start_countdown = self.AUTO_START_DELAY
        self._countdown_base_msg = msg
        self._show_countdown()
        self.auto_start_timer.start(self.TIMER_INTERVAL_MS)

    def _show_countdown(self):
        color = self._phase_color()
        self.status_label.setText(
            f'{self._countdown_base_msg}（{self.auto_start_countdown} 秒）'
        )
        self.status_label.setStyleSheet(f'color: {color};')

    def _auto_start_tick(self):
        self.auto_start_countdown -= 1
        if self.auto_start_countdown <= 0:
            self._cancel_auto_start()
            self.start_timer()
        else:
            self._show_countdown()

    def _cancel_auto_start(self):
        self.auto_start_timer.stop()
        self.auto_start_countdown = 0
        self._set_controls()
        self.task_input.setEnabled(True)

    # ── Settings ──────────────────────────────────────────────────────────────

    def update_work_time(self):
        if not self.is_running:
            self.work_time = self.work_spinbox.value() * 60
            if self.is_working:
                self.remaining_time = self.work_time
                self.current_phase_total = self.work_time
                self._refresh_display()

    def update_break_time(self):
        if not self.is_running:
            self.break_time = self.break_spinbox.value() * 60
            if not self.is_working and not self.is_long_break:
                self.remaining_time = self.break_time
                self.current_phase_total = self.break_time
                self._refresh_display()

    def update_long_break_time(self):
        if not self.is_running:
            self.long_break_time = self.long_break_spinbox.value() * 60
            if not self.is_working and self.is_long_break:
                self.remaining_time = self.long_break_time
                self.current_phase_total = self.long_break_time
                self._refresh_display()

    # ── Display ───────────────────────────────────────────────────────────────

    def _phase_color(self):
        if self.is_working:
            return self.current_theme['working']
        if self.is_long_break:
            return self.current_theme['long_break']
        return self.current_theme['resting']

    def _refresh_display(self):
        m, s = divmod(self.remaining_time, 60)
        color = self._phase_color()
        progress = self.remaining_time / max(self.current_phase_total, 1)
        self.timer_display.update_display(
            f'{m:02d}:{s:02d}', color, progress, self.current_theme['track']
        )
        if self.auto_start_countdown <= 0:
            if self.is_working:
                status = '工作中...' if self.is_running else '準備工作'
            elif self.is_long_break:
                status = '長休息中...' if self.is_running else '長休息'
            else:
                status = '休息中...' if self.is_running else '準備休息'
            self.status_label.setText(status)
            self.status_label.setStyleSheet(f'color: {color};')

    # ── Theme ─────────────────────────────────────────────────────────────────

    def toggle_theme(self):
        self.is_dark_mode = not self.is_dark_mode
        self.current_theme = self.DARK_THEME if self.is_dark_mode else self.LIGHT_THEME
        self._update_all_colors()
        self.theme_btn.setText('☀️' if self.is_dark_mode else '🌙')

    def _apply_container_style(self):
        t = self.current_theme
        self.centralWidget().setStyleSheet(f"""
            QFrame#container {{
                background-color: {t['bg']};
                border-radius: 16px;
            }}
            QWidget#titleBar {{
                background-color: {t['titlebar']};
                border-top-left-radius: 16px;
                border-top-right-radius: 16px;
            }}
            QSpinBox {{
                background-color: {t['input_bg']};
                color: {t['text']};
                border: 1px solid {t['input_border']};
                border-radius: 4px;
                padding: 1px 2px;
            }}
            QLineEdit {{
                background-color: {t['input_bg']};
                color: {t['text']};
                border: 1px solid {t['input_border']};
                border-radius: 8px;
                padding: 4px 8px;
            }}
            QLabel {{
                color: {t['text']};
                background: transparent;
            }}
        """)

    def _update_all_colors(self):
        self._apply_container_style()
        self._apply_action_style(self.start_btn, 'start')
        self._apply_action_style(self.pause_btn, 'pause')
        self._apply_action_style(self.reset_btn, 'reset')
        self._apply_icon_style(self.tasks_btn,    'tasks')
        self._apply_icon_style(self.history_btn,  'history')
        self._apply_icon_style(self.theme_btn,    'theme')
        self._apply_icon_style(self.minimize_btn, 'minimize')
        self._apply_icon_style(self.close_btn,    'close')
        self.stats_label.setStyleSheet(
            f'color: {self.current_theme["status_text"]}; background: transparent;'
        )
        self._refresh_display()

    # ── Tasks ─────────────────────────────────────────────────────────────────

    def _toggle_tasks(self):
        if self._task_dialog is None:
            self._task_dialog = TaskListDialog(self)
        if self._task_dialog.isVisible():
            self._task_dialog.hide()
        else:
            self._task_dialog.show()
            self._task_dialog.raise_()

    # ── History ───────────────────────────────────────────────────────────────

    def _history_path(self):
        return os.path.join(_get_app_data_dir(), 'history.json')

    def _save_session(self):
        task = self.task_input.text().strip() or '未命名任務'
        now = datetime.now()
        entry = {
            'date': now.strftime('%Y-%m-%d'),
            'time': now.strftime('%H:%M'),
            'task': task,
            'type': 'work',
            'duration_min': self.work_spinbox.value(),
        }
        path = self._history_path()
        try:
            data = []
            if os.path.isfile(path):
                with open(path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
            data.append(entry)
            with open(path, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception:
            pass

    def _show_history(self):
        path = self._history_path()
        data = []
        if os.path.isfile(path):
            try:
                with open(path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
            except Exception:
                pass

        dlg = QDialog(self)
        dlg.setWindowTitle('歷史紀錄')
        dlg.resize(440, 340)
        layout = QVBoxLayout(dlg)

        records = list(reversed(data))[:20]
        table = QTableWidget(len(records), 4)
        table.setHorizontalHeaderLabels(['日期', '時間', '任務', '分鐘'])
        table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        table.verticalHeader().setVisible(False)
        table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        table.setAlternatingRowColors(True)

        for row, rec in enumerate(records):
            table.setItem(row, 0, QTableWidgetItem(rec.get('date', '')))
            table.setItem(row, 1, QTableWidgetItem(rec.get('time', '')))
            table.setItem(row, 2, QTableWidgetItem(rec.get('task', '')))
            table.setItem(row, 3, QTableWidgetItem(str(rec.get('duration_min', ''))))

        layout.addWidget(table)
        close_btn = QPushButton('關閉')
        close_btn.clicked.connect(dlg.accept)
        layout.addWidget(close_btn, alignment=Qt.AlignmentFlag.AlignRight)
        dlg.exec()

    # ── Sound ─────────────────────────────────────────────────────────────────

    def play_sound(self):
        ringtone_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'ringtone.mp3')
        if os.path.isfile(ringtone_path):
            try:
                import subprocess
                ps_script = f'''
Add-Type -AssemblyName presentationCore
$player = New-Object System.Windows.Media.MediaPlayer
$player.Open([Uri]"{ringtone_path}")
$player.Play()
$duration = 5000; $steps = 50; $interval = $duration / $steps
for($i = 0; $i -lt $steps; $i++) {{
    $player.Volume = $i / $steps
    Start-Sleep -Milliseconds $interval
}}
$player.Stop()
'''
                subprocess.Popen(
                    ['powershell', '-NoProfile', '-WindowStyle', 'Hidden', '-Command', ps_script],
                    creationflags=0x08000000
                )
            except Exception:
                self._fallback_sound()
        else:
            self._fallback_sound()

    def _fallback_sound(self):
        try:
            import winsound
            for _ in range(3):
                winsound.Beep(1000, 300)
                winsound.Beep(800, 100)
        except ImportError:
            pass

    def closeEvent(self, event):
        self.timer.stop()
        self.auto_start_timer.stop()
        if self._task_dialog:
            self._task_dialog.close()
        event.accept()


def main():
    app = QApplication(sys.argv)
    app.setApplicationName('番茄鐘')
    window = PomodoroTimer()
    window.show()
    sys.exit(app.exec())


if __name__ == '__main__':
    main()
