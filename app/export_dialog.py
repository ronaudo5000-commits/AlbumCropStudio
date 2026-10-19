from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QButtonGroup,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPushButton,
    QRadioButton,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from app.config import Config


class ExportDialog(QDialog):
    def __init__(
        self,
        export_items,
        initial_output_directory="",
        parent=None,
    ):
        super().__init__(parent)

        self.export_items = list(
            export_items
        )

        self.initial_output_directory = str(
            initial_output_directory
        )

        self.individual_settings = {}

        self.loading_individual_settings = False

        self.setWindowTitle(
            self.tr("書き出し設定")
        )

        self.setMinimumWidth(520)
        self.setMinimumHeight(620)

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

        self.selection_summary_label = QLabel()

        self.selection_summary_label.setAlignment(
            Qt.AlignmentFlag.AlignRight
        )

        # ---------------------------------
        # 切り抜き一覧
        # ---------------------------------
        self.export_list = QListWidget()

        self.export_list.setStyleSheet("""
            QListWidget::item {
                padding: 6px;
                margin: 1px;
                border: 1px solid transparent;
                border-radius: 4px;
            }

            QListWidget::item:selected {
                background-color: #263f5f;
                border: 1px solid #2f80ed;
                color: #ffffff;
            }
        """)

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

        self.export_list.itemChanged.connect(
            self.update_selection_summary
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

        self.output_dir_edit = QLineEdit()

        self.output_dir_edit.setPlaceholderText(
            self.tr("保存先フォルダを選択")
        )

        self.output_dir_edit.setText(
            self.initial_output_directory
        )

        self.output_dir_button = QPushButton(
            self.tr("参照...")
        )

        self.output_dir_button.clicked.connect(
            self.choose_output_directory
        )

        output_dir_layout = QHBoxLayout()

        output_dir_layout.addWidget(
            self.output_dir_edit,
            1,
        )

        output_dir_layout.addWidget(
            self.output_dir_button
        )

        output_settings_layout.addRow(
            self.tr("保存先"),
            output_dir_layout,
        )

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
        # 書き出しジョブ要約
        # ---------------------------------
        self.job_summary_label = QLabel()

        self.job_summary_label.setWordWrap(
            True
        )

        self.job_summary_label.setTextInteractionFlags(
            Qt.TextInteractionFlag.TextSelectableByMouse
        )

        self.job_summary_label.setStyleSheet("""
            QLabel {
                padding: 10px;
                background-color: #252525;
                border: 1px solid #444444;
                border-radius: 5px;
                color: #dddddd;
            }
        """)

        # ---------------------------------
        # 個別設定
        # ---------------------------------
        self.selected_item_label = QLabel(
            self.tr("選択中: -")
        )

        self.common_settings_radio = QRadioButton(
            self.tr("共通設定を使用")
        )

        self.individual_settings_radio = (
            QRadioButton(
                self.tr(
                    "この切り抜きだけ"
                    "個別設定を使用"
                )
            )
        )

        self.settings_mode_group = QButtonGroup(
            self
        )

        self.settings_mode_group.addButton(
            self.common_settings_radio
        )

        self.settings_mode_group.addButton(
            self.individual_settings_radio
        )

        self.common_settings_radio.setChecked(
            True
        )

        self.individual_settings_container = (
            QWidget()
        )

        individual_settings_layout = (
            QFormLayout(
                self.individual_settings_container
            )
        )

        individual_settings_layout.setContentsMargins(
            18,
            0,
            0,
            0,
        )

        self.individual_dpi_spin = QSpinBox()
        self.individual_dpi_spin.setRange(
            200,
            1200,
        )

        self.individual_dpi_spin.setSuffix(
            self.tr(" dpi")
        )

        self.individual_dpi_spin.setValue(
            self.dpi_spin.value()
        )

        individual_settings_layout.addRow(
            self.tr("解像度"),
            self.individual_dpi_spin,
        )

        self.individual_jpeg_quality_spin = (
            QSpinBox()
        )

        self.individual_jpeg_quality_spin.setRange(
            1,
            100,
        )

        self.individual_jpeg_quality_spin.setSuffix(
            self.tr(" %")
        )

        self.individual_jpeg_quality_spin.setValue(
            self.jpeg_quality_spin.value()
        )

        individual_settings_layout.addRow(
            self.tr("JPEG品質"),
            self.individual_jpeg_quality_spin,
        )

        self.individual_margin_mm_spin = (
            QSpinBox()
        )

        self.individual_margin_mm_spin.setRange(
            0,
            20,
        )

        self.individual_margin_mm_spin.setSuffix(
            self.tr(" mm")
        )

        self.individual_margin_mm_spin.setValue(
            self.margin_mm_spin.value()
        )

        individual_settings_layout.addRow(
            self.tr("余白"),
            self.individual_margin_mm_spin,
        )

        self.individual_settings_container.setVisible(
            False
        )

        self.export_list.currentItemChanged.connect(
            self.on_export_item_changed
        )

        self.individual_settings_radio.toggled.connect(
            self.on_individual_settings_toggled
        )

        self.individual_dpi_spin.valueChanged.connect(
            self.save_current_individual_settings
        )

        self.individual_jpeg_quality_spin.valueChanged.connect(
            self.save_current_individual_settings
        )

        self.individual_margin_mm_spin.valueChanged.connect(
            self.save_current_individual_settings
        )

        self.output_dir_edit.textChanged.connect(
            self.update_job_summary
        )

        self.dpi_spin.valueChanged.connect(
            self.update_job_summary
        )

        self.jpeg_quality_spin.valueChanged.connect(
            self.update_job_summary
        )

        self.margin_mm_spin.valueChanged.connect(
            self.update_job_summary
        )

        if self.export_list.count() > 0:
            self.export_list.setCurrentRow(
                0
            )

        self.update_selection_summary()

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
            self.validate_and_accept
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

        main_layout.addWidget(
            self.selection_summary_label
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
            12
        )

        main_layout.addWidget(
            self.job_summary_label
        )

        main_layout.addSpacing(
            12
        )

        main_layout.addWidget(
            self.selected_item_label
        )

        main_layout.addWidget(
            self.common_settings_radio
        )

        main_layout.addWidget(
            self.individual_settings_radio
        )

        main_layout.addWidget(
            self.individual_settings_container
        )

        main_layout.addSpacing(
            8
        )

        main_layout.addWidget(
            self.button_box
        )

    def update_job_summary(
        self,
        *args,
    ):
        selected_indexes = (
            self.selected_export_indexes()
        )

        selected_count = len(
            selected_indexes
        )

        total_count = (
            self.export_list.count()
        )

        output_directory = (
            self.selected_output_directory()
        )

        if not output_directory:
            output_directory = self.tr(
                "未選択"
            )

        selected_index_set = set(
            selected_indexes
        )

        individual_count = sum(
            1
            for export_index
            in self.individual_settings
            if export_index
            in selected_index_set
        )

        summary_text = self.tr(
            "今回の書き出し\n"
            "選択: {selected} / {total}\n"
            "保存先: {output_directory}\n"
            "共通設定: {dpi} dpi / "
            "JPEG {jpeg_quality}% / "
            "余白 {margin_mm} mm\n"
            "個別設定: {individual_count}件"
        ).format(
            selected=selected_count,
            total=total_count,
            output_directory=output_directory,
            dpi=self.dpi_spin.value(),
            jpeg_quality=(
                self.jpeg_quality_spin.value()
            ),
            margin_mm=(
                self.margin_mm_spin.value()
            ),
            individual_count=individual_count,
        )

        self.job_summary_label.setText(
            summary_text
        )

    def update_selection_summary(
        self,
        *args,
    ):
        selected_count = len(
            self.selected_export_indexes()
        )

        total_count = (
            self.export_list.count()
        )

        self.selection_summary_label.setText(
            self.tr(
                "選択中: {selected} / {total}"
            ).format(
                selected=selected_count,
                total=total_count,
            )
        )

        self.update_job_summary()

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

        self.update_selection_summary()

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

        self.update_selection_summary()

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

    def choose_output_directory(self):
        current_directory = (
            self.output_dir_edit.text().strip()
        )

        selected_directory = (
            QFileDialog.getExistingDirectory(
                self,
                self.tr(
                    "保存先フォルダを選択"
                ),
                current_directory,
            )
        )

        if not selected_directory:
            return

        self.output_dir_edit.setText(
            selected_directory
        )

    def selected_output_directory(self):
        return (
            self.output_dir_edit.text().strip()
        )

    def validate_and_accept(self):
        if not self.selected_output_directory():
            QMessageBox.warning(
                self,
                self.tr(
                    "保存先が選択されていません"
                ),
                self.tr(
                    "保存先フォルダを選択してから"
                    "書き出してください。"
                ),
            )

            self.output_dir_edit.setFocus()

            return

        self.save_current_individual_settings()

        self.accept()

    def current_export_index(self):
        current_item = (
            self.export_list.currentItem()
        )

        if current_item is None:
            return None

        export_index = current_item.data(
            Qt.ItemDataRole.UserRole
        )

        if export_index is None:
            return None

        return int(export_index)

    def save_current_individual_settings(
        self,
        *args,
    ):
        if self.loading_individual_settings:
            return

        export_index = (
            self.current_export_index()
        )

        if export_index is None:
            return

        if not self.individual_settings_radio.isChecked():
            self.individual_settings.pop(
                export_index,
                None,
            )

            self.update_job_summary()

            return

        self.individual_settings[
            export_index
        ] = {
            "dpi": (
                self.individual_dpi_spin.value()
            ),
            "jpeg_quality": (
                self.individual_jpeg_quality_spin.value()
            ),
            "margin_mm": (
                self.individual_margin_mm_spin.value()
            ),
        }

        self.update_job_summary()

    def load_individual_settings(
        self,
        export_index,
    ):
        self.loading_individual_settings = True

        settings = self.individual_settings.get(
            export_index
        )

        if settings is None:
            self.common_settings_radio.setChecked(
                True
            )

            self.individual_dpi_spin.setValue(
                self.dpi_spin.value()
            )

            self.individual_jpeg_quality_spin.setValue(
                self.jpeg_quality_spin.value()
            )

            self.individual_margin_mm_spin.setValue(
                self.margin_mm_spin.value()
            )

            self.individual_settings_container.setVisible(
                False
            )

        else:
            self.individual_settings_radio.setChecked(
                True
            )

            self.individual_dpi_spin.setValue(
                settings["dpi"]
            )

            self.individual_jpeg_quality_spin.setValue(
                settings["jpeg_quality"]
            )

            self.individual_margin_mm_spin.setValue(
                settings["margin_mm"]
            )

            self.individual_settings_container.setVisible(
                True
            )

        self.loading_individual_settings = False

    def on_export_item_changed(
        self,
        current_item,
        previous_item,
    ):
        if previous_item is not None:
            previous_export_index = (
                previous_item.data(
                    Qt.ItemDataRole.UserRole
                )
            )

            if previous_export_index is not None:
                previous_export_index = int(
                    previous_export_index
                )

        if current_item is None:
            return

        export_index = current_item.data(
            Qt.ItemDataRole.UserRole
        )

        if export_index is None:
            return

        self.selected_item_label.setText(
            self.tr(
                "選択中: {name}"
            ).format(
                name=current_item.text()
            )
        )

        self.load_individual_settings(
            int(export_index)
        )

    def on_individual_settings_toggled(
        self,
        enabled,
    ):
        if self.loading_individual_settings:
            return

        self.individual_settings_container.setVisible(
            enabled
        )

        if enabled:
            export_index = (
                self.current_export_index()
            )

            if (
                export_index is not None
                and export_index
                not in self.individual_settings
            ):
                self.individual_dpi_spin.setValue(
                    self.dpi_spin.value()
                )

                self.individual_jpeg_quality_spin.setValue(
                    self.jpeg_quality_spin.value()
                )

                self.individual_margin_mm_spin.setValue(
                    self.margin_mm_spin.value()
                )

        self.save_current_individual_settings()

    def selected_individual_settings(self):
        self.save_current_individual_settings()

        return {
            export_index: dict(settings)
            for export_index, settings
            in self.individual_settings.items()
        }