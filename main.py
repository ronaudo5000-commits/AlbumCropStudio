import sys

from PySide6.QtWidgets import QApplication

from app.main_window import MainWindow

import traceback

from app.logger import get_logger

def main():
    logger = get_logger()

    try:
        app = QApplication(sys.argv)

        window = MainWindow()
        window.show()

        sys.exit(app.exec())

    except Exception:
        logger.exception(
            "Unexpected application error"
        )

        print(traceback.format_exc())

        raise

if __name__ == "__main__":
    main()