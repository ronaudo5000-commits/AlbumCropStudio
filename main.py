import sys
import traceback
import ctypes

from pathlib import Path

from PySide6.QtCore import (
    Qt,
    QTimer,
)

from PySide6.QtGui import (
    QIcon,
    QPixmap,
)

from PySide6.QtWidgets import (
    QApplication,
    QSplashScreen,
)

from app.main_window import MainWindow
from app.logger import get_logger


def main():
    logger = get_logger()

    try:
        # ---------------------------------
        # Windows上でACSを独立したアプリとして識別
        # ---------------------------------
        if sys.platform == "win32":
            app_user_model_id = (
                "AlbumCropStudio."
                "AlbumCropStudio"
            )

            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(
                app_user_model_id
            )

        app = QApplication(sys.argv)

        # ---------------------------------
        # リソース
        # ---------------------------------
        project_root = Path(
            __file__
        ).resolve().parent

        resources_dir = (
            project_root
            / "resources"
        )

        icon_path = (
            resources_dir
            / "app_icon.png"
        )

        splash_path = (
            resources_dir
            / "splash.png"
        )

        # ---------------------------------
        # アプリアイコン
        # ---------------------------------
        if icon_path.exists():
            app_icon = QIcon(
                str(icon_path)
            )

            app.setWindowIcon(
                app_icon
            )
        else:
            app_icon = QIcon()

        # ---------------------------------
        # 起動スプラッシュ
        # ---------------------------------
        splash = None

        if splash_path.exists():
            splash_pixmap = QPixmap(
                str(splash_path)
            )

            if not splash_pixmap.isNull():
                splash_pixmap = (
                    splash_pixmap.scaled(
                        900,
                        506,
                        Qt.AspectRatioMode.KeepAspectRatio,
                        Qt.TransformationMode.SmoothTransformation,
                    )
                )

                splash = QSplashScreen(
                    splash_pixmap
                )

                splash.show()

                app.processEvents()

        # ---------------------------------
        # メインウィンドウ
        # ---------------------------------
        window = MainWindow()

        if not app_icon.isNull():
            window.setWindowIcon(
                app_icon
            )

        if splash is not None:

            def show_main_window():
                window.show()
                splash.finish(
                    window
                )

            QTimer.singleShot(
                2000,
                show_main_window,
            )

        else:
            window.show()

        sys.exit(
            app.exec()
        )

    except Exception:
        logger.exception(
            "Unexpected application error"
        )

        print(
            traceback.format_exc()
        )

        raise


if __name__ == "__main__":
    main()