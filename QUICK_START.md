# Быстрый старт

## Установка uv (если ещё не установлен)

```bash
# Linux/macOS
curl -LsSf https://astral.sh/uv/install.sh | sh

# Windows (PowerShell)
powershell -c "irm https://astral.sh/uv/install.ps1 | iex"
```

## Сборка для Linux

```bash
# 1. Запусти сборку (uv sync выполнится автоматически)
./build.sh

# 2. Запусти приложение
./dist/instagram-reels-publisher
```

## Сборка для Windows

```cmd
REM 1. Запусти сборку (uv sync выполнится автоматически)
build.bat

REM 2. Запусти приложение
dist\instagram-reels-publisher.exe
```

## Ручная сборка (если скрипты не работают)

```bash
# Linux/Windows
uv sync
uv run pyinstaller build.spec --clean --noconfirm
```

## Решение проблем

### Ошибка "multiprocessing"

Если видишь ошибки связанные с multiprocessing, убедись что используешь Python 3.14+ и что `multiprocessing.freeze_support()` вызывается в `main.py` (уже добавлено).

### Браузеры не загружаются

При первом запуске Camoufox/Playwright автоматически загрузят браузеры. Это может занять несколько минут. Просто подожди.

### Большой размер файла

Это нормально - PySide6 и Playwright добавляют ~100-200 МБ. Можно использовать UPX для сжатия (см. BUILD.md).
