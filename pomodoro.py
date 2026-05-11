import sys
import time
import os
from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout,
                             QHBoxLayout, QLabel, QPushButton, QSpinBox, QMessageBox)
from PyQt6.QtCore import QTimer, Qt
from PyQt6.QtGui import QFont

class PomodoroTimer(QMainWindow):
    # 時間配置（秒）
    DEFAULT_WORK_TIME = 25 * 60
    DEFAULT_BREAK_TIME = 5 * 60

    # UI配置
    WINDOW_WIDTH = 400
    WINDOW_HEIGHT = 300
    TIMER_INTERVAL_MS = 1000

    # 字體大小
    FONT_SIZE_TITLE = 20
    FONT_SIZE_STATUS = 12
    FONT_SIZE_TIME = 48
    FONT_SIZE_BUTTON = 11
    FONT_SIZE_LABEL = 10
    FONT_SIZE_STATS = 11

    # 淺色主題
    LIGHT_THEME = {
        'bg': '#f5f5f5',
        'text': '#333',
        'status_text': '#666',
        'working': '#d9534f',
        'resting': '#5cb85c',
        'buttons': {
            'start': {'bg': '#5cb85c', 'hover': '#4cae4c'},
            'pause': {'bg': '#f0ad4e', 'hover': '#ec971f'},
            'reset': {'bg': '#5bc0de', 'hover': '#46b8da'},
            'theme': {'bg': '#6c757d', 'hover': '#5a6268'},
        }
    }

    # 深色主題
    DARK_THEME = {
        'bg': '#1e1e1e',
        'text': '#e0e0e0',
        'status_text': '#b0b0b0',
        'working': '#ff6b6b',
        'resting': '#51cf66',
        'buttons': {
            'start': {'bg': '#51cf66', 'hover': '#40c057'},
            'pause': {'bg': '#ffa94d', 'hover': '#ff922b'},
            'reset': {'bg': '#74c0fc', 'hover': '#4dabf7'},
            'theme': {'bg': '#495057', 'hover': '#373b3f'},
        }
    }

    # 預設為淺色主題
    COLOR_WORKING = LIGHT_THEME['working']
    COLOR_RESTING = LIGHT_THEME['resting']
    COLOR_TEXT = LIGHT_THEME['status_text']
    BUTTON_STYLES = LIGHT_THEME['buttons']

    def __init__(self):
        super().__init__()
        self.work_time = self.DEFAULT_WORK_TIME
        self.break_time = self.DEFAULT_BREAK_TIME
        self.remaining_time = self.work_time
        self.is_working = True
        self.is_running = False
        self.total_sessions = 0
        self.is_dark_mode = False
        self.current_theme = self.LIGHT_THEME

        self.timer = QTimer()
        self.timer.timeout.connect(self.update_timer)

        self._setup_fonts()
        self.init_ui()

    def _setup_fonts(self):
        self.font_title = self._create_font(self.FONT_SIZE_TITLE, bold=True)
        self.font_status = self._create_font(self.FONT_SIZE_STATUS)
        self.font_time = self._create_font(self.FONT_SIZE_TIME, bold=True)
        self.font_button = self._create_font(self.FONT_SIZE_BUTTON)
        self.font_label = self._create_font(self.FONT_SIZE_LABEL)
        self.font_stats = self._create_font(self.FONT_SIZE_STATS)

    @staticmethod
    def _create_font(size, bold=False):
        font = QFont()
        font.setPointSize(size)
        if bold:
            font.setBold(True)
        return font

    def init_ui(self):
        self.setWindowTitle('番茄鐘')
        self.setGeometry(100, 100, self.WINDOW_WIDTH, self.WINDOW_HEIGHT)
        self._apply_theme()

        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        main_layout = QVBoxLayout()
        main_layout.setSpacing(15)
        main_layout.setContentsMargins(20, 20, 20, 20)

        # 主題按鈕
        theme_btn = self._create_styled_button('theme', self.toggle_theme)
        theme_btn.setText('🌙 深色')
        theme_btn.setMaximumWidth(100)
        self.theme_btn = theme_btn
        main_layout.addWidget(theme_btn, alignment=Qt.AlignmentFlag.AlignRight)

        main_layout.addWidget(self._create_label('番茄鐘計時器', self.font_title,
                                                  alignment=Qt.AlignmentFlag.AlignCenter))

        self.status_label = self._create_label('準備工作', self.font_status,
                                               alignment=Qt.AlignmentFlag.AlignCenter,
                                               color=self.COLOR_WORKING)
        main_layout.addWidget(self.status_label)

        self.time_label = self._create_label('25:00', self.font_time,
                                             alignment=Qt.AlignmentFlag.AlignCenter,
                                             color=self.COLOR_WORKING)
        main_layout.addWidget(self.time_label)

        main_layout.addLayout(self._create_button_layout())
        main_layout.addLayout(self._create_settings_layout())

        self.stats_label = self._create_label('完成的番茄鐘: 0', self.font_stats,
                                              alignment=Qt.AlignmentFlag.AlignCenter,
                                              color=self.COLOR_TEXT)
        main_layout.addWidget(self.stats_label)

        central_widget.setLayout(main_layout)

    def _create_label(self, text, font, alignment=None, color=None):
        label = QLabel(text)
        label.setFont(font)
        if alignment:
            label.setAlignment(alignment)
        if color:
            label.setStyleSheet(f"color: {color};")
        return label

    def _create_button_layout(self):
        layout = QHBoxLayout()

        self.start_btn = self._create_styled_button('start', self.start_timer)
        self.pause_btn = self._create_styled_button('pause', self.pause_timer)
        self.reset_btn = self._create_styled_button('reset', self.reset_timer)
        self.pause_btn.setEnabled(False)

        layout.addWidget(self.start_btn)
        layout.addWidget(self.pause_btn)
        layout.addWidget(self.reset_btn)

        return layout

    def _create_styled_button(self, style_key, callback):
        style = self.current_theme['buttons'].get(style_key, self.current_theme['buttons']['start'])
        text_map = {'start': '開始', 'pause': '暫停', 'reset': '重置', 'theme': '🌙 深色'}
        text = text_map.get(style_key, '按鈕')

        btn = QPushButton(text)
        btn.setFont(self.font_button)
        btn.clicked.connect(callback)
        self._apply_button_style(btn, style)
        return btn

    def _apply_button_style(self, btn, style):
        btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {style['bg']};
                color: white;
                border: none;
                border-radius: 5px;
                padding: 8px 16px;
                font-weight: bold;
            }}
            QPushButton:hover:enabled {{
                background-color: {style['hover']};
            }}
            QPushButton:disabled {{
                background-color: #ccc;
            }}
        """)

    def _create_settings_layout(self):
        layout = QHBoxLayout()

        layout.addWidget(self._create_label('工作時間 (分):', self.font_label))
        self.work_spinbox = QSpinBox()
        self.work_spinbox.setValue(25)
        self.work_spinbox.setRange(1, 60)
        self.work_spinbox.setMaximumWidth(80)
        self.work_spinbox.valueChanged.connect(self.update_work_time)
        layout.addWidget(self.work_spinbox)

        layout.addSpacing(20)

        layout.addWidget(self._create_label('休息時間 (分):', self.font_label))
        self.break_spinbox = QSpinBox()
        self.break_spinbox.setValue(5)
        self.break_spinbox.setRange(1, 30)
        self.break_spinbox.setMaximumWidth(80)
        self.break_spinbox.valueChanged.connect(self.update_break_time)
        layout.addWidget(self.break_spinbox)

        return layout

    def start_timer(self):
        if not self.is_running:
            self.is_running = True
            self._set_controls_enabled(start=False, pause=True, spinboxes=False)
            self.timer.start(self.TIMER_INTERVAL_MS)

    def pause_timer(self):
        self.is_running = False
        self._set_controls_enabled(start=True, pause=False, spinboxes=False)
        self.timer.stop()

    def reset_timer(self):
        self.timer.stop()
        self.is_running = False
        self.is_working = True
        self.remaining_time = self.work_time
        self.update_display()
        self._set_controls_enabled()

    def _set_controls_enabled(self, start=True, pause=False, spinboxes=True):
        self.start_btn.setEnabled(start)
        self.pause_btn.setEnabled(pause)
        self.work_spinbox.setEnabled(spinboxes)
        self.break_spinbox.setEnabled(spinboxes)

    def update_timer(self):
        self.remaining_time -= 1
        self.update_display()

        if self.remaining_time <= 0:
            self.timer_finished()

    def update_display(self):
        minutes = self.remaining_time // 60
        seconds = self.remaining_time % 60
        self.time_label.setText(f'{minutes:02d}:{seconds:02d}')

        if self.is_working:
            color = self.current_theme['working']
            self._set_status('工作中...', color)
        else:
            color = self.current_theme['resting']
            self._set_status('休息中...', color)

        self.time_label.setStyleSheet(f"color: {color};")

    def _set_status(self, text, color):
        self.status_label.setText(text)
        self.status_label.setStyleSheet(f"color: {color};")

    def timer_finished(self):
        self.play_sound()
        self.is_running = False
        self._set_controls_enabled()

        if self.is_working:
            self.is_working = False
            self.remaining_time = self.break_time
            self.total_sessions += 1
            self.stats_label.setText(f'完成的番茄鐘: {self.total_sessions}')
            QMessageBox.information(self, '通知', '工作時間結束！\n現在開始休息。')
        else:
            self.is_working = True
            self.remaining_time = self.work_time
            QMessageBox.information(self, '通知', '休息時間結束！\n準備開始下一個番茄鐘。')

        self.update_display()

    def play_sound(self):
        ringtone_path = os.path.join(os.path.dirname(__file__), 'ringtone.mp3')
        if os.path.isfile(ringtone_path):
            try:
                import subprocess
                ps_script = f'''
Add-Type -AssemblyName presentationCore
$player = New-Object System.Windows.Media.MediaPlayer
$player.Open([Uri]"{ringtone_path}")
$player.Play()
$duration = 5000
$steps = 50
$interval = $duration / $steps
for($i = 0; $i -lt $steps; $i++) {{
    $player.Volume = $i / $steps
    Start-Sleep -Milliseconds $interval
}}
$player.Stop()
'''
                subprocess.Popen(['powershell', '-NoProfile', '-WindowStyle', 'Hidden', '-Command', ps_script],
                               creationflags=0x08000000)
            except Exception as e:
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

    def update_work_time(self):
        if not self.is_running:
            self.work_time = self.work_spinbox.value() * 60
            if self.is_working:
                self.remaining_time = self.work_time
                self.update_display()

    def update_break_time(self):
        if not self.is_running:
            self.break_time = self.break_spinbox.value() * 60
            if not self.is_working:
                self.remaining_time = self.break_time
                self.update_display()

    def toggle_theme(self):
        self.is_dark_mode = not self.is_dark_mode
        self.current_theme = self.DARK_THEME if self.is_dark_mode else self.LIGHT_THEME
        self._apply_theme()
        self._update_all_colors()
        self.theme_btn.setText('☀️ 淺色' if self.is_dark_mode else '🌙 深色')

    def _apply_theme(self):
        self.setStyleSheet(f"background-color: {self.current_theme['bg']};")

    def _update_all_colors(self):
        # 更新所有按鈕樣式
        self._apply_button_style(self.start_btn, self.current_theme['buttons']['start'])
        self._apply_button_style(self.pause_btn, self.current_theme['buttons']['pause'])
        self._apply_button_style(self.reset_btn, self.current_theme['buttons']['reset'])
        self._apply_button_style(self.theme_btn, self.current_theme['buttons']['theme'])

        # 更新標籤顏色
        color = self.current_theme['working'] if self.is_working else self.current_theme['resting']
        self._set_status(self.status_label.text(), color)
        self.time_label.setStyleSheet(f"color: {color};")

        # 更新統計標籤
        self.stats_label.setStyleSheet(f"color: {self.current_theme['status_text']};")

    def closeEvent(self, event):
        self.timer.stop()
        event.accept()

def main():
    app = QApplication(sys.argv)
    window = PomodoroTimer()
    window.show()
    sys.exit(app.exec())

if __name__ == '__main__':
    main()
