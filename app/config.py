from PySide6.QtCore import QSettings


class Config:
    # 既存の設定保存場所を維持する
    ORGANIZATION = "AlbumCropStudio"
    APPLICATION = "AlbumCropStudio"

    DEFAULT_DPI = 350
    DEFAULT_JPEG_QUALITY = 95

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