from PySide6.QtCore import QSettings


class Config:
    # 既存のmain_window.pyと同じ保存場所を使用する
    ORGANIZATION = "AlbumCropStudio"
    APPLICATION = "AlbumCropStudio"

    DEFAULT_DPI = 350

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