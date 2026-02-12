# Сборка для разных платформ

## Текущая ситуация

PyInstaller собирает приложение **только для текущей платформы**:
- На **Linux** → собирается Linux версия
- На **Windows** → собирается Windows версия (.exe)

## Где находятся собранные файлы

### Linux
```
dist/instagram-reels-publisher
```
- Исполняемый файл для Linux
- Запуск: `./dist/instagram-reels-publisher`

### Windows
```
dist\instagram-reels-publisher.exe
```
- Исполняемый файл для Windows
- Запуск: `dist\instagram-reels-publisher.exe`

## Как собрать для другой платформы

### Вариант 1: Использовать нужную платформу (рекомендуется)

**Для Windows версии:**
- Используй Windows машину
- Запусти `build.bat`

**Для Linux версии:**
- Используй Linux машину
- Запусти `./build.sh`

### Вариант 2: Виртуальная машина

1. Установи виртуальную машину (VirtualBox, VMware, QEMU)
2. Установи нужную ОС (Windows или Linux)
3. Скопируй проект в виртуальную машину
4. Запусти соответствующий скрипт сборки

### Вариант 3: WSL (для Windows → Linux)

Если у тебя Windows и нужно собрать Linux версию:

```powershell
# В WSL
wsl
cd /mnt/c/path/to/browser-automation
./build.sh
```

### Вариант 4: Docker (продвинутый)

Можно создать Docker контейнер для сборки:

```dockerfile
FROM python:3.14-slim
WORKDIR /app
COPY . .
RUN pip install uv && uv sync
RUN uv run pyinstaller build.spec --clean --noconfirm
```

## Проверка платформы

После сборки можно проверить:

```bash
# Linux
file dist/instagram-reels-publisher
# Должно показать: ELF 64-bit LSB executable

# Windows
# Файл должен иметь расширение .exe
```

## Рекомендации

1. **Для продакшена**: Собирай на целевой платформе
2. **Для тестирования**: Используй виртуальную машину
3. **Для разработки**: Используй `uv run python -m browser_automation.main`
