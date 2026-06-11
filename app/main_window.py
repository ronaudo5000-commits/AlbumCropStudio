from pathlib import Path
from PIL import Image

from PySide6.QtCore import Qt, QRect
from PySide6.QtGui import QPixmap, QPainter, QPen, QColor
from PySide6.QtWidgets import (
    QFileDialog,
    QLabel,
    QMainWindow,
    QPushButton,
    QSpinBox,
    QVBoxLayout,
    QHBoxLayout,
    QWidget,
    QGroupBox,
)

from core.photo_detector import detect_photos

from app.photo_canvas import PhotoCanvas


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("AlbumCrop Studio")
        self.resize(1000, 700)
        self.setAcceptDrops(True)

        self.current_image_path = None
        self.current_pixmap = None
        self.detected_rects = []

        self.selected_rect = -1

        self.dragging = False
        self.last_mouse_x = 0
        self.last_mouse_y = 0

        central = QWidget()
        self.setCentralWidget(central)

        main_layout = QVBoxLayout(central)

        self.preview_area = PhotoCanvas()
        main_layout.addWidget(self.preview_area)

        settings_box = QGroupBox("出力設定")
        settings_layout = QHBoxLayout()

        dpi_label = QLabel("DPI")
        self.dpi_spin = QSpinBox()
        self.dpi_spin.setRange(72, 1200)
        self.dpi_spin.setValue(350)

        margin_label = QLabel("余白(mm)")
        self.margin_spin = QSpinBox()
        self.margin_spin.setRange(0, 20)
        self.margin_spin.setValue(0)

        settings_layout.addWidget(dpi_label)
        settings_layout.addWidget(self.dpi_spin)
        settings_layout.addSpacing(20)
        settings_layout.addWidget(margin_label)
        settings_layout.addWidget(self.margin_spin)

        settings_box.setLayout(settings_layout)
        main_layout.addWidget(settings_box)

        button_layout = QHBoxLayout()

        self.open_button = QPushButton("画像を開く")
        self.open_button.setMinimumHeight(40)
        self.open_button.clicked.connect(self.open_image)

        self.detect_button = QPushButton("写真を検出")
        self.detect_button.setMinimumHeight(40)
        self.detect_button.clicked.connect(self.detect_photos)

        self.add_rect_button = QPushButton("枠追加")
        self.add_rect_button.setMinimumHeight(40)
        self.add_rect_button.setCheckable(True)
        self.add_rect_button.clicked.connect(self.toggle_add_mode)

        self.save_button = QPushButton("保存")
        self.save_button.setMinimumHeight(40)
        self.save_button.clicked.connect(self.save_crops)

        button_layout.addWidget(self.open_button)
        button_layout.addWidget(self.detect_button)
        button_layout.addWidget(self.add_rect_button)
        button_layout.addWidget(self.save_button)

        main_layout.addLayout(button_layout)

        self.status_label = QLabel("検出数: 0")
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        main_layout.addWidget(self.status_label)

    def open_image(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "画像を開く",
            "",
            "Image Files (*.jpg *.jpeg *.png *.tif *.tiff)",
        )

        if file_path:
            self.load_image(file_path)

    def load_image(self, file_path):
        path = Path(file_path)

        if path.suffix.lower() not in [".jpg", ".jpeg", ".png", ".tif", ".tiff"]:
            self.preview_area.setText("対応していないファイル形式です。")
            return

        pixmap = QPixmap(str(path))

        if pixmap.isNull():
            self.preview_area.setText("画像を読み込めませんでした。")
            return

        self.current_image_path = str(path)
        self.current_pixmap = pixmap
        self.detected_rects = []
        self.show_image()

    def show_image(self):
        if self.current_pixmap is None:
            return

        self.preview_area.set_image(self.current_pixmap)
        self.preview_area.set_rects(self.detected_rects)

    def detect_photos(self):
        if not self.current_image_path:
            self.preview_area.setText(
                "先に画像を読み込んでください。"
            )
            return

        self.detected_rects = detect_photos(
            self.current_image_path
        )

        self.status_label.setText(
            f"検出数: {len(self.detected_rects)}"
        )

        self.show_image()

    def toggle_add_mode(self):
        self.preview_area.set_add_mode(
            self.add_rect_button.isChecked()
        )

    def save_crops(self):
        if not self.current_image_path:
            print("画像が読み込まれていません")
            return

        if not self.preview_area.rects:
            print("保存する枠がありません")
            return

        output_dir = Path(self.current_image_path).parent / "cropped_photos"
        output_dir.mkdir(exist_ok=True)

        image = Image.open(self.current_image_path)

        for index, (x, y, w, h) in enumerate(self.preview_area.rects, start=1):
            crop = image.crop(
                (
                    int(x),
                    int(y),
                    int(x + w),
                    int(y + h),
                )
            )

            output_path = output_dir / f"photo_{index:03}.jpg"
            crop.save(output_path, "JPEG", quality=95, dpi=(350, 350))

        print(f"{len(self.preview_area.rects)}枚の写真を保存しました")
        print(f"保存先: {output_dir}")

    def mousePressEvent(self, event):
        if self.current_pixmap is None:
            return

        if not self.detected_rects:
            return

        pos = event.position()

        scaled_pixmap = self.current_pixmap.scaled(
            self.preview_area.size(),
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )

        label_w = self.preview_area.width()
        label_h = self.preview_area.height()
        displayed_w = scaled_pixmap.width()
        displayed_h = scaled_pixmap.height()

        offset_x = (label_w - displayed_w) / 2
        offset_y = (label_h - displayed_h) / 2

        image_x = pos.x() - offset_x
        image_y = pos.y() - offset_y

        if image_x < 0 or image_y < 0:
            return

        if image_x > displayed_w or image_y > displayed_h:
            return

        scale_x = self.current_pixmap.width() / displayed_w
        scale_y = self.current_pixmap.height() / displayed_h

        original_x = image_x * scale_x
        original_y = image_y * scale_y

        for index, (x, y, w, h) in enumerate(self.detected_rects):
            if (
                original_x >= x
                and original_x <= x + w
                and original_y >= y
                and original_y <= y + h
            ):
                self.selected_rect = index
                self.dragging = True
                self.last_mouse_x = original_x
                self.last_mouse_y = original_y

                print(f"選択: {index}")

                self.show_image()
                return

        self.selected_rect = -1
        self.show_image()

    def mouseMoveEvent(self, event):
        if not self.dragging:
            return

        if self.selected_rect < 0:
            return

        if self.current_pixmap is None:
            return

        pos = event.position()

        scaled_pixmap = self.current_pixmap.scaled(
            self.preview_area.size(),
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )

        displayed_w = scaled_pixmap.width()
        displayed_h = scaled_pixmap.height()

        scale_x = self.current_pixmap.width() / displayed_w
        scale_y = self.current_pixmap.height() / displayed_h

        current_x = pos.x() * scale_x
        current_y = pos.y() * scale_y

        dx = current_x - self.last_mouse_x
        dy = current_y - self.last_mouse_y

        x, y, w, h = self.detected_rects[self.selected_rect]

        self.detected_rects[self.selected_rect] = (
            int(x + dx),
            int(y + dy),
            w,
            h,
        )

        self.last_mouse_x = current_x
        self.last_mouse_y = current_y

        self.show_image()

    def mouseReleaseEvent(self, event):
        self.dragging = False

    def resizeEvent(self, event):
        super().resizeEvent(event)

        if self.current_pixmap is not None:
            self.show_image()

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            file_path = event.mimeData().urls()[0].toLocalFile()
            suffix = Path(file_path).suffix.lower()

            if suffix in [".jpg", ".jpeg", ".png", ".tif", ".tiff"]:
                event.acceptProposedAction()
                return

        event.ignore()

    def dropEvent(self, event):
        if event.mimeData().hasUrls():
            file_path = event.mimeData().urls()[0].toLocalFile()
            self.load_image(file_path)
            event.acceptProposedAction()