
from pathlib import Path
from tkinter import Tk, filedialog
import tempfile

import pypdfium2 as pdfium


def main():
    root = Tk()
    root.withdraw()

    pdf_path = filedialog.askopenfilename(
        title="テストするPDFを選択",
        filetypes=[("PDF files", "*.pdf")],
    )

    root.destroy()

    if not pdf_path:
        print("キャンセルしました。")
        return

    document = pdfium.PdfDocument(pdf_path)

    try:
        print(f"PDF: {pdf_path}")
        print(f"ページ数: {len(document)}")

        if len(document) == 0:
            return

        page = document[0]

        try:
            bitmap = page.render(
                scale=300 / 72,
            )

            image = bitmap.to_pil().convert("RGB")

            output_dir = Path(
                tempfile.mkdtemp(
                    prefix="acs_pdfium_test_"
                )
            )

            output_path = (
                output_dir / "pdfium_page_0001.png"
            )

            image.save(output_path)

            print(f"画像サイズ: {image.size}")
            print(f"画像モード: {image.mode}")
            print(f"保存先: {output_path}")
            print("変換成功")

        finally:
            page.close()

    finally:
        document.close()


if __name__ == "__main__":
    main()
