from pathlib import Path

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


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("AlbumCrop Studio")
        self.resize(1000, 700)
        self.setAcceptDrops(True)

        self.current_image_path = None
        self.current_pixmap = None
        self.detected_rects = []

        central = QWidget()
        self.setCentralWidget(central)

        main_layout = QVBoxLayout(central)

        self.preview_area = QLabel(
            "画像をここへドラッグ＆ドロップ\n\nまたは『画像を開く』ボタンを使用"
        )
        self.preview_area.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.preview_area.setMinimumHeight(400)
        self.preview_area.setStyleSheet(
            """
            QLabel {
                border: 2px dashed gray;
                font-size: 16px;
            }
            """
        )

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

        button_layout.addWidget(self.open_button)
        button_layout.addWidget(self.detect_button)

        main_layout.addLayout(button_layout)

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

        scaled_pixmap = self.current_pixmap.scaled(
            self.preview_area.size(),
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )

        display_pixmap = QPixmap(scaled_pixmap)

        if self.detected_rects:
            painter = QPainter(display_pixmap)
            pen = QPen(QColor(255, 0, 0))
            pen.setWidth(3)
            painter.setPen(pen)

            original_w = self.current_pixmap.width()
            original_h = self.current_pixmap.height()
            displayed_w = scaled_pixmap.width()
            displayed_h = scaled_pixmap.height()

            scale_x = displayed_w / original_w
            scale_y = displayed_h / original_h

            for x, y, w, h in self.detected_rects:
                painter.drawRect(
                    QRect(
                        int(x * scale_x),
                        int(y * scale_y),
                        int(w * scale_x),
                        int(h * scale_y),
                    )
                )

            painter.end()

        self.preview_area.setPixmap(display_pixmap)

    def detect_photos(self):
        if not self.current_image_path:
            self.preview_area.setText("先に画像を読み込んでください。")
            return

        self.detected_rects = detect_photos(self.current_image_path)
        self.show_image()

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