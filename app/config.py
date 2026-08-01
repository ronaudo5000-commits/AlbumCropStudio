from PySide6.QtCore import QSettings


class Config:
    # 既存の設定保存場所を維持する
    ORGANIZATION = "AlbumCropStudio"
    APPLICATION = "AlbumCropStudio"

    DEFAULT_DPI = 350
    DEFAULT_JPEG_QUALITY = 95
    DEFAULT_MARGIN_MM = 0

    @classmethod
    def settings(cls):
        return QSettings(
            cls.ORGANIZATION,
            cls.APPLICATION,
        )

    @classmethod
    def get_dpi(cls):
        dpi = int(
            cls.settings().value(
                "dpi",
                cls.DEFAULT_DPI,
            )
        )

        return max(
            200,
            min(dpi, 1200),
        )

    @classmethod
    def set_dpi(
        cls,
        dpi,
    ):
        safe_dpi = max(
            200,
            min(int(dpi), 1200),
        )

        cls.settings().setValue(
            "dpi",
            safe_dpi,
        )

    @classmethod
    def get_jpeg_quality(cls):
        quality = int(
            cls.settings().value(
                "jpeg_quality",
                cls.DEFAULT_JPEG_QUALITY,
            )
        )

        # 設定データが壊れていた場合にも
        # 安全な範囲へ収める
        return max(
            1,
            min(quality, 100),
        )

    @classmethod
    def set_jpeg_quality(
        cls,
        quality,
    ):
        safe_quality = max(
            1,
            min(int(quality), 100),
        )

        cls.settings().setValue(
            "jpeg_quality",
            safe_quality,
        )

    @classmethod
    def get_margin_mm(cls):
        margin_mm = int(
            cls.settings().value(
                "margin_mm",
                cls.DEFAULT_MARGIN_MM,
            )
        )

        return max(
            0,
            min(margin_mm, 20),
        )

    @classmethod
    def set_margin_mm(
        cls,
        margin_mm,
    ):
        safe_margin_mm = max(
            0,
            min(int(margin_mm), 20),
        )

        cls.settings().setValue(
            "margin_mm",
            safe_margin_mm,
        )