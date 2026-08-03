from PySide6.QtCore import (
    QObject,
    Signal,
)

from core.photo_detector import detect_photos


class DetectionWorker(QObject):
    finished = Signal(list)
    failed = Signal(str)

    def __init__(
        self,
        image_path,
    ):
        super().__init__()

        self.image_path = image_path

    def run(self):
        try:
            rects = detect_photos(
                self.image_path
            )

            self.finished.emit(
                list(rects)
            )

        except Exception as e:
            self.failed.emit(
                str(e)
            )