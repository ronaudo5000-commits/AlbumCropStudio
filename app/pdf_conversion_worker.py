import time
from pathlib import Path

import pymupdf

from PySide6.QtCore import (
    QObject,
    Signal,
)


class PdfConversionWorker(QObject):
    progress = Signal(
        int,
        int,
    )

    finished = Signal(
        object,
        bool,
    )

    failed = Signal(
        str,
    )

    def __init__(
        self,
        pdf_path,
        output_dir,
        max_pages=None,
        parent=None,
    ):
        super().__init__(parent)

        self.pdf_path = str(
            pdf_path
        )

        self.output_dir = Path(
            output_dir
        )

        self.max_pages = max_pages

        self.cancel_requested = False

    def cancel(self):
        self.cancel_requested = True

    def run(self):
        converted_paths = []
        document = None

        try:
            document = pymupdf.open(
                self.pdf_path
            )

            pdf_name = Path(
                self.pdf_path
            ).stem

            total_page_count = (
                document.page_count
            )

            page_count = total_page_count

            if self.max_pages is not None:
                page_count = min(
                    page_count,
                    self.max_pages,
                )

            was_limited = (
                self.max_pages is not None
                and total_page_count
                > self.max_pages
            )

            for page_index in range(
                page_count
            ):
                if self.cancel_requested:
                    return

                page = document.load_page(
                    page_index
                )

                pixmap = page.get_pixmap(
                    dpi=300,
                    colorspace=pymupdf.csRGB,
                    alpha=False,
                )

                output_path = (
                    self.output_dir
                    / (
                        f"{pdf_name}_"
                        f"page_{page_index + 1:04}.png"
                    )
                )

                pixmap.save(
                    str(output_path)
                )

                converted_paths.append(
                    str(output_path)
                )

                self.progress.emit(
                    page_index + 1,
                    page_count,
                )

                # ---------------------------------
                # PDF変換がCPUを連続占有しないよう、
                # ページ間で短時間だけ処理を譲る。
                #
                # PDF変換速度よりも、
                # GUIの応答性を優先する。
                # ---------------------------------
                if (
                    page_index + 1
                    < page_count
                ):
                    time.sleep(
                        0.02
                    )

            self.finished.emit(
                converted_paths,
                was_limited,
            )

        except Exception as e:
            self.failed.emit(
                str(e)
            )

        finally:
            if document is not None:
                document.close()