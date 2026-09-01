from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QLabel,
    QMessageBox,
    QSpinBox,
    QVBoxLayout,
)

from app.config import Config


class SettingsDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)

        self.restart_requested = False

        self.setWindowTitle(
            self.tr("設定")
        )

        self.setMinimumWidth(420)
        self.setMinimumHeight(300)

        main_layout = QVBoxLayout(self)

        title_label = QLabel(
            self.tr("AlbumCrop Studio 設定")
        )

        title_label.setAlignment(
            Qt.AlignmentFlag.AlignCenter
        )

        form_layout = QFormLayout()

        # ---------------------------------
        # 初期DPI
        # ---------------------------------
        self.dpi_spin = QSpinBox()
        self.dpi_spin.setRange(200, 1200)
        self.dpi_spin.setSuffix(
            self.tr(" dpi")
        )

        self.dpi_spin.setValue(
            Config.get_dpi()
        )

        self.dpi_spin.setToolTip(
            self.tr(
                "新しい作業で使用する初期解像度を指定します"
            )
        )

        form_layout.addRow(
            self.tr("初期DPI"),
            self.dpi_spin,
        )

        # ---------------------------------
        # JPEG品質
        # ---------------------------------
        self.jpeg_quality_spin = QSpinBox()
        self.jpeg_quality_spin.setRange(1, 100)
        self.jpeg_quality_spin.setSuffix(
            self.tr(" %")
        )

        self.jpeg_quality_spin.setValue(
            Config.get_jpeg_quality()
        )

        self.jpeg_quality_spin.setToolTip(
            self.tr(
                "JPEG書き出し時の画質を指定します。"
                "数値を高くすると画質とファイル容量が増えます"
            )
        )

        form_layout.addRow(
            self.tr("JPEG品質"),
            self.jpeg_quality_spin,
        )

        # ---------------------------------
        # 余白
        # ---------------------------------
        self.margin_mm_spin = QSpinBox()
        self.margin_mm_spin.setRange(0, 20)
        self.margin_mm_spin.setSuffix(
            self.tr(" mm")
        )

        self.margin_mm_spin.setValue(
            Config.get_margin_mm()
        )

        self.margin_mm_spin.setToolTip(
            self.tr(
                "写真の切り抜き範囲へ追加する余白を"
                "ミリメートル単位で指定します。"
                "0の場合は余白を追加しません"
            )
        )

        form_layout.addRow(
            self.tr("余白"),
            self.margin_mm_spin,
        )

        # ---------------------------------
        # 言語
        # ---------------------------------
        self.language_combo = QComboBox()

        self.language_combo.addItem(
            "日本語",
            "ja",
        )

        self.language_combo.addItem(
            "English",
            "en",
        )

        current_language = (
            Config.get_language()
        )

        language_index = (
            self.language_combo.findData(
                current_language
            )
        )

        if language_index >= 0:
            self.language_combo.setCurrentIndex(
                language_index
            )

        self.language_combo.setToolTip(
            self.tr(
                "言語の変更は次回起動時に反映されます"
            )
        )

        form_layout.addRow(
            self.tr("言語"),
            self.language_combo,
        )

        # ---------------------------------
        # 保存／キャンセル
        # ---------------------------------
        self.button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save
            | QDialogButtonBox.StandardButton.Cancel
        )

        save_button = self.button_box.button(
            QDialogButtonBox.StandardButton.Save
        )

        cancel_button = self.button_box.button(
            QDialogButtonBox.StandardButton.Cancel
        )

        save_button.setText(
            self.tr("保存")
        )

        cancel_button.setText(
            self.tr("キャンセル")
        )

        self.button_box.accepted.connect(
            self.save_settings
        )

        self.button_box.rejected.connect(
            self.reject
        )

        main_layout.addWidget(title_label)
        main_layout.addSpacing(12)
        main_layout.addLayout(form_layout)
        main_layout.addStretch()
        main_layout.addWidget(self.button_box)

    def save_settings(self):
        previous_language = (
            Config.get_language()
        )

        selected_language = (
            self.language_combo.currentData()
        )

        Config.set_dpi(
            self.dpi_spin.value()
        )

        Config.set_jpeg_quality(
            self.jpeg_quality_spin.value()
        )

        Config.set_margin_mm(
            self.margin_mm_spin.value()
        )

        Config.set_language(
            selected_language
        )

        language_changed = (
            previous_language
            != selected_language
        )

        if language_changed:
            answer = QMessageBox.question(
                self,
                self.tr(
                    "言語の変更"
                ),
                self.tr(
                    "言語の変更を反映するには、"
                    "AlbumCrop Studioの再起動が必要です。"
                    "\n\n"
                    "今すぐ再起動しますか？"
                ),
                (
                    QMessageBox.StandardButton.Yes
                    | QMessageBox.StandardButton.No
                ),
                QMessageBox.StandardButton.Yes,
            )

            self.restart_requested = (
                answer
                == QMessageBox.StandardButton.Yes
            )

        self.accept()