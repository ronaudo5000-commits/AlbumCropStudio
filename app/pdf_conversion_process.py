import argparse
import json
import sys
import time
from pathlib import Path

import pymupdf


def send_message(
    message_type,
    **data,
):
    message = {
        "type": message_type,
        **data,
    }

    # ---------------------------------
    # QProcessの標準出力はWindows環境で
    # 必ずしもUTF-8になるとは限らない。
    #
    # 日本語を含むファイルパスが文字化けすると、
    # AlbumCrop Studio本体が存在しないパスとして
    # 受け取ってしまうため、
    # JSON通信はASCIIのみで送信する。
    #
    # json.loads() 時に \uXXXX は
    # 元のUnicode文字列へ自動復元される。
    # ---------------------------------
    print(
        json.dumps(
            message,
            ensure_ascii=True,
        ),
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

        document = pymupdf.open(
            pdf_path
        )

        pdf_name = Path(
            pdf_path
        ).stem

        total_page_count = (
            document.page_count
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
            page = document.load_page(
                page_index
            )

            pixmap = page.get_pixmap(
                dpi=300,
                colorspace=pymupdf.csRGB,
                alpha=False,
            )

            output_path = (
                output_dir
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


def main():
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

    args = parser.parse_args()

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