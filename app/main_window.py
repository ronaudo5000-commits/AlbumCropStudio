from pathlib import Path
from io import BytesIO
from PIL import Image

from PySide6.QtCore import Qt, QRect, QSettings, QSize, QPointF
from PySide6.QtGui import (
    QPixmap,
    QPainter,
    QPen,
    QColor,
    QImage,
    QIcon,
    QTransform,
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
    QAbstractItemView,
    QScrollArea,
    QMessageBox,
)

from core.photo_detector import detect_photos

from app.photo_canvas import PhotoCanvas


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

        self.setWindowTitle("AlbumCrop Studio")
        self.resize(1000, 700)
        self.setAcceptDrops(True)

        self.settings = QSettings("AlbumCropStudio", "AlbumCropStudio")

        self.current_image_path = None
        self.current_pixmap = None
        self.detected_rects = []

        self.image_paths = []
        self.current_page_index = -1
        self.page_rects = {}
        self.page_angles = {}
        self.deleted_pages_stack = []

        self.selected_rect = -1

        self.dragging = False
        self.last_mouse_x = 0
        self.last_mouse_y = 0

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
        self.page_list.setMinimumWidth(180)
        self.page_list.setMaximumWidth(260)
        self.page_list.setIconSize(
            QSize(120, 90)
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

        dpi_label = QLabel("DPI")
        self.dpi_spin = QSpinBox()
        self.dpi_spin.setRange(72, 1200)
        self.dpi_spin.setValue(
            int(self.settings.value("dpi", 350))
        )

        margin_label = QLabel("余白(mm)")
        self.margin_spin = QSpinBox()
        self.margin_spin.setRange(0, 20)
        self.margin_spin.setValue(
            int(self.settings.value("margin_mm", 0))
        )

        # self.dpi_spin.valueChanged.connect(
         #    self.save_settings
         # )

         # self.margin_spin.valueChanged.connect(
         #    self.save_settings
         # )

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

        self.prev_button = QPushButton("◀ 前へ")
        self.prev_button.setMinimumHeight(40)
        self.prev_button.clicked.connect(self.show_previous_page)

        self.page_label = QLabel("0 / 0")
        self.page_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.next_button = QPushButton("次へ ▶")
        self.next_button.setMinimumHeight(40)
        self.next_button.clicked.connect(self.show_next_page)

        self.detect_button = QPushButton("写真を検出")
        self.detect_button.setMinimumHeight(40)
        self.detect_button.clicked.connect(self.detect_photos)

        self.add_rect_button = QPushButton("枠追加")
        self.add_rect_button.setMinimumHeight(40)
        self.add_rect_button.setCheckable(True)
        self.add_rect_button.clicked.connect(self.toggle_add_mode)

        self.copy_rect_button = QPushButton("枠をコピー")
        self.copy_rect_button.setMinimumHeight(40)
        self.copy_rect_button.clicked.connect(
        self.copy_selected_rect
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

        self.save_button = QPushButton("切り抜き")
        self.save_button.setMinimumHeight(40)
        self.save_button.clicked.connect(self.save_crops)

        button_layout.addWidget(self.open_button)
        button_layout.addWidget(self.prev_button)
        button_layout.addWidget(self.page_label)
        button_layout.addWidget(self.next_button)
        button_layout.addWidget(self.detect_button)
        button_layout.addWidget(self.add_rect_button)
        button_layout.addWidget(self.copy_rect_button)
        button_layout.addWidget(self.manual_count_label)
        button_layout.addWidget(self.manual_count_spin)
        button_layout.addWidget(self.generate_rects_button)
        button_layout.addWidget(self.save_button)

        main_layout.addLayout(button_layout)

        self.status_label = QLabel("検出数: 0")
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        main_layout.addWidget(self.status_label)

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

    def open_image(self):
        file_paths, _ = QFileDialog.getOpenFileNames(
            self,
            "画像を開く",
            "",
            "Image Files (*.jpg *.jpeg *.png *.tif *.tiff)",
        )

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

        self.update_page_label()

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

        if path.suffix.lower() not in [".jpg", ".jpeg", ".png", ".tif", ".tiff"]:
            self.preview_area.setText("対応していないファイル形式です。")
            return

        try:
            image = Image.open(path).convert("RGB")
        except Exception as e:
            print(f"画像を読み込めませんでした: {e}")
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
        self.status_label.setText("🔍 写真を検出中...")
        self.status_label.repaint()
        QApplication.processEvents()

        self.detected_rects = detect_photos(
            self.current_image_path
        )

        # 検出終了
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

        rows = (count + columns - 1) // columns

        margin_x = int(image_w * 0.05)
        margin_y = int(image_h * 0.05)

        usable_w = image_w - (margin_x * 2)
        usable_h = image_h - (margin_y * 2)

        cell_w = usable_w / columns
        cell_h = usable_h / rows

        rects = list(self.preview_area.rects)

        for index in range(count):
            row = index // columns
            column = index % columns

            x = margin_x + int(column * cell_w)
            y = margin_y + int(row * cell_h)

            w = int(cell_w * 0.8)
            h = int(cell_h * 0.8)

            rects.append(
                (
                    x,
                    y,
                    w,
                    h,
                )
            )

        self.detected_rects = rects
        self.preview_area.set_rects(rects)

        self.status_label.setText(
            f"枠数: {len(rects)}"
        )

        self.save_current_page_rects()

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
        self.settings.setValue(
            "dpi",
            self.dpi_spin.value()
        )

        self.settings.setValue(
            "margin_mm",
            self.margin_spin.value()
        )

    def create_rotated_crop_image(
        self,
        image,
        x,
        y,
        w,
        h,
        angle,
    ):
        # 回転していない場合は従来どおり切り抜く
        if abs(angle) < 0.001:
            left = int(x)
            top = int(y)
            right = int(x + w)
            bottom = int(y + h)

            return image.crop(
                (
                    left,
                    top,
                    right,
                    bottom,
                )
            )

        center_x = x + w / 2
        center_y = y + h / 2

        # 枠中心を基準に画像全体を逆回転
        rotated = image.rotate(
            angle,
            resample=Image.Resampling.BICUBIC,
            center=(
                center_x,
                center_y,
            ),
        )

        # 回転補正後、元の枠サイズで切り抜く
        left = int(
            round(center_x - w / 2)
        )

        top = int(
            round(center_y - h / 2)
        )

        right = int(
            round(center_x + w / 2)
        )

        bottom = int(
            round(center_y + h / 2)
        )

        return rotated.crop(
            (
                left,
                top,
                right,
                bottom,
            )
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

        margin_mm = (
            self.margin_spin.value()
        )

        margin_px = int(
            (margin_mm / 25.4) * dpi
        )

        saved_count = 0

        # -------------------------
        # 全ページを順番に処理
        # -------------------------

        for page_index, image_path in enumerate(
            self.image_paths
        ):
            page_rects = self.page_rects.get(
                page_index,
                [],
            )

            page_angles = self.page_angles.get(
                page_index,
                [],
            )

            # 枠がないページは飛ばす
            if not page_rects:
                continue

            try:
                with Image.open(
                    image_path
                ) as source_image:
                    image = source_image.convert(
                        "RGB"
                    )

                    for crop_index, (
                        x,
                        y,
                        w,
                        h,
                    ) in enumerate(
                        page_rects,
                        start=1,
                    ):
                        angle = 0.0

                        angle_index = (
                            crop_index - 1
                        )

                        if (
                            angle_index
                            < len(page_angles)
                        ):
                            angle = page_angles[
                                angle_index
                            ]

                        crop_x = (
                            x - margin_px
                        )

                        crop_y = (
                            y - margin_px
                        )

                        crop_w = (
                            w
                            + margin_px * 2
                        )

                        crop_h = (
                            h
                            + margin_px * 2
                        )

                        crop = (
                            self.create_rotated_crop_image(
                                image,
                                crop_x,
                                crop_y,
                                crop_w,
                                crop_h,
                                angle,
                            )
                        )

                        output_path = (
                            output_dir
                            / (
                                f"page_{page_index + 1:03}_"
                                f"photo_{crop_index:03}.jpg"
                            )
                        )

                        crop.save(
                            output_path,
                            "JPEG",
                            quality=95,
                            dpi=(dpi, dpi),
                        )

                        saved_count += 1

            except Exception as e:
                print(
                    f"ページ {page_index + 1} "
                    f"の書き出しに失敗しました: "
                    f"{e}"
                )

        print(
            f"{saved_count}枚の写真を"
            "保存しました"
        )

        print(
            f"保存先: {output_dir}"
        )

        self.status_label.setText(
            f"✅ {saved_count}枚"
            "切り抜き完了"
        )

        self.save_button.setEnabled(True)

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
        crop_w = max(1, int(round(w)))
        crop_h = max(1, int(round(h)))

        result = QPixmap(
            crop_w,
            crop_h,
        )

        result.fill(
            Qt.GlobalColor.transparent
        )

        painter = QPainter(result)

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

        # 元画像上の枠中心が
        # 出力画像の中心に来るよう移動
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

        if self.current_pixmap is None:
            return QPixmap()

        if abs(angle) < 0.001:
            return self.current_pixmap.copy(
                int(x),
                int(y),
                int(w),
                int(h),
            )

        center_x = x + w / 2
        center_y = y + h / 2

        # 元画像全体を、対象枠の中心を基準に逆回転
        transform = QTransform()

        transform.translate(
            center_x,
            center_y,
        )

        transform.rotate(
            -angle
        )

        transform.translate(
            -center_x,
            -center_y,
        )

        rotated_pixmap = self.current_pixmap.transformed(
            transform,
            Qt.TransformationMode.SmoothTransformation,
        )

        # transformed() では画像全体の外接矩形サイズが変わるため、
        # ここではまず補助関数だけ用意する
        return rotated_pixmap

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