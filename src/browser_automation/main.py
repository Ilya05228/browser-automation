import logging

from .gui_modern import main

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
if __name__ == "__main__":
    main()
