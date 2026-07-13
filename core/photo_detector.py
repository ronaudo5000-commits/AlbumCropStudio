import cv2
import numpy as np

def create_gray(image):
    return cv2.cvtColor(
        image,
        cv2.COLOR_BGR2GRAY,
    )

def create_edges(gray):
    edges = cv2.Canny(gray, 20, 80)

    kernel_edges = cv2.getStructuringElement(
        cv2.MORPH_RECT,
        (7, 7),
    )

    edges = cv2.dilate(
        edges,
        kernel_edges,
        iterations=1,
    )

    return edges

def create_mask(gray):
    mask = cv2.adaptiveThreshold(
        gray,
        255,
        cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
        cv2.THRESH_BINARY_INV,
        101,
        20,
    )

    kernel = cv2.getStructuringElement(
        cv2.MORPH_RECT,
        (15, 15),
    )

    mask = cv2.morphologyEx(
        mask,
        cv2.MORPH_CLOSE,
        kernel,
        iterations=2,
    )

    return mask

def contour_to_candidate(contour, image, edges, image_area, width, height):
    x, y, w, h = cv2.boundingRect(contour)
    area = w * h

    if area < 50000:
        return None

    img_h, img_w = image.shape[:2]
    if w > img_w * 0.9 and h > img_h * 0.5:
        return None

    ratio = w / h

    if ratio < 0.4 or ratio > 2.5:
        return None

    if ratio < 0.75 and h > w * 1.4:
        return None

    if area < image_area * 0.008:
        return None

    contour_area = cv2.contourArea(contour)
    fill_ratio = contour_area / area

    if fill_ratio < 0.30:
        return None

    perimeter = cv2.arcLength(contour, True)
    approx = cv2.approxPolyDP(
        contour,
        0.03 * perimeter,
        True,
    )

    if len(approx) < 4 or len(approx) > 12:
        return None

    x, y, w, h = grow_rect(image, x, y, w, h)

    if area > image_area * 0.35:
        return None

    if w < width * 0.06:
        return None

    if h < height * 0.06:
        return None

    roi_edges = edges[y:y + h, x:x + w]

    if roi_edges.size == 0:
        return None

    if not is_photo_like_candidate(image, edges, x, y, w, h):
        return None

    return (x, y, w, h)

def build_candidates(
    contours,
    image,
    edges,
    image_area,
    width,
    height,
):
    candidates = []

    for contour in contours:
        candidate = contour_to_candidate(
            contour,
            image,
            edges,
            image_area,
            width,
            height,
        )

        if candidate is None:
            continue

        candidates.append(candidate)

    return candidates

def find_photo_contours(mask):
    contours, _ = cv2.findContours(
        mask,
        cv2.RETR_EXTERNAL,
        cv2.CHAIN_APPROX_SIMPLE,
    )

    return contours

def find_all_contours(mask, edges):
    contours_edge, _ = cv2.findContours(
        edges,
        cv2.RETR_LIST,
        cv2.CHAIN_APPROX_SIMPLE,
    )

    contours_mask = find_photo_contours(mask)

    return (
        list(contours_edge)
        + list(contours_mask)
    )

def detect_photos(image_path):
    image = cv2.imread(image_path)

    if image is None:
        return []

    height, width = image.shape[:2]
    image_area = width * height

    gray = create_gray(image)

    edges = create_edges(gray)

    # edges = cv2.morphologyEx(
    #     edges,
    #     cv2.MORPH_CLOSE,
    #     kernel_close,
    #     iterations=1,
    # )

    # median_brightness = int(cv2.medianBlur(gray, 51).mean())

    # if median_brightness < 100:
    #     _, mask = cv2.threshold(
    #         gray,
    #         60,
    #         255,
    #         cv2.THRESH_BINARY
    #     )
    # else:
    
    mask = create_mask(gray)

    contours = find_all_contours(mask, edges)

    candidates = build_candidates(
        contours,
        image,
        edges,
        image_area,
        width,
        height,
    )

    candidates = postprocess_candidates(candidates)

    return candidates

def grow_rect(image, x, y, w, h):
    img_h, img_w = image.shape[:2]

    grow_left = 30
    padding = 12

    new_x = max(0, x - grow_left)
    new_y = max(0, y - padding)
    new_w = min(img_w - new_x, w + (x - new_x) + padding)
    new_h = min(img_h - new_y, h + padding * 2)

    return new_x, new_y, new_w, new_h

def split_large_rects(rects):
    result = []

    for rect in rects:
        x, y, w, h = rect

        # まずは何も分割しない
        result.append(rect)

    return result

def remove_inner_overlaps(candidates):
    filtered = []

    for rect in sorted(
        candidates,
        key=lambda r: r[2] * r[3],
        reverse=True,
    ):
        x, y, w, h = rect

        inside = False

        for fx, fy, fw, fh in filtered:
            if (
                x >= fx
                and y >= fy
                and x + w <= fx + fw
                and y + h <= fy + fh
            ):
                inside = True
                break

            overlap_x1 = max(x, fx)
            overlap_y1 = max(y, fy)
            overlap_x2 = min(x + w, fx + fw)
            overlap_y2 = min(y + h, fy + fh)

            overlap_w = max(0, overlap_x2 - overlap_x1)
            overlap_h = max(0, overlap_y2 - overlap_y1)

            inter = overlap_w * overlap_h

            if inter == 0:
                continue

            inside_ratio = inter / min(w * h, fw * fh)

            if inside_ratio > 0.9:
                inside = True
                break

        if not inside:
            filtered.append(rect)

    return filtered

def postprocess_candidates(candidates):
    candidates = remove_inner_overlaps(candidates)
    candidates = split_large_rects(candidates)
    candidates = remove_lower_overlap_rects(candidates)
    candidates = remove_duplicate_rects(candidates)
    candidates = sort_rects_reading_order(candidates)

    return candidates

def remove_lower_overlap_rects(rects):
    result = []

    for rect in sorted(
        rects,
        key=lambda r: r[2] * r[3],
        reverse=True,
    ):
        x, y, w, h = rect

        remove = False

        for bx, by, bw, bh in result:
            # 大きい矩形の下半分
            lower_y = by + int(bh * 0.55)

            overlap_x1 = max(x, bx)
            overlap_y1 = max(y, lower_y)
            overlap_x2 = min(x + w, bx + bw)
            overlap_y2 = min(y + h, by + bh)

            overlap_w = max(0, overlap_x2 - overlap_x1)
            overlap_h = max(0, overlap_y2 - overlap_y1)

            overlap_area = overlap_w * overlap_h
            rect_area = w * h
            
            # 大きい矩形の下側に重なっている横長矩形だけ除外
            if h < w * 0.45 and overlap_area > 0:
                remove = True
                break

            if rect_area > 0 and overlap_area / rect_area > 0.25:
                remove = True
                break

        if not remove:
            result.append(rect)

    return result

def is_photo_like_candidate(image, edges, x, y, w, h):

    roi = edges[y:y+h, x:x+w]

    if roi.size == 0:
        return False

    edge_ratio = cv2.countNonZero(roi) / roi.size

    if edge_ratio < 0.02:
        return False

    return True

def debug_long_lines(image, x, y, w, h):
    roi = image[y:y+h, x:x+w]

    if roi.size == 0:
        return

    gray = cv2.cvtColor(
        roi,
        cv2.COLOR_BGR2GRAY
    )

    edges_roi = cv2.Canny(
        gray,
        50,
        150
    )

    lines = cv2.HoughLinesP(
        edges_roi,
        1,
        np.pi / 180,
        threshold=80,
        minLineLength=int(min(w, h) * 0.5),
        maxLineGap=20,
    )

    count = 0 if lines is None else len(lines)

    print(
        f"LINES x={x}, y={y}, w={w}, h={h}, lines={count}"
    )

def remove_inner_rects(rects):
    result = []

    for i, rect in enumerate(rects):
        x, y, w, h = rect
        inside = False

        for j, other in enumerate(rects):
            if i == j:
                continue

            ox, oy, ow, oh = other

            if (
                x > ox
                and y > oy
                and x + w < ox + ow
                and y + h < oy + oh
            ):
                inside = True
                break

        if not inside:
            result.append(rect)

    return result

def merge_close_rects(rects):
    merged = []

    used = [False] * len(rects)

    for i, r1 in enumerate(rects):
        if used[i]:
            continue

        x1, y1, w1, h1 = r1
        rx1 = x1 + w1
        by1 = y1 + h1

        for j, r2 in enumerate(rects):
            if i == j or used[j]:
                continue

            x2, y2, w2, h2 = r2
            rx2 = x2 + w2
            by2 = y2 + h2

            overlap_x = min(rx1, rx2) - max(x1, x2)
            overlap_y = min(by1, by2) - max(y1, y2)

            # 少しでも重なっていたら結合
            if overlap_x > 40 and overlap_y > 40:
                nx = min(x1, x2)
                ny = min(y1, y2)
                nr = max(rx1, rx2)
                nb = max(by1, by2)

                x1 = nx
                y1 = ny
                w1 = nr - nx
                h1 = nb - ny

                used[j] = True

        merged.append((x1, y1, w1, h1))

    return merged

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

def remove_duplicate_rects(rects):
    if not rects:
        return []

    result = []

    for rect in rects:
        x1, y1, w1, h1 = rect
        area1 = w1 * h1

        duplicate = False

        for other in result:
            x2, y2, w2, h2 = other
            area2 = w2 * h2

            ix1 = max(x1, x2)
            iy1 = max(y1, y2)
            ix2 = min(x1 + w1, x2 + w2)
            iy2 = min(y1 + h1, y2 + h2)

            if ix2 <= ix1 or iy2 <= iy1:
                continue

            inter = (ix2 - ix1) * (iy2 - iy1)

            overlap = inter / min(area1, area2)

            if overlap > 0.90:
                duplicate = True
                break

        if not duplicate:
            result.append(rect)

    return result