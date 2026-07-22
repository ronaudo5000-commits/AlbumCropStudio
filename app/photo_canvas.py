from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QPainter, QPen, QColor, QPixmap, QFont
from PySide6.QtWidgets import QWidget


class PhotoCanvas(QWidget):
    zoom_changed = Signal(float)
    rects_changed = Signal()

    def __init__(self):
        super().__init__()

        self.pixmap = None
        self.rects = []
        self.selected_rect = -1
        self.undo_stack = []
        self.zoom_factor = 1.0
        
        self.pan_x = 0.0
        self.pan_y = 0.0

        self.panning = False
        self.last_pan_pos = None

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

        self.zoom_factor = 1.0
        self.pan_x = 0.0
        self.pan_y = 0.0

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

        self.rects_changed.emit()

        self.update()

    def set_add_mode(self, enabled):
        self.add_mode = enabled
        self.adding_rect = False
        self.selected_rect = -1
        self.update()

    def image_display_info(self):
        if self.pixmap is None:
            return None

        base_size = self.size()

        scaled_pixmap = self.pixmap.scaled(
            int(base_size.width() * self.zoom_factor),
            int(base_size.height() * self.zoom_factor),
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )

        x_offset = (
            (self.width() - scaled_pixmap.width()) / 2
            + self.pan_x
        )

        y_offset = (
            (self.height() - scaled_pixmap.height()) / 2
            + self.pan_y
        )

        scale_x = scaled_pixmap.width() / self.pixmap.width()
        scale_y = scaled_pixmap.height() / self.pixmap.height()

        return scaled_pixmap, x_offset, y_offset, scale_x, scale_y

    def resize_handles(self, x, y, w, h):
        return {
            "top_left": (x, y),
            "top": (x + w / 2, y),
            "top_right": (x + w, y),
            "right": (x + w, y + h / 2),
            "bottom_right": (x + w, y + h),
            "bottom": (x + w / 2, y + h),
            "bottom_left": (x, y + h),
            "left": (x, y + h / 2),
        }

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

                for hx, hy in self.resize_handles(x, y, w, h).values():
                    handle_x = int(x_offset + hx * scale_x) - handle_size // 2
                    handle_y = int(y_offset + hy * scale_y) - handle_size // 2

                    painter.fillRect(
                        handle_x,
                        handle_y,
                        handle_size,
                        handle_size,
                        QColor(255, 200, 0),
                    )

                delete_button_size = 28

                delete_x = int(
                    x_offset + (x + w) * scale_x
                ) - delete_button_size

                delete_y = int(
                    y_offset + y * scale_y
                ) - delete_button_size - 4

                painter.fillRect(
                    delete_x,
                    delete_y,
                    delete_button_size,
                    delete_button_size,
                    QColor(220, 60, 60),
                )

                painter.setPen(QColor(255, 255, 255))

                painter.drawText(
                    delete_x,
                    delete_y,
                    delete_button_size,
                    delete_button_size,
                    Qt.AlignmentFlag.AlignCenter,
                    "×",
                )

                copy_button_size = 28

                copy_x = delete_x - copy_button_size - 4
                copy_y = delete_y

                painter.fillRect(
                    copy_x,
                    copy_y,
                    copy_button_size,
                    copy_button_size,
                    QColor(70, 120, 220),
                )

                painter.setPen(QColor(255, 255, 255))

                painter.drawText(
                    copy_x,
                    copy_y,
                    copy_button_size,
                    copy_button_size,
                    Qt.AlignmentFlag.AlignCenter,
                    "⧉",
                )

    def mousePressEvent(self, event):

        # 中ボタンでパン開始
        if event.button() == Qt.MouseButton.MiddleButton:
            self.panning = True
            self.last_pan_pos = event.position()
            event.accept()
            return

        if self.pixmap is None:
            return

        info = self.image_display_info()
        if info is None:
            return

        _, x_offset, y_offset, scale_x, scale_y = info

        pos = event.position()

        image_x = (pos.x() - x_offset) / scale_x
        image_y = (pos.y() - y_offset) / scale_y

        # 選択中の枠に表示している
        # コピー／削除ボタンをクリックしたか確認
        if self.selected_rect >= 0:
            x, y, w, h = self.rects[self.selected_rect]

            button_size = 28

            delete_x = int(
                x_offset + (x + w) * scale_x
            ) - button_size

            delete_y = int(
                y_offset + y * scale_y
            ) - button_size - 4

            copy_x = delete_x - button_size - 4
            copy_y = delete_y

            # コピーボタン
            if (
                copy_x <= pos.x() <= copy_x + button_size
                and copy_y <= pos.y() <= copy_y + button_size
            ):
                self.save_undo_state()

                offset = 30

                copied_rect = (
                    x + offset,
                    y + offset,
                    w,
                    h,
                )

                self.rects.append(copied_rect)

                # コピーした新しい枠を選択状態にする
                self.selected_rect = len(self.rects) - 1

                self.dragging = False
                self.adding_rect = False
                self.resizing = False

                self.rects_changed.emit()
                self.update()
                return

            # 削除ボタン
            if (
                delete_x <= pos.x() <= delete_x + button_size
                and delete_y <= pos.y() <= delete_y + button_size
            ):
                self.save_undo_state()

                del self.rects[self.selected_rect]

                self.selected_rect = -1
                self.dragging = False
                self.adding_rect = False
                self.resizing = False

                self.rects_changed.emit()
                self.update()
                return

        # 画像の表示範囲外をクリックした場合は何もしない
        if (
            image_x < 0
            or image_y < 0
            or image_x > self.pixmap.width()
            or image_y > self.pixmap.height()
        ):
            return

        # 選択中の枠のリサイズハンドルを最優先で判定
        if self.selected_rect >= 0:
            x, y, w, h = self.rects[self.selected_rect]

            handle_area = self.resize_handle_size / scale_x

            for handle_name, (hx, hy) in self.resize_handles(
                x, y, w, h
            ).items():
                if (
                    hx - handle_area <= image_x <= hx + handle_area
                    and hy - handle_area <= image_y <= hy + handle_area
                ):
                    self.save_undo_state()

                    self.resizing = True
                    self.resize_handle = handle_name
                    self.dragging = False
                    self.adding_rect = False

                    self.last_image_x = image_x
                    self.last_image_y = image_y
                    return

        # 既存の枠の中をクリックしたか確認
        # 後から作った枠を優先する
        for index in range(len(self.rects) - 1, -1, -1):
            x, y, w, h = self.rects[index]

            if (
                x <= image_x <= x + w
                and y <= image_y <= y + h
            ):
                self.selected_rect = index

                self.save_undo_state()

                self.dragging = True
                self.adding_rect = False
                self.resizing = False

                self.last_image_x = image_x
                self.last_image_y = image_y

                self.update()
                return

        # 既存枠の外なら、新しい枠を作成
        self.save_undo_state()

        self.adding_rect = True
        self.dragging = False
        self.resizing = False

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

    def mouseMoveEvent(self, event):
        if self.panning:
            if self.last_pan_pos is None:
                return

            current_pos = event.position()

            dx = current_pos.x() - self.last_pan_pos.x()
            dy = current_pos.y() - self.last_pan_pos.y()

            self.pan_x += dx
            self.pan_y += dy

            self.last_pan_pos = current_pos

            self.update()
            return
        if self.resizing:
            info = self.image_display_info()
            if info is None:
                return

            _, x_offset, y_offset, scale_x, scale_y = info
            pos = event.position()

            image_x = (pos.x() - x_offset) / scale_x
            image_y = (pos.y() - y_offset) / scale_y

            x, y, w, h = self.rects[self.selected_rect]

            left = x
            top = y
            right = x + w
            bottom = y + h

            if self.resize_handle in ("top_left", "left", "bottom_left"):
                left = image_x

            if self.resize_handle in ("top_left", "top", "top_right"):
                top = image_y

            if self.resize_handle in ("top_right", "right", "bottom_right"):
                right = image_x

            if self.resize_handle in ("bottom_left", "bottom", "bottom_right"):
                bottom = image_y

            if right - left < 5:
                return

            if bottom - top < 5:
                return

            self.rects[self.selected_rect] = (
                int(left),
                int(top),
                int(right - left),
                int(bottom - top),
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
        # 中ボタンでパン終了
        if event.button() == Qt.MouseButton.MiddleButton:
            self.panning = False
            self.last_pan_pos = None
            event.accept()
            return

        was_editing_rect = (
            self.dragging
            or self.adding_rect
            or self.resizing
        )

        self.dragging = False
        self.adding_rect = False
        self.resizing = False
        self.resize_handle = None

        if was_editing_rect:
            self.rects_changed.emit()

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

    def zoom_in(self):
        self.zoom_factor *= 1.1
        self.zoom_factor = min(
            self.zoom_factor,
            5.0,
        )

        self.zoom_changed.emit(
            self.zoom_factor
        )

        self.update()


    def zoom_out(self):
        self.zoom_factor /= 1.1
        self.zoom_factor = max(
            self.zoom_factor,
            0.2,
        )

        self.zoom_changed.emit(
            self.zoom_factor
        )

        self.update()


    def reset_zoom(self):
        self.zoom_factor = 1.0

        self.zoom_changed.emit(
            self.zoom_factor
        )

        self.update()



    def wheelEvent(self, event):
        if self.pixmap is None:
            return

        modifiers = event.modifiers()

        # ホイール単体でも Ctrl + ホイールでもズーム
        if (
            modifiers == Qt.KeyboardModifier.NoModifier
            or modifiers & Qt.KeyboardModifier.ControlModifier
        ):
            delta = event.angleDelta().y()

            if delta > 0:
                self.zoom_factor *= 1.1
            else:
                self.zoom_factor /= 1.1

            self.zoom_factor = max(
                0.2,
                min(self.zoom_factor, 5.0)
            )

            self.zoom_changed.emit(
                self.zoom_factor
            )

            self.update()
            event.accept()
            return

        super().wheelEvent(event)