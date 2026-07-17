from pathlib import Path

import cv2
import numpy as np

DEBUG_SAVE_IMAGE = False


def load_image(image_path):
    image = cv2.imread(str(image_path))

    if image is None:
        raise ValueError(
            f"画像を読み込めませんでした: {image_path}"
        )

    return image


def create_gray(image):
    return cv2.cvtColor(
        image,
        cv2.COLOR_BGR2GRAY,
    )

def create_horizontal_line_mask(gray):
    binary = cv2.adaptiveThreshold(
        gray,
        255,
        cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
        cv2.THRESH_BINARY_INV,
        51,
        10,
    )

    image_width = gray.shape[1]
    kernel_width = max(20, image_width // 40)

    horizontal_kernel = cv2.getStructuringElement(
        cv2.MORPH_RECT,
        (kernel_width, 1),
    )

    horizontal_mask = cv2.morphologyEx(
        binary,
        cv2.MORPH_OPEN,
        horizontal_kernel,
        iterations=1,
    )

    return horizontal_mask

def create_vertical_line_mask(gray):
    binary = cv2.adaptiveThreshold(
        gray,
        255,
        cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
        cv2.THRESH_BINARY_INV,
        51,
        10,
    )

    image_height = gray.shape[0]
    kernel_height = max(20, image_height // 40)

    vertical_kernel = cv2.getStructuringElement(
        cv2.MORPH_RECT,
        (1, kernel_height),
    )

    vertical_mask = cv2.morphologyEx(
        binary,
        cv2.MORPH_OPEN,
        vertical_kernel,
        iterations=1,
    )

    return vertical_mask

def create_bright_mask(gray):
    _, bright_mask = cv2.threshold(
        gray,
        200,
        255,
        cv2.THRESH_BINARY,
    )

    kernel = cv2.getStructuringElement(
        cv2.MORPH_RECT,
        (9, 9),
    )

    bright_mask = cv2.morphologyEx(
        bright_mask,
        cv2.MORPH_CLOSE,
        kernel,
        iterations=2,
    )

    return bright_mask

def save_debug_image(image, output_path):
    output_path = Path(output_path)
    output_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    success = cv2.imwrite(
        str(output_path),
        image,
    )

    if not success:
        raise ValueError(
            f"デバッグ画像を保存できませんでした: {output_path}"
        )

def find_likely_photos(image, contours):
    likely_photo_debug = image.copy()

    photo_size_count = 0
    likely_photo_count = 0

    return (
        photo_size_count,
        likely_photo_count,
        likely_photo_debug,
        
    )

def detect_small_photos(image_path):
    image_path = Path(image_path)

    image = load_image(image_path)
    gray = create_gray(image)
    
    bright_mask = create_bright_mask(gray)
    photo_mask = cv2.bitwise_not(bright_mask)

    horizontal_mask = create_horizontal_line_mask(gray)
    vertical_mask = create_vertical_line_mask(gray)

    combined_mask = cv2.bitwise_or(
        horizontal_mask,
        vertical_mask,
    )

    kernel = np.ones((3, 3), np.uint8)

    combined_mask = cv2.dilate(
        combined_mask,
        kernel,
        iterations=1,
    )

    close_kernel = cv2.getStructuringElement(
        cv2.MORPH_RECT,
        (25, 25),
    )

    combined_mask = cv2.morphologyEx(
        combined_mask,
        cv2.MORPH_CLOSE,
        close_kernel,
    )

    blur = cv2.GaussianBlur(
        gray,
        (9, 9),
        0,
    )

    edges = cv2.Canny(
        blur,
        30,
        90,
    )

    quad_contours, _ = cv2.findContours(
        edges,
        cv2.RETR_LIST,
        cv2.CHAIN_APPROX_SIMPLE,
    )

    quad_debug = image.copy()
    quad_count = 0

    for contour in quad_contours:
        perimeter = cv2.arcLength(contour, True)

        approx = cv2.approxPolyDP(
            contour,
            0.02 * perimeter,
            True,
        )

        if len(approx) != 4:
            continue

        x, y, w, h = cv2.boundingRect(approx)

        if w < 250:
            continue

        if h < 180:
            continue

        ratio = w / h

        if ratio < 0.6 or ratio > 2.2:
            continue

        cv2.drawContours(
            quad_debug,
            [approx],
            -1,
            (255, 0, 0),
            4,
        )

        quad_count += 1

    print("Quadrilateral candidates:", quad_count)
    
    binary = cv2.adaptiveThreshold(
        gray,
        255,
        cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
        cv2.THRESH_BINARY_INV,
        51,
        10,
    )

    kernel = cv2.getStructuringElement(
        cv2.MORPH_RECT,
        (15, 15),
    )

    closed = cv2.morphologyEx(
        binary,
        cv2.MORPH_CLOSE,
        kernel,
        iterations=1,
    )

    open_kernel = cv2.getStructuringElement(
        cv2.MORPH_RECT,
        (3, 3),
    )

    opened = cv2.morphologyEx(
        closed,
        cv2.MORPH_OPEN,
        open_kernel,
        iterations=1,
    )

    dilate_kernel = cv2.getStructuringElement(
        cv2.MORPH_RECT,
        (3, 3),
    )

    dilated = cv2.dilate(
        opened,
        dilate_kernel,
        iterations=1,
    )

    contours, hierarchy = cv2.findContours(
        photo_mask,
        cv2.RETR_CCOMP,
        cv2.CHAIN_APPROX_SIMPLE,
    )

    parent_count = 0
    child_count = 0
    large_child_count = 0

    if hierarchy is not None:
        for contour_index, contour_hierarchy in enumerate(hierarchy[0]):
            parent_index = contour_hierarchy[3]

            if parent_index == -1:
                parent_count += 1
            else:
                child_count += 1

                x, y, w, h = cv2.boundingRect(
                    contours[contour_index]
                )

                if w >= 300 and h >= 200:
                    large_child_count += 1

                    print(
                        f"large child {contour_index}: "
                        f"x={x}, y={y}, w={w}, h={h}"
                    )
    photo_size_count = 0
    likely_photo_count = 0
    likely_photo_debug = image.copy()

    for contour_index, contour in enumerate(contours):
        x, y, w, h = cv2.boundingRect(contour)

        ratio = w / h

        if w < 300 or h < 200:
            continue

        if w > 2000 or h > 1500:
            continue

        if ratio < 0.6 or ratio > 2.2:
            continue

        photo_size_count += 1

        print(
            f"photo-size contour {contour_index}: "
            f"x={x}, y={y}, w={w}, h={h}, "
            f"ratio={ratio:.2f}"
        )

        if w >= 800 and h >= 600:
            likely_photo_count += 1

            print(
                f"likely photo {contour_index}: "
                f"x={x}, y={y}, w={w}, h={h}"
            )

            cv2.rectangle(
                likely_photo_debug,
                (x, y),
                (x + w, y + h),
                (0, 0, 255),
                8,
            )

    print("Contours:", len(contours))
    print("Parent contours:", parent_count)
    print("Child contours:", child_count)
    print("Large child contours:", large_child_count)

    (
        photo_size_count,
        likely_photo_count,
        likely_photo_debug,
    ) = find_likely_photos(
        image,
        contours,
    )

    print("Photo-size contours:", photo_size_count)
    print("Likely photos:", likely_photo_count)


#   for index, contour in enumerate(contours, start=1):
#       area = cv2.contourArea(contour)
# 
#       print(
#           f"contour {index}: "
#           f"area={area:.1f}"
#       )

    contour_debug = image.copy()

    filtered_contours = []

    for contour in contours:
        area = cv2.contourArea(contour)

        if area < 1000:
            continue

        filtered_contours.append(contour)

        x, y, w, h = cv2.boundingRect(contour)

#      print(
#           f"{w} x {h}  area={area}"
#      )

    cv2.drawContours(
        contour_debug,
        filtered_contours,
        -1,
        (0, 255, 0),
        3,
    )

    rect_debug = image.copy()
    rect_count = 0

    for contour in contours:
        x, y, w, h = cv2.boundingRect(contour)

        if w < 300 or h < 300:
            continue

        cv2.rectangle(
            rect_debug,
            (x, y),
            (x + w, y + h),
            (0, 0, 255),
            5,
        )

        rect_count += 1

    print("Rectangle candidates:", rect_count)

    print("Filtered contours:", len(filtered_contours))

    if DEBUG_SAVE_IMAGE:
        project_root = Path(__file__).resolve().parent.parent
        output_dir = project_root / "tests" / "output"

        print("DEBUG_SAVE_IMAGE block entered")
        print(f"output_dir = {output_dir}")

        save_debug_image(
            gray,
            output_dir / f"{image_path.stem}_small_gray.png",
        )

        save_debug_image(
            bright_mask,
            output_dir / f"{image_path.stem}_small_bright.png",
        )

        save_debug_image(
            photo_mask,
            output_dir / f"{image_path.stem}_small_photo_mask.png",
        )

        save_debug_image(
            blur,
            output_dir / f"{image_path.stem}_small_blur.png",
        )

        save_debug_image(
            edges,
            output_dir / f"{image_path.stem}_small_edges.png",
        )

        save_debug_image(
            closed,
            output_dir / f"{image_path.stem}_small_closed.png",
        )

        save_debug_image(
            opened,
            output_dir / f"{image_path.stem}_small_opened.png",
        )

        save_debug_image(
            dilated,
            output_dir / f"{image_path.stem}_small_dilated.png",
        )

        save_debug_image(
            binary,
            output_dir / f"{image_path.stem}_small_binary.png",
        )

        save_debug_image(
            horizontal_mask,
            output_dir / f"{image_path.stem}_small_horizontal.png",
        )

        save_debug_image(
            vertical_mask,
            output_dir / f"{image_path.stem}_small_vertical.png",
        )

        save_debug_image(
            combined_mask,
            output_dir / f"{image_path.stem}_small_combined.png",
        )

        save_debug_image(
            contour_debug,
            output_dir / f"{image_path.stem}_small_contours.png",
        )

        save_debug_image(
            rect_debug,
            output_dir / f"{image_path.stem}_small_rect_candidates.png",
        )

        save_debug_image(
            likely_photo_debug,
            output_dir / f"{image_path.stem}_small_likely_photos.png",
        )

        save_debug_image(
            quad_debug,
            output_dir / f"{image_path.stem}_small_quads.png",
        )

    return []

if __name__ == "__main__":
    test_image = (
        Path(__file__).resolve().parent.parent
        / "tests"
        / "images"
        / "141-009_8.jpg"
    )

    DEBUG_SAVE_IMAGE = True

    detect_small_photos(test_image)

    print("detector_small.py の動作確認が完了しました")