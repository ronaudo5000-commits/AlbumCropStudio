import cv2


def detect_photos(image_path):
    image = cv2.imread(image_path)

    if image is None:
        return []

    height, width = image.shape[:2]
    image_area = width * height

    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

    blurred = cv2.GaussianBlur(gray, (5, 5), 0)

    edges = cv2.Canny(
        blurred,
        50,
        150,
    )

    contours, _ = cv2.findContours(
        edges,
        cv2.RETR_LIST,
        cv2.CHAIN_APPROX_SIMPLE,
    )

    candidates = []

    for contour in contours:

        perimeter = cv2.arcLength(
            contour,
            True,
        )

        approx = cv2.approxPolyDP(
            contour,
            0.02 * perimeter,
            True,
        )

        if len(approx) != 4:
            continue

        x, y, w, h = cv2.boundingRect(
            approx
        )

        area = w * h

        if area < image_area * 0.03:
            continue

        if area > image_area * 0.80:
            continue

        aspect_ratio = w / h

        if aspect_ratio < 0.5:
            continue

        if aspect_ratio > 2.5:
            continue

        candidates.append(
            (x, y, w, h)
        )

    filtered = []

    for rect in candidates:

        x1, y1, w1, h1 = rect

        duplicate = False

        for existing in filtered:

            x2, y2, w2, h2 = existing

            if (
                abs(x1 - x2) < 20
                and abs(y1 - y2) < 20
                and abs(w1 - w2) < 20
                and abs(h1 - h2) < 20
            ):
                duplicate = True
                break

        if not duplicate:
            filtered.append(rect)

    filtered = sorted(
        filtered,
        key=lambda r: (r[1], r[0])
    )

    return filtered