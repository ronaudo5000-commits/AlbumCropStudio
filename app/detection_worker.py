from PySide6.QtCore import (
    QObject,
    Signal,
)

from core.detection_log import (
    write_detection_log,
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
        write_detection_log(
            "worker start "
            f"path={self.image_path!r}"
        )

        try:
            rects = detect_photos(
                self.image_path
            )

            rect_list = list(
                rects
            )

            write_detection_log(
                "worker finished "
                f"detected={len(rect_list)}"
            )

            self.finished.emit(
                rect_list
            )

        except Exception as e:
            write_detection_log(
                "worker failed "
                f"exception_type="
                f"{type(e).__name__} "
                f"message={e!r}"
            )

            self.failed.emit(
                str(e)
            )