from PySide6.QtCore import Qt
from PySide6.QtGui import QPainter, QPen, QColor, QPixmap, QFont
from PySide6.QtWidgets import QWidget


class PhotoCanvas(QWidget):
    def __init__(self):
        super().__init__()

        self.pixmap = None
        self.rects = []
        self.selected_rect = -1
        self.undo_stack = []
        

        self.dragging = False
        self.last_image_x = 0
        self.last_image_y = 0

        self.add_mode = False
        self.adding_rect = False
        self.add_start_x = 0
        self.add_start_y = 0

        self.resizing = False
        self.resize_handle_size = 10

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

    def save_undo_state(self):
        self.undo_stack.append(
            [tuple(rect) for rect in self.rects]
        )

        if len(self.undo_stack) > 30:
            self.undo_stack.pop(0)

    def undo(self):
        if not self.undo_stack:
            return

        self.rects = self.undo_stack.pop()
        self.selected_rect = -1
        self.dragging = False
        self.adding_rect = False
        self.resizing = False
        self.update()

    def set_add_mode(self, enabled):
        self.add_mode = enabled
        self.adding_rect = False
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

            painter.setFont(QFont("Arial", 14))

            painter.fillRect(
                int(x_offset + x * scale_x),
                int(y_offset + y * scale_y),
                28,
                24,
                QColor(255, 200, 0),
            )

            painter.setPen(QColor(0, 0, 0))

            painter.drawText(
                int(x_offset + x * scale_x),
                int(y_offset + y * scale_y),
                28,
                24,
                Qt.AlignmentFlag.AlignCenter,
                str(index + 1),
            )

            if index == self.selected_rect:
                handle_size = self.resize_handle_size
                handle_x = int(x_offset + (x + w) * scale_x) - handle_size // 2
                handle_y = int(y_offset + (y + h) * scale_y) - handle_size // 2

                painter.fillRect(
                    handle_x,
                    handle_y,
                    handle_size,
                    handle_size,
                    QColor(255, 200, 0),
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

        if self.selected_rect >= 0:
            x, y, w, h = self.rects[self.selected_rect]

            handle_area = self.resize_handle_size / scale_x

            if (
                x + w - handle_area <= image_x <= x + w + handle_area
                and y + h - handle_area <= image_y <= y + h + handle_area
            ):
                self.resizing = True
                self.dragging = False
                self.adding_rect = False
                self.last_image_x = image_x
                self.last_image_y = image_y
                return

        self.selected_rect = -1

        if self.add_mode:
            self.adding_rect = True
            self.add_start_x = image_x
            self.add_start_y = image_y

            self.rects.append(
                (
                    int(image_x),
                    int(image_y),
                    1,
                    1,
                )
            )

            self.selected_rect = len(self.rects) - 1
            self.update()
            return

        for index, (x, y, w, h) in enumerate(self.rects):
            if x <= image_x <= x + w and y <= image_y <= y + h:
                self.selected_rect = index
                self.dragging = True
                self.last_image_x = image_x
                self.last_image_y = image_y
                break

        self.update()

    def mouseMoveEvent(self, event):
        if self.resizing:
            info = self.image_display_info()
            if info is None:
                return

            _, x_offset, y_offset, scale_x, scale_y = info
            pos = event.position()

            image_x = (pos.x() - x_offset) / scale_x
            image_y = (pos.y() - y_offset) / scale_y

            x, y, w, h = self.rects[self.selected_rect]

            new_w = max(5, image_x - x)
            new_h = max(5, image_y - y)

            self.rects[self.selected_rect] = (
                x,
                y,
                int(new_w),
                int(new_h),
            )

            self.update()
            return

        if self.adding_rect:
            info = self.image_display_info()
            if info is None:
                return

            _, x_offset, y_offset, scale_x, scale_y = info
            pos = event.position()

            image_x = (pos.x() - x_offset) / scale_x
            image_y = (pos.y() - y_offset) / scale_y

            x = min(self.add_start_x, image_x)
            y = min(self.add_start_y, image_y)
            w = abs(image_x - self.add_start_x)
            h = abs(image_y - self.add_start_y)

            self.rects[self.selected_rect] = (
                int(x),
                int(y),
                int(w),
                int(h),
            )

            self.update()
            return

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
        self.adding_rect = False
        self.resizing = False     

    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_Delete:
            if self.selected_rect >= 0:
                self.save_undo_state()
                del self.rects[self.selected_rect]
                self.selected_rect = -1
                self.update()
            return

        if (
            event.key() == Qt.Key.Key_Z
            and event.modifiers() == Qt.KeyboardModifier.ControlModifier
        ):
            self.undo()
            return