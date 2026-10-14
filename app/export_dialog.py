from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QSpinBox,
    QVBoxLayout,
)

from app.config import Config


class ExportDialog(QDialog):
    def __init__(
        self,
        export_items,
        parent=None,
    ):
        super().__init__(parent)

        self.export_items = list(
            export_items
        )

        self.setWindowTitle(
            self.tr("書き出し設定")
        )

        self.setMinimumWidth(520)
        self.setMinimumHeight(480)

        main_layout = QVBoxLayout(self)

        title_label = QLabel(
            self.tr("書き出す切り抜きを選択")
        )

        title_label.setAlignment(
            Qt.AlignmentFlag.AlignCenter
        )

        description_label = QLabel(
            self.tr(
                "書き出したい切り抜きに"
                "チェックを入れてください。"
            )
        )

        description_label.setWordWrap(
            True
        )

        # ---------------------------------
        # 切り抜き一覧
        # ---------------------------------
        self.export_list = QListWidget()

        for export_index, export_item in enumerate(
            self.export_items
        ):
            list_item = QListWidgetItem(
                str(export_item)
            )

            list_item.setFlags(
                list_item.flags()
                | Qt.ItemFlag.ItemIsUserCheckable
            )

            list_item.setCheckState(
                Qt.CheckState.Checked
            )

            list_item.setData(
                Qt.ItemDataRole.UserRole,
                export_index,
            )

            self.export_list.addItem(
                list_item
            )

        # ---------------------------------
        # 全選択／全解除
        # ---------------------------------
        selection_button_layout = QHBoxLayout()

        self.select_all_button = QPushButton(
            self.tr("すべて選択")
        )

        self.clear_all_button = QPushButton(
            self.tr("すべて解除")
        )

        self.select_all_button.clicked.connect(
            self.select_all_items
        )

        self.clear_all_button.clicked.connect(
            self.clear_all_items
        )

        selection_button_layout.addWidget(
            self.select_all_button
        )

        selection_button_layout.addWidget(
            self.clear_all_button
        )

        selection_button_layout.addStretch()

        # ---------------------------------
        # 出力設定
        # ---------------------------------
        output_settings_layout = QFormLayout()

        self.dpi_spin = QSpinBox()
        self.dpi_spin.setRange(
            200,
            1200,
        )

        self.dpi_spin.setSuffix(
            self.tr(" dpi")
        )

        self.dpi_spin.setValue(
            Config.get_dpi()
        )

        output_settings_layout.addRow(
            self.tr("解像度"),
            self.dpi_spin,
        )

        self.jpeg_quality_spin = QSpinBox()
        self.jpeg_quality_spin.setRange(
            1,
            100,
        )

        self.jpeg_quality_spin.setSuffix(
            self.tr(" %")
        )

        self.jpeg_quality_spin.setValue(
            Config.get_jpeg_quality()
        )

        output_settings_layout.addRow(
            self.tr("JPEG品質"),
            self.jpeg_quality_spin,
        )

        self.margin_mm_spin = QSpinBox()
        self.margin_mm_spin.setRange(
            0,
            20,
        )

        self.margin_mm_spin.setSuffix(
            self.tr(" mm")
        )

        self.margin_mm_spin.setValue(
            Config.get_margin_mm()
        )

        output_settings_layout.addRow(
            self.tr("余白"),
            self.margin_mm_spin,
        )

        # ---------------------------------
        # 書き出し／キャンセル
        # ---------------------------------
        self.button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok
            | QDialogButtonBox.StandardButton.Cancel
        )

        export_button = self.button_box.button(
            QDialogButtonBox.StandardButton.Ok
        )

        cancel_button = self.button_box.button(
            QDialogButtonBox.StandardButton.Cancel
        )

        export_button.setText(
            self.tr("書き出し")
        )

        cancel_button.setText(
            self.tr("キャンセル")
        )

        self.button_box.accepted.connect(
            self.accept
        )

        self.button_box.rejected.connect(
            self.reject
        )

        main_layout.addWidget(
            title_label
        )

        main_layout.addSpacing(
            8
        )

        main_layout.addWidget(
            description_label
        )

        main_layout.addSpacing(
            8
        )

        main_layout.addWidget(
            self.export_list,
            1,
        )

        main_layout.addLayout(
            selection_button_layout
        )

        main_layout.addSpacing(
            12
        )

        main_layout.addLayout(
            output_settings_layout
        )

        main_layout.addSpacing(
            8
        )

        main_layout.addWidget(
            self.button_box
        )

    def select_all_items(self):
        for row in range(
            self.export_list.count()
        ):
            list_item = self.export_list.item(
                row
            )

            list_item.setCheckState(
                Qt.CheckState.Checked
            )

    def clear_all_items(self):
        for row in range(
            self.export_list.count()
        ):
            list_item = self.export_list.item(
                row
            )

            list_item.setCheckState(
                Qt.CheckState.Unchecked
            )

    def selected_export_indexes(self):
        selected_indexes = []

        for row in range(
            self.export_list.count()
        ):
            list_item = self.export_list.item(
                row
            )

            if (
                list_item.checkState()
                == Qt.CheckState.Checked
            ):
                export_index = list_item.data(
                    Qt.ItemDataRole.UserRole
                )

                selected_indexes.append(
                    int(export_index)
                )

        return selected_indexes

    def selected_dpi(self):
        return self.dpi_spin.value()

    def selected_jpeg_quality(self):
        return self.jpeg_quality_spin.value()

    def selected_margin_mm(self):
        return self.margin_mm_spin.value()