
import tempfile
import time
from pathlib import Path
from tkinter import Tk, filedialog

import pymupdf
import pypdfium2 as pdfium
from PIL import Image


def main():
    root = Tk()
    root.withdraw()

    pdf_path = filedialog.askopenfilename(
        title="比較するPDFを選択",
        filetypes=[("PDF files", "*.pdf")],
    )

    root.destroy()

    if not pdf_path:
        print("キャンセルしました。")
        return

    output_dir = Path(
        tempfile.mkdtemp(
            prefix="acs_pdf_compare_"
        )
    )

    print(f"PDF: {pdf_path}")
    print(f"保存先: {output_dir}")

    # PyMuPDFによる変換
    start = time.perf_counter()

    document = pymupdf.open(pdf_path)

    try:
        page = document.load_page(0)
        pixmap = page.get_pixmap(
            dpi=300,
            colorspace=pymupdf.csRGB,
            alpha=False,
        )

        pymupdf_path = (
            output_dir / "pymupdf.png"
        )
        pixmap.save(str(pymupdf_path))

        pymupdf_size = (
            pixmap.width,
            pixmap.height,
        )
    finally:
        document.close()

    pymupdf_time = (
        time.perf_counter() - start
    )

    # PDFiumによる変換
    start = time.perf_counter()

    document = pdfium.PdfDocument(pdf_path)

    try:
        page = document[0]

        try:
            bitmap = page.render(
                scale=300 / 72,
            )

            try:
                image = bitmap.to_pil().convert(
                    "RGB"
                )

                pdfium_path = (
                    output_dir / "pdfium.png"
                )
                image.save(pdfium_path)

                pdfium_size = image.size
            finally:
                bitmap.close()
        finally:
            page.close()
    finally:
        document.close()

    pdfium_time = (
        time.perf_counter() - start
    )

    print()
    print("=== 比較結果 ===")
    print(
        f"PyMuPDF 画像サイズ: {pymupdf_size}"
    )
    print(
        f"PDFium  画像サイズ: {pdfium_size}"
    )
    print(
        f"PyMuPDF 処理時間: {pymupdf_time:.3f}秒"
    )
    print(
        f"PDFium  処理時間: {pdfium_time:.3f}秒"
    )
    print(
        f"PyMuPDF PNGサイズ: "
        f"{pymupdf_path.stat().st_size:,} bytes"
    )
    print(
        f"PDFium  PNGサイズ: "
        f"{pdfium_path.stat().st_size:,} bytes"
    )
    print()
    print("比較画像:")
    print(pymupdf_path)
    print(pdfium_path)


if __name__ == "__main__":
    main()
