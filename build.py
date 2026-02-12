#!/usr/bin/env python3
"""
Скрипт для сборки исполняемых файлов с помощью PyInstaller.
Поддерживает сборку для Windows (exe) и Linux.
"""

import os
import sys
import platform
import subprocess
import shutil
from pathlib import Path

def clean_build_dirs():
    """Очистка временных директорий сборки."""
    dirs_to_clean = ["build", "dist", "__pycache__"]
    for dir_name in dirs_to_clean:
        if os.path.exists(dir_name):
            print(f"🧹 Очистка {dir_name}/...")
            shutil.rmtree(dir_name)
    
    # Очистка pycache в src
    for pycache in Path("src").rglob("__pycache__"):
        print(f"🧹 Очистка {pycache}/...")
        shutil.rmtree(pycache)

def build_windows():
    """Сборка для Windows (exe)."""
    print("🪟 Сборка для Windows...")
    
    # Создаём spec файл для Windows
    spec_content = f'''# -*- mode: python ; coding: utf-8 -*-

import sys
from pathlib import Path

sys.setrecursionlimit(5000)

a = Analysis(
    ['src/browser_automation/main.py'],
    pathex=[],
    binaries=[],
    datas=[
        ('src/browser_automation/gui/*', 'gui/'),
        ('src/browser_automation/modules/*', 'modules/'),
        ('src/browser_automation/profiles/*', 'profiles/'),
    ],
    hiddenimports=[
        'PySide6',
        'PySide6.QtCore',
        'PySide6.QtGui',
        'PySide6.QtWidgets',
        'camoufox',
        'camoufox.async_api',
        'multiprocessing',
        'multiprocessing.context',
        'queue',
        'json',
        'asyncio',
        'traceback',
        'pathlib',
        'logging',
    ],
    hookspath=[],
    hooksconfig={{}},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)

# Исключаем ненужные модули для уменьшения размера
excludes = [
    'tkinter',
    'test',
    'unittest',
    'pydoc',
    'pdb',
    'distutils',
    'setuptools',
    'pip',
    'wheel',
    'email',
    'http',
    'xml',
    'xmlrpc',
    'html',
    'ssl',
    'cryptography',
    'OpenSSL',
    'nacl',
    'nacl.bindings',
    'nacl.exceptions',
    'nacl.hash',
    'nacl.hashlib',
    'nacl.public',
    'nacl.secret',
    'nacl.signing',
    'nacl.utils',
    'nacl._sodium',
    'nacl._ffi',
    'nacl._lib',
    'nacl._randombytes',
    'nacl._sodium_ffi',
    'nacl._sodium_init',
    'nacl._sodium_version',
    'nacl._version',
    'nacl.encoding',
    'nacl.exceptions',
    'nacl.hash',
    'nacl.hashlib',
    'nacl.public',
    'nacl.secret',
    'nacl.signing',
    'nacl.utils',
]

for exclude in excludes:
    if exclude in a.binaries:
        a.binaries.remove(exclude)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='browser-automation',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,  # Запуск без консоли (GUI приложение)
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='icon.ico' if Path('icon.ico').exists() else None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='browser-automation',
)
'''
    
    spec_file = "browser-automation.spec"
    with open(spec_file, "w", encoding="utf-8") as f:
        f.write(spec_content)
    
    # Запускаем PyInstaller
    cmd = [
        sys.executable, "-m", "PyInstaller",
        "--clean",
        "--noconfirm",
        spec_file
    ]
    
    print(f"🚀 Запуск: {' '.join(cmd)}")
    result = subprocess.run(cmd, capture_output=True, text=True)
    
    if result.returncode == 0:
        print("✅ Сборка для Windows завершена успешно!")
        print(f"📁 Исполняемый файл: dist/browser-automation/browser-automation.exe")
    else:
        print("❌ Ошибка сборки для Windows:")
        print(result.stderr)
        return False
    
    return True

def build_linux():
    """Сборка для Linux."""
    print("🐧 Сборка для Linux...")
    
    # Создаём spec файл для Linux
    spec_content = f'''# -*- mode: python ; coding: utf-8 -*-

import sys
from pathlib import Path

sys.setrecursionlimit(5000)

a = Analysis(
    ['src/browser_automation/main.py'],
    pathex=[],
    binaries=[],
    datas=[
        ('src/browser_automation/gui/*', 'gui/'),
        ('src/browser_automation/modules/*', 'modules/'),
        ('src/browser_automation/profiles/*', 'profiles/'),
    ],
    hiddenimports=[
        'PySide6',
        'PySide6.QtCore',
        'PySide6.QtGui',
        'PySide6.QtWidgets',
        'camoufox',
        'camoufox.async_api',
        'multiprocessing',
        'multiprocessing.context',
        'queue',
        'json',
        'asyncio',
        'traceback',
        'pathlib',
        'logging',
    ],
    hookspath=[],
    hooksconfig={{}},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)

# Исключаем ненужные модули для уменьшения размера
excludes = [
    'tkinter',
    'test',
    'unittest',
    'pydoc',
    'pdb',
    'distutils',
    'setuptools',
    'pip',
    'wheel',
    'email',
    'http',
    'xml',
    'xmlrpc',
    'html',
    'ssl',
    'cryptography',
    'OpenSSL',
    'nacl',
    'nacl.bindings',
    'nacl.exceptions',
    'nacl.hash',
    'nacl.hashlib',
    'nacl.public',
    'nacl.secret',
    'nacl.signing',
    'nacl.utils',
    'nacl._sodium',
    'nacl._ffi',
    'nacl._lib',
    'nacl._randombytes',
    'nacl._sodium_ffi',
    'nacl._sodium_init',
    'nacl._sodium_version',
    'nacl._version',
    'nacl.encoding',
    'nacl.exceptions',
    'nacl.hash',
    'nacl.hashlib',
    'nacl.public',
    'nacl.secret',
    'nacl.signing',
    'nacl.utils',
]

for exclude in excludes:
    if exclude in a.binaries:
        a.binaries.remove(exclude)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='browser-automation',
    debug=False,
    bootloader_ignore_signals=False,
    strip=True,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,  # Запуск без консоли (GUI приложение)
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=True,
    upx=True,
    upx_exclude=[],
    name='browser-automation',
)
'''
    
    spec_file = "browser-automation-linux.spec"
    with open(spec_file, "w", encoding="utf-8") as f:
        f.write(spec_content)
    
    # Запускаем PyInstaller
    cmd = [
        sys.executable, "-m", "PyInstaller",
        "--clean",
        "--noconfirm",
        spec_file
    ]
    
    print(f"🚀 Запуск: {' '.join(cmd)}")
    result = subprocess.run(cmd, capture_output=True, text=True)
    
    if result.returncode == 0:
        print("✅ Сборка для Linux завершена успешно!")
        print(f"📁 Исполняемый файл: dist/browser-automation/browser-automation")
    else:
        print("❌ Ошибка сборки для Linux:")
        print(result.stderr)
        return False
    
    return True

def create_launcher_scripts():
    """Создание скриптов-запускалок для разных платформ."""
    
    # Windows batch файл
    windows_launcher = '''@echo off
chcp 65001 >nul
echo Запуск Instagram Reels Publisher...
echo.
dist\\browser-automation\\browser-automation.exe
pause
'''
    
    with open("run-windows.bat", "w", encoding="utf-8") as f:
        f.write(windows_launcher)
    
    # Linux bash скрипт
    linux_launcher = '''#!/bin/bash
echo "Запуск Instagram Reels Publisher..."
echo ""
cd "$(dirname "$0")"
chmod +x dist/browser-automation/browser-automation
./dist/browser-automation/browser-automation
'''
    
    with open("run-linux.sh", "w", encoding="utf-8") as f:
        f.write(linux_launcher)
    
    # Делаем Linux скрипт исполняемым
    os.chmod("run-linux.sh", 0o755)
    
    print("✅ Скрипты запуска созданы:")
    print("   - run-windows.bat (для Windows)")
    print("   - run-linux.sh (для Linux)")

def main():
    """Основная функция сборки."""
    print("🔨 Сборка Instagram Reels Publisher")
    print("=" * 50)
    
    # Определяем текущую платформу
    current_platform = platform.system()
    print(f"📱 Текущая платформа: {current_platform}")
    
    # Очистка перед сборкой
    clean_build_dirs()
    
    success = True
    
    # Сборка для текущей платформы
    if current_platform == "Windows":
        success = build_windows()
    elif current_platform == "Linux":
        success = build_linux()
    else:
        print(f"⚠️  Платформа {current_platform} не поддерживается")
        print("💡 Вы можете собрать вручную с помощью PyInstaller")
        success = False
    
    # Создание скриптов запуска
    if success:
        create_launcher_scripts()
        
        print("\n🎉 Сборка завершена!")
        print("\n📋 Инструкция по запуску:")
        print(f"   1. Для {current_platform}: запустите соответствующий скрипт")
        print("   2. Или перейдите в папку dist/browser-automation/")
        print("   3. Запустите исполняемый файл")
        
        print("\n⚠️  Важные замечания:")
        print("   - При первом запуске может потребоваться время для загрузки браузера")
        print("   - Убедитесь, что есть подключение к интернету")
        print("   - Для работы требуется установленный браузер Chrome/Chromium")
    
    return success

if __name__ == "__main__":
    try:
        sys.exit(0 if main() else 1)
    except KeyboardInterrupt:
        print("\n❌ Сборка прервана пользователем")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Неожиданная ошибка: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)