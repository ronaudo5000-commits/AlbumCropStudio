from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog,
    QLabel,
    QPushButton,
    QVBoxLayout,
)

from app.version import (
    APP_NAME,
    APP_VERSION,
    COPYRIGHT_TEXT,
)


class AboutDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)

        self.setWindowTitle(
            f"About {APP_NAME}"
        )

        self.setMinimumWidth(420)

        layout = QVBoxLayout(self)

        title = QLabel(
            f"<h2>{APP_NAME}</h2>"
        )

        title.setAlignment(
            Qt.AlignmentFlag.AlignCenter
        )

        tagline = QLabel(
            self.tr(
                "「資料」を「資源」に そして「資産」へ"
            )
        )

        tagline.setAlignment(
            Qt.AlignmentFlag.AlignCenter
        )

        tagline.setWordWrap(True)

        version = QLabel(
            f"Version {APP_VERSION}"
        )

        version.setAlignment(
            Qt.AlignmentFlag.AlignCenter
        )

        copyright_label = QLabel(
            COPYRIGHT_TEXT
        )

        copyright_label.setAlignment(
            Qt.AlignmentFlag.AlignCenter
        )

        close_button = QPushButton(
            self.tr("閉じる")
        )

        close_button.clicked.connect(
            self.accept
        )

        layout.addWidget(title)
        layout.addWidget(tagline)
        layout.addSpacing(10)
        layout.addWidget(version)
        layout.addSpacing(10)
        layout.addWidget(copyright_label)
        layout.addStretch()
        layout.addWidget(close_button)