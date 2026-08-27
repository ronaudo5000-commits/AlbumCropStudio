import math

from PySide6.QtCore import (
    Qt,
    Signal,
    QRectF,
    QTimer,
)
from PySide6.QtGui import (
    QPainter,
    QPen,
    QColor,
    QPixmap,
    QFont,
    QKeyEvent,
)
from PySide6.QtWidgets import (
    QWidget,
    QMenu,
)


class PhotoCanvas(QWidget):
    zoom_changed = Signal(float)
    rects_changed = Signal()
    selected_rect_changed = Signal(int)
    composite_create_finished = Signal()

    def __init__(self):
        super().__init__()

        self.pixmap = None
        self.rects = []
        self.rect_angles = []
        self.rect_aspect_modes = []
        self.rect_group_ids = []

        # 単一操作の基準になる枠
        self.selected_rect = -1

        # 複数選択されている枠番号
        self.selected_rects = set()

        # Ctrl+Cでコピーした枠情報を保持する
        self.copied_rects = []

        self.undo_stack = []
        self.redo_stack = []
        self.zoom_factor = 1.0
        
        self.pan_x = 0.0
        self.pan_y = 0.0

        self.panning = False
        self.last_pan_pos = None

        self.space_pressed = False
        self.space_pan_dragging = False

        # 選択枠の動く点線
        self.selection_dash_offset = 0.0

        self.selection_dash_timer = QTimer(
            self
        )

        self.selection_dash_timer.setInterval(
            200
        )

        self.selection_dash_timer.timeout.connect(
            self.advance_selection_dash
        )

        self.selection_dash_timer.start()

        self.dragging = False
        self.drag_undo_saved = False
        self.last_image_x = 0
        self.last_image_y = 0

        self.add_mode = False
        self.adding_rect = False
        self.add_start_x = 0
        self.add_start_y = 0

        self.composite_create_mode = False
        self.composite_create_indexes = []

        self.composite_member_edit_mode = False

        self.resizing = False
        self.resize_handle_size = 7
        self.resize_start_rect = None

        self.aspect_ratio_mode = "free"

        self.rotating = False
        self.rotation_handle_below = False

        # 回転操作開始時の状態
        self.rotation_start_pointer_angle = None
        self.rotation_start_rect_angle = 0.0

        # 回転感度
        self.rotation_sensitivity = 0.30
        self.rotation_fine_sensitivity = 0.10

        self.setMinimumHeight(400)
        self.setMouseTracking(True)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)

    def set_image(self, pixmap):
        self.pixmap = pixmap
        self.rects = []
        self.rect_angles = []
        self.rect_aspect_modes = []
        self.rect_group_ids = []
        self.selected_rect = -1
        self.selected_rects.clear()

        self.composite_create_indexes.clear()

        self.zoom_factor = 1.0
        self.pan_x = 0.0
        self.pan_y = 0.0

        self.update()

    def set_rects(
        self,
        rects,
        group_ids=None,
    ):
        self.rects = rects

        # 枠数に合わせて角度情報を用意する
        if len(self.rect_angles) < len(self.rects):
            missing_count = (
                len(self.rects) - len(self.rect_angles)
            )

            self.rect_angles.extend(
                [0.0] * missing_count
            )

        elif len(self.rect_angles) > len(self.rects):
            self.rect_angles = self.rect_angles[
                :len(self.rects)
            ]

        # 枠数に合わせて縦横比モードを用意する
        if (
            len(self.rect_aspect_modes)
            < len(self.rects)
        ):
            missing_count = (
                len(self.rects)
                - len(self.rect_aspect_modes)
            )

            self.rect_aspect_modes.extend(
                ["free"] * missing_count
            )

        elif (
            len(self.rect_aspect_modes)
            > len(self.rects)
        ):
            self.rect_aspect_modes = (
                self.rect_aspect_modes[
                    :len(self.rects)
                ]
            )

        # 枠数に合わせて複合枠group IDを用意する
        if group_ids is None:
            self.rect_group_ids = [
                None
                for _ in self.rects
            ]

        else:
            self.rect_group_ids = list(
                group_ids
            )

            while (
                len(self.rect_group_ids)
                < len(self.rects)
            ):
                self.rect_group_ids.append(
                    None
                )

            if (
                len(self.rect_group_ids)
                > len(self.rects)
            ):
                self.rect_group_ids = (
                    self.rect_group_ids[
                        :len(self.rects)
                    ]
                )

        self.selected_rect = -1
        self.selected_rects.clear()
        self.update()

    def save_undo_state(self):
        self.undo_stack.append(
            {
                "rects": [
                    tuple(rect)
                    for rect in self.rects
                ],
                "angles": list(
                    self.rect_angles
                ),
                "aspect_modes": list(
                    self.rect_aspect_modes
                ),
                "group_ids": list(
                    self.rect_group_ids
                ),
            }
        )

        if len(self.undo_stack) > 30:
            self.undo_stack.pop(0)

        self.redo_stack.clear()

    def undo(self):
        if not self.undo_stack:
            return

        self.redo_stack.append(
            {
                "rects": [
                    tuple(rect)
                    for rect in self.rects
                ],
                "angles": list(
                    self.rect_angles
                ),
                "aspect_modes": list(
                    self.rect_aspect_modes
                ),
                "group_ids": list(
                    self.rect_group_ids
                ),
            }
        )

        state = self.undo_stack.pop()

        self.rects = [
            tuple(rect)
            for rect in state.get(
                "rects",
                [],
            )
        ]

        self.rect_angles = list(
            state.get(
                "angles",
                [],
            )
        )

        self.rect_aspect_modes = list(
            state.get(
                "aspect_modes",
                [],
            )
        )

        self.rect_group_ids = list(
            state.get(
                "group_ids",
                [],
            )
        )

        while len(self.rect_angles) < len(self.rects):
            self.rect_angles.append(0.0)

        if len(self.rect_angles) > len(self.rects):
            self.rect_angles = self.rect_angles[
                :len(self.rects)
            ]

        while (
            len(self.rect_aspect_modes)
            < len(self.rects)
        ):
            self.rect_aspect_modes.append(
                "free"
            )

        if (
            len(self.rect_aspect_modes)
            > len(self.rects)
        ):
            self.rect_aspect_modes = (
                self.rect_aspect_modes[
                    :len(self.rects)
                ]
            )

        while (
            len(self.rect_group_ids)
            < len(self.rects)
        ):
            self.rect_group_ids.append(
                None
            )

        if (
            len(self.rect_group_ids)
            > len(self.rects)
        ):
            self.rect_group_ids = (
                self.rect_group_ids[
                    :len(self.rects)
                ]
            )

        self.selected_rect = -1
        self.selected_rects.clear()
        self.dragging = False
        self.adding_rect = False
        self.resizing = False
        self.rotating = False

        self.rects_changed.emit()
        self.update()

    def redo(self):
        if not self.redo_stack:
            return

        self.undo_stack.append(
            {
                "rects": [
                    tuple(rect)
                    for rect in self.rects
                ],
                "angles": list(
                    self.rect_angles
                ),
                "aspect_modes": list(
                    self.rect_aspect_modes
                ),
                "group_ids": list(
                    self.rect_group_ids
                ),
            }
        )

        state = self.redo_stack.pop()

        self.rects = [
            tuple(rect)
            for rect in state.get(
                "rects",
                [],
            )
        ]

        self.rect_angles = list(
            state.get(
                "angles",
                [],
            )
        )

        self.rect_aspect_modes = list(
            state.get(
                "aspect_modes",
                [],
            )
        )

        self.rect_group_ids = list(
            state.get(
                "group_ids",
                [],
            )
        )

        while len(self.rect_angles) < len(self.rects):
            self.rect_angles.append(0.0)

        if len(self.rect_angles) > len(self.rects):
            self.rect_angles = self.rect_angles[
                :len(self.rects)
            ]

        while (
            len(self.rect_aspect_modes)
            < len(self.rects)
        ):
            self.rect_aspect_modes.append(
                "free"
            )

        if (
            len(self.rect_aspect_modes)
            > len(self.rects)
        ):
            self.rect_aspect_modes = (
                self.rect_aspect_modes[
                    :len(self.rects)
                ]
            )

        while (
            len(self.rect_group_ids)
            < len(self.rects)
        ):
            self.rect_group_ids.append(
                None
            )

        if (
            len(self.rect_group_ids)
            > len(self.rects)
        ):
            self.rect_group_ids = (
                self.rect_group_ids[
                    :len(self.rects)
                ]
            )

        self.selected_rect = -1
        self.selected_rects.clear()
        self.dragging = False
        self.adding_rect = False
        self.resizing = False
        self.rotating = False

        self.rects_changed.emit()
        self.update()

    def set_add_mode(self, enabled):
        self.add_mode = enabled
        self.adding_rect = False
        self.selected_rect = -1
        self.selected_rects.clear()
        self.update()

    def set_composite_create_mode(
        self,
        enabled,
    ):
        self.composite_create_mode = bool(
            enabled
        )

        self.composite_create_indexes.clear()

        self.adding_rect = False
        self.dragging = False
        self.resizing = False
        self.rotating = False

        self.selected_rect = -1
        self.selected_rects.clear()

        self.update()

    def set_composite_member_edit_mode(
        self,
        enabled,
    ):
        self.composite_member_edit_mode = bool(
            enabled
        )

        self.dragging = False
        self.adding_rect = False
        self.resizing = False
        self.rotating = False

        self.selected_rect = -1
        self.selected_rects.clear()

        self.update()

    def normalize_singleton_groups(self):
        group_counts = {}

        for group_id in self.rect_group_ids:
            if group_id is None:
                continue

            group_counts[group_id] = (
                group_counts.get(
                    group_id,
                    0,
                )
                + 1
            )

        for index, group_id in enumerate(
            self.rect_group_ids
        ):
            if group_id is None:
                continue

            if group_counts.get(
                group_id,
                0,
            ) < 2:
                self.rect_group_ids[
                    index
                ] = None

    def next_group_id(self):
        existing_ids = [
            group_id
            for group_id in self.rect_group_ids
            if isinstance(group_id, int)
        ]

        if not existing_ids:
            return 1

        return max(existing_ids) + 1

    def group_selected_rects(self):
        selected_indexes = sorted(
            self.selected_rects
        )

        if len(selected_indexes) < 2:
            return

        # 枠数に合わせてgroup ID情報を補完する
        while (
            len(self.rect_group_ids)
            < len(self.rects)
        ):
            self.rect_group_ids.append(
                None
            )

        if (
            len(self.rect_group_ids)
            > len(self.rects)
        ):
            self.rect_group_ids = (
                self.rect_group_ids[
                    :len(self.rects)
                ]
            )

        # Phase 1では独立枠同士だけを結合する
        for index in selected_indexes:
            if (
                index < 0
                or index >= len(self.rects)
            ):
                return

            if (
                self.rect_group_ids[index]
                is not None
            ):
                return

        self.save_undo_state()

        group_id = self.next_group_id()

        for index in selected_indexes:
            self.rect_group_ids[
                index
            ] = group_id

        self.rects_changed.emit()
        self.update()

    def ungroup_selected_rect(self):
        if self.selected_rect < 0:
            return

        if self.selected_rect >= len(
            self.rect_group_ids
        ):
            return

        group_id = self.rect_group_ids[
            self.selected_rect
        ]

        if group_id is None:
            return

        self.save_undo_state()

        for index in range(
            len(self.rect_group_ids)
        ):
            if (
                self.rect_group_ids[index]
                == group_id
            ):
                self.rect_group_ids[
                    index
                ] = None

        self.rects_changed.emit()
        self.update()

    def get_active_aspect_ratio(
        self,
        start_w,
        start_h,
    ):
        if (
            start_w <= 0
            or start_h <= 0
        ):
            return None

        aspect_ratios = {
            "16:9": 16 / 9,
            "9:16": 9 / 16,
            "4:3": 4 / 3,
            "3:2": 3 / 2,
            "1:1": 1.0,
        }

        if self.aspect_ratio_mode == "free":
            return None

        if self.aspect_ratio_mode == "current":
            return start_w / start_h

        return aspect_ratios.get(
            self.aspect_ratio_mode
        )

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
    
    def rotate_point(
        self,
        point_x,
        point_y,
        center_x,
        center_y,
        angle_degrees,
    ):
        angle_rad = math.radians(
            angle_degrees
        )

        dx = point_x - center_x
        dy = point_y - center_y

        rotated_x = (
            center_x
            + dx * math.cos(angle_rad)
            - dy * math.sin(angle_rad)
        )

        rotated_y = (
            center_y
            + dx * math.sin(angle_rad)
            + dy * math.cos(angle_rad)
        )

        return rotated_x, rotated_y

    def aspect_locked_corner_rect(
        self,
        handle_name,
        mouse_x,
        mouse_y,
        start_x,
        start_y,
        start_w,
        start_h,
        aspect_ratio=None,
    ):
        if (
            start_w <= 0
            or start_h <= 0
        ):
            return None

        if aspect_ratio is None:
            aspect_ratio = (
                start_w / start_h
            )

        if aspect_ratio <= 0:
            return None

        if handle_name == "top_left":
            fixed_x = start_x + start_w
            fixed_y = start_y + start_h

            if (
                mouse_x >= fixed_x
                or mouse_y >= fixed_y
            ):
                return None

            raw_w = fixed_x - mouse_x
            raw_h = fixed_y - mouse_y

        elif handle_name == "top_right":
            fixed_x = start_x
            fixed_y = start_y + start_h

            if (
                mouse_x <= fixed_x
                or mouse_y >= fixed_y
            ):
                return None

            raw_w = mouse_x - fixed_x
            raw_h = fixed_y - mouse_y

        elif handle_name == "bottom_right":
            fixed_x = start_x
            fixed_y = start_y

            if (
                mouse_x <= fixed_x
                or mouse_y <= fixed_y
            ):
                return None

            raw_w = mouse_x - fixed_x
            raw_h = mouse_y - fixed_y

        elif handle_name == "bottom_left":
            fixed_x = start_x + start_w
            fixed_y = start_y

            if (
                mouse_x >= fixed_x
                or mouse_y <= fixed_y
            ):
                return None

            raw_w = fixed_x - mouse_x
            raw_h = mouse_y - fixed_y

        else:
            return None

        if (
            raw_w <= 0
            or raw_h <= 0
        ):
            return None

        if (
            raw_w / raw_h
            >= aspect_ratio
        ):
            new_w = raw_w
            new_h = (
                new_w / aspect_ratio
            )
        else:
            new_h = raw_h
            new_w = (
                new_h * aspect_ratio
            )

        if handle_name == "top_left":
            left = fixed_x - new_w
            top = fixed_y - new_h
            right = fixed_x
            bottom = fixed_y

        elif handle_name == "top_right":
            left = fixed_x
            top = fixed_y - new_h
            right = fixed_x + new_w
            bottom = fixed_y

        elif handle_name == "bottom_right":
            left = fixed_x
            top = fixed_y
            right = fixed_x + new_w
            bottom = fixed_y + new_h

        else:
            left = fixed_x - new_w
            top = fixed_y
            right = fixed_x
            bottom = fixed_y + new_h

        return (
            left,
            top,
            right,
            bottom,
        )

    def aspect_locked_edge_rect(
        self,
        handle_name,
        mouse_x,
        mouse_y,
        start_x,
        start_y,
        start_w,
        start_h,
        angle,
        aspect_ratio=None,
    ):
        if (
            start_w <= 0
            or start_h <= 0
        ):
            return None

        if aspect_ratio is None:
            aspect_ratio = (
                start_w / start_h
            )

        if aspect_ratio <= 0:
            return None

        start_center_x = (
            start_x + start_w / 2
        )

        start_center_y = (
            start_y + start_h / 2
        )

        angle_rad = math.radians(
            angle
        )

        if handle_name == "right":
            new_w = (
                mouse_x - start_x
            )

            if new_w <= 0:
                return None

            new_h = (
                new_w / aspect_ratio
            )

            center_shift = (
                new_w - start_w
            ) / 2

            new_center_x = (
                start_center_x
                + math.cos(angle_rad)
                * center_shift
            )

            new_center_y = (
                start_center_y
                + math.sin(angle_rad)
                * center_shift
            )

        elif handle_name == "left":
            new_w = (
                start_x
                + start_w
                - mouse_x
            )

            if new_w <= 0:
                return None

            new_h = (
                new_w / aspect_ratio
            )

            center_shift = (
                new_w - start_w
            ) / 2

            new_center_x = (
                start_center_x
                - math.cos(angle_rad)
                * center_shift
            )

            new_center_y = (
                start_center_y
                - math.sin(angle_rad)
                * center_shift
            )

        elif handle_name == "top":
            new_h = (
                start_y
                + start_h
                - mouse_y
            )

            if new_h <= 0:
                return None

            new_w = (
                new_h * aspect_ratio
            )

            center_shift = (
                new_h - start_h
            ) / 2

            new_center_x = (
                start_center_x
                + math.sin(angle_rad)
                * center_shift
            )

            new_center_y = (
                start_center_y
                - math.cos(angle_rad)
                * center_shift
            )

        elif handle_name == "bottom":
            new_h = (
                mouse_y - start_y
            )

            if new_h <= 0:
                return None

            new_w = (
                new_h * aspect_ratio
            )

            center_shift = (
                new_h - start_h
            ) / 2

            new_center_x = (
                start_center_x
                - math.sin(angle_rad)
                * center_shift
            )

            new_center_y = (
                start_center_y
                + math.cos(angle_rad)
                * center_shift
            )

        else:
            return None

        left = (
            new_center_x - new_w / 2
        )

        top = (
            new_center_y - new_h / 2
        )

        right = (
            new_center_x + new_w / 2
        )

        bottom = (
            new_center_y + new_h / 2
        )

        return (
            left,
            top,
            right,
            bottom,
        )

    def operation_control_geometry(
        self,
        x,
        y,
        w,
        h,
        angle,
        x_offset,
        y_offset,
        scale_x,
        scale_y,
    ):
        button_size = 28
        button_gap = 4
        rotate_handle_size = 18
        rotate_distance = 45
        edge_margin = 4

        screen_w = w * scale_x
        screen_h = h * scale_y

        screen_center_x = (
            x_offset
            + (x + w / 2) * scale_x
        )

        screen_center_y = (
            y_offset
            + (y + h / 2) * scale_y
        )

        angle_rad = math.radians(
            angle
        )

        # 枠の横方向を表す単位ベクトル
        width_axis_x = math.cos(
            angle_rad
        )

        width_axis_y = math.sin(
            angle_rad
        )

        # 枠の上から下へ向かう単位ベクトル
        down_axis_x = -math.sin(
            angle_rad
        )

        down_axis_y = math.cos(
            angle_rad
        )

        half_w = screen_w / 2
        half_h = screen_h / 2

        top_center_x = (
            screen_center_x
            - down_axis_x * half_h
        )

        top_center_y = (
            screen_center_y
            - down_axis_y * half_h
        )

        bottom_center_x = (
            screen_center_x
            + down_axis_x * half_h
        )

        bottom_center_y = (
            screen_center_y
            + down_axis_y * half_h
        )

        top_right_x = (
            screen_center_x
            + width_axis_x * half_w
            - down_axis_x * half_h
        )

        top_right_y = (
            screen_center_y
            + width_axis_y * half_w
            - down_axis_y * half_h
        )

        bottom_right_x = (
            screen_center_x
            + width_axis_x * half_w
            + down_axis_x * half_h
        )

        bottom_right_y = (
            screen_center_y
            + width_axis_y * half_w
            + down_axis_y * half_h
        )

        required_space = max(
            button_size + button_gap,
            rotate_distance
            + rotate_handle_size / 2,
        )

        available_top = min(
            top_center_y,
            top_right_y,
        ) - edge_margin

        available_bottom = (
            self.height()
            - edge_margin
            - max(
                bottom_center_y,
                bottom_right_y,
            )
        )

        if available_top >= required_space:
            place_below = False
        elif available_bottom >= required_space:
            place_below = True
        else:
            place_below = (
                available_bottom
                > available_top
            )

        if place_below:
            control_corner_x = bottom_right_x
            control_corner_y = bottom_right_y

            line_anchor_x = bottom_center_x
            line_anchor_y = bottom_center_y

            rotate_center_x = (
                bottom_center_x
                + down_axis_x
                * rotate_distance
            )

            rotate_center_y = (
                bottom_center_y
                + down_axis_y
                * rotate_distance
            )

            button_y = (
                control_corner_y
                + button_gap
            )

        else:
            control_corner_x = top_right_x
            control_corner_y = top_right_y

            line_anchor_x = top_center_x
            line_anchor_y = top_center_y

            rotate_center_x = (
                top_center_x
                - down_axis_x
                * rotate_distance
            )

            rotate_center_y = (
                top_center_y
                - down_axis_y
                * rotate_distance
            )

            button_y = (
                control_corner_y
                - button_size
                - button_gap
            )

        # コピーと削除を一組として左右端へ収める
        button_group_width = (
            button_size * 2
            + button_gap
        )

        desired_group_x = (
            control_corner_x
            - button_size
        )

        maximum_group_x = max(
            edge_margin,
            self.width()
            - button_group_width
            - edge_margin,
        )

        group_x = min(
            max(
                desired_group_x,
                edge_margin,
            ),
            maximum_group_x,
        )

        copy_x = group_x

        delete_x = (
            group_x
            + button_size
            + button_gap
        )

        maximum_button_y = max(
            edge_margin,
            self.height()
            - button_size
            - edge_margin,
        )

        button_y = min(
            max(
                button_y,
                edge_margin,
            ),
            maximum_button_y,
        )

        rotate_radius = (
            rotate_handle_size / 2
        )

        rotate_center_x = min(
            max(
                rotate_center_x,
                edge_margin
                + rotate_radius,
            ),
            max(
                edge_margin
                + rotate_radius,
                self.width()
                - edge_margin
                - rotate_radius,
            ),
        )

        rotate_center_y = min(
            max(
                rotate_center_y,
                edge_margin
                + rotate_radius,
            ),
            max(
                edge_margin
                + rotate_radius,
                self.height()
                - edge_margin
                - rotate_radius,
            ),
        )

        return {
            "button_size": button_size,
            "copy_x": int(copy_x),
            "copy_y": int(button_y),
            "delete_x": int(delete_x),
            "delete_y": int(button_y),
            "rotate_handle_size": (
                rotate_handle_size
            ),
            "rotate_center_x": (
                rotate_center_x
            ),
            "rotate_center_y": (
                rotate_center_y
            ),
            "line_anchor_x": (
                line_anchor_x
            ),
            "line_anchor_y": (
                line_anchor_y
            ),
            "place_below": place_below,
        }

    def advance_selection_dash(self):
        if not self.selected_rects:
            return

        self.selection_dash_offset += 1.0

        if self.selection_dash_offset >= 14.0:
            self.selection_dash_offset = 0.0

        self.update()

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
            is_selected = (
                index in self.selected_rects
            )

            if is_selected:
                pen = QPen(
                    QColor(
                        255,
                        200,
                        0,
                    )
                )
            else:
                pen = QPen(
                    QColor(
                        255,
                        0,
                        0,
                    )
                )

            pen.setWidthF(
                2.0
            )

            painter.setPen(
                pen
            )

            angle = 0.0

            if index < len(self.rect_angles):
                angle = self.rect_angles[index]

            screen_x = x_offset + x * scale_x
            screen_y = y_offset + y * scale_y
            screen_w = w * scale_x
            screen_h = h * scale_y

            center_x = screen_x + screen_w / 2
            center_y = screen_y + screen_h / 2

            painter.save()

            painter.translate(
                center_x,
                center_y,
            )

            painter.rotate(
                angle
            )

            rect_to_draw = QRectF(
                -screen_w / 2,
                -screen_h / 2,
                screen_w,
                screen_h,
            )

            painter.drawRect(
                rect_to_draw
            )

            if is_selected:
                animated_pen = QPen(
                    QColor(
                        30,
                        30,
                        30,
                    )
                )

                animated_pen.setWidthF(
                    1.5
                )

                animated_pen.setStyle(
                    Qt.PenStyle.CustomDashLine
                )

                animated_pen.setDashPattern(
                    [
                        5.0,
                        4.0,
                    ]
                )

                animated_pen.setDashOffset(
                    self.selection_dash_offset
                )

                painter.setPen(
                    animated_pen
                )

                painter.drawRect(
                    rect_to_draw
                )

            painter.restore()

            painter.setFont(QFont("Arial", 12))

            label_width = 48
            label_height = 24

            rect_center_x = x + w / 2
            rect_center_y = y + h / 2

            rotated_label_x, rotated_label_y = self.rotate_point(
                x,
                y,
                rect_center_x,
                rect_center_y,
                angle,
            )

            label_x = int(
                x_offset + rotated_label_x * scale_x
            )

            label_y = int(
                y_offset + rotated_label_y * scale_y
            )

            # ハンドルと重なりにくいよう少し外側へずらす
            label_x -= label_width
            label_y -= label_height

            painter.fillRect(
                label_x,
                label_y,
                label_width,
                label_height,
                QColor(255, 200, 0),
            )

            painter.setPen(
                QColor(0, 0, 0)
            )

            label_text = str(
                index + 1
            )

            if index < len(
                self.rect_group_ids
            ):
                group_id = (
                    self.rect_group_ids[
                        index
                    ]
                )

                if group_id is not None:
                    group_member_indexes = [
                        member_index
                        for (
                            member_index,
                            current_group_id,
                        )
                        in enumerate(
                            self.rect_group_ids
                        )
                        if current_group_id
                        == group_id
                    ]

                    try:
                        member_position = (
                            group_member_indexes.index(
                                index
                            )
                        )
                    except ValueError:
                        member_position = 0

                    member_letter = chr(
                        ord("A")
                        + member_position
                    )

                    label_text = (
                        f"G{group_id}-"
                        f"{member_letter}"
                    )

            painter.drawText(
                label_x,
                label_y,
                label_width,
                label_height,
                Qt.AlignmentFlag.AlignCenter,
                label_text,
            )

            if index == self.selected_rect:
                handle_size = self.resize_handle_size

                center_x = x + w / 2
                center_y = y + h / 2

                for hx, hy in self.resize_handles(x, y, w, h).values():
                    rotated_hx, rotated_hy = self.rotate_point(
                        hx,
                        hy,
                        center_x,
                        center_y,
                        angle,
                    )

                    handle_x = int(
                        x_offset + rotated_hx * scale_x
                    ) - handle_size // 2

                    handle_y = int(
                        y_offset + rotated_hy * scale_y
                    ) - handle_size // 2

                    painter.fillRect(
                        handle_x,
                        handle_y,
                        handle_size,
                        handle_size,
                        QColor(255, 200, 0),
                    )

                controls = (
                    self.operation_control_geometry(
                        x,
                        y,
                        w,
                        h,
                        angle,
                        x_offset,
                        y_offset,
                        scale_x,
                        scale_y,
                    )
                )

                button_size = controls[
                    "button_size"
                ]

                copy_x = controls[
                    "copy_x"
                ]

                copy_y = controls[
                    "copy_y"
                ]

                delete_x = controls[
                    "delete_x"
                ]

                delete_y = controls[
                    "delete_y"
                ]

                # ---------------------------------
                # 削除ボタン
                # ---------------------------------
                painter.fillRect(
                    delete_x,
                    delete_y,
                    button_size,
                    button_size,
                    QColor(220, 60, 60),
                )

                painter.setPen(
                    QColor(255, 255, 255)
                )

                painter.drawText(
                    delete_x,
                    delete_y,
                    button_size,
                    button_size,
                    Qt.AlignmentFlag.AlignCenter,
                    "×",
                )

                # ---------------------------------
                # コピーボタン
                # ---------------------------------
                painter.fillRect(
                    copy_x,
                    copy_y,
                    button_size,
                    button_size,
                    QColor(70, 120, 220),
                )

                painter.setPen(
                    QColor(255, 255, 255)
                )

                painter.drawText(
                    copy_x,
                    copy_y,
                    button_size,
                    button_size,
                    Qt.AlignmentFlag.AlignCenter,
                    "⧉",
                )

                # ---------------------------------
                # 回転ハンドル
                # ---------------------------------
                rotate_handle_size = controls[
                    "rotate_handle_size"
                ]

                rotate_center_x = controls[
                    "rotate_center_x"
                ]

                rotate_center_y = controls[
                    "rotate_center_y"
                ]

                line_anchor_x = controls[
                    "line_anchor_x"
                ]

                line_anchor_y = controls[
                    "line_anchor_y"
                ]

                rotate_x = int(
                    rotate_center_x
                    - rotate_handle_size / 2
                )

                rotate_y = int(
                    rotate_center_y
                    - rotate_handle_size / 2
                )

                painter.setPen(
                    QColor(0, 0, 0)
                )

                painter.drawLine(
                    int(line_anchor_x),
                    int(line_anchor_y),
                    int(rotate_center_x),
                    int(rotate_center_y),
                )

                painter.setBrush(
                    QColor(255, 200, 0)
                )

                painter.drawEllipse(
                    rotate_x,
                    rotate_y,
                    rotate_handle_size,
                    rotate_handle_size,
                )

                painter.setBrush(
                    Qt.BrushStyle.NoBrush
                )

                # ---------------------------------
                # 回転角度表示
                # ---------------------------------
                angle_label_width = 80
                angle_label_height = 24
                edge_margin = 4

                angle_label_x = (
                    rotate_x + 24
                )

                # 右側に表示できない場合は
                # 回転ハンドルの左側へ表示
                if (
                    angle_label_x
                    + angle_label_width
                    > self.width() - edge_margin
                ):
                    angle_label_x = (
                        rotate_x
                        - angle_label_width
                        - 6
                    )

                angle_label_x = max(
                    edge_margin,
                    min(
                        angle_label_x,
                        self.width()
                        - angle_label_width
                        - edge_margin,
                    ),
                )

                angle_label_y = max(
                    edge_margin,
                    min(
                        rotate_y,
                        self.height()
                        - angle_label_height
                        - edge_margin,
                    ),
                )

                painter.setPen(
                    QColor(255, 200, 0)
                )

                painter.drawText(
                    int(angle_label_x),
                    int(angle_label_y),
                    angle_label_width,
                    angle_label_height,
                    Qt.AlignmentFlag.AlignVCenter,
                    f"{angle:.1f}°",
                )

    def mouseDoubleClickEvent(self, event):
        if self.pixmap is None:
            return

        if self.selected_rect < 0:
            return

        if self.selected_rect >= len(
            self.rects
        ):
            return

        if event.button() != Qt.MouseButton.LeftButton:
            return

        info = self.image_display_info()

        if info is None:
            return

        (
            _,
            x_offset,
            y_offset,
            scale_x,
            scale_y,
        ) = info

        pos = event.position()

        x, y, w, h = self.rects[
            self.selected_rect
        ]

        angle = 0.0

        if self.selected_rect < len(
            self.rect_angles
        ):
            angle = self.rect_angles[
                self.selected_rect
            ]

        controls = (
            self.operation_control_geometry(
                x,
                y,
                w,
                h,
                angle,
                x_offset,
                y_offset,
                scale_x,
                scale_y,
            )
        )

        rotate_handle_size = controls[
            "rotate_handle_size"
        ]

        rotate_hit_margin = 14

        rotate_center_x = controls[
            "rotate_center_x"
        ]

        rotate_center_y = controls[
            "rotate_center_y"
        ]

        rotate_x = (
            rotate_center_x
            - rotate_handle_size / 2
        )

        rotate_y = (
            rotate_center_y
            - rotate_handle_size / 2
        )

        if (
            rotate_x - rotate_hit_margin
            <= pos.x()
            <= rotate_x
            + rotate_handle_size
            + rotate_hit_margin
            and
            rotate_y - rotate_hit_margin
            <= pos.y()
            <= rotate_y
            + rotate_handle_size
            + rotate_hit_margin
        ):
            self.save_undo_state()

            while len(
                self.rect_angles
            ) < len(
                self.rects
            ):
                self.rect_angles.append(
                    0.0
                )

            self.rect_angles[
                self.selected_rect
            ] = 0.0

            self.rotating = False

            self.rects_changed.emit()
            self.update()

            event.accept()
            return

    def select_rect_at_context_position(
        self,
        pos,
    ):
        if self.pixmap is None:
            return

        info = self.image_display_info()

        if info is None:
            return

        (
            _,
            x_offset,
            y_offset,
            scale_x,
            scale_y,
        ) = info

        image_x = (
            pos.x() - x_offset
        ) / scale_x

        image_y = (
            pos.y() - y_offset
        ) / scale_y

        # 後から作った枠を優先する
        for index in range(
            len(self.rects) - 1,
            -1,
            -1,
        ):
            x, y, w, h = self.rects[
                index
            ]

            angle = 0.0

            if index < len(
                self.rect_angles
            ):
                angle = self.rect_angles[
                    index
                ]

            center_x = x + w / 2
            center_y = y + h / 2

            local_x, local_y = (
                self.rotate_point(
                    image_x,
                    image_y,
                    center_x,
                    center_y,
                    -angle,
                )
            )

            inside_rect = (
                x <= local_x <= x + w
                and
                y <= local_y <= y + h
            )

            if not inside_rect:
                continue

            # すでに複数選択されている枠の
            # ひとつを右クリックした場合は、
            # 現在の複数選択を維持する。
            if (
                index in self.selected_rects
                and len(self.selected_rects) > 1
            ):
                self.selected_rect = index

                self.selected_rect_changed.emit(
                    self.selected_rect
                )

                self.update()
                return

            group_id = None

            if index < len(
                self.rect_group_ids
            ):
                group_id = (
                    self.rect_group_ids[
                        index
                    ]
                )

            if (
                group_id is not None
                and not self.composite_member_edit_mode
            ):
                self.selected_rects = {
                    group_index
                    for (
                        group_index,
                        current_group_id,
                    )
                    in enumerate(
                        self.rect_group_ids
                    )
                    if current_group_id
                    == group_id
                }
            else:
                self.selected_rects = {
                    index
                }

            self.selected_rect = index

            self.selected_rect_changed.emit(
                self.selected_rect
            )

            self.update()
            return
    def show_context_menu(self, global_pos):
        menu = QMenu(self)

        has_selection = bool(
            self.selected_rects
        ) or (
            0 <= self.selected_rect
            < len(self.rects)
        )

        selected_indexes = set(
            self.selected_rects
        )

        if (
            not selected_indexes
            and 0 <= self.selected_rect
            < len(self.rects)
        ):
            selected_indexes.add(
                self.selected_rect
            )

        can_group = (
            len(selected_indexes) >= 2
        )

        can_ungroup = False

        if (
            0 <= self.selected_rect
            < len(self.rect_group_ids)
        ):
            can_ungroup = (
                self.rect_group_ids[
                    self.selected_rect
                ]
                is not None
            )

        undo_action = menu.addAction(
            "元に戻す\tCtrl+Z"
        )
        undo_action.setEnabled(
            bool(self.undo_stack)
        )

        redo_action = menu.addAction(
            "やり直す\tCtrl+Y"
        )
        redo_action.setEnabled(
            bool(self.redo_stack)
        )

        menu.addSeparator()

        cut_action = menu.addAction(
            "切り取り\tCtrl+X"
        )
        cut_action.setEnabled(
            has_selection
        )

        copy_action = menu.addAction(
            "コピー\tCtrl+C"
        )
        copy_action.setEnabled(
            has_selection
        )

        paste_action = menu.addAction(
            "貼り付け\tCtrl+V"
        )
        paste_action.setEnabled(
            bool(self.copied_rects)
        )

        delete_action = menu.addAction(
            "削除\tDelete"
        )
        delete_action.setEnabled(
            has_selection
        )

        menu.addSeparator()

        select_all_action = menu.addAction(
            "すべて選択\tCtrl+A"
        )
        select_all_action.setEnabled(
            bool(self.rects)
        )

        menu.addSeparator()

        group_action = menu.addAction(
            "複合枠にまとめる\tCtrl+G"
        )
        group_action.setEnabled(
            can_group
        )

        ungroup_action = menu.addAction(
            "複合枠を解除\tCtrl+Shift+G"
        )
        ungroup_action.setEnabled(
            can_ungroup
        )

        selected_action = menu.exec(
            global_pos
        )

        if selected_action is None:
            return

        if selected_action == undo_action:
            self.undo()
            return

        if selected_action == redo_action:
            self.redo()
            return

        if selected_action == cut_action:
            key_event = QKeyEvent(
                QKeyEvent.Type.KeyPress,
                Qt.Key.Key_X,
                Qt.KeyboardModifier.ControlModifier,
            )
            self.keyPressEvent(key_event)
            return

        if selected_action == copy_action:
            key_event = QKeyEvent(
                QKeyEvent.Type.KeyPress,
                Qt.Key.Key_C,
                Qt.KeyboardModifier.ControlModifier,
            )
            self.keyPressEvent(key_event)
            return

        if selected_action == paste_action:
            self.paste_copied_rects(
                offset=30,
                save_undo=True,
            )
            return

        if selected_action == delete_action:
            key_event = QKeyEvent(
                QKeyEvent.Type.KeyPress,
                Qt.Key.Key_Delete,
                Qt.KeyboardModifier.NoModifier,
            )
            self.keyPressEvent(key_event)
            return

        if selected_action == select_all_action:
            key_event = QKeyEvent(
                QKeyEvent.Type.KeyPress,
                Qt.Key.Key_A,
                Qt.KeyboardModifier.ControlModifier,
            )
            self.keyPressEvent(key_event)
            return

        if selected_action == group_action:
            self.group_selected_rects()
            return

        if selected_action == ungroup_action:
            self.ungroup_selected_rect()
            return

    def mousePressEvent(self, event):
        # ---------------------------------
        # パン開始
        # 中ボタン または Space + 左ドラッグ
        # ---------------------------------
        middle_pan = (
            event.button()
            == Qt.MouseButton.MiddleButton
        )

        space_left_pan = (
            self.space_pressed
            and event.button()
            == Qt.MouseButton.LeftButton
        )

        if middle_pan or space_left_pan:
            self.panning = True
            self.last_pan_pos = (
                event.position()
            )

            self.space_pan_dragging = (
                space_left_pan
            )

            self.setCursor(
                Qt.CursorShape.ClosedHandCursor
            )

            event.accept()
            return

        # 右クリックでコンテキストメニュー
        if event.button() == Qt.MouseButton.RightButton:
            self.select_rect_at_context_position(
                event.position()
            )

            self.show_context_menu(
                event.globalPosition().toPoint()
            )

            event.accept()
            return

        # 左クリック以外では枠を操作しない
        if event.button() != Qt.MouseButton.LeftButton:
            return

        if self.pixmap is None:
            return

        info = self.image_display_info()

        if info is None:
            return

        _, x_offset, y_offset, scale_x, scale_y = info

        pos = event.position()

        image_x = (
            pos.x() - x_offset
        ) / scale_x

        image_y = (
            pos.y() - y_offset
        ) / scale_y

        # -------------------------------------------------
        # 1. 選択中の枠に表示している操作部品を判定
        # -------------------------------------------------
        if (
            self.selected_rect >= 0
            and self.selected_rect < len(self.rects)
        ):
            x, y, w, h = self.rects[
                self.selected_rect
            ]

            angle = 0.0

            if self.selected_rect < len(
                self.rect_angles
            ):
                angle = self.rect_angles[
                    self.selected_rect
                ]

            controls = (
                self.operation_control_geometry(
                    x,
                    y,
                    w,
                    h,
                    angle,
                    x_offset,
                    y_offset,
                    scale_x,
                    scale_y,
                )
            )

            button_size = controls[
                "button_size"
            ]

            copy_x = controls[
                "copy_x"
            ]

            copy_y = controls[
                "copy_y"
            ]

            delete_x = controls[
                "delete_x"
            ]

            delete_y = controls[
                "delete_y"
            ]

            # ---------------------------------------------
            # コピーボタン
            # ---------------------------------------------
            if (
                copy_x
                <= pos.x()
                <= copy_x + button_size
                and copy_y
                <= pos.y()
                <= copy_y + button_size
            ):
                self.save_undo_state()

                offset = 30

                copied_rect = (
                    x + offset,
                    y + offset,
                    w,
                    h,
                )

                self.rects.append(
                    copied_rect
                )

                # コピー元の回転角度もコピーする
                self.rect_angles.append(
                    angle
                )

                copied_mode = "free"

                if (
                    self.selected_rect
                    < len(self.rect_aspect_modes)
                ):
                    copied_mode = (
                        self.rect_aspect_modes[
                            self.selected_rect
                        ]
                    )

                self.rect_aspect_modes.append(
                    copied_mode
                )

                self.rect_group_ids.append(
                    None
                )

                self.selected_rect = (
                    len(self.rects) - 1
                )

                self.selected_rects = {
                    self.selected_rect
                }

                self.dragging = False
                self.adding_rect = False
                self.resizing = False
                self.rotating = False

                self.rects_changed.emit()
                self.update()
                return

            # ---------------------------------------------
            # 削除ボタン
            # ---------------------------------------------
            if (
                delete_x
                <= pos.x()
                <= delete_x + button_size
                and delete_y
                <= pos.y()
                <= delete_y + button_size
            ):
                self.save_undo_state()

                delete_indexes = set(
                    self.selected_rects
                )

                # 念のため単一選択状態にも対応
                if not delete_indexes:
                    delete_indexes.add(
                        self.selected_rect
                    )

                # インデックスずれを防ぐため、
                # 大きい番号から削除する
                for delete_index in sorted(
                    delete_indexes,
                    reverse=True,
                ):
                    if (
                        delete_index < 0
                        or delete_index >= len(self.rects)
                    ):
                        continue

                    del self.rects[
                        delete_index
                    ]

                    if delete_index < len(
                        self.rect_angles
                    ):
                        del self.rect_angles[
                            delete_index
                        ]

                    if delete_index < len(
                        self.rect_aspect_modes
                    ):
                        del self.rect_aspect_modes[
                            delete_index
                        ]

                    if delete_index < len(
                        self.rect_group_ids
                    ):
                        del self.rect_group_ids[
                            delete_index
                        ]

                self.normalize_singleton_groups()

                self.selected_rect = -1
                self.selected_rects.clear()
                self.dragging = False
                self.adding_rect = False
                self.resizing = False
                self.rotating = False

                self.rects_changed.emit()
                self.update()
                return

            # ---------------------------------------------
            # 回転ハンドル
            # ---------------------------------------------
            rotate_handle_size = controls[
                "rotate_handle_size"
            ]

            rotate_hit_margin = 14

            rotate_center_x = controls[
                "rotate_center_x"
            ]

            rotate_center_y = controls[
                "rotate_center_y"
            ]

            rotate_x = (
                rotate_center_x
                - rotate_handle_size / 2
            )

            rotate_y = (
                rotate_center_y
                - rotate_handle_size / 2
            )

            if (
                rotate_x - rotate_hit_margin
                <= pos.x()
                <= rotate_x
                + rotate_handle_size
                + rotate_hit_margin
                and
                rotate_y - rotate_hit_margin
                <= pos.y()
                <= rotate_y
                + rotate_handle_size
                + rotate_hit_margin
            ):
                self.save_undo_state()

                self.rotating = True

                self.rotation_handle_below = bool(
                    controls.get(
                        "place_below",
                        False,
                    )
                )

                # ---------------------------------
                # 回転開始時の状態を保存
                # ---------------------------------
                center_x = x + w / 2
                center_y = y + h / 2

                start_dx = (
                    image_x - center_x
                )

                start_dy = (
                    image_y - center_y
                )

                self.rotation_start_pointer_angle = (
                    math.degrees(
                        math.atan2(
                            start_dy,
                            start_dx,
                        )
                    )
                )

                self.rotation_start_rect_angle = angle

                self.dragging = False
                self.adding_rect = False
                self.resizing = False

                event.accept()
                return

        # -------------------------------------------------
        # 2. 画像の表示範囲外なら何もしない
        # -------------------------------------------------
        if (
            image_x < 0
            or image_y < 0
            or image_x > self.pixmap.width()
            or image_y > self.pixmap.height()
        ):
            return

        # -------------------------------------------------
        # 3. 選択中の枠のリサイズハンドルを判定
        # -------------------------------------------------
        if (
            self.selected_rect >= 0
            and self.selected_rect < len(self.rects)
        ):
            x, y, w, h = self.rects[
                self.selected_rect
            ]

            angle = 0.0

            if self.selected_rect < len(
                self.rect_angles
            ):
                angle = self.rect_angles[
                    self.selected_rect
                ]

            center_x = x + w / 2
            center_y = y + h / 2

            handle_hit_size = 8

            handles = self.resize_handles(
                x,
                y,
                w,
                h,
            )

            for (
                handle_name,
                (handle_x, handle_y),
            ) in handles.items():
                (
                    rotated_handle_x,
                    rotated_handle_y,
                ) = self.rotate_point(
                    handle_x,
                    handle_y,
                    center_x,
                    center_y,
                    angle,
                )

                handle_screen_x = (
                    x_offset
                    + rotated_handle_x
                    * scale_x
                )

                handle_screen_y = (
                    y_offset
                    + rotated_handle_y
                    * scale_y
                )

                if (
                    handle_screen_x
                    - handle_hit_size
                    <= pos.x()
                    <= handle_screen_x
                    + handle_hit_size
                    and
                    handle_screen_y
                    - handle_hit_size
                    <= pos.y()
                    <= handle_screen_y
                    + handle_hit_size
                ):
                    self.save_undo_state()

                    self.resizing = True
                    self.resize_handle = (
                        handle_name
                    )

                    self.resize_start_rect = tuple(
                        self.rects[
                            self.selected_rect
                        ]
                    )

                    self.dragging = False
                    self.adding_rect = False
                    self.rotating = False

                    self.last_image_x = (
                        image_x
                    )

                    self.last_image_y = (
                        image_y
                    )

                    return

        # -------------------------------------------------
        # 4. 既存の枠をクリックしたか判定
        #    後から作った枠を優先する
        # -------------------------------------------------
        for index in range(
            len(self.rects) - 1,
            -1,
            -1,
        ):
            x, y, w, h = self.rects[
                index
            ]

            # 枠本体の内側
            inside_rect = (
                x <= image_x <= x + w
                and
                y <= image_y <= y + h
            )

            # 番号ラベル付近
            label_width = (
                28 / scale_x
            )

            label_height = (
                24 / scale_y
            )

            inside_label = (
                x
                <= image_x
                <= x + label_width
                and
                y
                <= image_y
                <= y + label_height
            )

            if inside_rect or inside_label:
                ctrl_pressed = bool(
                    event.modifiers()
                    & Qt.KeyboardModifier.ControlModifier
                )

                if ctrl_pressed:
                    # Ctrl + クリックでは選択を追加／解除する
                    if index in self.selected_rects:
                        self.selected_rects.remove(index)

                        if index == self.selected_rect:
                            if self.selected_rects:
                                self.selected_rect = max(
                                    self.selected_rects
                                )
                            else:
                                self.selected_rect = -1
                    else:
                        self.selected_rects.add(index)
                        self.selected_rect = index

                else:
                    group_id = None

                    if index < len(
                        self.rect_group_ids
                    ):
                        group_id = (
                            self.rect_group_ids[
                                index
                            ]
                        )

                    if group_id is not None:
                        if self.composite_member_edit_mode:
                            # 構成領域編集モードでは、
                            # クリックした1領域だけ選択する
                            self.selected_rects = {
                                index
                            }

                            self.selected_rect = index

                        else:
                            # 通常時は複合枠全体を選択する
                            self.selected_rects = {
                                group_index
                                for (
                                    group_index,
                                    current_group_id,
                                )
                                in enumerate(
                                    self.rect_group_ids
                                )
                                if current_group_id
                                == group_id
                            }

                            self.selected_rect = index

                    elif (
                        index in self.selected_rects
                        and len(self.selected_rects) > 1
                    ):
                        # 通常の複数選択済み枠は、
                        # ドラッグ開始時には選択を維持する
                        self.selected_rect = index

                    else:
                        # 独立した通常枠は単一選択
                        self.selected_rects = {
                            index
                        }
                        self.selected_rect = index

                if self.selected_rect >= 0:
                    self.selected_rect_changed.emit(
                        self.selected_rect
                    )

                # Ctrlクリックは選択だけ行い、
                # そのままドラッグ移動は開始しない
                self.dragging = not ctrl_pressed

                self.drag_undo_saved = False
                self.adding_rect = False
                self.resizing = False
                self.rotating = False

                self.last_image_x = (
                    image_x
                )

                self.last_image_y = (
                    image_y
                )

                self.update()
                return

        # -------------------------------------------------
        # 5. 既存枠に当たらなければ新規枠を作成
        # -------------------------------------------------
        self.save_undo_state()

        self.adding_rect = True
        self.dragging = False
        self.resizing = False
        self.rotating = False

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

        # 新しい枠は必ず0度から開始
        self.rect_angles.append(
            0.0
        )

        # 作成時の縦横比モードを記録
        self.rect_aspect_modes.append(
            str(self.aspect_ratio_mode)
        )

        # 新規枠は独立した通常枠として開始
        self.rect_group_ids.append(
            None
        )

        self.selected_rect = (
            len(self.rects) - 1
        )

        self.selected_rects = {
            self.selected_rect
        }

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
        
        # 回転ハンドルをドラッグ中
        if self.rotating and self.selected_rect >= 0:
            info = self.image_display_info()

            if info is None:
                return

            _, x_offset, y_offset, scale_x, scale_y = info

            pos = event.position()

            image_x = (
                pos.x() - x_offset
            ) / scale_x

            image_y = (
                pos.y() - y_offset
            ) / scale_y

            x, y, w, h = self.rects[
                self.selected_rect
            ]

            center_x = x + w / 2
            center_y = y + h / 2

            dx = image_x - center_x
            dy = image_y - center_y

            pointer_angle = math.degrees(
                math.atan2(dy, dx)
            )

            if (
                self.rotation_start_pointer_angle
                is None
            ):
                self.rotation_start_pointer_angle = (
                    pointer_angle
                )

            # ---------------------------------
            # 回転開始位置からの角度差
            # ---------------------------------
            angle_delta = (
                pointer_angle
                - self.rotation_start_pointer_angle
            )

            # -180～180度の最短方向へ補正
            angle_delta = (
                (angle_delta + 180.0)
                % 360.0
            ) - 180.0

            # Shift押下中はさらに細かく回転
            shift_pressed = bool(
                event.modifiers()
                & Qt.KeyboardModifier.ShiftModifier
            )

            if shift_pressed:
                sensitivity = (
                    self.rotation_fine_sensitivity
                )
            else:
                sensitivity = (
                    self.rotation_sensitivity
                )

            angle = (
                self.rotation_start_rect_angle
                + angle_delta * sensitivity
            )

            # -180～180度に収める
            angle = (
                (angle + 180.0) % 360.0
            ) - 180.0

            while len(self.rect_angles) < len(self.rects):
                self.rect_angles.append(0.0)

            self.rect_angles[
                self.selected_rect
            ] = angle

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

            if self.resize_start_rect is not None:
                start_x, start_y, start_w, start_h = (
                    self.resize_start_rect
                )
            else:
                start_x, start_y, start_w, start_h = (
                    x, y, w, h
                )

            shift_pressed = bool(
                event.modifiers()
                & Qt.KeyboardModifier.ShiftModifier
            )

            if shift_pressed:
                active_aspect_ratio = (
                    start_w / start_h
                    if start_h > 0
                    else None
                )
            else:
                active_aspect_ratio = (
                    self.get_active_aspect_ratio(
                        start_w,
                        start_h,
                    )
                )

            corner_aspect_ratio = (
                active_aspect_ratio
            )

            edge_aspect_ratio = (
                active_aspect_ratio
            )

            keep_aspect_ratio = (
                active_aspect_ratio
                is not None
            )

            left = x
            top = y
            right = x + w
            bottom = y + h

            if self.resize_handle == "top":
                angle = 0.0

                if self.selected_rect < len(self.rect_angles):
                    angle = self.rect_angles[
                        self.selected_rect
                    ]

                start_center_x = (
                    start_x + start_w / 2
                )

                start_center_y = (
                    start_y + start_h / 2
                )

                local_mouse_x, local_mouse_y = self.rotate_point(
                    image_x,
                    image_y,
                    start_center_x,
                    start_center_y,
                    -angle,
                )

                left = start_x
                top = local_mouse_y
                right = start_x + start_w
                bottom = start_y + start_h

            if self.resize_handle == "top_left":
                angle = 0.0

                if self.selected_rect < len(self.rect_angles):
                    angle = self.rect_angles[
                        self.selected_rect
                    ]

                start_center_x = (
                    start_x + start_w / 2
                )

                start_center_y = (
                    start_y + start_h / 2
                )

                local_mouse_x, local_mouse_y = self.rotate_point(
                    image_x,
                    image_y,
                    start_center_x,
                    start_center_y,
                    -angle,
                )

                left = local_mouse_x
                top = local_mouse_y
                right = start_x + start_w
                bottom = start_y + start_h

            if self.resize_handle == "left":
                angle = 0.0

                if self.selected_rect < len(self.rect_angles):
                    angle = self.rect_angles[
                        self.selected_rect
                    ]

                start_center_x = (
                    start_x + start_w / 2
                )

                start_center_y = (
                    start_y + start_h / 2
                )

                local_mouse_x, local_mouse_y = self.rotate_point(
                    image_x,
                    image_y,
                    start_center_x,
                    start_center_y,
                    -angle,
                )

                left = local_mouse_x
                top = start_y
                right = start_x + start_w
                bottom = start_y + start_h       

            if self.resize_handle == "right":
                angle = 0.0

                if self.selected_rect < len(self.rect_angles):
                    angle = self.rect_angles[
                        self.selected_rect
                    ]

                start_center_x = (
                    start_x + start_w / 2
                )

                start_center_y = (
                    start_y + start_h / 2
                )

                local_mouse_x, local_mouse_y = self.rotate_point(
                    image_x,
                    image_y,
                    start_center_x,
                    start_center_y,
                    -angle,
                )

                left = start_x
                top = start_y
                right = local_mouse_x
                bottom = start_y + start_h

            if self.resize_handle == "top_right":
                angle = 0.0

                if self.selected_rect < len(self.rect_angles):
                    angle = self.rect_angles[
                        self.selected_rect
                    ]

                start_center_x = (
                    start_x + start_w / 2
                )

                start_center_y = (
                    start_y + start_h / 2
                )

                local_mouse_x, local_mouse_y = self.rotate_point(
                    image_x,
                    image_y,
                    start_center_x,
                    start_center_y,
                    -angle,
                )

                left = start_x
                top = local_mouse_y
                right = local_mouse_x
                bottom = start_y + start_h

            if self.resize_handle == "bottom_right":
                angle = 0.0

                if self.selected_rect < len(self.rect_angles):
                    angle = self.rect_angles[
                        self.selected_rect
                    ]

                start_center_x = (
                    start_x + start_w / 2
                )

                start_center_y = (
                    start_y + start_h / 2
                )

                local_mouse_x, local_mouse_y = self.rotate_point(
                    image_x,
                    image_y,
                    start_center_x,
                    start_center_y,
                    -angle,
                )

                left = start_x
                top = start_y
                right = local_mouse_x
                bottom = local_mouse_y

            if self.resize_handle == "bottom_left":
                angle = 0.0

                if self.selected_rect < len(self.rect_angles):
                    angle = self.rect_angles[
                        self.selected_rect
                    ]

                start_center_x = (
                    start_x + start_w / 2
                )

                start_center_y = (
                    start_y + start_h / 2
                )

                local_mouse_x, local_mouse_y = self.rotate_point(
                    image_x,
                    image_y,
                    start_center_x,
                    start_center_y,
                    -angle,
                )

                left = local_mouse_x
                top = start_y
                right = start_x + start_w
                bottom = local_mouse_y

            if self.resize_handle == "bottom":
                angle = 0.0

                if self.selected_rect < len(self.rect_angles):
                    angle = self.rect_angles[
                        self.selected_rect
                    ]

                start_center_x = (
                    start_x + start_w / 2
                )

                start_center_y = (
                    start_y + start_h / 2
                )

                local_mouse_x, local_mouse_y = self.rotate_point(
                    image_x,
                    image_y,
                    start_center_x,
                    start_center_y,
                    -angle,
                )

                left = start_x
                top = start_y
                right = start_x + start_w
                bottom = local_mouse_y

            corner_handles = {
                "top_left",
                "top_right",
                "bottom_right",
                "bottom_left",
            }

            edge_handles = {
                "top",
                "right",
                "bottom",
                "left",
            }

            if (
                corner_aspect_ratio is not None
                and self.resize_handle
                in corner_handles
            ):
                locked_rect = (
                    self.aspect_locked_corner_rect(
                        self.resize_handle,
                        local_mouse_x,
                        local_mouse_y,
                        start_x,
                        start_y,
                        start_w,
                        start_h,
                        corner_aspect_ratio,
                    )
                )

                if locked_rect is None:
                    return

                (
                    left,
                    top,
                    right,
                    bottom,
                ) = locked_rect

            if right - left < 5:
                return

            if (
                edge_aspect_ratio is not None
                and self.resize_handle
                in edge_handles
            ):
                angle = 0.0

                if self.selected_rect < len(
                    self.rect_angles
                ):
                    angle = self.rect_angles[
                        self.selected_rect
                    ]

                locked_rect = (
                    self.aspect_locked_edge_rect(
                        self.resize_handle,
                        local_mouse_x,
                        local_mouse_y,
                        start_x,
                        start_y,
                        start_w,
                        start_h,
                        angle,
                        edge_aspect_ratio,
                    )
                )

                if locked_rect is None:
                    return

                (
                    left,
                    top,
                    right,
                    bottom,
                ) = locked_rect

            if bottom - top < 5:
                return
            
            # 回転枠の右中央ハンドルを動かした場合、
            # ドラッグ開始時の左辺を固定して中心位置を補正する
            if (
                self.resize_handle == "right"
                and not keep_aspect_ratio
            ):
                old_center_x = (
                    start_x + start_w / 2
                )

                old_center_y = (
                    start_y + start_h / 2
                )

                new_w = right - left

                width_change = (
                    new_w - start_w
                )

                angle = 0.0

                if self.selected_rect < len(self.rect_angles):
                    angle = self.rect_angles[
                        self.selected_rect
                    ]

                angle_rad = math.radians(angle)

                center_shift = width_change / 2

                new_center_x = (
                    old_center_x
                    + math.cos(angle_rad) * center_shift
                )

                new_center_y = (
                    old_center_y
                    + math.sin(angle_rad) * center_shift
                )

                left = new_center_x - new_w / 2
                right = new_center_x + new_w / 2

                top = new_center_y - start_h / 2
                bottom = new_center_y + start_h / 2

            # 回転枠の左中央ハンドルを動かした場合、
            # ドラッグ開始時の右辺を固定して中心位置を補正する
            if (
                self.resize_handle == "left"
                and not keep_aspect_ratio
            ):
                old_center_x = (
                    start_x + start_w / 2
                )

                old_center_y = (
                    start_y + start_h / 2
                )

                new_w = right - left

                width_change = (
                    new_w - start_w
                )

                angle = 0.0

                if self.selected_rect < len(self.rect_angles):
                    angle = self.rect_angles[
                        self.selected_rect
                    ]

                angle_rad = math.radians(angle)

                center_shift = width_change / 2

                new_center_x = (
                    old_center_x
                    - math.cos(angle_rad) * center_shift
                )

                new_center_y = (
                    old_center_y
                    - math.sin(angle_rad) * center_shift
                )

                left = new_center_x - new_w / 2
                right = new_center_x + new_w / 2

                top = new_center_y - start_h / 2
                bottom = new_center_y + start_h / 2     

            # 回転枠の上中央ハンドルを動かした場合、
            # ドラッグ開始時の下辺を固定して中心位置を補正する
            if (
                self.resize_handle == "top"
                and not keep_aspect_ratio
            ):
                old_center_x = (
                    start_x + start_w / 2
                )

                old_center_y = (
                    start_y + start_h / 2
                )

                new_h = bottom - top

                height_change = (
                    new_h - start_h
                )

                angle = 0.0

                if self.selected_rect < len(self.rect_angles):
                    angle = self.rect_angles[
                        self.selected_rect
                    ]

                angle_rad = math.radians(angle)

                center_shift = height_change / 2

                new_center_x = (
                    old_center_x
                    + math.sin(angle_rad) * center_shift
                )

                new_center_y = (
                    old_center_y
                    - math.cos(angle_rad) * center_shift
                )

                left = new_center_x - start_w / 2
                right = new_center_x + start_w / 2

                top = new_center_y - new_h / 2
                bottom = new_center_y + new_h / 2



            # 回転枠の下中央ハンドルを動かした場合、
            # ドラッグ開始時の上辺を固定して中心位置を補正する
            if (
                self.resize_handle == "bottom"
                and not keep_aspect_ratio
            ):
                old_center_x = (
                    start_x + start_w / 2
                )

                old_center_y = (
                    start_y + start_h / 2
                )

                new_h = bottom - top

                height_change = (
                    new_h - start_h
                )

                angle = 0.0

                if self.selected_rect < len(self.rect_angles):
                    angle = self.rect_angles[
                        self.selected_rect
                    ]

                angle_rad = math.radians(angle)

                center_shift = height_change / 2

                new_center_x = (
                    old_center_x
                    - math.sin(angle_rad) * center_shift
                )

                new_center_y = (
                    old_center_y
                    + math.cos(angle_rad) * center_shift
                )

                left = new_center_x - start_w / 2
                right = new_center_x + start_w / 2

                top = new_center_y - new_h / 2
                bottom = new_center_y + new_h / 2

            # 回転枠の左上ハンドルを動かした場合、
            # ドラッグ開始時の右下を固定して中心位置を補正する
            if self.resize_handle == "top_left":
                new_w = right - left
                new_h = bottom - top

                angle = 0.0

                if self.selected_rect < len(self.rect_angles):
                    angle = self.rect_angles[
                        self.selected_rect
                    ]

                start_center_x = (
                    start_x + start_w / 2
                )

                start_center_y = (
                    start_y + start_h / 2
                )

                local_shift_x = (
                    (new_w - start_w) / 2
                )

                local_shift_y = (
                    (new_h - start_h) / 2
                )

                angle_rad = math.radians(angle)

                global_shift_x = (
                    -local_shift_x * math.cos(angle_rad)
                    + local_shift_y * math.sin(angle_rad)
                )

                global_shift_y = (
                    -local_shift_x * math.sin(angle_rad)
                    - local_shift_y * math.cos(angle_rad)
                )

                new_center_x = (
                    start_center_x + global_shift_x
                )

                new_center_y = (
                    start_center_y + global_shift_y
                )

                left = new_center_x - new_w / 2
                right = new_center_x + new_w / 2

                top = new_center_y - new_h / 2
                bottom = new_center_y + new_h / 2                

            # 回転枠の右上ハンドルを動かした場合、
            # ドラッグ開始時の左下を固定して中心位置を補正する
            if self.resize_handle == "top_right":
                new_w = right - left
                new_h = bottom - top

                angle = 0.0

                if self.selected_rect < len(self.rect_angles):
                    angle = self.rect_angles[
                        self.selected_rect
                    ]

                start_center_x = (
                    start_x + start_w / 2
                )

                start_center_y = (
                    start_y + start_h / 2
                )

                local_shift_x = (
                    (new_w - start_w) / 2
                )

                local_shift_y = (
                    (new_h - start_h) / 2
                )

                angle_rad = math.radians(angle)

                global_shift_x = (
                    local_shift_x * math.cos(angle_rad)
                    + local_shift_y * math.sin(angle_rad)
                )

                global_shift_y = (
                    local_shift_x * math.sin(angle_rad)
                    - local_shift_y * math.cos(angle_rad)
                )

                new_center_x = (
                    start_center_x + global_shift_x
                )

                new_center_y = (
                    start_center_y + global_shift_y
                )

                left = new_center_x - new_w / 2
                right = new_center_x + new_w / 2

                top = new_center_y - new_h / 2
                bottom = new_center_y + new_h / 2

            # 回転枠の右下ハンドルを動かした場合、
            # ドラッグ開始時の左上を固定して中心位置を補正する
            if self.resize_handle == "bottom_right":
                new_w = right - left
                new_h = bottom - top

                angle = 0.0

                if self.selected_rect < len(self.rect_angles):
                    angle = self.rect_angles[
                        self.selected_rect
                    ]

                start_center_x = (
                    start_x + start_w / 2
                )

                start_center_y = (
                    start_y + start_h / 2
                )

                local_shift_x = (
                    (new_w - start_w) / 2
                )

                local_shift_y = (
                    (new_h - start_h) / 2
                )

                angle_rad = math.radians(angle)

                global_shift_x = (
                    local_shift_x * math.cos(angle_rad)
                    - local_shift_y * math.sin(angle_rad)
                )

                global_shift_y = (
                    local_shift_x * math.sin(angle_rad)
                    + local_shift_y * math.cos(angle_rad)
                )

                new_center_x = (
                    start_center_x + global_shift_x
                )

                new_center_y = (
                    start_center_y + global_shift_y
                )

                left = new_center_x - new_w / 2
                right = new_center_x + new_w / 2

                top = new_center_y - new_h / 2
                bottom = new_center_y + new_h / 2

            # 回転枠の左下ハンドルを動かした場合、
            # ドラッグ開始時の右上を固定して中心位置を補正する
            if self.resize_handle == "bottom_left":
                new_w = right - left
                new_h = bottom - top

                angle = 0.0

                if self.selected_rect < len(self.rect_angles):
                    angle = self.rect_angles[
                        self.selected_rect
                    ]

                start_center_x = (
                    start_x + start_w / 2
                )

                start_center_y = (
                    start_y + start_h / 2
                )

                local_shift_x = (
                    (new_w - start_w) / 2
                )

                local_shift_y = (
                    (new_h - start_h) / 2
                )

                angle_rad = math.radians(angle)

                global_shift_x = (
                    -local_shift_x * math.cos(angle_rad)
                    - local_shift_y * math.sin(angle_rad)
                )

                global_shift_y = (
                    -local_shift_x * math.sin(angle_rad)
                    + local_shift_y * math.cos(angle_rad)
                )

                new_center_x = (
                    start_center_x + global_shift_x
                )

                new_center_y = (
                    start_center_y + global_shift_y
                )

                left = new_center_x - new_w / 2
                right = new_center_x + new_w / 2

                top = new_center_y - new_h / 2
                bottom = new_center_y + new_h / 2

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

            (
                _,
                x_offset,
                y_offset,
                scale_x,
                scale_y,
            ) = info

            pos = event.position()

            image_x = (
                pos.x() - x_offset
            ) / scale_x

            image_y = (
                pos.y() - y_offset
            ) / scale_y

            raw_w = abs(
                image_x - self.add_start_x
            )

            raw_h = abs(
                image_y - self.add_start_y
            )

            aspect_ratio = (
                self.get_active_aspect_ratio(
                    raw_w,
                    raw_h,
                )
            )

            if aspect_ratio is not None:
                if (
                    raw_h > 0
                    and raw_w / raw_h
                    >= aspect_ratio
                ):
                    w = raw_w
                    h = w / aspect_ratio
                else:
                    h = raw_h
                    w = h * aspect_ratio
            else:
                w = raw_w
                h = raw_h

            if image_x >= self.add_start_x:
                x = self.add_start_x
            else:
                x = self.add_start_x - w

            if image_y >= self.add_start_y:
                y = self.add_start_y
            else:
                y = self.add_start_y - h

            self.rects[
                self.selected_rect
            ] = (
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

        move_x = int(dx)
        move_y = int(dy)

        if move_x != 0 or move_y != 0:
            if not self.drag_undo_saved:
                self.save_undo_state()
                self.drag_undo_saved = True

            # 複数選択されている場合は全選択枠を移動する
            move_indexes = set(
                self.selected_rects
            )

            # 念のため単一選択状態も保証する
            if not move_indexes:
                move_indexes.add(
                    self.selected_rect
                )

            for rect_index in move_indexes:
                if (
                    rect_index < 0
                    or rect_index >= len(self.rects)
                ):
                    continue

                x, y, w, h = self.rects[
                    rect_index
                ]

                self.rects[rect_index] = (
                    x + move_x,
                    y + move_y,
                    w,
                    h,
                )

        self.last_image_x = image_x
        self.last_image_y = image_y

        self.update()

    def mouseReleaseEvent(self, event):
        # ---------------------------------
        # パン終了
        # ---------------------------------
        middle_pan_end = (
            event.button()
            == Qt.MouseButton.MiddleButton
        )

        space_pan_end = (
            self.space_pan_dragging
            and event.button()
            == Qt.MouseButton.LeftButton
        )

        if middle_pan_end or space_pan_end:
            self.panning = False
            self.last_pan_pos = None
            self.space_pan_dragging = False

            if self.space_pressed:
                self.setCursor(
                    Qt.CursorShape.OpenHandCursor
                )
            else:
                self.unsetCursor()

            event.accept()
            return

        was_dragging = self.dragging
        drag_moved = self.drag_undo_saved

        was_adding_rect = self.adding_rect
        was_resizing_rect = self.resizing

        was_editing_rect = (
            self.dragging
            or self.adding_rect
            or self.resizing
            or self.rotating
        )

        # 複数選択中の枠を通常クリックしただけの場合は、
        # クリックした1枠だけの選択へ戻す。
        #
        # 実際にドラッグした場合は、
        # 従来どおり複数選択を維持してグループ移動する。
        if (
            was_dragging
            and not drag_moved
            and self.selected_rect >= 0
            and len(self.selected_rects) > 1
            and (
                self.selected_rect
                >= len(self.rect_group_ids)
                or self.rect_group_ids[
                    self.selected_rect
                ]
                is None
            )
        ):
            self.selected_rects = {
                self.selected_rect
            }

            self.selected_rect_changed.emit(
                self.selected_rect
            )

            self.update()

        self.dragging = False
        self.drag_undo_saved = False
        self.adding_rect = False
        self.resizing = False
        self.rotating = False
        self.rotation_handle_below = False
        self.resize_handle = None
        self.resize_start_rect = None
        # 新規作成した枠が小さすぎる場合は削除
        if (
            was_adding_rect
            and self.selected_rect >= 0
            and self.selected_rect < len(self.rects)
        ):
            x, y, w, h = self.rects[
                self.selected_rect
            ]

            minimum_size = 20

            if (
                w < minimum_size
                or h < minimum_size
            ):
                del self.rects[
                    self.selected_rect
                ]

                if (
                    self.selected_rect
                    < len(self.rect_angles)
                ):
                    del self.rect_angles[
                        self.selected_rect
                    ]

                if (
                    self.selected_rect
                    < len(self.rect_aspect_modes)
                ):
                    del self.rect_aspect_modes[
                        self.selected_rect
                    ]

                if (
                    self.selected_rect
                    < len(self.rect_group_ids)
                ):
                    del self.rect_group_ids[
                        self.selected_rect
                    ]

                self.selected_rect = -1

                self.rects_changed.emit()
                self.update()
                return

        if (
            was_adding_rect
            and self.composite_create_mode
            and self.selected_rect >= 0
            and self.selected_rect
            < len(self.rects)
        ):
            if (
                self.selected_rect
                not in self.composite_create_indexes
            ):
                self.composite_create_indexes.append(
                    self.selected_rect
                )

        if (
            was_resizing_rect
            and self.selected_rect >= 0
            and self.selected_rect
            < len(self.rects)
        ):
            while (
                len(self.rect_aspect_modes)
                < len(self.rects)
            ):
                self.rect_aspect_modes.append(
                    "free"
                )

            self.rect_aspect_modes[
                self.selected_rect
            ] = str(
                self.aspect_ratio_mode
            )

        if was_editing_rect:
            self.rects_changed.emit()

        if (
            was_adding_rect
            and self.selected_rect >= 0
            and self.selected_rect
            < len(self.rects)
        ):
            self.selected_rect_changed.emit(
                self.selected_rect
            )

    def paste_copied_rects(
        self,
        offset=30,
        save_undo=True,
    ):
        if not self.copied_rects:
            return False

        if save_undo:
            self.save_undo_state()

        new_indexes = []

        group_id_map = {}

        for copied in self.copied_rects:
            x, y, w, h = copied[
                "rect"
            ]

            angle = copied.get(
                "angle",
                0.0,
            )

            aspect_mode = copied.get(
                "aspect_mode",
                "free",
            )

            source_group_id = copied.get(
                "group_id",
                None,
            )

            source_width = copied.get(
                "source_width",
                0,
            )

            source_height = copied.get(
                "source_height",
                0,
            )

            scale_x = 1.0
            scale_y = 1.0

            if (
                self.pixmap is not None
                and source_width > 0
                and source_height > 0
            ):
                scale_x = (
                    self.pixmap.width()
                    / source_width
                )

                scale_y = (
                    self.pixmap.height()
                    / source_height
                )

            new_rect = (
                int(round(
                    x * scale_x
                    + offset
                )),
                int(round(
                    y * scale_y
                    + offset
                )),
                max(
                    1,
                    int(round(
                        w * scale_x
                    )),
                ),
                max(
                    1,
                    int(round(
                        h * scale_y
                    )),
                ),
            )

            self.rects.append(
                new_rect
            )

            self.rect_angles.append(
                angle
            )

            self.rect_aspect_modes.append(
                aspect_mode
            )

            new_group_id = None

            if source_group_id is not None:
                if (
                    source_group_id
                    not in group_id_map
                ):
                    group_id_map[
                        source_group_id
                    ] = self.next_group_id()

                new_group_id = (
                    group_id_map[
                        source_group_id
                    ]
                )

            self.rect_group_ids.append(
                new_group_id
            )

            new_indexes.append(
                len(self.rects) - 1
            )

        self.selected_rects = set(
            new_indexes
        )

        if new_indexes:
            self.selected_rect = (
                new_indexes[-1]
            )
        else:
            self.selected_rect = -1

        if self.selected_rect >= 0:
            self.selected_rect_changed.emit(
                self.selected_rect
            )

        self.dragging = False
        self.drag_undo_saved = False
        self.adding_rect = False
        self.resizing = False
        self.rotating = False

        self.rects_changed.emit()
        self.update()

        return bool(
            new_indexes
        )

    def keyReleaseEvent(self, event):
        # ---------------------------------
        # Spaceキー：代替パン操作終了
        # ---------------------------------
        if event.key() == Qt.Key.Key_Space:
            self.space_pressed = False

            if self.space_pan_dragging:
                self.panning = False
                self.last_pan_pos = None
                self.space_pan_dragging = False

            self.unsetCursor()

            event.accept()
            return

        super().keyReleaseEvent(
            event
        )

    def keyPressEvent(self, event):
        # ---------------------------------
        # Spaceキー：代替パン操作
        # ---------------------------------
        if event.key() == Qt.Key.Key_Space:
            self.space_pressed = True

            if not self.panning:
                self.setCursor(
                    Qt.CursorShape.OpenHandCursor
                )

            event.accept()
            return

        if (
            self.composite_create_mode
            and event.key()
            in (
                Qt.Key.Key_Return,
                Qt.Key.Key_Enter,
            )
        ):
            valid_indexes = [
                index
                for index
                in self.composite_create_indexes
                if (
                    0 <= index
                    < len(self.rects)
                )
            ]

            if len(valid_indexes) >= 2:
                self.selected_rects = set(
                    valid_indexes
                )

                self.selected_rect = (
                    valid_indexes[-1]
                )

                self.group_selected_rects()

            self.composite_create_indexes.clear()

            self.composite_create_mode = False

            self.composite_create_finished.emit()

            event.accept()
            return

        if (
            event.key() == Qt.Key.Key_G
            and event.modifiers()
            == Qt.KeyboardModifier.ControlModifier
        ):
            self.group_selected_rects()

            event.accept()
            return

        if (
            event.key() == Qt.Key.Key_G
            and event.modifiers()
            == (
                Qt.KeyboardModifier.ControlModifier
                | Qt.KeyboardModifier.ShiftModifier
            )
        ):
            self.ungroup_selected_rect()

            event.accept()
            return

        if (
            event.key() == Qt.Key.Key_A
            and event.modifiers()
            == Qt.KeyboardModifier.ControlModifier
        ):
            if self.rects:
                self.selected_rects = set(
                    range(len(self.rects))
                )

                self.selected_rect = (
                    len(self.rects) - 1
                )

                self.selected_rect_changed.emit(
                    self.selected_rect
                )

            else:
                self.selected_rect = -1
                self.selected_rects.clear()

            self.dragging = False
            self.drag_undo_saved = False
            self.adding_rect = False
            self.resizing = False
            self.rotating = False

            self.update()

            event.accept()
            return

        if (
            event.key() == Qt.Key.Key_X
            and event.modifiers()
            == Qt.KeyboardModifier.ControlModifier
        ):
            cut_indexes = set(
                self.selected_rects
            )

            # 念のため単一選択状態にも対応
            if (
                not cut_indexes
                and self.selected_rect >= 0
            ):
                cut_indexes.add(
                    self.selected_rect
                )

            if cut_indexes:
                self.copied_rects = []

                for cut_index in sorted(
                    cut_indexes
                ):
                    if (
                        cut_index < 0
                        or cut_index >= len(self.rects)
                    ):
                        continue

                    x, y, w, h = self.rects[
                        cut_index
                    ]

                    angle = 0.0

                    if cut_index < len(
                        self.rect_angles
                    ):
                        angle = self.rect_angles[
                            cut_index
                        ]

                    aspect_mode = "free"

                    if cut_index < len(
                        self.rect_aspect_modes
                    ):
                        aspect_mode = (
                            self.rect_aspect_modes[
                                cut_index
                            ]
                        )

                    group_id = None

                    if cut_index < len(
                        self.rect_group_ids
                    ):
                        group_id = (
                            self.rect_group_ids[
                                cut_index
                            ]
                        )

                    self.copied_rects.append(
                        {
                            "rect": (
                                x,
                                y,
                                w,
                                h,
                            ),
                            "angle": angle,
                            "aspect_mode": aspect_mode,
                            "group_id": group_id,
                            "source_width": (
                                self.pixmap.width()
                                if self.pixmap is not None
                                else 0
                            ),
                            "source_height": (
                                self.pixmap.height()
                                if self.pixmap is not None
                                else 0
                            ),
                        }
                    )

                self.save_undo_state()

                # インデックスずれを防ぐため、
                # 大きい番号から削除する
                for cut_index in sorted(
                    cut_indexes,
                    reverse=True,
                ):
                    if (
                        cut_index < 0
                        or cut_index >= len(self.rects)
                    ):
                        continue

                    del self.rects[
                        cut_index
                    ]

                    if cut_index < len(
                        self.rect_angles
                    ):
                        del self.rect_angles[
                            cut_index
                        ]

                    if cut_index < len(
                        self.rect_aspect_modes
                    ):
                        del self.rect_aspect_modes[
                            cut_index
                        ]

                    if cut_index < len(
                        self.rect_group_ids
                    ):
                        del self.rect_group_ids[
                            cut_index
                        ]

                self.selected_rect = -1
                self.selected_rects.clear()

                self.dragging = False
                self.drag_undo_saved = False
                self.adding_rect = False
                self.resizing = False
                self.rotating = False

                self.rects_changed.emit()
                self.update()

            event.accept()
            return

        if (
            event.key() == Qt.Key.Key_C
            and event.modifiers()
            == Qt.KeyboardModifier.ControlModifier
        ):
            copy_indexes = set(
                self.selected_rects
            )

            # 念のため単一選択状態にも対応
            if (
                not copy_indexes
                and self.selected_rect >= 0
            ):
                copy_indexes.add(
                    self.selected_rect
                )

            if copy_indexes:
                self.copied_rects = []

                for copy_index in sorted(
                    copy_indexes
                ):
                    if (
                        copy_index < 0
                        or copy_index >= len(self.rects)
                    ):
                        continue

                    x, y, w, h = self.rects[
                        copy_index
                    ]

                    angle = 0.0

                    if copy_index < len(
                        self.rect_angles
                    ):
                        angle = self.rect_angles[
                            copy_index
                        ]

                    aspect_mode = "free"

                    if copy_index < len(
                        self.rect_aspect_modes
                    ):
                        aspect_mode = (
                            self.rect_aspect_modes[
                                copy_index
                            ]
                        )
                    group_id = None

                    if copy_index < len(
                        self.rect_group_ids
                    ):
                        group_id = (
                            self.rect_group_ids[
                                copy_index
                            ]
                        )

                    self.copied_rects.append(
                        {
                            "rect": (
                                x,
                                y,
                                w,
                                h,
                            ),
                            "angle": angle,
                            "aspect_mode": aspect_mode,
                            "group_id": group_id,
                            "source_width": (
                                self.pixmap.width()
                                if self.pixmap is not None
                                else 0
                            ),
                            "source_height": (
                                self.pixmap.height()
                                if self.pixmap is not None
                                else 0
                            ),
                        }
                    )

            event.accept()
            return

        if (
            event.key() == Qt.Key.Key_V
            and event.modifiers()
            == Qt.KeyboardModifier.ControlModifier
        ):
            self.paste_copied_rects(
                offset=30,
                save_undo=True,
            )

            event.accept()
            return

        if event.key() == Qt.Key.Key_Delete:
            delete_indexes = set(
                self.selected_rects
            )

            # 念のため単一選択状態にも対応
            if (
                not delete_indexes
                and self.selected_rect >= 0
            ):
                delete_indexes.add(
                    self.selected_rect
                )

            if delete_indexes:
                self.save_undo_state()

                # インデックスずれを防ぐため、
                # 大きい番号から削除する
                for delete_index in sorted(
                    delete_indexes,
                    reverse=True,
                ):
                    if (
                        delete_index < 0
                        or delete_index >= len(self.rects)
                    ):
                        continue

                    del self.rects[
                        delete_index
                    ]

                    if delete_index < len(
                        self.rect_angles
                    ):
                        del self.rect_angles[
                            delete_index
                        ]

                    if delete_index < len(
                        self.rect_aspect_modes
                    ):
                        del self.rect_aspect_modes[
                            delete_index
                        ]

                    if delete_index < len(
                        self.rect_group_ids
                    ):
                        del self.rect_group_ids[
                            delete_index
                        ]

                self.normalize_singleton_groups()

                self.selected_rect = -1
                self.selected_rects.clear()
                self.dragging = False
                self.adding_rect = False
                self.resizing = False
                self.rotating = False

                self.rects_changed.emit()
                self.update()

                event.accept()

            return

        if self.selected_rect >= 0:

            move_step = 1

            if event.modifiers() & Qt.KeyboardModifier.ShiftModifier:
                move_step = 10

            move_x = 0
            move_y = 0

            if event.key() == Qt.Key.Key_Left:
                move_x = -move_step

            elif event.key() == Qt.Key.Key_Right:
                move_x = move_step

            elif event.key() == Qt.Key.Key_Up:
                move_y = -move_step

            elif event.key() == Qt.Key.Key_Down:
                move_y = move_step

            if move_x != 0 or move_y != 0:
                self.save_undo_state()

                x, y, w, h = self.rects[
                    self.selected_rect
                ]

                self.rects[self.selected_rect] = (
                    x + move_x,
                    y + move_y,
                    w,
                    h,
                )

                self.rects_changed.emit()
                self.update()

                event.accept()
                return

        if (
            event.key() == Qt.Key.Key_Z
            and event.modifiers() == Qt.KeyboardModifier.ControlModifier
        ):
            self.undo()
            return

        if (
            event.key() == Qt.Key.Key_Y
            and event.modifiers() == Qt.KeyboardModifier.ControlModifier
        ):
            self.redo()
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

        # パン位置も初期化して、
        # 画像全体をキャンバス中央へ戻す
        self.pan_x = 0.0
        self.pan_y = 0.0

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