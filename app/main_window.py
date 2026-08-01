import json
from pathlib import Path
from io import BytesIO
from PIL import Image
import pymupdf
import traceback

from PySide6.QtCore import (
    Qt,
    QSize,
    QThread,
)

from PySide6.QtGui import (
    QAction,
    QPixmap,
    QPainter,
    QPen,
    QColor,
    QImage,
    QIcon,
    QKeySequence,
)

from PySide6.QtWidgets import (
    QApplication,
    QFileDialog,
    QLabel,
    QMainWindow,
    QPushButton,
    QSpinBox,
    QVBoxLayout,
    QHBoxLayout,
    QWidget,
    QGroupBox,
    QListWidget,
    QListWidgetItem,
    QListView,
    QAbstractItemView,
    QScrollArea,
    QMessageBox,
    QProgressBar,
    QComboBox,
)

from core.photo_detector import detect_photos

from app.photo_canvas import PhotoCanvas
from app.version import (
    APP_NAME,
    APP_VERSION,
)

from app.about_dialog import AboutDialog
from app.config import Config
from app.settings_dialog import SettingsDialog

from app.export_worker import CropExportWorker

class PageListWidget(QListWidget):
    def __init__(self, parent=None):
        super().__init__(parent)

        self.delete_button_size = 24
        self.delete_callback = None

    def paintEvent(self, event):
        super().paintEvent(event)

        current_row = self.currentRow()

        if current_row < 0:
            return

        item = self.item(current_row)

        if item is None:
            return

        item_rect = self.visualItemRect(item)

        painter = QPainter(self.viewport())

        size = self.delete_button_size

        delete_x = item_rect.right() - size - 6
        delete_y = item_rect.top() + 6

        painter.fillRect(
            delete_x,
            delete_y,
            size,
            size,
            QColor(220, 60, 60),
        )

        painter.setPen(
            QColor(255, 255, 255)
        )

        painter.drawText(
            delete_x,
            delete_y,
            size,
            size,
            Qt.AlignmentFlag.AlignCenter,
            "×",
        )

    def mousePressEvent(self, event):
        current_row = self.currentRow()

        if current_row >= 0:
            item = self.item(current_row)

            if item is not None:
                item_rect = self.visualItemRect(item)

                size = self.delete_button_size

                delete_x = item_rect.right() - size - 6
                delete_y = item_rect.top() + 6

                pos = event.position()

                if (
                    delete_x <= pos.x() <= delete_x + size
                    and delete_y <= pos.y() <= delete_y + size
                ):
                    if self.delete_callback is not None:
                        self.delete_callback()

                    return

        super().mousePressEvent(event)


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        self.export_thread = None
        self.export_worker = None

        self.export_running = False

        self.setWindowTitle(
            f"{APP_NAME} {APP_VERSION}"
        )
        self.resize(1000, 700)
        self.setAcceptDrops(True)

        self.current_image_path = None
        self.current_pixmap = None
        self.detected_rects = []

        self.current_project_path = None

        self.project_modified = False

        self.image_paths = []
        self.current_page_index = -1
        self.page_rects = {}
        self.page_angles = {}
        self.deleted_pages_stack = []

        self.pdf_temp_dir = (
            Path.home()
            / ".albumcrop_studio"
            / "pdf_pages"
        )

        self.pdf_temp_dir.mkdir(
            parents=True,
            exist_ok=True,
        )

        central = QWidget()
        self.setCentralWidget(central)

        main_layout = QVBoxLayout(central)

        content_layout = QHBoxLayout()

        self.page_list = PageListWidget()
        self.page_list.setStyleSheet("""
            QListWidget::item {
                padding: 4px;
                margin: 2px;
                border: 2px solid transparent;
            }

            QListWidget::item:selected {
                background-color: #cfe8ff;
                border: 3px solid #2f80ed;
                color: #111111;
            }
        """)
        self.page_list.setSelectionMode(
            QAbstractItemView.SelectionMode.ExtendedSelection
        )
        self.page_list.delete_callback = self.delete_current_page
        self.page_list.setMinimumWidth(145)
        self.page_list.setMaximumWidth(165)

        self.page_list.setViewMode(
            QListView.ViewMode.IconMode
        )

        self.page_list.setFlow(
            QListView.Flow.TopToBottom
        )

        self.page_list.setWrapping(False)

        self.page_list.setResizeMode(
            QListView.ResizeMode.Adjust
        )

        self.page_list.setMovement(
            QListView.Movement.Static
        )

        self.page_list.setIconSize(
            QSize(110, 82)
        )

        self.page_list.setGridSize(
            QSize(135, 120)
        )

        self.page_list.setTextElideMode(
            Qt.TextElideMode.ElideMiddle
        )
        self.page_list.currentRowChanged.connect(
            self.change_page_from_list
        )

        self.delete_page_button = QPushButton("🗑 ページを削除")
        self.delete_page_button.setMinimumHeight(36)
        self.delete_page_button.setEnabled(False)

        self.delete_page_button.clicked.connect(
            self.delete_current_page
        )

        page_list_layout = QVBoxLayout()
        page_list_layout.addWidget(self.page_list)
        page_list_layout.addWidget(self.delete_page_button)

        page_list_container = QWidget()
        page_list_container.setLayout(page_list_layout)

        self.preview_area = PhotoCanvas()

        self.preview_area.zoom_changed.connect(
            self.on_zoom_changed
        )

        self.preview_area.rects_changed.connect(
            self.update_crop_preview
        )

        self.preview_area.rects_changed.connect(
            self.mark_project_modified
        )

        self.zoom_out_button = QPushButton("−")
        self.zoom_out_button.setFixedWidth(40)

        self.zoom_label = QLabel("100%")
        self.zoom_label.setAlignment(
            Qt.AlignmentFlag.AlignCenter
        )
        self.zoom_label.setFixedWidth(60)

        self.zoom_in_button = QPushButton("+")
        self.zoom_in_button.setFixedWidth(40)

        self.fit_button = QPushButton("全体表示")
        self.fit_button.setMinimumWidth(80)

        self.zoom_out_button.clicked.connect(
            self.preview_area.zoom_out
        )
        self.zoom_out_button.clicked.connect(
            self.update_zoom_label
        )

        self.zoom_in_button.clicked.connect(
            self.preview_area.zoom_in
        )
        self.zoom_in_button.clicked.connect(
            self.update_zoom_label
        )

        self.fit_button.clicked.connect(
            self.preview_area.reset_zoom
        )
        self.fit_button.clicked.connect(
            self.update_zoom_label
        )

        zoom_layout = QHBoxLayout()

        zoom_layout.addWidget(self.zoom_out_button)
        zoom_layout.addWidget(self.zoom_label)
        zoom_layout.addWidget(self.zoom_in_button)
        zoom_layout.addWidget(self.fit_button)

        zoom_layout.addStretch() 

        # 切り抜き後プレビュー欄
        self.crop_preview_box = QGroupBox("切り抜きプレビュー")
        self.crop_preview_box.setMinimumWidth(180)
        self.crop_preview_box.setMaximumWidth(260)

        crop_preview_layout = QVBoxLayout()

        self.crop_preview_scroll = QScrollArea()
        self.crop_preview_scroll.setWidgetResizable(True)

        self.crop_preview_container = QWidget()
        self.crop_preview_list_layout = QVBoxLayout(
            self.crop_preview_container
        )

        self.crop_preview_label = QLabel(
            "切り抜き結果が\nここに表示されます"
        )
        self.crop_preview_label.setAlignment(
            Qt.AlignmentFlag.AlignCenter
        )

        self.crop_preview_list_layout.addWidget(
            self.crop_preview_label
        )

        self.crop_preview_list_layout.addStretch()

        self.crop_preview_scroll.setWidget(
            self.crop_preview_container
        )

        crop_preview_layout.addWidget(
            self.crop_preview_scroll
        )

        self.crop_preview_box.setLayout(
            crop_preview_layout
        )

        preview_layout = QVBoxLayout()
        preview_layout.addWidget(self.preview_area, 1)
        preview_layout.addLayout(zoom_layout)

        preview_container = QWidget()
        preview_container.setLayout(preview_layout)

        content_layout.addWidget(page_list_container)
        content_layout.addWidget(preview_container, 1)
        content_layout.addWidget(self.crop_preview_box)

        main_layout.addLayout(content_layout)

        settings_box = QGroupBox("出力設定")
        settings_layout = QHBoxLayout()

        dpi_label = QLabel("解像度")

        self.dpi_spin = QSpinBox()
        self.dpi_spin.setRange(200, 1200)
        self.dpi_spin.setSuffix(" dpi")

        self.dpi_spin.setValue(
            Config.get_dpi()
        )

        self.dpi_preset_combo = QComboBox()

        self.dpi_preset_combo.addItems([
            "プリセット",
            "200",
            "300",
            "350",
            "400",
            "600",
            "800",
            "1000",
            "1200",
        ])

        self.dpi_preset_combo.setFixedWidth(90)
        self.dpi_preset_combo.setCurrentIndex(0)

        self.dpi_preset_combo.currentTextChanged.connect(
            self.apply_dpi_preset
        )

        margin_label = QLabel("余白")
        self.margin_spin = QSpinBox()
        self.margin_spin.setRange(0, 20)
        self.margin_spin.setSuffix(" mm")

        self.margin_spin.setValue(
            Config.get_margin_mm()
        )

        self.margin_spin.valueChanged.connect(
            self.mark_project_modified
        )

        self.dpi_spin.valueChanged.connect(
            self.mark_project_modified
        )

        self.dpi_spin.valueChanged.connect(
            self.save_settings
        )

        self.margin_spin.valueChanged.connect(
            self.save_settings
        )

        self.dpi_spin.valueChanged.connect(
            self.update_dpi_preset
        )

        settings_layout.addWidget(dpi_label)
        settings_layout.addWidget(self.dpi_spin)
        settings_layout.addWidget(self.dpi_preset_combo)
        settings_layout.addSpacing(20)
        settings_layout.addWidget(margin_label)
        settings_layout.addWidget(self.margin_spin)

        settings_box.setLayout(settings_layout)
        main_layout.addWidget(settings_box)

        self.open_button = QPushButton("画像を開く")
        self.open_button.setMinimumHeight(40)
        self.open_button.clicked.connect(self.open_image)

        self.open_action = QAction(
            self.tr("画像を開く"),
            self,
        )

        self.open_action.setShortcut(
            QKeySequence.StandardKey.Open
        )

        self.open_action.triggered.connect(
            self.open_image
        )

        self.addAction(
            self.open_action
        )

        self.save_action = QAction(
            self.tr("作業を保存"),
            self,
        )

        self.save_action.setShortcut(
            QKeySequence.StandardKey.Save
        )

        self.save_action.triggered.connect(
            self.save_project_overwrite
        )

        self.addAction(
            self.save_action
        )

        self.save_as_action = QAction(
            self.tr("名前を付けて保存"),
            self,
        )

        self.save_as_action.setShortcut(
            QKeySequence("Ctrl+Shift+S")
        )

        self.save_as_action.triggered.connect(
            self.save_project
        )

        self.addAction(self.save_as_action)


        # ← この下へ追加
        self.load_project_action = QAction(
            self.tr("作業を開く"),
            self,
        )

        self.load_project_action.triggered.connect(
            self.load_project
        )

        self.addAction(self.load_project_action)

        self.settings_action = QAction(
            self.tr("設定..."),
            self,
        )

        self.settings_action.triggered.connect(
            self.show_settings_dialog
        )

        self.addAction(
            self.settings_action
        )

        self.exit_action = QAction(
            self.tr("終了"),
            self,
        )

        self.exit_action.setShortcut(
            QKeySequence.StandardKey.Quit
        )

        self.exit_action.triggered.connect(
            self.close
        )

        self.addAction(self.exit_action)  

        file_menu = self.menuBar().addMenu(
            self.tr("ファイル")
        )

        help_menu = self.menuBar().addMenu(
            self.tr("ヘルプ")
        )

        about_action = QAction(
            self.tr("About AlbumCrop Studio"),
            self,
        )

        about_action.triggered.connect(
            self.show_about_dialog
        )

        help_menu.addAction(
            about_action
        )

        file_menu.addAction(
            self.open_action
        )

        file_menu.addAction(
            self.load_project_action
        )

        file_menu.addSeparator()

        file_menu.addAction(
            self.save_action
        )

        file_menu.addAction(
            self.save_as_action
        )

        file_menu.addSeparator()

        file_menu.addAction(
            self.settings_action
        )

        file_menu.addSeparator()

        file_menu.addAction(
            self.exit_action
        )      

        self.prev_button = QPushButton("◀ 前へ")
        self.prev_button.setMinimumHeight(40)
        self.prev_button.clicked.connect(self.show_previous_page)

        self.page_label = QLabel("0 / 0")
        self.page_label.setAlignment(
            Qt.AlignmentFlag.AlignCenter
        )

        self.next_button = QPushButton("次へ ▶")
        self.next_button.setMinimumHeight(40)
        self.next_button.clicked.connect(self.show_next_page)

        self.detect_button = QPushButton("写真を検出")
        self.detect_button.setMinimumHeight(40)
        self.detect_button.clicked.connect(
            self.detect_photos
        )

        self.manual_count_label = QLabel("写真枚数")

        self.manual_count_spin = QSpinBox()
        self.manual_count_spin.setRange(1, 100)
        self.manual_count_spin.setValue(4)
        self.manual_count_spin.setMinimumHeight(40)

        self.generate_rects_button = QPushButton("枠を生成")
        self.generate_rects_button.setMinimumHeight(40)
        self.generate_rects_button.clicked.connect(
            self.generate_manual_rects
        )

        self.load_project_button = QPushButton(
            "作業を開く"
        )
        self.load_project_button.setMinimumHeight(40)
        self.load_project_button.clicked.connect(
            self.load_project
        )

        self.save_project_button = QPushButton(
            "作業を保存"
        )
        self.save_project_button.setMinimumHeight(40)
        self.save_project_button.clicked.connect(
            self.save_project_overwrite
        )

        self.save_project_as_button = QPushButton(
            "名前を付けて保存"
        )
        self.save_project_as_button.setMinimumHeight(40)
        self.save_project_as_button.clicked.connect(
            self.save_project
        )

        self.save_button = QPushButton("切り抜き")
        self.save_button.setMinimumHeight(40)
        self.save_button.clicked.connect(
            self.save_crops
        )

        self.open_button.setToolTip(
            self.tr(
                "画像またはPDFを開きます（Ctrl+O）"
            )
        )

        self.prev_button.setToolTip(
            self.tr(
                "前のページを表示します"
            )
        )

        self.next_button.setToolTip(
            self.tr(
                "次のページを表示します"
            )
        )

        self.detect_button.setToolTip(
            self.tr(
                "画像から写真を自動検出します"
            )
        )

        self.manual_count_spin.setToolTip(
            self.tr(
                "生成する写真枠の数を指定します"
            )
        )

        self.generate_rects_button.setToolTip(
            self.tr(
                "指定した枚数の枠を自動配置します"
            )
        )

        self.load_project_button.setToolTip(
            self.tr(
                "保存済みのプロジェクトを開きます"
            )
        )

        self.save_project_button.setToolTip(
            self.tr(
                "現在のプロジェクトへ上書き保存します（Ctrl+S）"
            )
        )

        self.save_project_as_button.setToolTip(
            self.tr(
                "名前を付けてプロジェクトを保存します（Ctrl+Shift+S）"
            )
        )

        self.save_button.setToolTip(
            self.tr(
                "切り抜いた画像を書き出します"
            )
        )

        self.zoom_out_button.setToolTip(
            self.tr(
                "表示を縮小します"
            )
        )

        self.zoom_in_button.setToolTip(
            self.tr(
                "表示を拡大します"
            )
        )

        self.fit_button.setToolTip(
            self.tr(
                "画像全体が見える表示へ戻します"
            )
        )

        self.delete_page_button.setToolTip(
            self.tr(
                "選択したページを削除します"
            )
        )

        self.dpi_preset_combo.setToolTip(
            self.tr(
                "よく使う解像度を一覧から選びます"
            )
        )

        self.dpi_spin.setToolTip(
            self.tr(
                "書き出す画像の解像度を指定します"
            )
        )

        self.margin_spin.setToolTip(
            self.tr(
                "切り抜く写真の周囲に追加する余白を指定します"
            )
        )

        # ファイル操作
        file_group = QGroupBox("ファイル")
        file_layout = QHBoxLayout()

        file_layout.addWidget(self.open_button)
        file_layout.addWidget(self.load_project_button)
        file_layout.addWidget(self.save_project_button)
        file_layout.addWidget(self.save_project_as_button)

        file_group.setLayout(file_layout)


        # 写真編集
        edit_group = QGroupBox("写真編集")
        edit_layout = QHBoxLayout()

        edit_layout.addWidget(self.detect_button)
        edit_layout.addWidget(self.manual_count_label)

        self.manual_count_spin.setFixedWidth(90)
        edit_layout.addWidget(self.manual_count_spin)

        edit_layout.addWidget(self.generate_rects_button)

        edit_group.setLayout(edit_layout)


        # ページ操作
        page_group = QGroupBox("ページ")
        page_layout = QHBoxLayout()

        page_layout.addWidget(self.prev_button)

        self.page_label.setMinimumWidth(70)
        page_layout.addWidget(self.page_label)

        page_layout.addWidget(self.next_button)

        page_group.setLayout(page_layout)


        # 出力
        export_group = QGroupBox("出力")
        export_layout = QHBoxLayout()

        export_layout.addWidget(self.save_button)

        export_group.setLayout(export_layout)


        # グループ全体
        controls_layout = QHBoxLayout()

        controls_layout.addWidget(file_group, 4)
        controls_layout.addWidget(edit_group, 3)
        controls_layout.addWidget(page_group, 2)
        controls_layout.addWidget(export_group, 1)

        main_layout.addLayout(controls_layout)

        self.status_label = QLabel("検出数: 0")
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setVisible(False)

        main_layout.addWidget(self.progress_bar)
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        main_layout.addWidget(self.status_label)

    def update_export_progress(self, value):
        self.progress_bar.setValue(value)
        QApplication.processEvents()

    def export_finished(self, saved_count):
        self.progress_bar.setValue(100)

        print(
            f"{saved_count}枚の写真を保存しました"
        )

        self.status_label.setText(
            f"✅ {saved_count}枚切り抜き完了"
        )

        # ---------------------------------
        # 現在ページの枠と回転角度を維持
        # ---------------------------------
        if (
            self.current_page_index >= 0
            and self.current_page_index
            < len(self.image_paths)
        ):
            saved_rects = self.page_rects.get(
                self.current_page_index,
                [],
            )

            saved_angles = self.page_angles.get(
                self.current_page_index,
                [],
            )

            self.preview_area.set_rects(
                list(saved_rects)
            )

            self.preview_area.rect_angles = list(
                saved_angles
            )

            while len(
                self.preview_area.rect_angles
            ) < len(
                self.preview_area.rects
            ):
                self.preview_area.rect_angles.append(
                    0.0
                )

            if len(
                self.preview_area.rect_angles
            ) > len(
                self.preview_area.rects
            ):
                self.preview_area.rect_angles = (
                    self.preview_area.rect_angles[
                        :len(self.preview_area.rects)
                    ]
                )

            self.detected_rects = list(
                saved_rects
            )

            self.preview_area.update()
            self.update_crop_preview()

        self.progress_bar.setVisible(False)
        self.save_button.setEnabled(True)
        self.export_running = False

    def export_failed(self, error_message):
        print(
            f"画像の書き出しに失敗しました: "
            f"{error_message}"
        )

        self.status_label.setText(
            "❌ 切り抜き保存に失敗しました"
        )

        self.progress_bar.setVisible(False)
        self.save_button.setEnabled(True)
        self.export_running = False

        QMessageBox.critical(
            self,
            "書き出しエラー",
            (
                "画像の書き出し中に"
                "エラーが発生しました。\n\n"
                f"{error_message}"
            ),
        )

    def export_thread_finished(self):
        self.export_worker = None
        self.export_thread = None

    def mark_project_modified(self, *args):
        self.project_modified = True

    def apply_dpi_preset(self, text):
        if text == "プリセット":
            return

        self.dpi_spin.setValue(int(text))

    def update_dpi_preset(self, value):
        text = str(value)

        index = self.dpi_preset_combo.findText(text)

        if index >= 0:
            self.dpi_preset_combo.setCurrentIndex(index)
        else:
            self.dpi_preset_combo.setCurrentIndex(0)

    def update_zoom_label(self):
        zoom_percent = int(
            round(self.preview_area.zoom_factor * 100)
        )

        self.zoom_label.setText(
            f"{zoom_percent}%"
        )

    def on_zoom_changed(self, zoom_factor):
        zoom_percent = int(
            round(zoom_factor * 100)
        )

        self.zoom_label.setText(
            f"{zoom_percent}%"
        )

    def clear_pdf_cache(self):
        if not self.pdf_temp_dir.exists():
            return

        for file in self.pdf_temp_dir.glob("*.png"):
            try:
                file.unlink()
            except Exception as e:
                print(
                    f"キャッシュ削除失敗: {e}"
                )

    def convert_pdf_to_images(
        self,
        pdf_path,
    ):
        converted_paths = []

        try:
            document = pymupdf.open(
                pdf_path
            )

            pdf_name = Path(
                pdf_path
            ).stem

            for page_index in range(
                document.page_count
            ):
                page = document.load_page(
                    page_index
                )

                pixmap = page.get_pixmap(
                    dpi=300,
                    colorspace=pymupdf.csRGB,
                    alpha=False,
                )

                output_path = (
                    self.pdf_temp_dir
                    / (
                        f"{pdf_name}_"
                        f"page_{page_index + 1:04}.png"
                    )
                )

                success = pixmap.save(str(output_path))

                print(f"保存先: {output_path}")
                print(f"保存成功: {success}")
                print(f"存在確認: {output_path.exists()}")

                converted_paths.append(
                    str(output_path)
                )

            document.close()

        except Exception as e:
            print(
                f"PDF変換エラー: {e}"
            )

            QMessageBox.critical(
                self,
                "PDF読み込みエラー",
                (
                    "PDFを画像へ変換できませんでした。\n\n"
                    f"{e}"
                ),
            )

            return []

        return converted_paths

    def open_image(self):
        file_paths, _ = QFileDialog.getOpenFileNames(
            self,
            "画像またはPDFを開く",
            "",
            (
                "対応ファイル "
                "(*.jpg *.jpeg *.png *.tif *.tiff *.pdf);;"
                "画像ファイル "
                "(*.jpg *.jpeg *.png *.tif *.tiff);;"
                "PDFファイル (*.pdf)"
            ),
        )

        if not file_paths:
            return

        image_file_paths = []

        for file_path in file_paths:
            suffix = Path(
                file_path
            ).suffix.lower()

            if suffix == ".pdf":
                self.status_label.setText(
                    "📄 PDFを画像へ変換中..."
                )

                QApplication.processEvents()

                converted_paths = (
                    self.convert_pdf_to_images(
                        file_path
                    )
                )

                image_file_paths.extend(
                    converted_paths
                )

            else:
                image_file_paths.append(
                    file_path
                )

        self.add_images(
            image_file_paths
        )

    def add_images(self, file_paths):
        if not file_paths:
            return

        if self.image_paths:
            self.save_current_page_rects()

        was_empty = len(self.image_paths) == 0

        new_file_paths = []

        for file_path in file_paths:
            if file_path not in self.image_paths:
                self.image_paths.append(file_path)
                new_file_paths.append(file_path)

        if was_empty and self.image_paths:
            self.current_page_index = 0

        # 新しく追加された画像だけサムネイルを作成
        for file_path in new_file_paths:
            item_name = Path(file_path).name

            thumbnail = QPixmap()

            try:
                with Image.open(file_path) as pil_image:
                    pil_image = pil_image.convert("RGB")

                    # Pillow側で先にサムネイルサイズへ縮小
                    pil_image.thumbnail(
                        (120, 90)
                    )

                    # メモリ上でPNGへ変換
                    buffer = BytesIO()

                    pil_image.save(
                        buffer,
                        format="PNG",
                    )

                    thumbnail.loadFromData(
                        buffer.getvalue(),
                        "PNG",
                    )

            except Exception as e:
                print(
                    f"サムネイルを作成できませんでした: "
                    f"{file_path} / {e}"
                )

            # サムネイル生成の成否に関係なく
            # ファイル項目自体は必ず追加する
            item = QListWidgetItem(
                QIcon(thumbnail),
                item_name,
            )

            self.page_list.addItem(item)

        if was_empty and self.image_paths:
            self.page_list.setCurrentRow(0)

            self.load_image(
                self.image_paths[self.current_page_index]
            )

        self.delete_page_button.setEnabled(
            len(self.image_paths) > 0
        )

        self.project_modified = True

        self.update_page_label()

    def dropEvent(self, event):
        if not event.mimeData().hasUrls():
            event.ignore()
            return

        image_file_paths = []

        for url in event.mimeData().urls():
            file_path = url.toLocalFile()

            if not file_path:
                continue

            suffix = Path(file_path).suffix.lower()

            if suffix == ".pdf":
                self.status_label.setText(
                    "📄 PDFを画像へ変換中..."
                )

                QApplication.processEvents()

                converted_paths = self.convert_pdf_to_images(
                    file_path
                )

                image_file_paths.extend(converted_paths)

            else:
                image_file_paths.append(file_path)

        if not image_file_paths:
            event.ignore()
            return

        self.add_images(image_file_paths)

        event.acceptProposedAction()

    def update_page_label(self):
        total = len(self.image_paths)

        if total == 0 or self.current_page_index < 0:
            self.page_label.setText("0 / 0")
            return

        self.page_label.setText(
            f"{self.current_page_index + 1} / {total}"
        )

    def save_current_page_rects(self):
        if self.current_page_index < 0:
            return

        self.page_rects[self.current_page_index] = list(
            self.preview_area.rects
        )

        self.page_angles[self.current_page_index] = list(
            self.preview_area.rect_angles
        )

    def build_project_data(self):
        self.save_current_page_rects()

        pages = []

        for page_index, image_path in enumerate(
            self.image_paths
        ):
            rects = self.page_rects.get(
                page_index,
                [],
            )

            angles = self.page_angles.get(
                page_index,
                [],
            )

            pages.append(
                {
                    "image_path": image_path,
                    "rects": [
                        list(rect)
                        for rect in rects
                    ],
                    "angles": list(angles),
                }
            )

        project_data = {
            "version": 1,
            "current_page_index": self.current_page_index,
            "pages": pages,
            "settings": {
                "dpi": self.dpi_spin.value(),
                "margin_mm": self.margin_spin.value(),
            },
        }

        return project_data
    
    def save_project(self):
        project_data = self.build_project_data()

        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "作業を保存",
            "",
            "AlbumCrop Studio Project (*.acsp.json)",
        )

        if not file_path:
            return

        if not file_path.lower().endswith(
            ".acsp.json"
        ):
            file_path += ".acsp.json"

        project_path = Path(file_path)

        if project_path.exists():
            reply = QMessageBox.warning(
                self,
                "上書き確認",
                (
                    "同じ名前のプロジェクトファイルが"
                    "すでに存在します。\n\n"
                    "上書きしますか？"
                ),
                QMessageBox.StandardButton.Yes
                | QMessageBox.StandardButton.Cancel,
                QMessageBox.StandardButton.Cancel,
            )

            if reply != QMessageBox.StandardButton.Yes:
                self.status_label.setText(
                    "保存をキャンセルしました"
                )
                return

        try:
            with open(
                file_path,
                "w",
                encoding="utf-8",
            ) as file:
                json.dump(
                    project_data,
                    file,
                    ensure_ascii=False,
                    indent=2,
                )

            self.current_project_path = file_path
            self.project_modified = False

            self.status_label.setText(
                "✅ 作業を保存しました"
            )

        except Exception as e:
            print(
                f"プロジェクト保存エラー: {e}"
            )

            self.status_label.setText(
                "❌ 作業の保存に失敗しました"
            )

    def save_project_overwrite(self):
        # まだ保存先が決まっていない場合は
        # 従来の「作業を保存」を使う
        if not self.current_project_path:
            self.save_project()
            return

        project_data = self.build_project_data()

        try:
            with open(
                self.current_project_path,
                "w",
                encoding="utf-8",
            ) as file:
                json.dump(
                    project_data,
                    file,
                    ensure_ascii=False,
                    indent=2,
                )

            self.project_modified = False

            self.status_label.setText(
                "✅ 作業を上書き保存しました"
            )

        except Exception as e:
            print(
                f"プロジェクト上書き保存エラー: {e}"
            )

            self.status_label.setText(
                "❌ 作業の上書き保存に失敗しました"
        )

    def load_project(self):

        if not self.confirm_discard_changes():
            return
        
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "作業を開く",
            "",
            "AlbumCrop Studio Project (*.acsp.json)",
        )

        if not file_path:
            return

        try:
            with open(
                file_path,
                "r",
                encoding="utf-8",
            ) as file:
                project_data = json.load(file)

        except Exception as e:
            print(
                f"プロジェクト読み込みエラー: {e}"
            )

            self.status_label.setText(
                "❌ 作業の読み込みに失敗しました"
            )
            return

        pages = project_data.get(
            "pages",
            [],
        )

        if not pages:
            self.status_label.setText(
                "❌ プロジェクトに画像がありません"
            )
            return
        
        # 元画像がすべて存在するか確認
        missing_files = []

        for page_data in pages:
            image_path = page_data.get(
                "image_path",
                "",
            )

            if (
                not image_path
                or not Path(image_path).exists()
            ):
                missing_files.append(
                    image_path
                )

        if missing_files:
            missing_names = "\n".join(
                Path(path).name
                if path
                else "(ファイルパスなし)"
                for path in missing_files[:10]
            )

            if len(missing_files) > 10:
                missing_names += (
                    f"\nほか "
                    f"{len(missing_files) - 10} 件"
                )

            QMessageBox.warning(
                self,
                "元画像が見つかりません",
                (
                    "プロジェクトで使用している"
                    "元画像が見つかりません。\n\n"
                    f"{missing_names}\n\n"
                    "元画像を元の場所に戻してから、"
                    "もう一度プロジェクトを開いてください。"
                ),
            )

            self.status_label.setText(
                "❌ 元画像が見つかりません"
            )
            return

        # 現在の状態をいったん初期化
        self.image_paths = []
        self.page_rects = {}
        self.page_angles = {}
        self.deleted_pages_stack = []

        self.page_list.clear()

        # 保存されたページ情報を復元
        for page_index, page_data in enumerate(
            pages
        ):
            image_path = page_data.get(
                "image_path",
                "",
            )

            rects = page_data.get(
                "rects",
                [],
            )

            angles = page_data.get(
                "angles",
                [],
            )

            self.image_paths.append(
                image_path
            )

            self.page_rects[
                page_index
            ] = [
                tuple(rect)
                for rect in rects
            ]

            self.page_angles[
                page_index
            ] = list(
                angles
            )

            # サムネイルを作成
            item_name = Path(
                image_path
            ).name

            thumbnail = QPixmap()

            try:
                with Image.open(
                    image_path
                ) as pil_image:
                    pil_image = pil_image.convert(
                        "RGB"
                    )

                    pil_image.thumbnail(
                        (120, 90)
                    )

                    buffer = BytesIO()

                    pil_image.save(
                        buffer,
                        format="PNG",
                    )

                    thumbnail.loadFromData(
                        buffer.getvalue(),
                        "PNG",
                    )

            except Exception as e:
                print(
                    f"サムネイル作成エラー: "
                    f"{image_path} / {e}"
                )

            item = QListWidgetItem(
                QIcon(thumbnail),
                item_name,
            )

            self.page_list.addItem(
                item
            )

        # 設定を復元
        settings = project_data.get(
            "settings",
            {},
        )

        self.dpi_spin.setValue(
            int(
                settings.get(
                    "dpi",
                    350,
                )
            )
        )

        self.margin_spin.setValue(
            int(
                settings.get(
                    "margin_mm",
                    0,
                )
            )
        )

        # 保存時のページ位置を復元
        self.current_page_index = int(
            project_data.get(
                "current_page_index",
                0,
            )
        )

        if (
            self.current_page_index < 0
            or self.current_page_index
            >= len(self.image_paths)
        ):
            self.current_page_index = 0

        # 現在ページを表示
        self.load_image(
            self.image_paths[
                self.current_page_index
            ]
        )

        saved_rects = self.page_rects.get(
            self.current_page_index,
            [],
        )

        saved_angles = self.page_angles.get(
            self.current_page_index,
            [],
        )

        self.preview_area.set_rects(
            list(saved_rects)
        )

        self.preview_area.rect_angles = list(
            saved_angles
        )

        while len(
            self.preview_area.rect_angles
        ) < len(
            self.preview_area.rects
        ):
            self.preview_area.rect_angles.append(
                0.0
            )

        self.detected_rects = list(
            saved_rects
        )

        self.page_list.setCurrentRow(
            self.current_page_index
        )

        self.delete_page_button.setEnabled(
            True
        )

        self.current_project_path = file_path
        self.project_modified = False

        self.status_label.setText(
            "✅ 作業を読み込みました"
        )

        self.update_crop_preview()
        self.update_page_label()
        self.preview_area.update()

    def change_page_from_list(self, row):
        if row < 0:
            return

        if row >= len(self.image_paths):
            return

        if row == self.current_page_index:
            return

        self.save_current_page_rects()

        self.current_page_index = row

        self.load_image(
            self.image_paths[self.current_page_index]
        )

        saved_rects = self.page_rects.get(
            self.current_page_index,
            [],
        )

        self.preview_area.set_rects(saved_rects)
        self.detected_rects = list(saved_rects)

        saved_angles = self.page_angles.get(
            self.current_page_index,
            [],
        )

        self.preview_area.rect_angles = list(
            saved_angles
        )

        while len(self.preview_area.rect_angles) < len(
            self.preview_area.rects
        ):
            self.preview_area.rect_angles.append(0.0)

        self.preview_area.update()

        self.status_label.setText(
            f"検出数: {len(saved_rects)}"
        )

        self.delete_page_button.setEnabled(True)

        self.update_crop_preview()
        self.update_page_label()

    def delete_current_page(self):
        selected_items = self.page_list.selectedItems()

        if not selected_items:
            return

        selected_rows = sorted(
            [
                self.page_list.row(item)
                for item in selected_items
            ],
            reverse=True,
        )

        self.save_current_page_rects()

        deleted_group = []

        for delete_index in selected_rows:
            deleted_path = self.image_paths[delete_index]

            deleted_rects = list(
                self.page_rects.get(
                    delete_index,
                    [],
                )
            )

            deleted_angles = list(
                self.page_angles.get(
                    delete_index,
                    [],
                )
            )

            deleted_group.append(
                {
                    "index": delete_index,
                    "path": deleted_path,
                    "rects": deleted_rects,
                    "angles": deleted_angles,
                }
)

            self.image_paths.pop(delete_index)
            self.page_list.takeItem(delete_index)

            if delete_index in self.page_rects:
                del self.page_rects[delete_index]

            if delete_index in self.page_angles:
                del self.page_angles[delete_index]

            new_page_rects = {}

            for old_index, rects in self.page_rects.items():
                if old_index > delete_index:
                    new_page_rects[old_index - 1] = rects
                else:
                    new_page_rects[old_index] = rects

            self.page_rects = new_page_rects

            new_page_angles = {}

            for old_index, angles in self.page_angles.items():
                if old_index > delete_index:
                    new_page_angles[old_index - 1] = angles
                else:
                    new_page_angles[old_index] = angles

            self.page_angles = new_page_angles

        self.deleted_pages_stack.append(
            {
                "type": "group",
                "pages": deleted_group,
            }
        )

        if not self.image_paths:
            self.current_page_index = -1
            self.current_image_path = None
            self.current_pixmap = None

            self.preview_area.set_image(None)
            self.preview_area.set_rects([])

            self.page_label.setText("0 / 0")
            self.status_label.setText("検出数: 0")

            self.clear_crop_preview()

            self.delete_page_button.setEnabled(False)
            self.project_modified = True
            return

        self.current_page_index = min(
            min(selected_rows),
            len(self.image_paths) - 1,
        )

        self.load_image(
            self.image_paths[self.current_page_index]
        )

        saved_rects = self.page_rects.get(
            self.current_page_index,
            [],
        )

        self.preview_area.set_rects(saved_rects)
        self.detected_rects = list(saved_rects)

        saved_angles = self.page_angles.get(
            self.current_page_index,
            [],
        )

        self.preview_area.rect_angles = list(
            saved_angles
        )

        while len(self.preview_area.rect_angles) < len(
            self.preview_area.rects
        ):
            self.preview_area.rect_angles.append(0.0)

        self.preview_area.update()

        self.page_list.setCurrentRow(
            self.current_page_index
        )

        self.status_label.setText(
            f"検出数: {len(saved_rects)}"
        )

        self.delete_page_button.setEnabled(True)

        self.project_modified = True

        self.update_crop_preview()
        self.update_page_label()

    def restore_deleted_page(self):
        if not self.deleted_pages_stack:
            return

        deleted = self.deleted_pages_stack.pop()

        # 複数ページ削除のUndo
        if deleted.get("type") == "group":
            pages = sorted(
                deleted["pages"],
                key=lambda page: page["index"],
            )

            for page in pages:
                restore_index = page["index"]
                restore_path = page["path"]
                restore_rects = page["rects"]
                restore_angles = page.get(
                    "angles",
                    [],
                )

                if restore_index > len(self.image_paths):
                    restore_index = len(self.image_paths)

                self.image_paths.insert(
                    restore_index,
                    restore_path,
                )

                new_page_rects = {}

                for old_index, rects in self.page_rects.items():
                    if old_index >= restore_index:
                        new_page_rects[old_index + 1] = rects
                    else:
                        new_page_rects[old_index] = rects

                new_page_rects[restore_index] = list(
                    restore_rects
                )

                new_page_angles = {}

                for old_index, angles in self.page_angles.items():
                    if old_index >= restore_index:
                        new_page_angles[old_index + 1] = angles
                    else:
                        new_page_angles[old_index] = angles

                new_page_angles[restore_index] = list(
                    restore_angles
                )

                self.page_angles = new_page_angles

                self.page_rects = new_page_rects

                item_name = Path(restore_path).name

                thumbnail = QPixmap(restore_path)

                item = QListWidgetItem(
                    QIcon(thumbnail),
                    item_name,
                )

                self.page_list.insertItem(
                    restore_index,
                    item,
                )

            first_index = pages[0]["index"]

            self.current_page_index = min(
                first_index,
                len(self.image_paths) - 1,
            )

        # 1ページ削除のUndo
        else:
            restore_index = deleted["index"]
            restore_path = deleted["path"]
            restore_rects = deleted["rects"]

            if restore_index > len(self.image_paths):
                restore_index = len(self.image_paths)

            self.image_paths.insert(
                restore_index,
                restore_path,
            )

            new_page_rects = {}

            for old_index, rects in self.page_rects.items():
                if old_index >= restore_index:
                    new_page_rects[old_index + 1] = rects
                else:
                    new_page_rects[old_index] = rects

            new_page_rects[restore_index] = list(
                restore_rects
            )

            self.page_rects = new_page_rects

            item_name = Path(restore_path).name

            thumbnail = QPixmap(restore_path)

            if not thumbnail.isNull():
                thumbnail = thumbnail.scaled(
                    120,
                    90,
                    Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.SmoothTransformation,
                )

            item = QListWidgetItem(
                QIcon(thumbnail),
                item_name,
            )

            self.page_list.insertItem(
                restore_index,
                item,
            )

            self.current_page_index = restore_index

        # 復元後の現在ページを表示
        self.load_image(
            self.image_paths[self.current_page_index]
        )

        saved_rects = self.page_rects.get(
            self.current_page_index,
            [],
        )

        self.preview_area.set_rects(
            list(saved_rects)
        )
        self.detected_rects = list(
            saved_rects
        )

        saved_angles = self.page_angles.get(
            self.current_page_index,
            [],
        )

        self.preview_area.rect_angles = list(
            saved_angles
        )

        while len(self.preview_area.rect_angles) < len(
            self.preview_area.rects
        ):
            self.preview_area.rect_angles.append(0.0)

        self.preview_area.update()

        self.page_list.setCurrentRow(
            self.current_page_index
        )

        self.delete_page_button.setEnabled(True)

        self.status_label.setText(
            f"検出数: {len(saved_rects)}"
        )

        self.update_crop_preview()
        self.update_page_label()

    def show_previous_page(self):
        if not self.image_paths:
            return

        if self.current_page_index <= 0:
            return

        self.save_current_page_rects()

        self.current_page_index -= 1

        self.load_image(
            self.image_paths[self.current_page_index]
        )

        saved_rects = self.page_rects.get(
            self.current_page_index,
            [],
        )

        self.preview_area.set_rects(saved_rects)
        self.detected_rects = list(saved_rects)

        saved_angles = self.page_angles.get(
            self.current_page_index,
            [],
        )

        self.preview_area.rect_angles = list(
            saved_angles
        )

        while len(self.preview_area.rect_angles) < len(
            self.preview_area.rects
        ):
            self.preview_area.rect_angles.append(0.0)

        self.preview_area.update()        

        self.status_label.setText(
            f"検出数: {len(saved_rects)}"
        ) 

        self.update_crop_preview()

        self.page_list.setCurrentRow(
            self.current_page_index
        ) 

        self.update_page_label()

    def show_next_page(self):
        if not self.image_paths:
            return

        if self.current_page_index >= len(self.image_paths) - 1:
            return

        self.save_current_page_rects()

        self.current_page_index += 1

        self.load_image(
            self.image_paths[self.current_page_index]
        )

        saved_rects = self.page_rects.get(
            self.current_page_index,
            [],
        )

        self.preview_area.set_rects(saved_rects)
        self.detected_rects = list(saved_rects)

        saved_angles = self.page_angles.get(
            self.current_page_index,
            [],
        )

        self.preview_area.rect_angles = list(
            saved_angles
        )

        while len(self.preview_area.rect_angles) < len(
            self.preview_area.rects
        ):
            self.preview_area.rect_angles.append(0.0)

        self.preview_area.update()        

        self.status_label.setText(
            f"検出数: {len(saved_rects)}"
        )

        self.update_crop_preview()

        self.page_list.setCurrentRow(
            self.current_page_index
        )

        self.update_page_label()

    def load_image(self, file_path):
        path = Path(file_path)

        print(f"load_image(): {path}")
        print(f"exists: {path.exists()}")

        if path.suffix.lower() not in [".jpg", ".jpeg", ".png", ".tif", ".tiff"]:
            self.preview_area.setText("対応していないファイル形式です。")
            return

        try:
            image = Image.open(path).convert("RGB")
        except Exception as e:
            print("=" * 60)
            traceback.print_exc()
            print("=" * 60)
            return

        w, h = image.size
        data = image.tobytes("raw", "RGB")

        qimage = QImage(
            data,
            w,
            h,
            w * 3,
            QImage.Format.Format_RGB888,
        )

        pixmap = QPixmap.fromImage(qimage)

        self.current_image_path = str(path)
        self.current_pixmap = pixmap
        self.detected_rects = []

        self.preview_area.set_image(pixmap)
        self.preview_area.set_rects([])

        self.status_label.setText("検出数: 0")

        if hasattr(self, "add_rect_button"):
            self.add_rect_button.setChecked(False)
            self.preview_area.set_add_mode(False)

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

        # 検出開始
        self.detect_button.setEnabled(False)

        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(0)

        self.status_label.setText("🔍 写真を検出中...")
        self.status_label.repaint()

        QApplication.processEvents()

        self.detected_rects = detect_photos(
            self.current_image_path
        )

        # 検出終了
        self.progress_bar.setValue(100)

        QApplication.processEvents()

        self.progress_bar.setVisible(False)

        self.detect_button.setEnabled(True)

        self.status_label.setText(
            f"検出数: {len(self.detected_rects)}"
        )

        self.show_image()

    def generate_manual_rects(self):
        if self.current_pixmap is None:
            self.status_label.setText(
                "先に画像を読み込んでください。"
            )
            return

        count = self.manual_count_spin.value()

        image_w = self.current_pixmap.width()
        image_h = self.current_pixmap.height()

        if count <= 4:
            columns = 2
        elif count <= 6:
            columns = 3
        else:
            columns = 4

        rows = (
            count + columns - 1
        ) // columns

        margin_x = int(
            image_w * 0.05
        )

        margin_y = int(
            image_h * 0.05
        )

        usable_w = (
            image_w - margin_x * 2
        )

        usable_h = (
            image_h - margin_y * 2
        )

        cell_w = (
            usable_w / columns
        )

        cell_h = (
            usable_h / rows
        )

        # 枠生成前の状態をUndo履歴へ保存
        self.preview_area.save_undo_state()

        rects = list(
            self.preview_area.rects
        )

        angles = list(
            self.preview_area.rect_angles
        )

        for index in range(count):
            row = index // columns
            column = index % columns

            x = (
                margin_x
                + int(column * cell_w)
            )

            y = (
                margin_y
                + int(row * cell_h)
            )

            w = int(
                cell_w * 0.8
            )

            h = int(
                cell_h * 0.8
            )

            rects.append(
                (
                    x,
                    y,
                    w,
                    h,
                )
            )

            # 生成枠はすべて0度
            angles.append(0.0)

        self.preview_area.rects = rects
        self.preview_area.rect_angles = angles
        self.preview_area.selected_rect = -1

        self.detected_rects = list(
            rects
        )

        self.preview_area.rects_changed.emit()
        self.preview_area.update()

        self.status_label.setText(
            f"枠数: {len(rects)}"
        )

        self.save_current_page_rects()

        # 枠生成後、キーボード操作の入力先を
        # キャンバスへ戻す
        self.preview_area.setFocus(
            Qt.FocusReason.OtherFocusReason
        )

    def copy_selected_rect(self):
        selected_index = self.preview_area.selected_rect

        if selected_index < 0:
            self.status_label.setText(
                "コピーする枠を選択してください。"
            )
            return

        if selected_index >= len(self.preview_area.rects):
            return

        x, y, w, h = self.preview_area.rects[selected_index]

        offset = 30

        copied_rect = (
            x + offset,
            y + offset,
            w,
            h,
        )

        new_rects = list(self.preview_area.rects)
        new_rects.append(copied_rect)

        self.preview_area.set_rects(new_rects)
        self.detected_rects = list(new_rects)

        self.save_current_page_rects()

        self.status_label.setText(
            f"枠数: {len(new_rects)}"
        )

    def toggle_add_mode(self):
        self.preview_area.set_add_mode(
            self.add_rect_button.isChecked()
        )

    def save_settings(self):
        Config.set_dpi(
            self.dpi_spin.value()
        )

        Config.set_margin_mm(
            self.margin_spin.value()
        )

    def save_crops(self):
        self.save_button.setEnabled(False)
        self.status_label.setText(
            "✂️ 切り抜き中..."
        )
        QApplication.processEvents()

        # 現在編集中のページ状態を保存
        self.save_current_page_rects()

        if not self.image_paths:
            print("画像が読み込まれていません")

            self.status_label.setText(
                "画像が読み込まれていません"
            )

            self.save_button.setEnabled(True)
            return

        # 全ページの枠数を確認
        total_crops = sum(
            len(
                self.page_rects.get(
                    page_index,
                    [],
                )
            )
            for page_index in range(
                len(self.image_paths)
            )
        )

        if total_crops == 0:
            print("保存する枠がありません")

            self.status_label.setText(
                "保存する枠がありません"
            )

            self.save_button.setEnabled(True)
            return

        output_dir_text = (
            QFileDialog.getExistingDirectory(
                self,
                "保存先フォルダを選択",
                str(
                    Path(
                        self.current_image_path
                    ).parent
                ),
            )
        )

        if not output_dir_text:
            self.status_label.setText(
                "保存をキャンセルしました"
            )

            self.save_button.setEnabled(True)
            return

        output_dir = Path(
            output_dir_text
        )

        # -------------------------
        # 同名ファイルの事前確認
        # -------------------------

        existing_files = []

        for page_index in range(
            len(self.image_paths)
        ):
            page_rects = self.page_rects.get(
                page_index,
                [],
            )

            for crop_index in range(
                1,
                len(page_rects) + 1,
            ):
                output_path = (
                    output_dir
                    / (
                        f"page_{page_index + 1:03}_"
                        f"photo_{crop_index:03}.jpg"
                    )
                )

                if output_path.exists():
                    existing_files.append(
                        output_path
                    )

        if existing_files:
            reply = QMessageBox.warning(
                self,
                "上書き確認",
                (
                    f"保存先に同名ファイルが"
                    f"{len(existing_files)}件あります。\n\n"
                    "既存のファイルを"
                    "上書きしますか？"
                ),
                QMessageBox.StandardButton.Yes
                | QMessageBox.StandardButton.Cancel,
                QMessageBox.StandardButton.Cancel,
            )

            if (
                reply
                != QMessageBox.StandardButton.Yes
            ):
                self.status_label.setText(
                    "保存をキャンセルしました"
                )

                self.save_button.setEnabled(True)
                return

        dpi = self.dpi_spin.value()

        jpeg_quality = (
            Config.get_jpeg_quality()
        )

        margin_mm = (
            self.margin_spin.value()
        )

        margin_px = int(
            (margin_mm / 25.4) * dpi
        )

        # 進捗バーを表示
        self.progress_bar.setValue(0)
        self.progress_bar.setVisible(True)

        QApplication.processEvents()

        self.export_thread = QThread()

        self.export_worker = CropExportWorker(
            self.image_paths,
            self.page_rects,
            self.page_angles,
            output_dir,
            dpi,
            margin_px,
            jpeg_quality,
            total_crops,
        )

        self.export_worker.moveToThread(
            self.export_thread
        )

        self.export_thread.started.connect(
            self.export_worker.run
        )

        self.export_worker.progress.connect(
            self.update_export_progress
        )

        self.export_worker.finished.connect(
            self.export_finished
        )

        self.export_worker.failed.connect(
            self.export_failed
        )

        self.export_worker.finished.connect(
            self.export_thread.quit
        )

        self.export_worker.failed.connect(
            self.export_thread.quit
        )

        self.export_worker.finished.connect(
            self.export_worker.deleteLater
        )

        self.export_worker.failed.connect(
            self.export_worker.deleteLater
        )

        self.export_thread.finished.connect(
            self.export_thread_finished
        )

        self.export_thread.finished.connect(
            self.export_thread.deleteLater
        )

        self.export_running = True
        self.save_button.setEnabled(False)

        print(
            f"保存先: {output_dir}"
        )

        self.export_thread.start()

    def confirm_discard_changes(self):
        if not self.project_modified:
            return True

        reply = QMessageBox.question(
            self,
            "未保存の変更",
            (
                "保存されていない変更があります。\n\n"
                "作業を保存しますか？"
            ),
            QMessageBox.StandardButton.Save
            | QMessageBox.StandardButton.Discard
            | QMessageBox.StandardButton.Cancel,
            QMessageBox.StandardButton.Save,
        )

        if reply == QMessageBox.StandardButton.Save:
            self.save_project_overwrite()
            return not self.project_modified

        if reply == QMessageBox.StandardButton.Discard:
            return True

        return False

    def closeEvent(self, event):
        if self.confirm_discard_changes():
            event.accept()
        else:
            event.ignore()

    def show_about_dialog(self):
        dialog = AboutDialog(self)
        dialog.exec()

    def show_settings_dialog(self):
        dialog = SettingsDialog(self)

        result = dialog.exec()

        if result:
            self.dpi_spin.setValue(
                Config.get_dpi()
            )

            self.margin_spin.setValue(
                Config.get_margin_mm()
            )

            self.update_dpi_preset(
                self.dpi_spin.value()
            )

            self.status_label.setText(
                self.tr(
                    "✅ 設定を保存しました"
                )
            )

    def resizeEvent(self, event):
        super().resizeEvent(event)

        if self.current_pixmap is not None:
            self.show_image()

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            file_path = event.mimeData().urls()[0].toLocalFile()
            suffix = Path(file_path).suffix.lower()

            if suffix in [
                ".jpg",
                ".jpeg",
                ".png",
                ".tif",
                ".tiff",
                ".pdf",
            ]:
                event.acceptProposedAction()
                return

        event.ignore()

    def keyPressEvent(self, event):
        if (
            event.key() == Qt.Key.Key_Z
            and event.modifiers()
            == Qt.KeyboardModifier.ControlModifier
        ):
            self.restore_deleted_page()
            return

        super().keyPressEvent(event)

    def create_rotated_crop_pixmap(
        self,
        x,
        y,
        w,
        h,
        angle,
    ):
        if self.current_pixmap is None:
            return QPixmap()

        # 回転していない枠は、
        # 従来どおりそのまま切り抜く
        if abs(angle) < 0.001:
            return self.current_pixmap.copy(
                int(x),
                int(y),
                int(w),
                int(h),
            )

        # 切り抜き先のサイズ
        crop_w = max(
            1,
            int(round(w)),
        )

        crop_h = max(
            1,
            int(round(h)),
        )

        result = QPixmap(
            crop_w,
            crop_h,
        )

        result.fill(
            Qt.GlobalColor.transparent
        )

        painter = QPainter(
            result
        )

        painter.setRenderHint(
            QPainter.RenderHint.SmoothPixmapTransform,
            True,
        )

        # 出力画像の中心を原点にする
        painter.translate(
            crop_w / 2,
            crop_h / 2,
        )

        # 枠の回転を打ち消して水平化
        painter.rotate(
            -angle
        )

        # 元画像上の枠中心が、
        # 出力画像の中心へ来るよう移動
        center_x = x + w / 2
        center_y = y + h / 2

        painter.translate(
            -center_x,
            -center_y,
        )

        # 元画像を描画
        painter.drawPixmap(
            0,
            0,
            self.current_pixmap,
        )

        painter.end()

        return result

    def clear_crop_preview(self):
        while self.crop_preview_list_layout.count():
            item = self.crop_preview_list_layout.takeAt(0)

            widget = item.widget()

            if widget is not None:
                widget.deleteLater()

        empty_label = QLabel(
            "切り抜き結果が\nここに表示されます"
        )
        empty_label.setAlignment(
            Qt.AlignmentFlag.AlignCenter
        )

        self.crop_preview_list_layout.addWidget(
            empty_label
        )

        self.crop_preview_list_layout.addStretch()

    def update_crop_preview(self):
        if self.current_pixmap is None:
            return

        # 既存のプレビュー表示を全部削除
        while self.crop_preview_list_layout.count():
            item = self.crop_preview_list_layout.takeAt(0)

            widget = item.widget()

            if widget is not None:
                widget.deleteLater()

        # 枠がない場合
        if not self.preview_area.rects:
            empty_label = QLabel(
                "切り抜き結果が\nここに表示されます"
            )
            empty_label.setAlignment(
                Qt.AlignmentFlag.AlignCenter
            )

            self.crop_preview_list_layout.addWidget(
                empty_label
            )

            self.crop_preview_list_layout.addStretch()
            return

        # すべての枠を順番にプレビュー表示
        for index, (x, y, w, h) in enumerate(
            self.preview_area.rects,
            start=1,
        ):
            angle = 0.0

            angle_index = index - 1

            if angle_index < len(
                self.preview_area.rect_angles
            ):
                angle = self.preview_area.rect_angles[
                    angle_index
                ]

            crop_pixmap = self.create_rotated_crop_pixmap(
                x,
                y,
                w,
                h,
                angle,
            )

            if crop_pixmap.isNull():
                continue

            title_label = QLabel(
                f"写真 {index}"
            )

            preview_label = QLabel()
            preview_label.setAlignment(
                Qt.AlignmentFlag.AlignCenter
            )

            preview_pixmap = crop_pixmap.scaled(
                220,
                180,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )

            preview_label.setPixmap(
                preview_pixmap
            )

            self.crop_preview_list_layout.addWidget(
                title_label
            )

            self.crop_preview_list_layout.addWidget(
                preview_label
            )

        self.crop_preview_list_layout.addStretch()