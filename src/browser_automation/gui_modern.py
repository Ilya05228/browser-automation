import os
import sys
from multiprocessing import get_context
from queue import Empty
from pathlib import Path

from PySide6.QtCore import Qt, QThread, Signal, QTimer
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
    QTabWidget,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from .automation_worker import run_worker, run_open_instagram_worker


class QueueReaderThread(QThread):
    """Читает сообщения из очереди процесса и шлёт сигналы в GUI."""
    status_update = Signal(str)
    finished = Signal()
    error = Signal(str)

    def __init__(self, out_queue, process):
        super().__init__()
        self.out_queue = out_queue
        self.process = process

    def run(self):
        while True:
            try:
                msg = self.out_queue.get(timeout=0.3)
            except Empty:
                if not self.process.is_alive():
                    # Процесс завершился без "done" — сбрасываем UI, чтобы кнопки снова работали
                    self.error.emit("Процесс завершился. Можно снова выбрать файлы и начать.")
                    break
                continue
            if msg[0] == "status":
                self.status_update.emit(msg[1])
            elif msg[0] == "finished":
                self.finished.emit()
            elif msg[0] == "error":
                self.error.emit(msg[1])
            elif msg[0] == "done":
                break


class ModernGUI(QMainWindow):
    def __init__(self):
        super().__init__()
        self.worker_process = None
        self.in_queue = None
        self.out_queue = None
        self.reader_thread = None
        self.selected_files = []
        # Для второй вкладки - список открытых браузеров
        self.open_browsers = []  # Список словарей: {"process": Process, "account": str, "out_queue": Queue, "reader_thread": QThread}
        self.init_ui()
        self.load_fonts()
        
        # Таймер для периодического обновления списка браузеров
        self.browsers_update_timer = QTimer()
        self.browsers_update_timer.timeout.connect(self.update_browsers_list)
        self.browsers_update_timer.start(5000)  # Обновляем каждые 5 секунд

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

        # Создаём вкладки
        self.tabs = QTabWidget()

        # Вкладка 1: Автопостинг
        self.autopost_tab = QWidget()
        self.init_autopost_tab()
        self.tabs.addTab(self.autopost_tab, "📤 Автопостинг")

        # Вкладка 2: Открыть Instagram
        self.open_instagram_tab = QWidget()
        self.init_open_instagram_tab()
        self.tabs.addTab(self.open_instagram_tab, "🔐 Открыть Instagram")

        main_layout.addWidget(self.tabs)

        # Общий статус для обеих вкладок
        self.status_label = QLabel("Готов к работе")
        self.status_label.setAlignment(Qt.AlignCenter)
        self.status_label.setStyleSheet(
            "color: #5f6368; font-size: 14px; padding: 10px;"
        )
        main_layout.addWidget(self.status_label)

    def init_autopost_tab(self):
        """Инициализация вкладки автопостинга."""
        layout = QVBoxLayout(self.autopost_tab)
        layout.setSpacing(20)
        layout.setContentsMargins(20, 20, 20, 20)

        description_frame = self.create_input_frame("Описание для Reels")
        self.description_edit = QTextEdit()
        self.description_edit.setPlaceholderText("Введите описание для всех Reels...")
        self.description_edit.setMaximumHeight(100)
        description_frame.layout().addWidget(self.description_edit)
        layout.addWidget(description_frame)

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
        layout.addWidget(files_frame)

        account_frame = self.create_input_frame("Аккаунт Instagram")
        self.account_edit = QLineEdit()
        self.account_edit.setPlaceholderText("Введите имя аккаунта (без @)")
        account_frame.layout().addWidget(self.account_edit)
        layout.addWidget(account_frame)

        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        layout.addWidget(self.progress_bar)

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

        layout.addLayout(buttons_layout)
        layout.addStretch()

    def init_open_instagram_tab(self):
        """Инициализация вкладки открытия Instagram."""
        layout = QVBoxLayout(self.open_instagram_tab)
        layout.setSpacing(20)
        layout.setContentsMargins(20, 20, 20, 20)

        info_label = QLabel(
            "Эта вкладка открывает страницу логина Instagram.\n"
            "Войдите в аккаунт, и сессия будет автоматически сохранена локально.\n"
            "Можно открыть несколько браузеров одновременно.\n"
            "Куки обновляются автоматически каждую минуту."
        )
        info_label.setAlignment(Qt.AlignCenter)
        info_label.setStyleSheet("color: #ffffff; font-size: 14px; padding: 20px;")
        layout.addWidget(info_label)

        account_frame = self.create_input_frame("Аккаунт Instagram")
        self.open_instagram_account_edit = QLineEdit()
        self.open_instagram_account_edit.setPlaceholderText("Введите имя аккаунта (без @)")
        account_frame.layout().addWidget(self.open_instagram_account_edit)
        layout.addWidget(account_frame)

        self.open_instagram_btn = QPushButton("🔐 Открыть Instagram")
        self.open_instagram_btn.setStyleSheet(
            self.get_button_style("#1a73e8", hover_color="#4285f4")
        )
        self.open_instagram_btn.clicked.connect(self.open_instagram_process)
        self.open_instagram_btn.setMinimumHeight(50)
        layout.addWidget(self.open_instagram_btn)

        # Список открытых браузеров
        browsers_frame = self.create_input_frame("Открытые браузеры")
        self.open_browsers_list = QListWidget()
        self.open_browsers_list.setMaximumHeight(200)
        browsers_frame.layout().addWidget(self.open_browsers_list)
        layout.addWidget(browsers_frame)

        layout.addStretch()

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
            QTabWidget::pane {
                border: 1px solid #333333;
                background-color: #1e1e1e;
                border-radius: 5px;
            }
            QTabBar::tab {
                background-color: #2d2d2d;
                color: #ffffff;
                padding: 10px 20px;
                margin-right: 2px;
                border-top-left-radius: 5px;
                border-top-right-radius: 5px;
            }
            QTabBar::tab:selected {
                background-color: #1a73e8;
                color: #ffffff;
            }
            QTabBar::tab:hover {
                background-color: #4285f4;
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
            self, "Выберите медиа файлы", "", "All Files (*)"
        )
        if files:
            self.selected_files = files
            self.files_list.clear()
            for file in files:
                self.files_list.addItem(file)
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

        # spawn = новый процесс без наследования asyncio/Qt от родителя (fork даёт "Sync API inside asyncio loop")
        ctx = get_context("spawn")
        self.in_queue = ctx.Queue()
        self.out_queue = ctx.Queue()
        self.worker_process = ctx.Process(
            target=run_worker,
            args=(self.in_queue, self.out_queue, description, self.selected_files, account),
        )
        self.worker_process.start()
        self.reader_thread = QueueReaderThread(self.out_queue, self.worker_process)
        self.reader_thread.status_update.connect(self.update_status)
        self.reader_thread.finished.connect(self.on_finished)
        self.reader_thread.error.connect(self.show_error)
        self.reader_thread.start()

        self.continue_btn.setEnabled(True)
        self.progress_bar.setVisible(True)
        self.progress_bar.setRange(0, 0)

    def continue_process(self):
        if not self.in_queue:
            return
        self.continue_btn.setEnabled(False)
        self.in_queue.put("continue")

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

    def open_instagram_process(self):
        """Обработчик для открытия Instagram."""
        account = self.open_instagram_account_edit.text().strip().lower().replace("@", "")
        if not account:
            QMessageBox.warning(self, "Ошибка", "Введите имя аккаунта Instagram")
            return

        # Проверяем, не открыт ли уже браузер для этого аккаунта
        for browser_info in self.open_browsers:
            if browser_info["account"] == account:
                QMessageBox.warning(
                    self, "Внимание", f"Браузер для аккаунта {account} уже открыт!"
                )
                return

        # Очищаем форму сразу после нажатия кнопки
        self.open_instagram_account_edit.clear()

        ctx = get_context("spawn")
        out_queue = ctx.Queue()
        worker_process = ctx.Process(
            target=run_open_instagram_worker,
            args=(out_queue, account),
        )
        worker_process.start()

        # Создаём reader thread для этого браузера
        reader_thread = QueueReaderThread(out_queue, worker_process)
        reader_thread.status_update.connect(
            lambda msg, acc=account: self.update_open_instagram_status(msg, acc)
        )
        reader_thread.finished.connect(
            lambda acc=account: self.on_open_instagram_finished(acc)
        )
        reader_thread.error.connect(
            lambda err, acc=account: self.show_open_instagram_error(err, acc)
        )
        reader_thread.start()

        # Сохраняем информацию о браузере
        browser_info = {
            "process": worker_process,
            "account": account,
            "out_queue": out_queue,
            "reader_thread": reader_thread,
        }
        self.open_browsers.append(browser_info)

        # Обновляем список открытых браузеров
        self.update_browsers_list()

        self.update_status(f"Запуск браузера для {account}...")

    def update_browsers_list(self):
        """Обновляет список открытых браузеров."""
        self.open_browsers_list.clear()
        for browser_info in self.open_browsers:
            account = browser_info["account"]
            process = browser_info["process"]
            status = "🟢 Работает" if process.is_alive() else "🔴 Закрыт"
            self.open_browsers_list.addItem(f"{status} - {account}")

    def update_open_instagram_status(self, message, account):
        """Обновляет статус для конкретного браузера."""
        self.update_status(f"[{account}] {message}")

    def on_open_instagram_finished(self, account):
        """Обработчик завершения открытия Instagram."""
        self.update_status(f"Браузер для {account} открыт и работает. Куки обновляются каждую минуту.")
        self.update_browsers_list()

    def show_open_instagram_error(self, error_message, account):
        """Обработчик ошибки при открытии Instagram."""
        QMessageBox.critical(
            self, "Ошибка", f"Ошибка при открытии браузера для {account}:\n{error_message}"
        )
        # Удаляем браузер из списка при ошибке
        self.open_browsers = [
            b for b in self.open_browsers if b["account"] != account
        ]
        self.update_browsers_list()
        self.update_status("Готов к работе")


def main():
    app = QApplication(sys.argv)
    app.setApplicationName("Instagram Reels Publisher")

    window = ModernGUI()
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
