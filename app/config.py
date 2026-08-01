from PySide6.QtCore import QSettings


class Config:
    # 既存の設定保存場所を維持する
    ORGANIZATION = "AlbumCropStudio"
    APPLICATION = "AlbumCropStudio"

    DEFAULT_DPI = 350
    DEFAULT_JPEG_QUALITY = 95
    DEFAULT_MARGIN_PX = 0

    @classmethod
    def settings(cls):
        return QSettings(
            cls.ORGANIZATION,
            cls.APPLICATION,
        )

    @classmethod
    def get_dpi(cls):
        return int(
            cls.settings().value(
                "dpi",
                cls.DEFAULT_DPI,
            )
        )

    @classmethod
    def set_dpi(
        cls,
        dpi,
    ):
        cls.settings().setValue(
            "dpi",
            int(dpi),
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
    def get_margin_px(cls):
        margin_px = int(
            cls.settings().value(
                "margin_px",
                cls.DEFAULT_MARGIN_PX,
            )
        )

        # 負の余白や極端に大きな値を防止する
        return max(
            0,
            min(margin_px, 1000),
        )

    @classmethod
    def set_margin_px(
        cls,
        margin_px,
    ):
        safe_margin_px = max(
            0,
            min(int(margin_px), 1000),
        )

        cls.settings().setValue(
            "margin_px",
            safe_margin_px,
        )