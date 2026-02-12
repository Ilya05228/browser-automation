import os
import sys
import traceback
from pathlib import Path

from PySide6.QtCore import Qt, QThread, Signal
from PySide6.QtGui import QColor, QFont, QFontDatabase
from PySide6.QtWidgets import (
    QApplication,
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QMainWindow,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from .automation import Automation


class AutomationThread(QThread):
    status_update = Signal(str)
    finished = Signal()
    error = Signal(str)

    def __init__(self, automation, mode="start"):
        super().__init__()
        self.automation = automation
        self.mode = mode

    def run(self):
        try:
            if self.mode == "start":
                self.status_update.emit("Запуск браузера...")
                self.automation.start()
                self.status_update.emit(
                    "Войдите в аккаунт Instagram, затем нажмите 'Продолжить'"
                )
            elif self.mode == "continue":
                self.status_update.emit("Публикация Reels...")
                self.automation.continue_after_login()
                self.status_update.emit("Все Reels опубликованы!")
                self.finished.emit()
        except Exception as e:
            error_msg = f"{str(e)}\n\n{traceback.format_exc()}"
            self.error.emit(error_msg)


class ModernGUI(QMainWindow):
    def __init__(self):
        super().__init__()
        self.automation = None
        self.automation_thread = None
        self.selected_files = []
        self.init_ui()
        self.load_fonts()

    def load_fonts(self):
        font_paths = [
            "/usr/share/fonts/truetype/roboto/Roboto-Regular.ttf",
            "/usr/share/fonts/truetype/roboto/Roboto-Medium.ttf",
            "/usr/share/fonts/truetype/roboto/Roboto-Bold.ttf",
            "/usr/local/share/fonts/Roboto-Regular.ttf",
            str(Path.home() / ".fonts/Roboto-Regular.ttf"),
        ]

        for font_path in font_paths:
            if os.path.exists(font_path):
                font_id = QFontDatabase.addApplicationFont(font_path)
                if font_id != -1:
                    print(f"Шрифт Roboto загружен: {font_path}")
                    break

    def init_ui(self):
        self.setWindowTitle("Instagram Reels Publisher")
        self.setGeometry(100, 100, 800, 700)

        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        main_layout.setSpacing(20)
        main_layout.setContentsMargins(30, 30, 30, 30)

        title_label = QLabel("Instagram Reels Publisher")
        title_font = QFont()
        title_font.setPointSize(24)
        title_font.setBold(True)
        title_label.setFont(title_font)
        title_label.setAlignment(Qt.AlignCenter)
        title_label.setStyleSheet("color: #1a73e8; margin-bottom: 20px;")
        main_layout.addWidget(title_label)

        description_frame = self.create_input_frame("Описание для Reels")
        self.description_edit = QTextEdit()
        self.description_edit.setPlaceholderText("Введите описание для всех Reels...")
        self.description_edit.setMaximumHeight(100)
        description_frame.layout().addWidget(self.description_edit)
        main_layout.addWidget(description_frame)

        files_frame = self.create_input_frame("Видео файлы")
        files_layout = QVBoxLayout()

        files_button_layout = QHBoxLayout()
        self.select_files_btn = QPushButton("📁 Выбрать файлы")
        self.select_files_btn.setStyleSheet(self.get_button_style("#4285f4"))
        self.select_files_btn.clicked.connect(self.select_files)
        files_button_layout.addWidget(self.select_files_btn)

        self.clear_files_btn = QPushButton("🗑️ Очистить")
        self.clear_files_btn.setStyleSheet(self.get_button_style("#ea4335"))
        self.clear_files_btn.clicked.connect(self.clear_files)
        files_button_layout.addWidget(self.clear_files_btn)
        files_layout.addLayout(files_button_layout)

        self.files_list = QListWidget()
        self.files_list.setMaximumHeight(150)
        files_layout.addWidget(self.files_list)
        files_frame.layout().addLayout(files_layout)
        main_layout.addWidget(files_frame)

        account_frame = self.create_input_frame("Аккаунт Instagram")
        self.account_edit = QLineEdit()
        self.account_edit.setPlaceholderText("Введите имя аккаунта (без @)")
        account_frame.layout().addWidget(self.account_edit)
        main_layout.addWidget(account_frame)

        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        main_layout.addWidget(self.progress_bar)

        buttons_layout = QHBoxLayout()
        buttons_layout.setSpacing(20)

        self.start_btn = QPushButton("🚀 Начать")
        self.start_btn.setStyleSheet(
            self.get_button_style("#34a853", hover_color="#2e8b47")
        )
        self.start_btn.clicked.connect(self.start_process)
        self.start_btn.setMinimumHeight(50)
        buttons_layout.addWidget(self.start_btn)

        self.continue_btn = QPushButton("➡️ Продолжить")
        self.continue_btn.setStyleSheet(
            self.get_button_style("#fbbc05", hover_color="#e6ac00")
        )
        self.continue_btn.clicked.connect(self.continue_process)
        self.continue_btn.setMinimumHeight(50)
        self.continue_btn.setEnabled(False)
        buttons_layout.addWidget(self.continue_btn)

        main_layout.addLayout(buttons_layout)

        self.status_label = QLabel("Готов к работе")
        self.status_label.setAlignment(Qt.AlignCenter)
        self.status_label.setStyleSheet(
            "color: #5f6368; font-size: 14px; padding: 10px;"
        )
        main_layout.addWidget(self.status_label)

        self.setStyleSheet("""
            QMainWindow {
                background-color: #121212;
            }
            QFrame {
                background-color: #1e1e1e;
                border-radius: 10px;
                padding: 15px;
                border: 1px solid #333333;
            }
            QLabel {
                color: #ffffff;
            }
            QTextEdit, QLineEdit, QListWidget {
                background-color: #2d2d2d;
                color: #ffffff;
                border: 1px solid #444444;
                border-radius: 5px;
                padding: 8px;
                font-size: 14px;
                selection-background-color: #1a73e8;
            }
            QTextEdit:focus, QLineEdit:focus {
                border: 2px solid #1a73e8;
            }
            QListWidget::item {
                padding: 5px;
                border-bottom: 1px solid #333333;
                color: #ffffff;
            }
            QListWidget::item:selected {
                background-color: #1a73e8;
                color: #ffffff;
            }
            QProgressBar {
                border: 1px solid #444444;
                border-radius: 5px;
                text-align: center;
                color: #ffffff;
            }
            QProgressBar::chunk {
                background-color: #1a73e8;
                border-radius: 5px;
            }
        """)

        font = QFont("Roboto", 10)
        QApplication.setFont(font)

    def create_input_frame(self, title):
        frame = QFrame()
        frame.setFrameShape(QFrame.StyledPanel)
        layout = QVBoxLayout(frame)

        title_label = QLabel(title)
        title_font = QFont()
        title_font.setPointSize(14)
        title_font.setBold(True)
        title_label.setFont(title_font)
        title_label.setStyleSheet("color: #3c4043; margin-bottom: 10px;")
        layout.addWidget(title_label)

        return frame

    def get_button_style(self, color, hover_color=None):
        if not hover_color:
            hover_color = self.darken_color(color)
        return f"""
            QPushButton {{
                background-color: {color};
                color: white;
                border: none;
                border-radius: 8px;
                padding: 12px 24px;
                font-size: 14px;
                font-weight: bold;
            }}
            QPushButton:hover {{
                background-color: {hover_color};
            }}
            QPushButton:disabled {{
                background-color: #dadce0;
                color: #9aa0a6;
            }}
        """

    def darken_color(self, color):
        return QColor(color).darker(120).name()

    def select_files(self):
        files, _ = QFileDialog.getOpenFileNames(
            self, "Выберите видео файлы", "", "Video Files (*.mp4 *.mov);;All Files (*)"
        )
        if files:
            self.selected_files = files
            self.files_list.clear()
            for file in files:
                self.files_list.addItem(os.path.basename(file))
            self.update_status(f"Выбрано {len(files)} файлов")

    def clear_files(self):
        self.selected_files = []
        self.files_list.clear()
        self.update_status("Файлы очищены")

    def start_process(self):
        description = self.description_edit.toPlainText().strip()
        account = self.account_edit.text().strip().lower().replace("@", "")

        if not description:
            QMessageBox.warning(self, "Ошибка", "Введите описание для Reels")
            return
        if not self.selected_files:
            QMessageBox.warning(self, "Ошибка", "Выберите хотя бы один видео файл")
            return
        if not account:
            QMessageBox.warning(self, "Ошибка", "Введите имя аккаунта Instagram")
            return

        self.description_edit.setEnabled(False)
        self.account_edit.setEnabled(False)
        self.select_files_btn.setEnabled(False)
        self.clear_files_btn.setEnabled(False)
        self.start_btn.setEnabled(False)

        self.automation = Automation(description, self.selected_files, account)
        self.automation_thread = AutomationThread(self.automation, "start")
        self.automation_thread.status_update.connect(self.update_status)
        self.automation_thread.error.connect(self.show_error)
        self.automation_thread.start()

        self.continue_btn.setEnabled(True)
        self.progress_bar.setVisible(True)
        self.progress_bar.setRange(0, 0)

    def continue_process(self):
        if not self.automation:
            return

        self.continue_btn.setEnabled(False)
        self.automation_thread = AutomationThread(self.automation, "continue")
        self.automation_thread.status_update.connect(self.update_status)
        self.automation_thread.finished.connect(self.on_finished)
        self.automation_thread.error.connect(self.show_error)
        self.automation_thread.start()

    def update_status(self, message):
        self.status_label.setText(message)
        if "ошибка" in message.lower() or "error" in message.lower():
            self.status_label.setStyleSheet(
                "color: #ea4335; font-size: 14px; padding: 10px;"
            )
        elif "готово" in message.lower() or "успешно" in message.lower():
            self.status_label.setStyleSheet(
                "color: #34a853; font-size: 14px; padding: 10px;"
            )
        else:
            self.status_label.setStyleSheet(
                "color: #5f6368; font-size: 14px; padding: 10px;"
            )

    def on_finished(self):
        self.progress_bar.setVisible(False)
        QMessageBox.information(self, "Успешно", "Все Reels опубликованы!")
        self.reset_ui()

    def show_error(self, error_message):
        self.progress_bar.setVisible(False)
        QMessageBox.critical(self, "Ошибка", f"Произошла ошибка:\n{error_message}")
        self.reset_ui()

    def reset_ui(self):
        self.description_edit.setEnabled(True)
        self.account_edit.setEnabled(True)
        self.select_files_btn.setEnabled(True)
        self.clear_files_btn.setEnabled(True)
        self.start_btn.setEnabled(True)
        self.continue_btn.setEnabled(False)
        self.update_status("Готов к работе")


def main():
    app = QApplication(sys.argv)
    app.setApplicationName("Instagram Reels Publisher")

    window = ModernGUI()
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
