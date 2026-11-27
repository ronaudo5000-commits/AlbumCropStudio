
from pathlib import Path

from PySide6.QtCore import Qt, QSize
from PySide6.QtGui import QImageReader, QPixmap
from PySide6.QtWidgets import (
    QWidget,
    QGridLayout,
    QVBoxLayout,
    QLabel,
    QFrame,
    QSizePolicy,
)


class FitImageLabel(QLabel):
    """表示領域に合わせて画像全体を縮小・拡大する。"""

    def __init__(self, parent=None):
        super().__init__(parent)

        self.source_pixmap = None

        self.setAlignment(
            Qt.AlignmentFlag.AlignCenter
        )

        self.setMinimumSize(0, 0)

        self.setSizePolicy(
            QSizePolicy.Policy.Ignored,
            QSizePolicy.Policy.Ignored,
        )

    def set_source_pixmap(self, pixmap):
        self.source_pixmap = pixmap
        self.update_scaled_pixmap()

    def update_scaled_pixmap(self):
        if (
            self.source_pixmap is None
            or self.source_pixmap.isNull()
        ):
            return

        available_size = self.contentsRect().size()

        if (
            available_size.width() <= 0
            or available_size.height() <= 0
        ):
            return

        scaled_pixmap = self.source_pixmap.scaled(
            available_size,
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )

        self.setPixmap(scaled_pixmap)

    def resizeEvent(self, event):
        super().resizeEvent(event)

        self.update_scaled_pixmap()


class MultiPageOverview(QWidget):
    """最大5ページを2列で表示する読み取り専用ビュー。"""

    def __init__(self, parent=None):
        super().__init__(parent)

        self.grid = QGridLayout(self)

        self.grid.setSpacing(12)

        self.grid.setContentsMargins(
            12, 12, 12, 12
        )

        # 中央エリアの幅を狭くできるようにする
        self.setMinimumSize(0, 0)

        self.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Preferred,
        )

        # 2列を同じ比率で伸縮させる
        self.grid.setColumnStretch(0, 1)
        self.grid.setColumnStretch(1, 1)

    def set_pages(self, image_paths):
        # 既存の表示内容を破棄する
        while self.grid.count():
            item = self.grid.takeAt(0)
            widget = item.widget()

            if widget is not None:
                widget.deleteLater()

        # 最大5枚まで表示
        for index, image_path in enumerate(
            list(image_paths)[:5]
        ):
            card = QFrame(self)

            card.setFrameShape(
                QFrame.Shape.StyledPanel
            )

            # 縦方向は高さを確保してスクロール
            card.setMinimumHeight(350)
            card.setMinimumWidth(0)

            layout = QVBoxLayout(card)

            image_label = FitImageLabel()

            reader = QImageReader(
                str(image_path)
            )

            reader.setAutoTransform(True)

            source_size = reader.size()

            if source_size.isValid():
                scaled_size = source_size.scaled(
                    QSize(900, 650),
                    Qt.AspectRatioMode.KeepAspectRatio,
                )

                reader.setScaledSize(scaled_size)

            image = reader.read()

            if not image.isNull():
                pixmap = QPixmap.fromImage(image)

                image_label.set_source_pixmap(
                    pixmap
                )
            else:
                image_label.setText(
                    "画像を表示できません"
                )

            title = QLabel(
                f"{index + 1:02d}  "
                f"{Path(image_path).name}"
            )

            title.setAlignment(
                Qt.AlignmentFlag.AlignCenter
            )

            title.setWordWrap(True)
            title.setMinimumWidth(0)

            layout.addWidget(
                image_label,
                1,
            )

            layout.addWidget(title)

            # 標準は2列表示
            row = index // 2
            column = index % 2

            self.grid.addWidget(
                card,
                row,
                column,
            )
