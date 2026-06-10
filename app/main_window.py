from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap
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


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("AlbumCrop Studio")
        self.resize(1000, 700)

        self.current_image_path = None
        self.current_pixmap = None

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

        if not file_path:
            return

        pixmap = QPixmap(file_path)

        if pixmap.isNull():
            self.preview_area.setText("画像を読み込めませんでした。")
            return

        self.current_image_path = file_path
        self.current_pixmap = pixmap
        self.show_image()

    def show_image(self):
        if self.current_pixmap is None:
            return

        scaled_pixmap = self.current_pixmap.scaled(
            self.preview_area.size(),
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )

        self.preview_area.setPixmap(scaled_pixmap)

    def resizeEvent(self, event):
        super().resizeEvent(event)

        if self.current_pixmap is not None:
            self.show_image()