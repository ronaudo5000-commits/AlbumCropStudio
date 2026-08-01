from PIL import Image

from app.config import Config

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
        output_dir,
        dpi,
        margin_px,
        jpeg_quality,
        total_crops,
        main_window,
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

        self.output_dir = output_dir
        self.dpi = dpi
        self.margin_px = margin_px

        self.jpeg_quality = max(
            1,
            min(int(jpeg_quality), 100),
        )

        self.total_crops = total_crops
        self.main_window = main_window

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

        # 枠データが異常な場合でも、
        # 最低1pxの切り抜き範囲を確保する
        if right <= left:
            right = min(
                image_width,
                left + 1,
            )

        if bottom <= top:
            bottom = min(
                image_height,
                top + 1,
            )

        safe_x = left
        safe_y = top
        safe_w = right - left
        safe_h = bottom - top

        return (
            safe_x,
            safe_y,
            safe_w,
            safe_h,
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

    def export_images(self):
        saved_count = 0

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

            if not page_rects:
                continue

            try:
                with Image.open(
                    image_path
                ) as source_image:
                    image = source_image.convert(
                        "RGB"
                    )

                    image_width = image.width
                    image_height = image.height

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
                            self.output_dir
                            / (
                                f"page_{page_index + 1:03}_"
                                f"photo_{crop_index:03}.jpg"
                            )
                        )

                        crop.save(
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