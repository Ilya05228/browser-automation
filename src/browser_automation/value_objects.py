from enum import Enum
from pathlib import Path


class OnErrorBrowser(Enum):
    """При ошибке: закрыть браузер или оставить открытым для отладки."""

    CLOSE = "close"  # по умолчанию — закрыть браузер
    KEEP_OPEN = "keep_open"  # оставить открытым, чтобы посмотреть, что не так


class DelayRange:
    """Value object: задержка «от» и «до» в секундах (для случайной паузы между действиями)."""

    def __init__(self, min_sec: float, max_sec: float) -> None:
        if min_sec < 0 or max_sec < 0:
            raise ValueError("min_sec и max_sec должны быть >= 0")
        if min_sec > max_sec:
            raise ValueError("min_sec не может быть больше max_sec")
        self.min_sec = min_sec
        self.max_sec = max_sec


VIDEO_EXTENSIONS = frozenset({".mp4", ".mov", ".avi", ".mkv", ".webm", ".m4v", ".flv"})
PHOTO_EXTENSIONS = frozenset({".jpg", ".jpeg", ".png", ".gif", ".webp", ".bmp", ".heic"})


class InstagramProfile:
    """Value object: Instagram username + password (не пустые)."""

    def __init__(self, username: str, password: str) -> None:
        if not username or not username.strip():
            raise ValueError("Instagram username не может быть пустым")
        if not password or not password.strip():
            raise ValueError("Instagram password не может быть пустым")
        self.username = username.strip()
        self.password = password.strip()


class VideoPath:
    """Value object: путь к видеофайлу (должен существовать и быть видео)."""

    def __init__(self, path: str | Path) -> None:
        self._path = Path(path)
        if not self._path.exists():
            raise FileNotFoundError(f"Видеофайл не найден: {self._path}")
        if not self._path.is_file():
            raise ValueError(f"Путь не является файлом: {self._path}")
        ext = self._path.suffix.lower()
        if ext not in VIDEO_EXTENSIONS:
            raise ValueError(
                f"Файл не является видео (ожидаются расширения {sorted(VIDEO_EXTENSIONS)}): {self._path}"
            )

    @property
    def path(self) -> Path:
        return self._path

    def __fspath__(self) -> str:
        return str(self._path)


class PhotoPath:
    """Value object: путь к фото (должен существовать и быть изображением)."""

    def __init__(self, path: str | Path) -> None:
        self._path = Path(path)
        if not self._path.exists():
            raise FileNotFoundError(f"Фото не найдено: {self._path}")
        if not self._path.is_file():
            raise ValueError(f"Путь не является файлом: {self._path}")
        ext = self._path.suffix.lower()
        if ext not in PHOTO_EXTENSIONS:
            raise ValueError(
                f"Файл не является фото (ожидаются расширения {sorted(PHOTO_EXTENSIONS)}): {self._path}"
            )

    @property
    def path(self) -> Path:
        return self._path

    def __fspath__(self) -> str:
        return str(self._path)


class PostDescription:
    """Value object: описание публикации в Instagram."""

    def __init__(self, description: str = "") -> None:
        self._description = description if description else ""

    @property
    def text(self) -> str:
        return self._description

    def __str__(self) -> str:
        return self._description
