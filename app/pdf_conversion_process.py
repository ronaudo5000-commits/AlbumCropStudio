import argparse
import ctypes
import json
import sys
import time
from ctypes import wintypes
from pathlib import Path

import pypdfium2 as pdfium


def send_message(
    message_type,
    **data,
):
    message = {
        "type": message_type,
        **data,
    }

    # 日本語のファイルパスを安全に扱うため、
    # JSON通信はASCII形式にする。
    message_bytes = (
        json.dumps(
            message,
            ensure_ascii=True,
        ) + "\n"
    ).encode("ascii")

    if (
        sys.platform == "win32"
        and getattr(sys, "frozen", False)
    ):
        # PyInstallerのGUI版では、
        # Pythonのstdoutが使えない場合がある。
        # Windowsの標準出力ハンドルを利用する。
        kernel32 = ctypes.WinDLL(
            "kernel32",
            use_last_error=True,
        )

        kernel32.GetStdHandle.argtypes = [
            wintypes.DWORD,
        ]
        kernel32.GetStdHandle.restype = (
            wintypes.HANDLE
        )

        kernel32.WriteFile.argtypes = [
            wintypes.HANDLE,
            wintypes.LPCVOID,
            wintypes.DWORD,
            ctypes.POINTER(wintypes.DWORD),
            wintypes.LPVOID,
        ]
        kernel32.WriteFile.restype = (
            wintypes.BOOL
        )

        stdout_handle = kernel32.GetStdHandle(
            0xFFFFFFF5
        )

        if stdout_handle in (
            None,
            0,
            ctypes.c_void_p(-1).value,
        ):
            raise OSError(
                "PDF Workerの標準出力を取得できません。"
            )

        buffer = ctypes.create_string_buffer(
            message_bytes
        )

        written = wintypes.DWORD(0)

        success = kernel32.WriteFile(
            stdout_handle,
            buffer,
            len(message_bytes),
            ctypes.byref(written),
            None,
        )

        if (
            not success
            or written.value != len(message_bytes)
        ):
            error_code = ctypes.get_last_error()
            raise OSError(
                "PDF Workerの通知送信に失敗しました。"
                f" Windows error: {error_code}"
            )

    else:
        # 開発環境では従来どおりprintを使用。
        print(
            message_bytes.decode("ascii"),
            end="",
            flush=True,
        )


def convert_pdf(
    pdf_path,
    output_dir,
    max_pages=None,
):
    converted_paths = []
    document = None

    try:
        pdf_path = str(
            pdf_path
        )

        output_dir = Path(
            output_dir
        )

        output_dir.mkdir(
            parents=True,
            exist_ok=True,
        )

        document = pdfium.PdfDocument(
            pdf_path
        )

        pdf_name = Path(
            pdf_path
        ).stem

        total_page_count = (
            len(document)
        )

        page_count = (
            total_page_count
        )

        if max_pages is not None:
            page_count = min(
                page_count,
                max_pages,
            )

        was_limited = (
            max_pages is not None
            and total_page_count
            > max_pages
        )

        for page_index in range(
            page_count
        ):
            page = document[page_index]

            try:
                bitmap = page.render(
                    scale=300 / 72,
                )

                try:
                    image = (
                        bitmap.to_pil().convert("RGB")
                    )

                    output_path = (
                        output_dir
                        / (
                            f"{pdf_name}_"
                            f"page_{page_index + 1:04}.png"
                        )
                    )

                    image.save(
                        str(output_path)
                    )

                finally:
                    bitmap.close()

            finally:
                page.close()

            converted_paths.append(
                str(output_path)
            )

            # ---------------------------------
            # 1ページの変換が完了した時点で、
            # AlbumCrop Studio本体へ通知する。
            #
            # PDF全体の変換完了を待たず、
            # ページ一覧への追加と
            # サムネイル生成を開始できるようにする。
            # ---------------------------------
            send_message(
                "page_ready",
                path=str(output_path),
                current=page_index + 1,
                total=page_count,
            )

            send_message(
                "progress",
                current=page_index + 1,
                total=page_count,
            )

            # ---------------------------------
            # PDF変換がCPUを連続占有しすぎないよう、
            # ページ間で短時間だけ処理を譲る。
            # ---------------------------------
            if (
                page_index + 1
                < page_count
            ):
                time.sleep(
                    0.02
                )

        send_message(
            "finished",
            paths=converted_paths,
            was_limited=was_limited,
        )

        return 0

    except Exception as e:
        send_message(
            "failed",
            message=str(e),
        )

        return 1

    finally:
        if document is not None:
            document.close()


def main(
    argv=None,
):
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--pdf",
        required=True,
    )

    parser.add_argument(
        "--output-dir",
        required=True,
    )

    parser.add_argument(
        "--max-pages",
        type=int,
        default=-1,
    )

    args = parser.parse_args(
        argv
    )

    max_pages = args.max_pages

    if max_pages < 0:
        max_pages = None

    return convert_pdf(
        pdf_path=args.pdf,
        output_dir=args.output_dir,
        max_pages=max_pages,
    )


if __name__ == "__main__":
    sys.exit(
        main()
    )