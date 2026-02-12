# Сборка для Windows

## Быстрый старт

### Вариант 1: Автоматическая сборка (рекомендуется)

1. **Открой командную строку (CMD) или PowerShell** в папке проекта

2. **Запусти скрипт сборки:**
   ```cmd
   build.bat
   ```

3. **Готово!** Исполняемый файл будет в `dist\instagram-reels-publisher.exe`

### Вариант 2: Ручная сборка

Если скрипт не работает, выполни команды вручную:

```cmd
REM 1. Синхронизация зависимостей
uv sync

REM 2. Сборка
uv run pyinstaller build.spec --clean --noconfirm
```

## Требования

- **Windows 10/11**
- **Python 3.14+** (или через uv)
- **uv** - установи: https://github.com/astral-sh/uv
  - PowerShell: `powershell -c "irm https://astral.sh/uv/install.ps1 | iex"`
  - CMD: скачай установщик с GitHub

## Пошаговая инструкция

### Шаг 1: Установка uv (если ещё не установлен)

**PowerShell:**
```powershell
powershell -c "irm https://astral.sh/uv/install.ps1 | iex"
```

**Или скачай установщик:**
1. Перейди на https://github.com/astral-sh/uv/releases
2. Скачай `uv-x86_64-pc-windows-msvc.zip`
3. Распакуй и добавь в PATH

### Шаг 2: Клонирование/копирование проекта

```cmd
cd C:\path\to\browser-automation
```

### Шаг 3: Сборка

```cmd
build.bat
```

Или вручную:

```cmd
uv sync
uv run pyinstaller build.spec --clean --noconfirm
```

### Шаг 4: Запуск

```cmd
dist\instagram-reels-publisher.exe
```

## Решение проблем

### Ошибка "uv не найден"

1. Проверь, что uv установлен:
   ```cmd
   uv --version
   ```

2. Если не установлен, установи (см. Шаг 1)

3. Перезапусти командную строку после установки

### Ошибка "Python не найден"

Если используешь uv, Python не нужен отдельно - uv его установит автоматически.

### Ошибка импортов

Убедись, что все импорты абсолютные (уже исправлено в коде):
- `from browser_automation.gui_modern import main`
- НЕ `from .gui_modern import main`

### Большой размер файла

Это нормально - PySide6 и Playwright добавляют ~100-200 МБ.

### Антивирус блокирует

Некоторые антивирусы могут блокировать PyInstaller сборки. Добавь исключение для папки `dist`.

## Структура после сборки

```
browser-automation/
├── dist/
│   └── instagram-reels-publisher.exe  ← Запускай этот файл
├── build/                              ← Временные файлы (можно удалить)
└── ...
```

## Распространение

Для распространения приложения:
1. Скопируй `dist\instagram-reels-publisher.exe`
2. Можно создать ZIP архив
3. Пользователям не нужен Python - всё включено в .exe

## Примечания

- При первом запуске браузеры Playwright загрузятся автоматически
- Сессии сохраняются в `cache\sessions.json` (создастся автоматически)
- Для работы нужен интернет (для загрузки браузеров при первом запуске)
