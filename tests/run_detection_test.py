import sys
from pathlib import Path

# プロジェクトのルートフォルダを読み込み対象に追加
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from core.photo_detector import detect_photos


TEST_IMAGE_DIR = Path(__file__).parent / "images"

SUPPORTED_EXTENSIONS = {
    ".jpg",
    ".jpeg",
    ".png",
    ".tif",
    ".tiff",
}


def get_expected_count(image_path):
    try:
        return int(image_path.stem.rsplit("_", 1)[1])
    except (IndexError, ValueError):
        return None


passed = 0
failed = 0
skipped = 0

for image_path in sorted(TEST_IMAGE_DIR.iterdir()):
    if not image_path.is_file():
        continue

    if image_path.suffix.lower() not in SUPPORTED_EXTENSIONS:
        continue

    expected_count = get_expected_count(image_path)

    if expected_count is None:
        print(
            f"SKIP: {image_path.name} "
            "（ファイル名末尾に正解枚数がありません）"
        )
        skipped += 1
        continue

    detected_rects = detect_photos(str(image_path))
    detected_count = len(detected_rects)

    if detected_count == expected_count:
        print(
            f"OK:   {image_path.name} "
            f"expected={expected_count} "
            f"detected={detected_count}"
        )
        passed += 1
    else:
        print(
            f"NG:   {image_path.name} "
            f"expected={expected_count} "
            f"detected={detected_count}"
        )
        failed += 1

print()
print("----- テスト結果 -----")
print(f"成功: {passed}")
print(f"失敗: {failed}")
print(f"除外: {skipped}")
print(f"合計: {passed + failed + skipped}")

if failed > 0:
    sys.exit(1)