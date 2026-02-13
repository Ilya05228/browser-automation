"""Точка входа: запуск GUI."""

from pathlib import Path

DEFAULT_PROFILES_PATH = Path.home() / ".config" / "browser-automation" / "profiles.json"


def main(profiles_path: Path | str | None = None) -> None:
    """
    Запуск GUI.
    Путь к profiles.json задаётся в init (по умолчанию ~/.config/browser-automation/profiles.json).
    """
    from browser_automation.gui_main import MainWindow

    from PySide6.QtWidgets import QApplication

    path = profiles_path or DEFAULT_PROFILES_PATH
    app = QApplication([])
    win = MainWindow(profiles_path=path)
    win.show()
    app.exec()


if __name__ == "__main__":
    main()
