import math
from pathlib import Path

from PIL import (
    Image,
    ImageDraw,
)

from PySide6.QtCore import (
    QObject,
    Signal,
)


def build_export_filename(
    image_path,
    crop_index,
):
    source_name = Path(
        image_path
    ).stem

    return (
        f"{source_name}_"
        f"{crop_index:03}.jpg"
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
        page_mosaic_angles=None,
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

        if page_mosaic_angles is None:
            page_mosaic_angles = {}

        self.page_mosaic_angles = {
            page_index: list(
                angles
            )
            for page_index, angles
            in page_mosaic_angles.items()
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

    def apply_mosaic_rects(
        self,
        image,
        mosaic_rects,
        mosaic_angles=None,
    ):
        if not mosaic_rects:
            return image

        if mosaic_angles is None:
            mosaic_angles = []

        image_width = image.width
        image_height = image.height

        # モザイク1ブロックを
        # おおよそ36px程度にする
        block_size = 36

        for mosaic_index, rect in enumerate(
            mosaic_rects
        ):
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

            angle = 0.0

            if mosaic_index < len(
                mosaic_angles
            ):
                try:
                    angle = float(
                        mosaic_angles[
                            mosaic_index
                        ]
                    )

                except (
                    TypeError,
                    ValueError,
                    OverflowError,
                ):
                    angle = 0.0

            if not math.isfinite(
                angle
            ):
                angle = 0.0

            center_x = x + w / 2
            center_y = y + h / 2

            angle_rad = math.radians(
                angle
            )

            cos_a = math.cos(
                angle_rad
            )

            sin_a = math.sin(
                angle_rad
            )

            rotated_corners = []

            for local_x, local_y in (
                (-w / 2, -h / 2),
                (w / 2, -h / 2),
                (w / 2, h / 2),
                (-w / 2, h / 2),
            ):
                rotated_x = (
                    center_x
                    + local_x * cos_a
                    - local_y * sin_a
                )

                rotated_y = (
                    center_y
                    + local_x * sin_a
                    + local_y * cos_a
                )

                rotated_corners.append(
                    (
                        rotated_x,
                        rotated_y,
                    )
                )

            left = max(
                0,
                int(
                    math.floor(
                        min(
                            point[0]
                            for point
                            in rotated_corners
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
                            in rotated_corners
                        )
                    )
                ),
            )

            right = min(
                image_width,
                int(
                    math.ceil(
                        max(
                            point[0]
                            for point
                            in rotated_corners
                        )
                    )
                ),
            )

            bottom = min(
                image_height,
                int(
                    math.ceil(
                        max(
                            point[1]
                            for point
                            in rotated_corners
                        )
                    )
                ),
            )

            if (
                right <= left
                or bottom <= top
            ):
                continue

            region_width = (
                right - left
            )

            region_height = (
                bottom - top
            )

            mosaic_region = image.crop(
                (
                    left,
                    top,
                    right,
                    bottom,
                )
            )

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

            mask = Image.new(
                "L",
                (
                    region_width,
                    region_height,
                ),
                0,
            )

            mask_draw = ImageDraw.Draw(
                mask
            )

            local_polygon = [
                (
                    int(
                        round(
                            point_x - left
                        )
                    ),
                    int(
                        round(
                            point_y - top
                        )
                    ),
                )
                for point_x, point_y
                in rotated_corners
            ]

            mask_draw.polygon(
                local_polygon,
                fill=255,
            )

            image.paste(
                pixelated,
                (
                    left,
                    top,
                ),
                mask,
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

    def create_group_crop_image_from_source(
        self,
        image,
        prepared_members,
        page_mosaic_rects,
    ):
        if not prepared_members:
            raise ValueError(
                "グループ枠の構成領域がありません"
            )

        # ---------------------------------
        # 構成枠ごとに
        # 異なる回転角度を持つか確認する
        # ---------------------------------
        reference_angle = float(
            prepared_members[0]["angle"]
        )

        has_mixed_angles = False

        for member in prepared_members[1:]:
            member_angle = float(
                member["angle"]
            )

            angle_difference = (
                (
                    member_angle
                    - reference_angle
                    + 180.0
                )
                % 360.0
            ) - 180.0

            if abs(
                angle_difference
            ) > 0.001:
                has_mixed_angles = True
                break

        # ---------------------------------
        # 構成枠ごとに角度が異なる場合
        #
        # 各枠をそれぞれの角度で
        # 独立して回転補正したあと、
        # 元画像上の位置関係を保ったまま
        # 1枚のグループ画像へ合成する。
        # ---------------------------------
        if has_mixed_angles:
            source_image = image.copy()

            source_image = self.apply_mosaic_rects(
                source_image,
                page_mosaic_rects,
            )

            left = int(
                math.floor(
                    min(
                        member["x"]
                        for member
                        in prepared_members
                    )
                )
            )

            top = int(
                math.floor(
                    min(
                        member["y"]
                        for member
                        in prepared_members
                    )
                )
            )

            right = int(
                math.ceil(
                    max(
                        member["x"]
                        + member["w"]
                        for member
                        in prepared_members
                    )
                )
            )

            bottom = int(
                math.ceil(
                    max(
                        member["y"]
                        + member["h"]
                        for member
                        in prepared_members
                    )
                )
            )

            output_width = (
                right - left
            )

            output_height = (
                bottom - top
            )

            if (
                output_width <= 0
                or output_height <= 0
            ):
                raise ValueError(
                    "グループ枠の切り抜き範囲が不正です"
                )

            output_image = Image.new(
                "RGB",
                (
                    output_width,
                    output_height,
                ),
                (
                    255,
                    255,
                    255,
                ),
            )

            for member in prepared_members:
                member_image = (
                    self.create_rotated_crop_image(
                        source_image,
                        member["x"],
                        member["y"],
                        member["w"],
                        member["h"],
                        member["angle"],
                    )
                )

                destination_x = int(
                    round(
                        member["x"] - left
                    )
                )

                destination_y = int(
                    round(
                        member["y"] - top
                    )
                )

                output_image.paste(
                    member_image,
                    (
                        destination_x,
                        destination_y,
                    ),
                )

            return output_image

        # ---------------------------------
        # 全構成枠が同じ角度の場合は、
        # 従来の共通変換処理を使用する
        # ---------------------------------
        group_angle = reference_angle

        angle_rad = math.radians(
            -group_angle
        )

        cos_a = math.cos(
            angle_rad
        )

        sin_a = math.sin(
            angle_rad
        )

        transformed_members = []

        # ---------------------------------
        # グループ全構成枠を、
        # 共通角度で補正した座標系へ変換する
        # ---------------------------------
        for member in prepared_members:
            center_x = (
                member["x"]
                + member["w"] / 2
            )

            center_y = (
                member["y"]
                + member["h"] / 2
            )

            transformed_center_x = (
                center_x * cos_a
                - center_y * sin_a
            )

            transformed_center_y = (
                center_x * sin_a
                + center_y * cos_a
            )

            transformed_members.append(
                {
                    "left": (
                        transformed_center_x
                        - member["w"] / 2
                    ),
                    "top": (
                        transformed_center_y
                        - member["h"] / 2
                    ),
                    "right": (
                        transformed_center_x
                        + member["w"] / 2
                    ),
                    "bottom": (
                        transformed_center_y
                        + member["h"] / 2
                    ),
                }
            )

        left = int(
            math.floor(
                min(
                    member["left"]
                    for member
                    in transformed_members
                )
            )
        )

        top = int(
            math.floor(
                min(
                    member["top"]
                    for member
                    in transformed_members
                )
            )
        )

        right = int(
            math.ceil(
                max(
                    member["right"]
                    for member
                    in transformed_members
                )
            )
        )

        bottom = int(
            math.ceil(
                max(
                    member["bottom"]
                    for member
                    in transformed_members
                )
            )
        )

        output_width = (
            right - left
        )

        output_height = (
            bottom - top
        )

        if (
            output_width <= 0
            or output_height <= 0
        ):
            raise ValueError(
                "グループ枠の切り抜き範囲が不正です"
            )

        # ---------------------------------
        # モザイクは元画像へ一度だけ適用する
        # ---------------------------------
        source_image = image.copy()

        source_image = self.apply_mosaic_rects(
            source_image,
            page_mosaic_rects,
        )

        # ---------------------------------
        # PillowのAFFINEは、
        # 出力座標から元画像座標への
        # 逆変換を指定する。
        #
        # グループ全体を1回だけ補正するため、
        # 構成枠ごとの回転は行わない。
        # ---------------------------------
        source_angle_rad = math.radians(
            group_angle
        )

        source_cos = math.cos(
            source_angle_rad
        )

        source_sin = math.sin(
            source_angle_rad
        )

        affine_data = (
            source_cos,
            -source_sin,
            (
                source_cos * left
                - source_sin * top
            ),
            source_sin,
            source_cos,
            (
                source_sin * left
                + source_cos * top
            ),
        )

        transformed_image = (
            source_image.transform(
                (
                    output_width,
                    output_height,
                ),
                Image.Transform.AFFINE,
                affine_data,
                resample=Image.Resampling.BICUBIC,
                fillcolor=(
                    255,
                    255,
                    255,
                ),
            )
        )

        # ---------------------------------
        # G1-A / G1-Bなどの構成領域を
        # 1つの和集合マスクへまとめる。
        #
        # 重なり領域も255のままなので、
        # 同じ文字を二重に貼ることはない。
        # ---------------------------------
        mask = Image.new(
            "L",
            (
                output_width,
                output_height,
            ),
            0,
        )

        for member in transformed_members:
            member_left = int(
                math.floor(
                    member["left"] - left
                )
            )

            member_top = int(
                math.floor(
                    member["top"] - top
                )
            )

            member_right = int(
                math.ceil(
                    member["right"] - left
                )
            )

            member_bottom = int(
                math.ceil(
                    member["bottom"] - top
                )
            )

            mask.paste(
                255,
                (
                    member_left,
                    member_top,
                    member_right,
                    member_bottom,
                ),
            )

        white_background = Image.new(
            "RGB",
            (
                output_width,
                output_height,
            ),
            (
                255,
                255,
                255,
            ),
        )

        white_background.paste(
            transformed_image,
            (
                0,
                0,
            ),
            mask,
        )

        return white_background

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

            page_mosaic_rects = (
                self.page_mosaic_rects.get(
                    page_index,
                    [],
                )
            )

            page_mosaic_angles = (
                self.page_mosaic_angles.get(
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

                    # ---------------------------------
                    # モザイクはページ元画像へ
                    # 一度だけ適用する。
                    #
                    # 各切り抜き枠ごとに
                    # 同じ処理を繰り返さない。
                    # ---------------------------------
                    mosaic_source_image = (
                        self.apply_mosaic_rects(
                            image.copy(),
                            page_mosaic_rects,
                            page_mosaic_angles,
                        )
                    )

                    for (
                        crop_index,
                        member_indexes,
                    ) in enumerate(
                        crop_units,
                        start=1,
                    ):
                        prepared_members = []

                        is_group_unit = (
                            len(member_indexes) > 1
                        )

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

                            member_data = {
                                "x": crop_x,
                                "y": crop_y,
                                "w": crop_w,
                                "h": crop_h,
                                "angle": angle,
                            }

                            # グループは個別画像を作らず、
                            # 座標情報だけを準備する。
                            if is_group_unit:
                                prepared_members.append(
                                    member_data
                                )

                                continue

                            # 単独枠だけ従来の
                            # 個別切り抜き処理を行う。
                            crop = (
                                self.create_rotated_crop_image(
                                    mosaic_source_image,
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

                            member_data[
                                "image"
                            ] = crop

                            prepared_members.append(
                                member_data
                            )

                        if is_group_unit:
                            output_image = (
                                self.create_group_crop_image_from_source(
                                    mosaic_source_image,
                                    prepared_members,
                                    [],
                                )
                            )

                        else:
                            output_image = (
                                prepared_members[
                                    0
                                ][
                                    "image"
                                ]
                            )

                        output_path = (
                            self.output_dir
                            / build_export_filename(
                                image_path,
                                crop_index,
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