# Инструкция по сборке приложения

## Требования

- Python 3.14+
- **uv** (менеджер пакетов) - установи: `curl -LsSf https://astral.sh/uv/install.sh | sh`
- Все зависимости из `pyproject.toml` (установятся автоматически через `uv sync`)

## Сборка для Linux

```bash
chmod +x build.sh
./build.sh
```

Исполняемый файл будет в `dist/instagram-reels-publisher`

## Сборка для Windows

```cmd
build.bat
```

Или вручную:

```cmd
uv sync
uv run pyinstaller build.spec --clean --noconfirm
```

Исполняемый файл будет в `dist/instagram-reels-publisher.exe`

## Ручная сборка

Если нужно настроить параметры:

```bash
# Linux
uv sync
uv run pyinstaller build.spec --clean

# Windows
uv sync
uv run pyinstaller build.spec --clean --noconfirm
```

## Важные замечания

1. **Браузеры Playwright/Camoufox**: При первом запуске приложения браузеры будут автоматически загружены. Это нормально.

2. **Размер сборки**: Из-за включения PySide6 и Playwright, размер может быть большим (100-200 МБ).

3. **Multiprocessing**: Используется `spawn` метод, который работает на всех платформах.

4. **Кеш сессий**: Папка `cache/` будет создана автоматически при первом запуске.

## Оптимизация размера (опционально)

Если нужно уменьшить размер:

```bash
# Использовать UPX для сжатия (если установлен)
pyinstaller build.spec --upx-dir=/path/to/upx
```

## Добавление иконки

1. Создай файл `icon.ico` (Windows) или `icon.png` (Linux)
2. В `build.spec` измени строку:
   ```python
   icon='icon.ico',  # или 'icon.png'
   ```
