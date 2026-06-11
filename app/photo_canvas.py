from PySide6.QtCore import Qt
from PySide6.QtGui import QPainter, QPen, QColor, QPixmap
from PySide6.QtWidgets import QWidget


class PhotoCanvas(QWidget):
    def __init__(self):
        super().__init__()

        self.pixmap = None
        self.rects = []
        self.selected_rect = -1

        self.dragging = False
        self.last_image_x = 0
        self.last_image_y = 0

        self.setMinimumHeight(400)
        self.setMouseTracking(True)

        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)

    def set_image(self, pixmap):
        self.pixmap = pixmap
        self.rects = []
        self.selected_rect = -1
        self.update()

    def set_rects(self, rects):
        self.rects = rects
        self.selected_rect = -1
        self.update()

    def image_display_info(self):
        if self.pixmap is None:
            return None

        scaled_pixmap = self.pixmap.scaled(
            self.size(),
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )

        x_offset = (self.width() - scaled_pixmap.width()) / 2
        y_offset = (self.height() - scaled_pixmap.height()) / 2

        scale_x = scaled_pixmap.width() / self.pixmap.width()
        scale_y = scaled_pixmap.height() / self.pixmap.height()

        return scaled_pixmap, x_offset, y_offset, scale_x, scale_y

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.fillRect(self.rect(), QColor(245, 245, 245))

        if self.pixmap is None:
            painter.setPen(QColor(80, 80, 80))
            painter.drawText(
                self.rect(),
                Qt.AlignmentFlag.AlignCenter,
                "画像をここへドラッグ＆ドロップ\n\nまたは『画像を開く』ボタンを使用",
            )
            return

        info = self.image_display_info()
        if info is None:
            return

        scaled_pixmap, x_offset, y_offset, scale_x, scale_y = info

        painter.drawPixmap(
            int(x_offset),
            int(y_offset),
            scaled_pixmap,
        )

        for index, (x, y, w, h) in enumerate(self.rects):
            if index == self.selected_rect:
                pen = QPen(QColor(255, 200, 0))
            else:
                pen = QPen(QColor(255, 0, 0))

            pen.setWidth(3)
            painter.setPen(pen)

            painter.drawRect(
                int(x_offset + x * scale_x),
                int(y_offset + y * scale_y),
                int(w * scale_x),
                int(h * scale_y),
            )

    def mousePressEvent(self, event):
        if self.pixmap is None:
            return

        info = self.image_display_info()
        if info is None:
            return

        _, x_offset, y_offset, scale_x, scale_y = info

        pos = event.position()

        image_x = (pos.x() - x_offset) / scale_x
        image_y = (pos.y() - y_offset) / scale_y

        self.selected_rect = -1

        for index, (x, y, w, h) in enumerate(self.rects):
            if x <= image_x <= x + w and y <= image_y <= y + h:
                self.selected_rect = index
                self.dragging = True
                self.last_image_x = image_x
                self.last_image_y = image_y
                break

        self.update()

    def mouseMoveEvent(self, event):
        if not self.dragging:
            return

        if self.selected_rect < 0:
            return

        info = self.image_display_info()
        if info is None:
            return

        _, x_offset, y_offset, scale_x, scale_y = info

        pos = event.position()

        image_x = (pos.x() - x_offset) / scale_x
        image_y = (pos.y() - y_offset) / scale_y

        dx = image_x - self.last_image_x
        dy = image_y - self.last_image_y

        x, y, w, h = self.rects[self.selected_rect]

        self.rects[self.selected_rect] = (
            int(x + dx),
            int(y + dy),
            w,
            h,
        )

        self.last_image_x = image_x
        self.last_image_y = image_y

        self.update()

    def mouseReleaseEvent(self, event):
        self.dragging = False       

    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_Delete:
            if self.selected_rect >= 0:
                del self.rects[self.selected_rect]
                self.selected_rect = -1
                self.update()