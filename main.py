import sys
import traceback
import ctypes

from pathlib import Path

from PySide6.QtCore import (
    Qt,
    QCoreApplication,
    QElapsedTimer,
    QTimer,
    QTranslator,
)

from PySide6.QtGui import (
    QIcon,
    QPixmap,
)

from PySide6.QtWidgets import (
    QApplication,
    QLabel,
    QSplashScreen,
)

from app.main_window import MainWindow
from app.logger import get_logger
from app.config import Config


def load_app_translator(
    app,
    project_root,
    language,
):
    if language == "ja":
        return None

    translations_dir = (
        project_root
        / "translations"
    )

    qm_path = (
        translations_dir
        / f"albumcrop_{language}.qm"
    )

    if not qm_path.exists():
        return None

    translator = QTranslator(
        app
    )

    if not translator.load(
        str(qm_path)
    ):
        return None

    app.installTranslator(
        translator
    )

    return translator


def get_splash_path(
    resources_dir,
    language,
):
    if language == "ja":
        return (
            resources_dir
            / "splash.png"
        )

    localized_splash_path = (
        resources_dir
        / f"splash_{language}.png"
    )

    if localized_splash_path.exists():
        return localized_splash_path

    return (
        resources_dir
        / "splash.png"
    )


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
        # プロジェクトルート
        # ---------------------------------
        project_root = Path(
            __file__
        ).resolve().parent

        # ---------------------------------
        # 言語
        #
        # 日本語を基準言語とする。
        # 設定に保存された言語を読み込み、
        # 対応する .qm がある場合のみ
        # QTranslatorで読み込む。
        # ---------------------------------
        app_language = (
            Config.get_language()
        )

        app_translator = (
            load_app_translator(
                app,
                project_root,
                app_language,
            )
        )

        # QTranslatorをmain()終了まで保持する
        _ = app_translator

        # ---------------------------------
        # リソース
        # ---------------------------------
        resources_dir = (
            project_root
            / "resources"
        )

        icon_path = (
            resources_dir
            / "app_icon.png"
        )

        splash_path = (
            get_splash_path(
                resources_dir,
                app_language,
            )
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
        splash_message_label = None
        splash_timer = QElapsedTimer()

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

                splash_message_label = QLabel(
                    splash
                )

                splash_message_label.setText(
                    QCoreApplication.translate(
                        "Main",
                        "設定を読み込んでいます…",
                    )
                )

                splash_message_label.setAlignment(
                    Qt.AlignmentFlag.AlignCenter
                )

                splash_message_label.setStyleSheet(
                    """
                    QLabel {
                        color: white;
                        background: transparent;
                        font-size: 15px;
                    }
                    """
                )

                splash_message_label.setGeometry(
                    0,
                    int(
                        splash_pixmap.height()
                        * 0.68
                    ),
                    splash_pixmap.width(),
                    36,
                )

                splash_message_label.show()

                splash_timer.start()

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
            minimum_splash_time = 3000

            elapsed_time = (
                splash_timer.elapsed()
            )

            def show_splash_message(
                message,
            ):
                if (
                    splash_message_label
                    is not None
                ):
                    splash_message_label.setText(
                        message
                    )

            def show_main_window():
                window.show()

                splash.finish(
                    window
                )

            QTimer.singleShot(
                max(
                    0,
                    750 - elapsed_time,
                ),
                lambda: show_splash_message(
                    QCoreApplication.translate(
                        "Main",
                        "画面を準備しています…",
                    )
                ),
            )

            QTimer.singleShot(
                max(
                    0,
                    1500 - elapsed_time,
                ),
                lambda: show_splash_message(
                    QCoreApplication.translate(
                        "Main",
                        "コンポーネントを初期化しています…",
                    )
                ),
            )

            QTimer.singleShot(
                max(
                    0,
                    2250 - elapsed_time,
                ),
                lambda: show_splash_message(
                    QCoreApplication.translate(
                        "Main",
                        "起動を完了しています…",
                    )
                ),
            )

            QTimer.singleShot(
                max(
                    0,
                    minimum_splash_time
                    - elapsed_time,
                ),
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