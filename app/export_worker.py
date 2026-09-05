import math
import time

from PIL import Image

from PySide6.QtCore import (
    QObject,
    Signal,
)

class CropExportWorker(QObject):
    progress = Signal(
        int,
        int,
        int,
    )
    finished = Signal(int)
    failed = Signal(str)

    def __init__(
        self,
        image_paths,
        page_rects,
        page_angles,
        page_group_ids,
        page_mosaic_rects,
        output_dir,
        dpi,
        margin_px,
        jpeg_quality,
        total_crops,
        export_page_indexes=None,
    ):
        super().__init__()

        self.image_paths = list(
            image_paths
        )

        self.page_rects = {
            page_index: list(rects)
            for page_index, rects
            in page_rects.items()
        }

        self.page_angles = {
            page_index: list(angles)
            for page_index, angles
            in page_angles.items()
        }

        self.page_group_ids = {
            page_index: list(group_ids)
            for page_index, group_ids
            in page_group_ids.items()
        }

        self.page_mosaic_rects = {
            page_index: [
                tuple(rect)
                for rect in mosaic_rects
            ]
            for page_index, mosaic_rects
            in page_mosaic_rects.items()
        }

        self.output_dir = output_dir
        self.dpi = dpi
        self.margin_px = margin_px

        self.jpeg_quality = max(
            1,
            min(int(jpeg_quality), 100),
        )

        self.total_crops = total_crops

        if export_page_indexes is None:
            self.export_page_indexes = None
        else:
            self.export_page_indexes = {
                int(page_index)
                for page_index
                in export_page_indexes
            }

    def validate_crop_rect(
        self,
        rect,
        page_index,
        crop_index,
    ):
        if (
            not isinstance(rect, (list, tuple))
            or len(rect) != 4
        ):
            raise ValueError(
                (
                    f"ページ {page_index + 1}、"
                    f"写真 {crop_index} の"
                    "枠データ形式が正しくありません"
                )
            )

        try:
            x, y, w, h = (
                float(value)
                for value in rect
            )

        except (
            TypeError,
            ValueError,
            OverflowError,
        ) as e:
            raise ValueError(
                (
                    f"ページ {page_index + 1}、"
                    f"写真 {crop_index} の"
                    "座標またはサイズが数値ではありません"
                )
            ) from e

        if not all(
            math.isfinite(value)
            for value in (
                x,
                y,
                w,
                h,
            )
        ):
            raise ValueError(
                (
                    f"ページ {page_index + 1}、"
                    f"写真 {crop_index} に"
                    "無効な数値が含まれています"
                )
            )

        if w <= 0:
            raise ValueError(
                (
                    f"ページ {page_index + 1}、"
                    f"写真 {crop_index} の"
                    f"幅が不正です: {w}"
                )
            )

        if h <= 0:
            raise ValueError(
                (
                    f"ページ {page_index + 1}、"
                    f"写真 {crop_index} の"
                    f"高さが不正です: {h}"
                )
            )

        return (
            x,
            y,
            w,
            h,
        )

    def clamp_crop_rect(
        self,
        x,
        y,
        w,
        h,
        image_width,
        image_height,
    ):
        left = max(
            0,
            int(round(x)),
        )

        top = max(
            0,
            int(round(y)),
        )

        right = min(
            image_width,
            int(round(x + w)),
        )

        bottom = min(
            image_height,
            int(round(y + h)),
        )

        # 枠が画像とまったく重ならない場合は、
        # 無理に1pxへ補正せずエラーにする
        if (
            left >= image_width
            or top >= image_height
            or right <= 0
            or bottom <= 0
            or right <= left
            or bottom <= top
        ):
            raise ValueError(
                "切り抜き枠が元画像の範囲外です"
            )

        return (
            left,
            top,
            right - left,
            bottom - top,
        )

    def transform_mosaic_rects_for_crop(
        self,
        mosaic_rects,
        crop_x,
        crop_y,
        crop_w,
        crop_h,
        angle,
    ):
        if not mosaic_rects:
            return []

        crop_center_x = (
            crop_x + crop_w / 2
        )

        crop_center_y = (
            crop_y + crop_h / 2
        )

        angle_rad = math.radians(
            -angle
        )

        cos_a = math.cos(
            angle_rad
        )

        sin_a = math.sin(
            angle_rad
        )

        transformed_rects = []

        for rect in mosaic_rects:
            if (
                not isinstance(
                    rect,
                    (list, tuple),
                )
                or len(rect) != 4
            ):
                continue

            try:
                x, y, w, h = (
                    float(value)
                    for value in rect
                )

            except (
                TypeError,
                ValueError,
                OverflowError,
            ):
                continue

            if not all(
                math.isfinite(value)
                for value in (
                    x,
                    y,
                    w,
                    h,
                )
            ):
                continue

            if w <= 0 or h <= 0:
                continue

            corners = (
                (x, y),
                (x + w, y),
                (x + w, y + h),
                (x, y + h),
            )

            transformed_points = []

            for point_x, point_y in corners:
                dx = (
                    point_x
                    - crop_center_x
                )

                dy = (
                    point_y
                    - crop_center_y
                )

                rotated_x = (
                    crop_center_x
                    + dx * cos_a
                    - dy * sin_a
                )

                rotated_y = (
                    crop_center_y
                    + dx * sin_a
                    + dy * cos_a
                )

                transformed_points.append(
                    (
                        rotated_x - crop_x,
                        rotated_y - crop_y,
                    )
                )

            left = max(
                0,
                int(
                    math.floor(
                        min(
                            point[0]
                            for point
                            in transformed_points
                        )
                    )
                ),
            )

            top = max(
                0,
                int(
                    math.floor(
                        min(
                            point[1]
                            for point
                            in transformed_points
                        )
                    )
                ),
            )

            right = min(
                int(round(crop_w)),
                int(
                    math.ceil(
                        max(
                            point[0]
                            for point
                            in transformed_points
                        )
                    )
                ),
            )

            bottom = min(
                int(round(crop_h)),
                int(
                    math.ceil(
                        max(
                            point[1]
                            for point
                            in transformed_points
                        )
                    )
                ),
            )

            if (
                right <= left
                or bottom <= top
            ):
                continue

            transformed_rects.append(
                (
                    left,
                    top,
                    right - left,
                    bottom - top,
                )
            )

        return transformed_rects

    def apply_mosaic_rects(
        self,
        image,
        mosaic_rects,
    ):
        if not mosaic_rects:
            return image

        image_width = image.width
        image_height = image.height

        for rect in mosaic_rects:
            if (
                not isinstance(
                    rect,
                    (list, tuple),
                )
                or len(rect) != 4
            ):
                continue

            try:
                x, y, w, h = (
                    float(value)
                    for value in rect
                )

            except (
                TypeError,
                ValueError,
                OverflowError,
            ):
                continue

            if not all(
                math.isfinite(value)
                for value in (
                    x,
                    y,
                    w,
                    h,
                )
            ):
                continue

            if w <= 0 or h <= 0:
                continue

            left = max(
                0,
                int(round(x)),
            )

            top = max(
                0,
                int(round(y)),
            )

            right = min(
                image_width,
                int(round(x + w)),
            )

            bottom = min(
                image_height,
                int(round(y + h)),
            )

            if (
                right <= left
                or bottom <= top
            ):
                continue

            mosaic_region = image.crop(
                (
                    left,
                    top,
                    right,
                    bottom,
                )
            )

            region_width = (
                right - left
            )

            region_height = (
                bottom - top
            )

            # モザイク1ブロックを
            # おおよそ20px程度にする
            block_size = 20

            reduced_width = max(
                1,
                region_width // block_size,
            )

            reduced_height = max(
                1,
                region_height // block_size,
            )

            reduced = mosaic_region.resize(
                (
                    reduced_width,
                    reduced_height,
                ),
                Image.Resampling.BOX,
            )

            pixelated = reduced.resize(
                (
                    region_width,
                    region_height,
                ),
                Image.Resampling.NEAREST,
            )

            image.paste(
                pixelated,
                (
                    left,
                    top,
                ),
            )

        return image

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

        # 最終的に切り抜く範囲
        left = int(x)
        top = int(y)
        right = int(x + w)
        bottom = int(y + h)

        # 回転中心
        center_x = x + w / 2
        center_y = y + h / 2

        angle_rad = math.radians(angle)

        cos_a = abs(math.cos(angle_rad))
        sin_a = abs(math.sin(angle_rad))

        # 最終切り抜き範囲が回転中心から
        # どこまで離れているかを求める
        max_dx = max(
            abs(left - center_x),
            abs(right - center_x),
        )
        max_dy = max(
            abs(top - center_y),
            abs(bottom - center_y),
        )

        # 回転後の切り抜きに必要となる
        # 元画像側の最小領域を計算
        source_half_w = (
            max_dx * cos_a
            + max_dy * sin_a
        )
        source_half_h = (
            max_dx * sin_a
            + max_dy * cos_a
        )

        # BICUBIC補間が周囲の画素を参照するため、
        # 数ピクセル余裕を持たせる
        interpolation_padding = 3

        source_left = (
            math.floor(
                center_x - source_half_w
            )
            - interpolation_padding
        )
        source_top = (
            math.floor(
                center_y - source_half_h
            )
            - interpolation_padding
        )
        source_right = (
            math.ceil(
                center_x + source_half_w
            )
            + interpolation_padding
        )
        source_bottom = (
            math.ceil(
                center_y + source_half_h
            )
            + interpolation_padding
        )

        # 必要な領域だけを元画像から取り出す
        local_image = image.crop(
            (
                source_left,
                source_top,
                source_right,
                source_bottom,
            )
        )

        # 元画像上の回転中心を
        # 局所画像上の座標へ変換
        local_center_x = (
            center_x - source_left
        )
        local_center_y = (
            center_y - source_top
        )

        # 局所画像だけを回転
        rotated_local = local_image.rotate(
            angle,
            resample=Image.Resampling.BICUBIC,
            center=(
                local_center_x,
                local_center_y,
            ),
        )

        # 元画像上の最終切り抜き位置を
        # 局所画像上の座標へ変換
        local_left = left - source_left
        local_top = top - source_top
        local_right = right - source_left
        local_bottom = bottom - source_top

        return rotated_local.crop(
            (
                local_left,
                local_top,
                local_right,
                local_bottom,
            )
        )

    def build_crop_units(
        self,
        page_rects,
        page_group_ids,
    ):
        crop_units = []
        processed_group_ids = set()

        for rect_index in range(
            len(page_rects)
        ):
            group_id = None

            if rect_index < len(
                page_group_ids
            ):
                group_id = page_group_ids[
                    rect_index
                ]

            if group_id is None:
                crop_units.append(
                    [rect_index]
                )
                continue

            if group_id in processed_group_ids:
                continue

            member_indexes = [
                member_index
                for member_index in range(
                    len(page_rects)
                )
                if (
                    member_index
                    < len(page_group_ids)
                    and page_group_ids[
                        member_index
                    ]
                    == group_id
                )
            ]

            if member_indexes:
                crop_units.append(
                    member_indexes
                )

            processed_group_ids.add(
                group_id
            )

        return crop_units

    def export_images(self):
        saved_count = 0
        timing_results = []

        for page_index, image_path in enumerate(
            self.image_paths
        ):
            if (
                self.export_page_indexes
                is not None
                and page_index
                not in self.export_page_indexes
            ):
                continue

            page_rects = self.page_rects.get(
                page_index,
                [],
            )

            page_angles = self.page_angles.get(
                page_index,
                [],
            )

            page_group_ids = (
                self.page_group_ids.get(
                    page_index,
                    [],
                )
            )

            page_mosaic_rects = (
                self.page_mosaic_rects.get(
                    page_index,
                    [],
                )
            )

            if not page_rects:
                continue

            crop_units = self.build_crop_units(
                page_rects,
                page_group_ids,
            )

            try:
                with Image.open(
                    image_path
                ) as source_image:
                    image = source_image.convert(
                        "RGB"
                    )

                    image_width = image.width
                    image_height = image.height

                    for (
                        crop_index,
                        member_indexes,
                    ) in enumerate(
                        crop_units,
                        start=1,
                    ):
                        prepared_members = []

                        for rect_index in member_indexes:
                            rect = page_rects[
                                rect_index
                            ]

                            (
                                x,
                                y,
                                w,
                                h,
                            ) = self.validate_crop_rect(
                                rect,
                                page_index,
                                rect_index + 1,
                            )

                            angle = 0.0

                            if rect_index < len(
                                page_angles
                            ):
                                try:
                                    angle = float(
                                        page_angles[
                                            rect_index
                                        ]
                                    )

                                except (
                                    TypeError,
                                    ValueError,
                                    OverflowError,
                                ) as e:
                                    raise ValueError(
                                        (
                                            f"ページ "
                                            f"{page_index + 1}、"
                                            f"写真 "
                                            f"{rect_index + 1} の"
                                            "回転角度が不正です"
                                        )
                                    ) from e

                                if not math.isfinite(
                                    angle
                                ):
                                    raise ValueError(
                                        (
                                            f"ページ "
                                            f"{page_index + 1}、"
                                            f"写真 "
                                            f"{rect_index + 1} の"
                                            "回転角度に無効な数値が"
                                            "含まれています"
                                        )
                                    )

                            crop_x = (
                                x - self.margin_px
                            )

                            crop_y = (
                                y - self.margin_px
                            )

                            crop_w = (
                                w
                                + self.margin_px * 2
                            )

                            crop_h = (
                                h
                                + self.margin_px * 2
                            )

                            try:
                                (
                                    crop_x,
                                    crop_y,
                                    crop_w,
                                    crop_h,
                                ) = self.clamp_crop_rect(
                                    crop_x,
                                    crop_y,
                                    crop_w,
                                    crop_h,
                                    image_width,
                                    image_height,
                                )

                            except ValueError as e:
                                raise ValueError(
                                    (
                                        f"ページ "
                                        f"{page_index + 1}、"
                                        f"写真 "
                                        f"{rect_index + 1} の"
                                        "切り抜き範囲が不正です。"
                                        f"\n詳細: {e}"
                                    )
                                ) from e

                            start_time = time.perf_counter()

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

                            transformed_mosaic_rects = (
                                self.transform_mosaic_rects_for_crop(
                                    page_mosaic_rects,
                                    crop_x,
                                    crop_y,
                                    crop_w,
                                    crop_h,
                                    angle,
                                )
                            )

                            crop = self.apply_mosaic_rects(
                                crop,
                                transformed_mosaic_rects,
                            )

                            elapsed_time = (
                                time.perf_counter()
                                - start_time
                            )

                            timing_results.append(
                                (
                                    page_index + 1,
                                    rect_index + 1,
                                    angle,
                                    elapsed_time,
                                )
                            )

                            if (
                                crop.width <= 0
                                or crop.height <= 0
                            ):
                                raise ValueError(
                                    (
                                        f"ページ "
                                        f"{page_index + 1}、"
                                        f"写真 "
                                        f"{rect_index + 1} の"
                                        "切り抜き結果のサイズが"
                                        "不正です"
                                    )
                                )

                            prepared_members.append(
                                {
                                    "x": crop_x,
                                    "y": crop_y,
                                    "w": crop_w,
                                    "h": crop_h,
                                    "image": crop,
                                }
                            )

                        if len(prepared_members) == 1:
                            output_image = (
                                prepared_members[
                                    0
                                ][
                                    "image"
                                ]
                            )

                        else:
                            left = min(
                                member["x"]
                                for member
                                in prepared_members
                            )

                            top = min(
                                member["y"]
                                for member
                                in prepared_members
                            )

                            right = max(
                                member["x"]
                                + member["w"]
                                for member
                                in prepared_members
                            )

                            bottom = max(
                                member["y"]
                                + member["h"]
                                for member
                                in prepared_members
                            )

                            canvas_width = max(
                                1,
                                int(round(
                                    right - left
                                )),
                            )

                            canvas_height = max(
                                1,
                                int(round(
                                    bottom - top
                                )),
                            )

                            output_image = Image.new(
                                "RGB",
                                (
                                    canvas_width,
                                    canvas_height,
                                ),
                                (
                                    255,
                                    255,
                                    255,
                                ),
                            )

                            for member in prepared_members:
                                paste_x = int(round(
                                    member["x"]
                                    - left
                                ))

                                paste_y = int(round(
                                    member["y"]
                                    - top
                                ))

                                output_image.paste(
                                    member["image"],
                                    (
                                        paste_x,
                                        paste_y,
                                    ),
                                )

                        output_path = (
                            self.output_dir
                            / (
                                f"page_{page_index + 1:03}_"
                                f"photo_{crop_index:03}.jpg"
                            )
                        )

                        output_image.save(
                            output_path,
                            "JPEG",
                            quality=self.jpeg_quality,
                            dpi=(
                                self.dpi,
                                self.dpi,
                            ),
                        )

                        saved_count += 1

                        progress_value = int(
                            (
                                saved_count
                                / self.total_crops
                            )
                            * 100
                        )

                        self.progress.emit(
                            progress_value,
                            saved_count,
                            self.total_crops,
                        )

            except Exception as e:
                image_name = str(
                    image_path
                )

                raise RuntimeError(
                    (
                        f"ページ {page_index + 1} の"
                        f"書き出しに失敗しました。\n"
                        f"対象ファイル: {image_name}\n"
                        f"詳細: {e}"
                    )
                ) from e

        if timing_results:
            total_time = sum(
                result[3]
                for result in timing_results
            )

            average_time = (
                total_time
                / len(timing_results)
            )

            timing_path = (
                self.output_dir
                / "crop_timing.txt"
            )

            with open(
                timing_path,
                "w",
                encoding="utf-8",
            ) as timing_file:
                for (
                    page_number,
                    photo_number,
                    angle,
                    elapsed_time,
                ) in timing_results:
                    timing_file.write(
                        f"page={page_number} "
                        f"photo={photo_number} "
                        f"angle={angle:.2f} "
                        f"time={elapsed_time:.6f}s\n"
                    )

                timing_file.write(
                    "\n"
                )

                timing_file.write(
                    f"count="
                    f"{len(timing_results)}\n"
                )

                timing_file.write(
                    f"total="
                    f"{total_time:.6f}s\n"
                )

                timing_file.write(
                    f"average="
                    f"{average_time:.6f}s\n"
                )

        return saved_count

        return saved_count

    def run(self):
        try:
            saved_count = self.export_images()

            self.finished.emit(
                saved_count
            )

        except Exception as e:
            self.failed.emit(
                str(e)
            )