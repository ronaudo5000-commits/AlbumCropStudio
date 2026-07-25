from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import (
    QLabel,
    QVBoxLayout,
    QWidget,
)


class PageThumbnailWidget(QWidget):
    clicked = Signal()

    def __init__(
        self,
        pixmap,
        file_name,
        parent=None,
    ):
        super().__init__(parent)

        self.file_name = file_name

        self.setCursor(
            Qt.CursorShape.PointingHandCursor
        )

        self.setMinimumWidth(120)
        self.setMaximumWidth(140)

        layout = QVBoxLayout(self)

        layout.setContentsMargins(
            6,
            6,
            6,
            6,
        )

        layout.setSpacing(4)

        self.thumbnail_label = QLabel()
        self.thumbnail_label.setAlignment(
            Qt.AlignmentFlag.AlignCenter
        )

        self.thumbnail_label.setFixedSize(
            120,
            90,
        )

        if isinstance(pixmap, QPixmap):
            scaled_pixmap = pixmap.scaled(
                120,
                90,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )

            self.thumbnail_label.setPixmap(
                scaled_pixmap
            )

        self.file_name_label = QLabel(
            file_name
        )

        self.file_name_label.setAlignment(
            Qt.AlignmentFlag.AlignCenter
        )

        self.file_name_label.setWordWrap(False)

        self.file_name_label.setToolTip(
            file_name
        )

        layout.addWidget(
            self.thumbnail_label
        )

        layout.addWidget(
            self.file_name_label
        )

    def mousePressEvent(self, event):
        if (
            event.button()
            == Qt.MouseButton.LeftButton
        ):
            self.clicked.emit()

        super().mousePressEvent(event)