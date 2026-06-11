import cv2


def detect_photos(image_path):
    image = cv2.imread(image_path)

    if image is None:
        return []

    height, width = image.shape[:2]
    image_area = width * height

    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

    # 黒い台紙から、明るい写真部分を抽出
    _, mask = cv2.threshold(
        gray,
        60,
        255,
        cv2.THRESH_BINARY,
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

        if area > image_area * 0.60:
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

    candidates = sorted(
        candidates,
        key=lambda r: (r[1], r[0]),
    )

    return candidates