import math

from PIL import Image

from PySide6.QtCore import (
    QObject,
    Signal,
)

class CropExportWorker(QObject):
    progress = Signal(int)
    finished = Signal(int)
    failed = Signal(str)

    def __init__(
        self,
        image_paths,
        page_rects,
        page_angles,
        page_group_ids,
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

    def create_rotated_crop_image(
        self,
        image,
        x,
        y,
        w,
        h,
        angle,
    ):
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

        rotated = image.rotate(
            angle,
            resample=Image.Resampling.BICUBIC,
            center=(
                center_x,
                center_y,
            ),
        )

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
                            progress_value
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