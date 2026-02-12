import logging
import sys
import multiprocessing

# Важно для PyInstaller и multiprocessing
if sys.platform.startswith('win'):
    multiprocessing.freeze_support()

from .gui_modern import main

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)

if __name__ == "__main__":
    # Для PyInstaller на Windows
    if sys.platform.startswith('win'):
        multiprocessing.freeze_support()
    main()
