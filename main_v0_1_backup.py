import sys

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QApplication,
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

        central = QWidget()
        self.setCentralWidget(central)

        main_layout = QVBoxLayout(central)

        # ドラッグ&ドロップ領域
        self.drop_area = QLabel(
            "画像をここへドラッグ＆ドロップ\n\nまたは今後追加する『開く』ボタンを使用"
        )
        self.drop_area.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.drop_area.setMinimumHeight(400)
        self.drop_area.setStyleSheet(
            """
            QLabel {
                border: 2px dashed gray;
                font-size: 16px;
            }
            """
        )

        main_layout.addWidget(self.drop_area)

        # 設定
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

        # ボタン
        self.detect_button = QPushButton("写真を検出")
        self.detect_button.setMinimumHeight(40)

        main_layout.addWidget(self.detect_button)


app = QApplication(sys.argv)

window = MainWindow()
window.show()

sys.exit(app.exec())