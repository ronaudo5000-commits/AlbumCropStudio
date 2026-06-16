import cv2


def detect_photos(image_path):
    image = cv2.imread(image_path)

    if image is None:
        return []

    height, width = image.shape[:2]
    image_area = width * height

    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

    median_brightness = int(cv2.medianBlur(gray, 51).mean())

    if median_brightness < 100:
        # 黒台紙アルバム用：明るい写真部分を抽出
        _, mask = cv2.threshold(
            gray,
            60,
            255,
            cv2.THRESH_BINARY,
        )
    else:
        # 明るい台紙アルバム用：台紙より暗い写真部分を抽出
        _, mask = cv2.threshold(
            gray,
            140,
            255,
            cv2.THRESH_BINARY_INV,
        )

    kernel = cv2.getStructuringElement(
        cv2.MORPH_RECT,
        (25, 25),
    )

    mask = cv2.morphologyEx(
        mask,
        cv2.MORPH_CLOSE,
        kernel,
        iterations=2,
    )

    contours, _ = cv2.findContours(
        mask,
        cv2.RETR_EXTERNAL,
        cv2.CHAIN_APPROX_SIMPLE,
    )

    candidates = []

    for contour in contours:
        x, y, w, h = cv2.boundingRect(contour)
        area = w * h

        if area < image_area * 0.015:
            continue

        if area > image_area * 0.35:
            continue

        aspect_ratio = w / h if h else 0

        if aspect_ratio < 0.3:
            continue

        if aspect_ratio > 3.5:
            continue

        if w < width * 0.06:
            continue

        if h < height * 0.06:
            continue

        candidates.append((x, y, w, h))

    candidates = sort_rects_reading_order(
        candidates
    )

    return candidates

def sort_rects_reading_order(rects):
    if not rects:
        return []

    rows = []

    row_threshold = 80

    rects = sorted(
        rects,
        key=lambda r: r[1]
    )

    for rect in rects:
        x, y, w, h = rect

        placed = False

        for row in rows:
            row_y = row[0][1]

            if abs(y - row_y) < row_threshold:
                row.append(rect)
                placed = True
                break

        if not placed:
            rows.append([rect])

    result = []

    for row in rows:
        row.sort(key=lambda r: r[0])
        result.extend(row)

    return result