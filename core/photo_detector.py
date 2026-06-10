import cv2


def detect_photos(image_path):
    image = cv2.imread(image_path)

    if image is None:
        return []

    height, width = image.shape[:2]

    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    blurred = cv2.GaussianBlur(gray, (5, 5), 0)

    edges = cv2.Canny(blurred, 50, 150)

    contours, _ = cv2.findContours(
        edges,
        cv2.RETR_EXTERNAL,
        cv2.CHAIN_APPROX_SIMPLE
    )

    candidates = []

    image_area = width * height

    for contour in contours:
        x, y, w, h = cv2.boundingRect(contour)
        area = w * h

        if area < image_area * 0.02:
            continue

        if area > image_area * 0.8:
            continue

        aspect_ratio = w / h if h != 0 else 0

        if aspect_ratio < 0.4 or aspect_ratio > 3.0:
            continue

        candidates.append((x, y, w, h))

    candidates = sorted(candidates, key=lambda r: (r[1], r[0]))

    return candidates