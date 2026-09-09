from PySide6.QtCore import (
    QObject,
    QSize,
    Signal,
    Qt,
)

from PySide6.QtGui import (
    QImageReader,
)


class ThumbnailWorker(QObject):
    thumbnail_ready = Signal(
        str,
        object,
    )

    failed = Signal(
        str,
        str,
    )

    finished = Signal()

    def __init__(
        self,
        file_paths,
        parent=None,
    ):
        super().__init__(parent)

        self.file_paths = list(
            file_paths
        )

        self.cancel_requested = False

    def cancel(self):
        self.cancel_requested = True

    def run(self):
        try:
            for file_path in self.file_paths:
                if self.cancel_requested:
                    break

                try:
                    reader = QImageReader(
                        str(file_path)
                    )

                    reader.setAutoTransform(
                        True
                    )

                    source_size = reader.size()

                    if (
                        source_size.isValid()
                        and source_size.width() > 0
                        and source_size.height() > 0
                    ):
                        target_size = (
                            source_size.scaled(
                                QSize(
                                    120,
                                    90,
                                ),
                                Qt.AspectRatioMode.KeepAspectRatio,
                            )
                        )

                        reader.setScaledSize(
                            target_size
                        )

                    thumbnail_image = (
                        reader.read()
                    )

                    if thumbnail_image.isNull():
                        self.failed.emit(
                            str(file_path),
                            reader.errorString(),
                        )
                        continue

                    self.thumbnail_ready.emit(
                        str(file_path),
                        thumbnail_image,
                    )

                except Exception as e:
                    self.failed.emit(
                        str(file_path),
                        str(e),
                    )

        finally:
            self.finished.emit()