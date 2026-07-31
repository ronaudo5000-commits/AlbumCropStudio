from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog,
    QLabel,
    QPushButton,
    QVBoxLayout,
)


class SettingsDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)

        self.setWindowTitle(
            self.tr("設定")
        )

        self.setMinimumWidth(420)
        self.setMinimumHeight(220)

        layout = QVBoxLayout(self)

        title_label = QLabel(
            self.tr("AlbumCrop Studio 設定")
        )

        title_label.setAlignment(
            Qt.AlignmentFlag.AlignCenter
        )

        placeholder_label = QLabel(
            self.tr(
                "設定項目は今後ここに追加されます。"
            )
        )

        placeholder_label.setAlignment(
            Qt.AlignmentFlag.AlignCenter
        )

        close_button = QPushButton(
            self.tr("閉じる")
        )

        close_button.clicked.connect(
            self.accept
        )

        layout.addWidget(title_label)
        layout.addStretch()
        layout.addWidget(placeholder_label)
        layout.addStretch()
        layout.addWidget(close_button)