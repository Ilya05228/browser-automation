#!/usr/bin/env python3
"""
Проверка зависимостей перед сборкой.
"""

import sys
import subprocess
import pkg_resources

REQUIRED_PACKAGES = [
    'camoufox',
    'PySide6',
    'pyinstaller',
]

def check_package(package_name):
    """Проверяет, установлен ли пакет."""
    try:
        dist = pkg_resources.get_distribution(package_name)
        print(f"✅ {package_name} ({dist.version})")
        return True
    except pkg_resources.DistributionNotFound:
        print(f"❌ {package_name} не установлен")
        return False

def main():
    print("🔍 Проверка зависимостей...")
    print("=" * 50)
    
    all_ok = True
    for package in REQUIRED_PACKAGES:
        if not check_package(package):
            all_ok = False
    
    print("\n" + "=" * 50)
    
    if all_ok:
        print("🎉 Все зависимости установлены!")
        print("\n💡 Для сборки выполните:")
        print("   python build.py")
    else:
        print("⚠️  Некоторые зависимости отсутствуют")
        print("\n💡 Установите недостающие зависимости:")
        print("   pip install -r requirements.txt")
        print("   или")
        print("   pip install camoufox[geoip] PySide6 pyinstaller")
    
    return 0 if all_ok else 1

if __name__ == "__main__":
    sys.exit(main())