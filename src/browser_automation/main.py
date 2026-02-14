"""Точка входа: запуск GUI."""

import signal
from pathlib import Path

DEFAULT_PROFILES_PATH = Path.home() / ".config" / "browser-automation" / "profiles.json"


def main(profiles_path: Path | str | None = None) -> None:
    """
    Запуск GUI.
    Путь к profiles.json задаётся в init (по умолчанию ~/.config/browser-automation/profiles.json).
    Ctrl+C в терминале — завершение приложения.
    """
    from browser_automation.gui_main import MainWindow

    from PySide6.QtWidgets import QApplication

    path = profiles_path or DEFAULT_PROFILES_PATH
    app = QApplication([])
    win = MainWindow(profiles_path=path)
    win.show()

    def _on_sigint(*_args):
        win.close()  # вызовет closeEvent (сохранение куков, остановка браузеров)

    signal.signal(signal.SIGINT, _on_sigint)

    app.exec()


if __name__ == "__main__":
    main()
