import os
from pathlib import Path
import time

import cv2
import numpy as np

from core.detection_log import (
    write_detection_environment,
    write_detection_log,
)

DEBUG = False
DEBUG_SAVE_IMAGE = False

SMALL_CANDIDATE_MIN_RATIO = 0.004
SMALL_CANDIDATE_MAX_RATIO = 0.008

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

def create_small_photo_mask(gray):
    mask = cv2.adaptiveThreshold(
        gray,
        255,
        cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
        cv2.THRESH_BINARY_INV,
        101,
        20,
    )

    close_kernel = cv2.getStructuringElement(
        cv2.MORPH_RECT,
        (21, 21),
    )

    mask = cv2.morphologyEx(
        mask,
        cv2.MORPH_CLOSE,
        close_kernel,
        iterations=1,
    )

    open_kernel = cv2.getStructuringElement(
        cv2.MORPH_RECT,
        (5, 5),
    )

    mask = cv2.morphologyEx(
        mask,
        cv2.MORPH_OPEN,
        open_kernel,
        iterations=1,
    )

    return mask


def create_background_separation_mask(
    image,
):
    height, width = image.shape[:2]

    min_side = min(
        width,
        height,
    )

    border_size = max(
        10,
        int(min_side * 0.03),
    )

    lab_image = cv2.cvtColor(
        image,
        cv2.COLOR_BGR2LAB,
    )

    top_pixels = lab_image[
        :border_size,
        :,
    ].reshape(-1, 3)

    bottom_pixels = lab_image[
        height - border_size:,
        :,
    ].reshape(-1, 3)

    left_pixels = lab_image[
        :,
        :border_size,
    ].reshape(-1, 3)

    right_pixels = lab_image[
        :,
        width - border_size:,
    ].reshape(-1, 3)

    border_pixels = np.concatenate(
        (
            top_pixels,
            bottom_pixels,
            left_pixels,
            right_pixels,
        ),
        axis=0,
    )

    background_color = np.median(
        border_pixels,
        axis=0,
    ).astype(
        np.float32
    )

    lab_float = lab_image.astype(
        np.float32
    )

    difference = (
        lab_float
        - background_color
    )

    distance = np.sqrt(
        np.sum(
            difference * difference,
            axis=2,
        )
    )

    mask = np.where(
        distance > 18.0,
        255,
        0,
    ).astype(
        np.uint8
    )

    close_size = max(
        5,
        int(min_side * 0.008),
    )

    if close_size % 2 == 0:
        close_size += 1

    close_kernel = (
        cv2.getStructuringElement(
            cv2.MORPH_RECT,
            (
                close_size,
                close_size,
            ),
        )
    )

    mask = cv2.morphologyEx(
        mask,
        cv2.MORPH_CLOSE,
        close_kernel,
        iterations=1,
    )

    open_size = max(
        3,
        int(min_side * 0.002),
    )

    if open_size % 2 == 0:
        open_size += 1

    open_kernel = (
        cv2.getStructuringElement(
            cv2.MORPH_RECT,
            (
                open_size,
                open_size,
            ),
        )
    )

    mask = cv2.morphologyEx(
        mask,
        cv2.MORPH_OPEN,
        open_kernel,
        iterations=1,
    )

    return (
        mask,
        background_color,
    )


def find_background_separation_candidates(
    mask,
    width,
    height,
    image_area,
):
    contours, _ = cv2.findContours(
        mask,
        cv2.RETR_EXTERNAL,
        cv2.CHAIN_APPROX_SIMPLE,
    )

    candidates = []

    for contour in contours:
        x, y, w, h = cv2.boundingRect(
            contour
        )

        area = w * h
        area_ratio = (
            area / image_area
        )

        if area_ratio < 0.015:
            continue

        if area_ratio > 0.40:
            continue

        if w < width * 0.12:
            continue

        if h < height * 0.10:
            continue

        ratio = w / h

        if ratio < 0.35:
            continue

        if ratio > 3.0:
            continue

        candidates.append(
            (
                x,
                y,
                w,
                h,
            )
        )

    return candidates


def detect_separator_bands(
    image,
    background_color,
):
    lab_image = cv2.cvtColor(
        image,
        cv2.COLOR_BGR2LAB,
    ).astype(
        np.float32
    )

    height, width = (
        lab_image.shape[:2]
    )

    difference = (
        lab_image
        - background_color
    )

    distance = np.sqrt(
        np.sum(
            difference * difference,
            axis=2,
        )
    )

    background_like = (
        distance < 20.0
    ).astype(
        np.float32
    )

    def find_runs(
        values,
        min_length,
    ):
        runs = []
        start = None

        for index, value in enumerate(
            values
        ):
            if value:
                if start is None:
                    start = index
            else:
                if start is not None:
                    if (
                        index - start
                        >= min_length
                    ):
                        runs.append(
                            (
                                start,
                                index - 1,
                            )
                        )

                    start = None

        if start is not None:
            if (
                len(values) - start
                >= min_length
            ):
                runs.append(
                    (
                        start,
                        len(values) - 1,
                    )
                )

        return runs

    horizontal_background_ratio = (
        np.mean(
            background_like,
            axis=1,
        )
    )

    horizontal_separator_flags = (
        horizontal_background_ratio
        > 0.60
    )

    horizontal_runs = find_runs(
        horizontal_separator_flags,
        max(
            10,
            int(height * 0.004),
        ),
    )

    inner_horizontal_runs = []

    outer_margin = int(
        height * 0.04
    )

    for start, end in horizontal_runs:
        center = int(
            (start + end) / 2
        )

        if center <= outer_margin:
            continue

        if center >= (
            height - outer_margin
        ):
            continue

        inner_horizontal_runs.append(
            (
                start,
                end,
            )
        )

    horizontal_centers = [
        int(
            (start + end) / 2
        )
        for start, end
        in inner_horizontal_runs
    ]

    row_boundaries = [
        0,
        *horizontal_centers,
        height,
    ]

    row_regions = []

    for index in range(
        len(row_boundaries) - 1
    ):
        y1 = row_boundaries[index]
        y2 = row_boundaries[index + 1]

        row_height = y2 - y1

        if row_height < height * 0.12:
            continue

        row_regions.append(
            (
                y1,
                y2,
            )
        )

    row_vertical_runs = []

    for row_index, (
        y1,
        y2,
    ) in enumerate(
        row_regions,
        start=1,
    ):
        row_background_like = (
            background_like[
                y1:y2,
                :,
            ]
        )

        vertical_background_ratio = (
            np.mean(
                row_background_like,
                axis=0,
            )
        )

        vertical_separator_flags = (
            vertical_background_ratio
            > 0.60
        )

        vertical_runs = find_runs(
            vertical_separator_flags,
            max(
                10,
                int(width * 0.004),
            ),
        )

        inner_vertical_runs = []

        side_margin = int(
            width * 0.05
        )

        for start, end in vertical_runs:
            center = int(
                (start + end) / 2
            )

            if center <= side_margin:
                continue

            if center >= (
                width - side_margin
            ):
                continue

            inner_vertical_runs.append(
                (
                    start,
                    end,
                )
            )

        row_vertical_runs.append(
            (
                row_index,
                y1,
                y2,
                inner_vertical_runs,
            )
        )

    write_detection_log(
        "separator analysis "
        f"horizontal="
        f"{inner_horizontal_runs} "
        f"rows={row_regions} "
        f"row_vertical="
        f"{row_vertical_runs}"
    )

    return (
        inner_horizontal_runs,
        row_regions,
        row_vertical_runs,
    )


def save_separator_debug_image(
    image,
    horizontal_runs,
    row_regions,
    row_vertical_runs,
    image_path,
):
    if not DEBUG_SAVE_IMAGE:
        return

    debug_image = image.copy()

    height, width = (
        debug_image.shape[:2]
    )

    for start, end in horizontal_runs:
        center = int(
            (start + end) / 2
        )

        cv2.line(
            debug_image,
            (0, center),
            (width, center),
            (255, 0, 0),
            5,
        )

    for (
        row_index,
        y1,
        y2,
        vertical_runs,
    ) in row_vertical_runs:
        for start, end in vertical_runs:
            center = int(
                (start + end) / 2
            )

            cv2.line(
                debug_image,
                (center, y1),
                (center, y2),
                (0, 0, 255),
                5,
            )

        cv2.putText(
            debug_image,
            f"ROW {row_index}",
            (
                20,
                min(
                    y2 - 10,
                    y1 + 60,
                ),
            ),
            cv2.FONT_HERSHEY_SIMPLEX,
            1.5,
            (0, 255, 0),
            4,
            cv2.LINE_AA,
        )

    output_dir = (
        Path(__file__).resolve().parent.parent
        / "tests"
        / "output"
    )

    output_dir.mkdir(
        parents=True,
        exist_ok=True,
    )

    image_name = Path(
        image_path
    ).stem

    output_path = (
        output_dir
        / (
            f"{image_name}_"
            "separator_debug.jpg"
        )
    )

    cv2.imwrite(
        str(output_path),
        debug_image,
    )

    write_detection_log(
        "separator debug "
        f"horizontal={horizontal_runs} "
        f"rows={row_regions} "
        f"row_vertical="
        f"{row_vertical_runs}"
    )


def build_layout_cells(
    image,
    row_regions,
    row_vertical_runs,
):
    height, width = image.shape[:2]

    vertical_by_row = {}

    for (
        row_index,
        y1,
        y2,
        vertical_runs,
    ) in row_vertical_runs:
        vertical_by_row[
            row_index
        ] = vertical_runs

    cells = []

    for row_index, (
        y1,
        y2,
    ) in enumerate(
        row_regions,
        start=1,
    ):
        vertical_runs = (
            vertical_by_row.get(
                row_index,
                [],
            )
        )

        vertical_centers = [
            int(
                (start + end) / 2
            )
            for start, end
            in vertical_runs
        ]

        x_boundaries = [
            0,
            *vertical_centers,
            width,
        ]

        for index in range(
            len(x_boundaries) - 1
        ):
            x1 = x_boundaries[index]
            x2 = x_boundaries[
                index + 1
            ]

            cell_width = x2 - x1
            cell_height = y2 - y1

            if (
                cell_width
                < width * 0.15
            ):
                continue

            if (
                cell_height
                < height * 0.12
            ):
                continue

            cells.append(
                (
                    x1,
                    y1,
                    cell_width,
                    cell_height,
                )
            )

    write_detection_log(
        "layout cells "
        f"count={len(cells)} "
        f"cells={cells}"
    )

    return cells


def fit_layout_cells_to_photos(
    image,
    layout_cells,
    background_color,
):
    lab_image = cv2.cvtColor(
        image,
        cv2.COLOR_BGR2LAB,
    ).astype(
        np.float32
    )

    fitted_cells = []

    fit_success_count = 0
    fit_failed_count = 0
    fit_rejected_count = 0
    empty_cell_count = 0

    for cell_number, (
        x,
        y,
        w,
        h,
    ) in enumerate(
        layout_cells,
        start=1,
    ):
        cell_lab = lab_image[
            y:y + h,
            x:x + w,
        ]

        if cell_lab.size == 0:
            empty_cell_count += 1

            continue

        difference = (
            cell_lab
            - background_color
        )

        distance = np.sqrt(
            np.sum(
                difference * difference,
                axis=2,
            )
        )

        foreground_like = (
            distance >= 20.0
        ).astype(
            np.float32
        )

        column_ratio = np.mean(
            foreground_like,
            axis=0,
        )

        row_ratio = np.mean(
            foreground_like,
            axis=1,
        )

        def smooth_profile(
            profile,
            window_size,
        ):
            window_size = max(
                3,
                int(window_size),
            )

            if window_size % 2 == 0:
                window_size += 1

            kernel = np.ones(
                window_size,
                dtype=np.float32,
            ) / window_size

            return np.convolve(
                profile,
                kernel,
                mode="same",
            )

        column_ratio = smooth_profile(
            column_ratio,
            max(
                5,
                int(w * 0.015),
            ),
        )

        row_ratio = smooth_profile(
            row_ratio,
            max(
                5,
                int(h * 0.015),
            ),
        )

        column_flags = (
            column_ratio > 0.45
        )

        row_flags = (
            row_ratio > 0.45
        )

        def largest_run(flags):
            best_start = None
            best_end = None
            best_length = 0

            start = None

            for index, value in enumerate(
                flags
            ):
                if value:
                    if start is None:
                        start = index
                else:
                    if start is not None:
                        length = (
                            index - start
                        )

                        if length > best_length:
                            best_start = start
                            best_end = index - 1
                            best_length = length

                        start = None

            if start is not None:
                length = (
                    len(flags) - start
                )

                if length > best_length:
                    best_start = start
                    best_end = (
                        len(flags) - 1
                    )

            return (
                best_start,
                best_end,
            )

        def find_strong_top_edge(
            cell_image,
        ):
            gray_cell = cv2.cvtColor(
                cell_image,
                cv2.COLOR_BGR2GRAY,
            ).astype(
                np.float32
            )

            cell_h, cell_w = (
                gray_cell.shape[:2]
            )

            if (
                cell_h < 2
                or cell_w < 20
            ):
                return None

            margin_x = max(
                1,
                int(cell_w * 0.05),
            )

            search_end = max(
                2,
                int(cell_h * 0.20),
            )

            center_area = gray_cell[
                :search_end,
                margin_x:cell_w - margin_x,
            ]

            if (
                center_area.shape[0] < 2
                or center_area.shape[1] < 2
            ):
                return None

            row_difference = np.mean(
                np.abs(
                    center_area[1:, :]
                    - center_area[:-1, :]
                ),
                axis=1,
            )

            if row_difference.size == 0:
                return None

            edge_index = int(
                np.argmax(
                    row_difference
                )
            )

            edge_strength = float(
                row_difference[
                    edge_index
                ]
            )

            if edge_strength < 20.0:
                return None

            return edge_index + 1

        left, right = largest_run(
            column_flags
        )

        top, bottom = largest_run(
            row_flags
        )

        if (
            left is None
            or right is None
            or top is None
            or bottom is None
        ):
            fit_failed_count += 1

            write_detection_log(
                "layout fit failed "
                f"cell={cell_number}"
            )

            fitted_cells.append(
                (
                    x,
                    y,
                    w,
                    h,
                )
            )

            continue

        original_top = top

        if top > h * 0.20:
            cell_image = image[
                y:y + h,
                x:x + w,
            ]

            edge_top = (
                find_strong_top_edge(
                    cell_image
                )
            )

            if edge_top is not None:
                top = edge_top

                write_detection_log(
                    "layout fit top corrected "
                    f"cell={cell_number} "
                    f"color_top={original_top} "
                    f"edge_top={edge_top}"
                )

        fitted_x = x + left
        fitted_y = y + top

        fitted_w = (
            right - left + 1
        )

        fitted_h = (
            bottom - top + 1
        )

        if (
            fitted_w < w * 0.45
            or fitted_h < h * 0.45
        ):
            fit_rejected_count += 1

            write_detection_log(
                "layout fit rejected "
                f"cell={cell_number} "
                f"original="
                f"({x},{y},{w},{h}) "
                f"fitted="
                f"({fitted_x},"
                f"{fitted_y},"
                f"{fitted_w},"
                f"{fitted_h})"
            )

            fitted_cells.append(
                (
                    x,
                    y,
                    w,
                    h,
                )
            )

            continue

        fitted_cells.append(
            (
                fitted_x,
                fitted_y,
                fitted_w,
                fitted_h,
            )
        )

        fit_success_count += 1

        write_detection_log(
            "layout fit "
            f"cell={cell_number} "
            f"original="
            f"({x},{y},{w},{h}) "
            f"fitted="
            f"({fitted_x},"
            f"{fitted_y},"
            f"{fitted_w},"
            f"{fitted_h})"
        )

    cell_count = len(
        layout_cells
    )

    fit_success_ratio = 0.0

    if cell_count > 0:
        fit_success_ratio = (
            fit_success_count
            / cell_count
        )

    write_detection_log(
        "layout fit summary "
        f"cells={cell_count} "
        f"fitted={fit_success_count} "
        f"failed={fit_failed_count} "
        f"rejected={fit_rejected_count} "
        f"empty={empty_cell_count} "
        f"fit_success_ratio="
        f"{fit_success_ratio:.3f}"
    )

    return (
        fitted_cells,
        fit_success_ratio,
    )


def find_bright_frame_candidates(
    image,
    image_area,
):
    gray = cv2.cvtColor(
        image,
        cv2.COLOR_BGR2GRAY,
    )

    height, width = gray.shape[:2]

    bright_mask = np.where(
        gray >= 200,
        255,
        0,
    ).astype(
        np.uint8
    )

    min_side = min(
        width,
        height,
    )

    close_size = max(
        5,
        int(min_side * 0.004),
    )

    if close_size % 2 == 0:
        close_size += 1

    close_kernel = (
        cv2.getStructuringElement(
            cv2.MORPH_RECT,
            (
                close_size,
                close_size,
            ),
        )
    )

    bright_mask = cv2.morphologyEx(
        bright_mask,
        cv2.MORPH_CLOSE,
        close_kernel,
        iterations=1,
    )

    contours, _ = cv2.findContours(
        bright_mask,
        cv2.RETR_LIST,
        cv2.CHAIN_APPROX_SIMPLE,
    )

    candidates = []

    for contour in contours:
        x, y, w, h = cv2.boundingRect(
            contour
        )

        area = w * h
        area_ratio = (
            area / image_area
        )

        if area_ratio < 0.010:
            continue

        if area_ratio > 0.080:
            continue

        if w < width * 0.08:
            continue

        if h < height * 0.08:
            continue

        ratio = w / h

        if ratio < 0.55:
            continue

        if ratio > 2.20:
            continue

        candidates.append(
            (
                x,
                y,
                w,
                h,
            )
        )

    candidates = remove_duplicate_rects(
        candidates
    )

    write_detection_log(
        "bright frame candidates "
        f"contours={len(contours)} "
        f"candidates={len(candidates)} "
        f"rects={candidates}"
    )

    return (
        bright_mask,
        candidates,
    )


def log_bright_frame_regularity(
    bright_frame_candidates,
):
    candidate_count = len(
        bright_frame_candidates
    )

    if candidate_count == 0:
        write_detection_log(
            "bright frame regularity "
            "count=0 "
            "width_cv=0.0000 "
            "height_cv=0.0000 "
            "area_cv=0.0000"
        )

        return False

    for candidate_number, (
        x,
        y,
        w,
        h,
    ) in enumerate(
        bright_frame_candidates,
        start=1,
    ):
        area = w * h
        aspect_ratio = (
            w / h
            if h > 0
            else 0.0
        )

        write_detection_log(
            "bright frame candidate detail "
            f"number={candidate_number} "
            f"x={x} "
            f"y={y} "
            f"w={w} "
            f"h={h} "
            f"area={area} "
            f"aspect_ratio={aspect_ratio:.3f}"
        )

    candidate_centers_x = [
        x + (w / 2.0)
        for (
            x,
            y,
            w,
            h,
        )
        in bright_frame_candidates
    ]

    candidate_centers_y = [
        y + (h / 2.0)
        for (
            x,
            y,
            w,
            h,
        )
        in bright_frame_candidates
    ]

    median_width = float(
        np.median(
            [
                w
                for (
                    x,
                    y,
                    w,
                    h,
                )
                in bright_frame_candidates
            ]
        )
    )

    median_height = float(
        np.median(
            [
                h
                for (
                    x,
                    y,
                    w,
                    h,
                )
                in bright_frame_candidates
            ]
        )
    )

    def cluster_positions(
        values,
        tolerance,
    ):
        clusters = []

        for value in sorted(values):
            matched_cluster = None

            for cluster in clusters:
                cluster_center = float(
                    np.mean(cluster)
                )

                if (
                    abs(
                        value - cluster_center
                    )
                    <= tolerance
                ):
                    matched_cluster = cluster
                    break

            if matched_cluster is None:
                clusters.append(
                    [value]
                )
            else:
                matched_cluster.append(
                    value
                )

        return [
            float(
                np.mean(cluster)
            )
            for cluster in clusters
        ]

    column_centers = cluster_positions(
        candidate_centers_x,
        median_width * 0.50,
    )

    row_centers = cluster_positions(
        candidate_centers_y,
        median_height * 0.50,
    )

    occupied_cells = set()

    for center_x, center_y in zip(
        candidate_centers_x,
        candidate_centers_y,
    ):
        column_index = min(
            range(len(column_centers)),
            key=lambda index: abs(
                center_x
                - column_centers[index]
            ),
        )

        row_index = min(
            range(len(row_centers)),
            key=lambda index: abs(
                center_y
                - row_centers[index]
            ),
        )

        occupied_cells.add(
            (
                column_index,
                row_index,
            )
        )

    column_count = len(
        column_centers
    )

    row_count = len(
        row_centers
    )

    expected_cell_count = (
        column_count * row_count
    )

    occupied_cell_count = len(
        occupied_cells
    )

    duplicate_cell_count = (
        candidate_count
        - occupied_cell_count
    )

    grid_fill_ratio = 0.0

    if expected_cell_count > 0:
        grid_fill_ratio = (
            occupied_cell_count
            / expected_cell_count
        )

    write_detection_log(
        "bright frame grid "
        f"columns={column_count} "
        f"rows={row_count} "
        f"expected_cells={expected_cell_count} "
        f"occupied_cells={occupied_cell_count} "
        f"duplicate_cells={duplicate_cell_count} "
        f"fill_ratio={grid_fill_ratio:.3f} "
        f"column_centers="
        f"{[round(value, 1) for value in column_centers]} "
        f"row_centers="
        f"{[round(value, 1) for value in row_centers]}"
    )

    widths = np.array(
        [
            w
            for (
                x,
                y,
                w,
                h,
            )
            in bright_frame_candidates
        ],
        dtype=np.float32,
    )

    heights = np.array(
        [
            h
            for (
                x,
                y,
                w,
                h,
            )
            in bright_frame_candidates
        ],
        dtype=np.float32,
    )

    areas = (
        widths * heights
    )

    width_mean = float(
        np.mean(
            widths
        )
    )

    height_mean = float(
        np.mean(
            heights
        )
    )

    area_mean = float(
        np.mean(
            areas
        )
    )

    width_cv = 0.0
    height_cv = 0.0
    area_cv = 0.0

    if width_mean > 0.0:
        width_cv = float(
            np.std(
                widths
            )
            / width_mean
        )

    if height_mean > 0.0:
        height_cv = float(
            np.std(
                heights
            )
            / height_mean
        )

    if area_mean > 0.0:
        area_cv = float(
            np.std(
                areas
            )
            / area_mean
        )

    candidate_count_ok = (
        candidate_count >= 4
    )

    regularity_ok = (
        width_cv <= 0.05
        and height_cv <= 0.05
        and area_cv <= 0.05
    )

    complete_grid_ok = (
        candidate_count >= 6
        and column_count >= 2
        and row_count >= 2
        and duplicate_cell_count == 0
        and grid_fill_ratio >= 0.95
    )

    trusted = (
        candidate_count_ok
        and (
            regularity_ok
            or complete_grid_ok
        )
    )

    write_detection_log(
        "bright frame regularity "
        f"count={candidate_count} "
        f"candidate_count_ok={candidate_count_ok} "
        f"width_cv={width_cv:.4f} "
        f"height_cv={height_cv:.4f} "
        f"area_cv={area_cv:.4f} "
        f"regularity_ok={regularity_ok} "
        f"complete_grid_ok={complete_grid_ok} "
        f"trusted={trusted}"
    )

    return trusted


def find_dark_hole_candidates(
    bright_mask,
    image_area,
):
    height, width = (
        bright_mask.shape[:2]
    )

    dark_mask = cv2.bitwise_not(
        bright_mask
    )

    min_side = min(
        width,
        height,
    )

    close_size = max(
        7,
        int(min_side * 0.008),
    )

    if close_size % 2 == 0:
        close_size += 1

    close_kernel = (
        cv2.getStructuringElement(
            cv2.MORPH_RECT,
            (
                close_size,
                close_size,
            ),
        )
    )

    dark_mask = cv2.morphologyEx(
        dark_mask,
        cv2.MORPH_CLOSE,
        close_kernel,
        iterations=1,
    )

    open_size = max(
        3,
        int(min_side * 0.002),
    )

    if open_size % 2 == 0:
        open_size += 1

    open_kernel = (
        cv2.getStructuringElement(
            cv2.MORPH_RECT,
            (
                open_size,
                open_size,
            ),
        )
    )

    dark_mask = cv2.morphologyEx(
        dark_mask,
        cv2.MORPH_OPEN,
        open_kernel,
        iterations=1,
    )

    contours, _ = cv2.findContours(
        dark_mask,
        cv2.RETR_EXTERNAL,
        cv2.CHAIN_APPROX_SIMPLE,
    )

    candidates = []

    border_margin = max(
        5,
        int(min_side * 0.01),
    )

    for contour in contours:
        x, y, w, h = cv2.boundingRect(
            contour
        )

        if (
            x <= border_margin
            or y <= border_margin
            or x + w
            >= width - border_margin
            or y + h
            >= height - border_margin
        ):
            continue

        area = w * h

        area_ratio = (
            area / image_area
        )

        if area_ratio < 0.015:
            continue

        if area_ratio > 0.12:
            continue

        if w < width * 0.10:
            continue

        if h < height * 0.10:
            continue

        ratio = w / h

        if ratio < 0.55:
            continue

        if ratio > 2.50:
            continue

        contour_area = cv2.contourArea(
            contour
        )

        if area <= 0:
            continue

        fill_ratio = (
            contour_area / area
        )

        if fill_ratio < 0.60:
            continue

        candidates.append(
            (
                x,
                y,
                w,
                h,
            )
        )

    candidates = remove_duplicate_rects(
        candidates
    )

    write_detection_log(
        "dark hole candidates "
        f"contours={len(contours)} "
        f"candidates={len(candidates)} "
        f"rects={candidates}"
    )

    return (
        dark_mask,
        candidates,
    )


def create_small_photo_line_debug(image, edges):
    debug_image = image.copy()

    height, width = image.shape[:2]
    min_side = min(width, height)

    lines = cv2.HoughLinesP(
        edges,
        1,
        np.pi / 180,
        threshold=80,
        minLineLength=int(min_side * 0.05),
        maxLineGap=int(min_side * 0.01),
    )

    line_count = 0

    if lines is not None:
        for line in lines:
            x1, y1, x2, y2 = line[0]

            dx = abs(x2 - x1)
            dy = abs(y2 - y1)

            # 水平または垂直に近い線だけ表示
            if dx >= dy * 4 or dy >= dx * 4:
                cv2.line(
                    debug_image,
                    (x1, y1),
                    (x2, y2),
                    (0, 0, 255),
                    3,
                )
                line_count += 1

    if DEBUG:
        print(f"small photo line count={line_count}")

    return debug_image

def get_image_info(image):
    height, width = image.shape[:2]
    image_area = width * height

    return width, height, image_area

def contour_to_candidate(
    contour,
    image,
    edges,
    image_area,
    width,
    height,
    allow_small=False,
):
    x, y, w, h = cv2.boundingRect(contour)
    area = w * h

    if area < 50000:
        return None

    img_h, img_w = image.shape[:2]

    if (
        w > img_w * 0.9
        and h > img_h * 0.5
    ):
        return None

    ratio = w / h

    if ratio < 0.4 or ratio > 2.5:
        return None

    if ratio < 0.75 and h > w * 1.4:
        return None

    area_ratio = area / image_area

    if allow_small:
        if (
            area_ratio
            < SMALL_CANDIDATE_MIN_RATIO
        ):
            return None

        if (
            area_ratio
            >= SMALL_CANDIDATE_MAX_RATIO
        ):
            return None

    else:
        if (
            area_ratio
            < SMALL_CANDIDATE_MAX_RATIO
        ):
            return None

    contour_area = cv2.contourArea(
        contour
    )

    fill_ratio = contour_area / area

    if fill_ratio < 0.30:
        return None

    perimeter = cv2.arcLength(
        contour,
        True,
    )

    approx = cv2.approxPolyDP(
        contour,
        0.03 * perimeter,
        True,
    )

    if (
        len(approx) < 4
        or len(approx) > 12
    ):
        return None

    x, y, w, h = grow_rect(
        image,
        x,
        y,
        w,
        h,
    )

    if area > image_area * 0.35:
        return None

    if w < width * 0.06:
        return None

    if h < height * 0.06:
        return None

    roi_edges = edges[
        y:y + h,
        x:x + w,
    ]

    if roi_edges.size == 0:
        return None

    if not is_photo_like_candidate(
        image,
        edges,
        x,
        y,
        w,
        h,
    ):
        return None

    if DEBUG and allow_small:
        print(
            f"SMALL candidate accepted "
            f"x={x}, y={y}, "
            f"w={w}, h={h}, "
            f"area_ratio={area_ratio:.5f}, "
            f"shape_ratio={ratio:.2f}"
        )

    return (x, y, w, h)


def log_small_candidate_diagnostics(
    contours,
    image,
    edges,
    image_area,
    width,
    height,
):
    counts = {
        "total": 0,
        "area_too_small": 0,
        "page_like": 0,
        "bad_ratio": 0,
        "portrait_rejected": 0,
        "area_ratio_low": 0,
        "area_ratio_high": 0,
        "fill_ratio_low": 0,
        "bad_polygon": 0,
        "area_too_large": 0,
        "width_too_small": 0,
        "height_too_small": 0,
        "empty_roi": 0,
        "edge_ratio_low": 0,
        "accepted": 0,
    }

    img_h, img_w = image.shape[:2]

    for contour in contours:
        counts["total"] += 1

        x, y, w, h = cv2.boundingRect(
            contour
        )

        area = w * h

        if area < 50000:
            counts[
                "area_too_small"
            ] += 1
            continue

        if (
            w > img_w * 0.9
            and h > img_h * 0.5
        ):
            counts["page_like"] += 1
            continue

        ratio = w / h

        if ratio < 0.4 or ratio > 2.5:
            counts["bad_ratio"] += 1
            continue

        if (
            ratio < 0.75
            and h > w * 1.4
        ):
            counts[
                "portrait_rejected"
            ] += 1
            continue

        area_ratio = area / image_area

        if (
            area_ratio
            < SMALL_CANDIDATE_MIN_RATIO
        ):
            counts[
                "area_ratio_low"
            ] += 1
            continue

        if (
            area_ratio
            >= SMALL_CANDIDATE_MAX_RATIO
        ):
            counts[
                "area_ratio_high"
            ] += 1
            continue

        contour_area = cv2.contourArea(
            contour
        )

        fill_ratio = contour_area / area

        if fill_ratio < 0.30:
            counts[
                "fill_ratio_low"
            ] += 1
            continue

        perimeter = cv2.arcLength(
            contour,
            True,
        )

        approx = cv2.approxPolyDP(
            contour,
            0.03 * perimeter,
            True,
        )

        if (
            len(approx) < 4
            or len(approx) > 12
        ):
            counts[
                "bad_polygon"
            ] += 1
            continue

        x, y, w, h = grow_rect(
            image,
            x,
            y,
            w,
            h,
        )

        if area > image_area * 0.35:
            counts[
                "area_too_large"
            ] += 1
            continue

        if w < width * 0.06:
            counts[
                "width_too_small"
            ] += 1
            continue

        if h < height * 0.06:
            counts[
                "height_too_small"
            ] += 1
            continue

        roi_edges = edges[
            y:y + h,
            x:x + w,
        ]

        if roi_edges.size == 0:
            counts[
                "empty_roi"
            ] += 1
            continue

        edge_ratio = (
            cv2.countNonZero(
                roi_edges
            )
            / roi_edges.size
        )

        if edge_ratio < 0.02:
            counts[
                "edge_ratio_low"
            ] += 1
            continue

        counts["accepted"] += 1

    diagnostic_text = " ".join(
        f"{key}={value}"
        for key, value
        in counts.items()
    )

    write_detection_log(
        "small candidate diagnostics "
        + diagnostic_text
    )


def log_candidate_metrics(
    candidate_number,
    candidate,
    contour,
    image,
    edges,
    image_area,
    candidate_type,
):
    x, y, w, h = candidate

    area = w * h
    area_ratio = area / image_area

    shape_ratio = w / h

    contour_area = cv2.contourArea(
        contour
    )

    (
        original_x,
        original_y,
        original_w,
        original_h,
    ) = cv2.boundingRect(
        contour
    )

    original_area = (
        original_w * original_h
    )

    if original_area > 0:
        fill_ratio = (
            contour_area
            / original_area
        )
    else:
        fill_ratio = 0.0

    perimeter = cv2.arcLength(
        contour,
        True,
    )

    approx = cv2.approxPolyDP(
        contour,
        0.03 * perimeter,
        True,
    )

    roi_edges = edges[
        y:y + h,
        x:x + w,
    ]

    edge_ratio = 0.0

    top_border_evidence = 0.0
    bottom_border_evidence = 0.0
    left_border_evidence = 0.0
    right_border_evidence = 0.0

    top_border_run_ratio = 0.0
    bottom_border_run_ratio = 0.0
    left_border_run_ratio = 0.0
    right_border_run_ratio = 0.0

    def longest_run_ratio(
        values,
    ):
        if values.size == 0:
            return 0.0

        flags = (
            values > 0
        )

        longest_run = 0
        current_run = 0

        for value in flags:
            if value:
                current_run += 1

                if current_run > longest_run:
                    longest_run = current_run
            else:
                current_run = 0

        return (
            longest_run
            / len(flags)
        )

    if roi_edges.size > 0:
        edge_ratio = (
            cv2.countNonZero(
                roi_edges
            )
            / roi_edges.size
        )

        border_band = max(
            3,
            min(
                40,
                int(
                    min(w, h) * 0.02
                ),
            ),
        )

        top_band = roi_edges[
            :border_band,
            :,
        ]

        bottom_band = roi_edges[
            max(
                0,
                h - border_band,
            ):h,
            :,
        ]

        left_band = roi_edges[
            :,
            :border_band,
        ]

        right_band = roi_edges[
            :,
            max(
                0,
                w - border_band,
            ):w,
        ]

        if top_band.size > 0:
            top_row_ratios = (
                np.count_nonzero(
                    top_band,
                    axis=1,
                )
                / top_band.shape[1]
            )

            top_row_index = int(
                np.argmax(
                    top_row_ratios
                )
            )

            top_border_evidence = float(
                top_row_ratios[
                    top_row_index
                ]
            )

            top_border_run_ratio = (
                longest_run_ratio(
                    top_band[
                        top_row_index,
                        :,
                    ]
                )
            )

        if bottom_band.size > 0:
            bottom_row_ratios = (
                np.count_nonzero(
                    bottom_band,
                    axis=1,
                )
                / bottom_band.shape[1]
            )

            bottom_row_index = int(
                np.argmax(
                    bottom_row_ratios
                )
            )

            bottom_border_evidence = float(
                bottom_row_ratios[
                    bottom_row_index
                ]
            )

            bottom_border_run_ratio = (
                longest_run_ratio(
                    bottom_band[
                        bottom_row_index,
                        :,
                    ]
                )
            )

        if left_band.size > 0:
            left_column_ratios = (
                np.count_nonzero(
                    left_band,
                    axis=0,
                )
                / left_band.shape[0]
            )

            left_column_index = int(
                np.argmax(
                    left_column_ratios
                )
            )

            left_border_evidence = float(
                left_column_ratios[
                    left_column_index
                ]
            )

            left_border_run_ratio = (
                longest_run_ratio(
                    left_band[
                        :,
                        left_column_index,
                    ]
                )
            )

        if right_band.size > 0:
            right_column_ratios = (
                np.count_nonzero(
                    right_band,
                    axis=0,
                )
                / right_band.shape[0]
            )

            right_column_index = int(
                np.argmax(
                    right_column_ratios
                )
            )

            right_border_evidence = float(
                right_column_ratios[
                    right_column_index
                ]
            )

            right_border_run_ratio = (
                longest_run_ratio(
                    right_band[
                        :,
                        right_column_index,
                    ]
                )
            )

    roi_image = image[
        y:y + h,
        x:x + w,
    ]

    gray_mean = 0.0
    gray_std = 0.0
    saturation_mean = 0.0
    saturation_std = 0.0

    if roi_image.size > 0:
        roi_gray = cv2.cvtColor(
            roi_image,
            cv2.COLOR_BGR2GRAY,
        )

        gray_mean = float(
            np.mean(
                roi_gray
            )
        )

        gray_std = float(
            np.std(
                roi_gray
            )
        )

        roi_hsv = cv2.cvtColor(
            roi_image,
            cv2.COLOR_BGR2HSV,
        )

        saturation = roi_hsv[
            :,
            :,
            1,
        ]

        saturation_mean = float(
            np.mean(
                saturation
            )
        )

        saturation_std = float(
            np.std(
                saturation
            )
        )

    write_detection_log(
        "candidate metrics "
        f"number={candidate_number} "
        f"type={candidate_type} "
        f"x={x} "
        f"y={y} "
        f"w={w} "
        f"h={h} "
        f"area_ratio={area_ratio:.5f} "
        f"shape_ratio={shape_ratio:.3f} "
        f"fill_ratio={fill_ratio:.3f} "
        f"edge_ratio={edge_ratio:.3f} "
        f"top_border_evidence="
        f"{top_border_evidence:.3f} "
        f"bottom_border_evidence="
        f"{bottom_border_evidence:.3f} "
        f"left_border_evidence="
        f"{left_border_evidence:.3f} "
        f"right_border_evidence="
        f"{right_border_evidence:.3f} "
        f"top_border_run_ratio="
        f"{top_border_run_ratio:.3f} "
        f"bottom_border_run_ratio="
        f"{bottom_border_run_ratio:.3f} "
        f"left_border_run_ratio="
        f"{left_border_run_ratio:.3f} "
        f"right_border_run_ratio="
        f"{right_border_run_ratio:.3f} "
        f"gray_mean={gray_mean:.2f} "
        f"gray_std={gray_std:.2f} "
        f"saturation_mean="
        f"{saturation_mean:.2f} "
        f"saturation_std="
        f"{saturation_std:.2f} "
        f"vertices={len(approx)}"
    )


def log_layout_border_metrics(
    fitted_layout_cells,
    edges,
):
    def longest_run_ratio(
        values,
    ):
        if values.size == 0:
            return 0.0

        flags = (
            values > 0
        )

        longest_run = 0
        current_run = 0

        for value in flags:
            if value:
                current_run += 1

                if current_run > longest_run:
                    longest_run = current_run
            else:
                current_run = 0

        return (
            longest_run
            / len(flags)
        )

    for cell_number, (
        x,
        y,
        w,
        h,
    ) in enumerate(
        fitted_layout_cells,
        start=1,
    ):
        roi_edges = edges[
            y:y + h,
            x:x + w,
        ]

        top_border_evidence = 0.0
        bottom_border_evidence = 0.0
        left_border_evidence = 0.0
        right_border_evidence = 0.0

        top_border_run_ratio = 0.0
        bottom_border_run_ratio = 0.0
        left_border_run_ratio = 0.0
        right_border_run_ratio = 0.0

        if roi_edges.size > 0:
            border_band = max(
                3,
                min(
                    40,
                    int(
                        min(w, h) * 0.02
                    ),
                ),
            )

            top_band = roi_edges[
                :border_band,
                :,
            ]

            bottom_band = roi_edges[
                max(
                    0,
                    h - border_band,
                ):h,
                :,
            ]

            left_band = roi_edges[
                :,
                :border_band,
            ]

            right_band = roi_edges[
                :,
                max(
                    0,
                    w - border_band,
                ):w,
            ]

            if top_band.size > 0:
                top_row_ratios = (
                    np.count_nonzero(
                        top_band,
                        axis=1,
                    )
                    / top_band.shape[1]
                )

                top_row_index = int(
                    np.argmax(
                        top_row_ratios
                    )
                )

                top_border_evidence = float(
                    top_row_ratios[
                        top_row_index
                    ]
                )

                top_border_run_ratio = (
                    longest_run_ratio(
                        top_band[
                            top_row_index,
                            :,
                        ]
                    )
                )

            if bottom_band.size > 0:
                bottom_row_ratios = (
                    np.count_nonzero(
                        bottom_band,
                        axis=1,
                    )
                    / bottom_band.shape[1]
                )

                bottom_row_index = int(
                    np.argmax(
                        bottom_row_ratios
                    )
                )

                bottom_border_evidence = float(
                    bottom_row_ratios[
                        bottom_row_index
                    ]
                )

                bottom_border_run_ratio = (
                    longest_run_ratio(
                        bottom_band[
                            bottom_row_index,
                            :,
                        ]
                    )
                )

            if left_band.size > 0:
                left_column_ratios = (
                    np.count_nonzero(
                        left_band,
                        axis=0,
                    )
                    / left_band.shape[0]
                )

                left_column_index = int(
                    np.argmax(
                        left_column_ratios
                    )
                )

                left_border_evidence = float(
                    left_column_ratios[
                        left_column_index
                    ]
                )

                left_border_run_ratio = (
                    longest_run_ratio(
                        left_band[
                            :,
                            left_column_index,
                        ]
                    )
                )

            if right_band.size > 0:
                right_column_ratios = (
                    np.count_nonzero(
                        right_band,
                        axis=0,
                    )
                    / right_band.shape[0]
                )

                right_column_index = int(
                    np.argmax(
                        right_column_ratios
                    )
                )

                right_border_evidence = float(
                    right_column_ratios[
                        right_column_index
                    ]
                )

                right_border_run_ratio = (
                    longest_run_ratio(
                        right_band[
                            :,
                            right_column_index,
                        ]
                    )
                )

        write_detection_log(
            "layout border metrics "
            f"cell={cell_number} "
            f"x={x} "
            f"y={y} "
            f"w={w} "
            f"h={h} "
            f"top_border_evidence="
            f"{top_border_evidence:.3f} "
            f"bottom_border_evidence="
            f"{bottom_border_evidence:.3f} "
            f"left_border_evidence="
            f"{left_border_evidence:.3f} "
            f"right_border_evidence="
            f"{right_border_evidence:.3f} "
            f"top_border_run_ratio="
            f"{top_border_run_ratio:.3f} "
            f"bottom_border_run_ratio="
            f"{bottom_border_run_ratio:.3f} "
            f"left_border_run_ratio="
            f"{left_border_run_ratio:.3f} "
            f"right_border_run_ratio="
            f"{right_border_run_ratio:.3f}"
        )


def log_layout_regularity(
    fitted_layout_cells,
):
    cell_count = len(
        fitted_layout_cells
    )

    if cell_count == 0:
        write_detection_log(
            "layout regularity "
            "cells=0 "
            "width_cv=0.0000 "
            "height_cv=0.0000 "
            "area_cv=0.0000"
        )

        return

    widths = np.array(
        [
            w
            for (
                x,
                y,
                w,
                h,
            )
            in fitted_layout_cells
        ],
        dtype=np.float32,
    )

    heights = np.array(
        [
            h
            for (
                x,
                y,
                w,
                h,
            )
            in fitted_layout_cells
        ],
        dtype=np.float32,
    )

    areas = (
        widths * heights
    )

    width_mean = float(
        np.mean(
            widths
        )
    )

    height_mean = float(
        np.mean(
            heights
        )
    )

    area_mean = float(
        np.mean(
            areas
        )
    )

    width_cv = 0.0
    height_cv = 0.0
    area_cv = 0.0

    if width_mean > 0.0:
        width_cv = float(
            np.std(
                widths
            )
            / width_mean
        )

    if height_mean > 0.0:
        height_cv = float(
            np.std(
                heights
            )
            / height_mean
        )

    if area_mean > 0.0:
        area_cv = float(
            np.std(
                areas
            )
            / area_mean
        )

    write_detection_log(
        "layout regularity "
        f"cells={cell_count} "
        f"width_cv={width_cv:.4f} "
        f"height_cv={height_cv:.4f} "
        f"area_cv={area_cv:.4f}"
    )


def log_candidate_layout_relations(
    candidates,
    fitted_layout_cells,
):
    if not fitted_layout_cells:
        write_detection_log(
            "candidate layout relation "
            "skipped reason=no_layout_cells"
        )

        return

    best_inside_ratios = []
    best_area_ratios = []

    for candidate_number, (
        x,
        y,
        w,
        h,
    ) in enumerate(
        candidates,
        start=1,
    ):
        candidate_area = (
            w * h
        )

        best_cell_number = 0
        best_inside_ratio = 0.0
        best_area_ratio = 0.0

        for cell_number, (
            cell_x,
            cell_y,
            cell_w,
            cell_h,
        ) in enumerate(
            fitted_layout_cells,
            start=1,
        ):
            overlap_x1 = max(
                x,
                cell_x,
            )

            overlap_y1 = max(
                y,
                cell_y,
            )

            overlap_x2 = min(
                x + w,
                cell_x + cell_w,
            )

            overlap_y2 = min(
                y + h,
                cell_y + cell_h,
            )

            overlap_w = max(
                0,
                overlap_x2 - overlap_x1,
            )

            overlap_h = max(
                0,
                overlap_y2 - overlap_y1,
            )

            overlap_area = (
                overlap_w
                * overlap_h
            )

            inside_ratio = 0.0

            if candidate_area > 0:
                inside_ratio = (
                    overlap_area
                    / candidate_area
                )

            cell_area = (
                cell_w * cell_h
            )

            candidate_to_cell_area_ratio = 0.0

            if cell_area > 0:
                candidate_to_cell_area_ratio = (
                    candidate_area
                    / cell_area
                )

            if (
                inside_ratio
                > best_inside_ratio
            ):
                best_cell_number = (
                    cell_number
                )

                best_inside_ratio = (
                    inside_ratio
                )

                best_area_ratio = (
                    candidate_to_cell_area_ratio
                )

        best_inside_ratios.append(
            best_inside_ratio
        )

        best_area_ratios.append(
            best_area_ratio
        )

        write_detection_log(
            "candidate layout relation "
            f"number={candidate_number} "
            f"best_cell={best_cell_number} "
            f"inside_ratio="
            f"{best_inside_ratio:.4f} "
            f"candidate_to_cell_area_ratio="
            f"{best_area_ratio:.3f}"
        )

    candidate_count = len(
        best_inside_ratios
    )

    inside_095_count = sum(
        1
        for ratio in best_inside_ratios
        if ratio >= 0.95
    )

    inside_095_ratio = 0.0

    if candidate_count > 0:
        inside_095_ratio = (
            inside_095_count
            / candidate_count
        )

    median_area_ratio = 0.0
    max_area_ratio = 0.0

    if best_area_ratios:
        median_area_ratio = float(
            np.median(
                best_area_ratios
            )
        )

        max_area_ratio = float(
            np.max(
                best_area_ratios
            )
        )

    write_detection_log(
        "candidate layout summary "
        f"candidate_count={candidate_count} "
        f"inside_095_count={inside_095_count} "
        f"inside_095_ratio="
        f"{inside_095_ratio:.3f} "
        f"median_candidate_to_cell_area_ratio="
        f"{median_area_ratio:.3f} "
        f"max_candidate_to_cell_area_ratio="
        f"{max_area_ratio:.3f}"
    )


def log_layout_trust_candidate(
    candidates,
    fitted_layout_cells,
    layout_fit_success_ratio,
):
    cell_count = len(
        fitted_layout_cells
    )

    cell_count_ok = (
        cell_count >= 4
    )

    width_cv = 0.0
    height_cv = 0.0
    area_cv = 0.0

    if fitted_layout_cells:
        widths = np.array(
            [
                w
                for (
                    x,
                    y,
                    w,
                    h,
                )
                in fitted_layout_cells
            ],
            dtype=np.float32,
        )

        heights = np.array(
            [
                h
                for (
                    x,
                    y,
                    w,
                    h,
                )
                in fitted_layout_cells
            ],
            dtype=np.float32,
        )

        areas = (
            widths * heights
        )

        width_mean = float(
            np.mean(
                widths
            )
        )

        height_mean = float(
            np.mean(
                heights
            )
        )

        area_mean = float(
            np.mean(
                areas
            )
        )

        if width_mean > 0.0:
            width_cv = float(
                np.std(
                    widths
                )
                / width_mean
            )

        if height_mean > 0.0:
            height_cv = float(
                np.std(
                    heights
                )
                / height_mean
            )

        if area_mean > 0.0:
            area_cv = float(
                np.std(
                    areas
                )
                / area_mean
            )

    regularity_ok = (
        width_cv <= 0.05
        and height_cv <= 0.05
        and area_cv <= 0.10
    )

    fit_success_ok = (
        layout_fit_success_ratio
        >= 0.95
    )

    best_inside_ratios = []
    best_area_ratios = []

    for (
        x,
        y,
        w,
        h,
    ) in candidates:
        candidate_area = (
            w * h
        )

        best_inside_ratio = 0.0
        best_area_ratio = 0.0

        for (
            cell_x,
            cell_y,
            cell_w,
            cell_h,
        ) in fitted_layout_cells:
            overlap_x1 = max(
                x,
                cell_x,
            )

            overlap_y1 = max(
                y,
                cell_y,
            )

            overlap_x2 = min(
                x + w,
                cell_x + cell_w,
            )

            overlap_y2 = min(
                y + h,
                cell_y + cell_h,
            )

            overlap_w = max(
                0,
                overlap_x2 - overlap_x1,
            )

            overlap_h = max(
                0,
                overlap_y2 - overlap_y1,
            )

            overlap_area = (
                overlap_w
                * overlap_h
            )

            inside_ratio = 0.0

            if candidate_area > 0:
                inside_ratio = (
                    overlap_area
                    / candidate_area
                )

            cell_area = (
                cell_w * cell_h
            )

            candidate_to_cell_area_ratio = 0.0

            if cell_area > 0:
                candidate_to_cell_area_ratio = (
                    candidate_area
                    / cell_area
                )

            if (
                inside_ratio
                > best_inside_ratio
            ):
                best_inside_ratio = (
                    inside_ratio
                )

                best_area_ratio = (
                    candidate_to_cell_area_ratio
                )

        best_inside_ratios.append(
            best_inside_ratio
        )

        best_area_ratios.append(
            best_area_ratio
        )

    candidate_count = len(
        best_inside_ratios
    )

    inside_095_count = sum(
        1
        for ratio in best_inside_ratios
        if ratio >= 0.95
    )

    inside_095_ratio = 0.0

    if candidate_count > 0:
        inside_095_ratio = (
            inside_095_count
            / candidate_count
        )

    containment_ok = (
        candidate_count > 0
        and inside_095_ratio >= 0.90
    )

    median_area_ratio = 0.0
    max_area_ratio = 0.0

    if best_area_ratios:
        median_area_ratio = float(
            np.median(
                best_area_ratios
            )
        )

        max_area_ratio = float(
            np.max(
                best_area_ratios
            )
        )

    candidate_size_ok = (
        candidate_count > 0
        and median_area_ratio <= 0.50
        and max_area_ratio <= 0.80
    )

    trusted = (
        cell_count_ok
        and regularity_ok
        and fit_success_ok
        and containment_ok
        and candidate_size_ok
    )

    write_detection_log(
        "layout trust candidate "
        f"cells={cell_count} "
        f"cell_count_ok={cell_count_ok} "
        f"width_cv={width_cv:.4f} "
        f"height_cv={height_cv:.4f} "
        f"area_cv={area_cv:.4f} "
        f"regularity_ok={regularity_ok} "
        f"fit_success_ratio="
        f"{layout_fit_success_ratio:.3f} "
        f"fit_success_ok={fit_success_ok} "
        f"inside_095_ratio="
        f"{inside_095_ratio:.3f} "
        f"containment_ok={containment_ok} "
        f"median_area_ratio="
        f"{median_area_ratio:.3f} "
        f"max_area_ratio="
        f"{max_area_ratio:.3f} "
        f"candidate_size_ok="
        f"{candidate_size_ok} "
        f"trusted={trusted}"
    )

    return trusted


def build_candidates(
    contours,
    image,
    edges,
    image_area,
    width,
    height,
    allow_small=False,
):
    candidates = []

    candidate_type = (
        "small"
        if allow_small
        else "normal"
    )

    for contour in contours:
        candidate = contour_to_candidate(
            contour,
            image,
            edges,
            image_area,
            width,
            height,
            allow_small=allow_small,
        )

        if candidate is None:
            continue

        candidates.append(
            candidate
        )

        candidate_number = len(
            candidates
        )

        log_candidate_metrics(
            candidate_number,
            candidate,
            contour,
            image,
            edges,
            image_area,
            candidate_type,
        )

        if DEBUG:
            x, y, w, h = candidate

            print(
                f"candidate "
                f"number={candidate_number}, "
                f"x={x}, y={y}, "
                f"w={w}, h={h}, "
                f"type={candidate_type}"
            )

    if DEBUG:
        print(
            f"contours={len(contours)}, "
            f"candidates={len(candidates)}, "
            f"type={candidate_type}"
        )

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

    contours_mask = find_photo_contours(
        mask
    )

    return (
        list(contours_edge)
        + list(contours_mask)
    )


def save_candidate_debug_image(
    image,
    candidates,
    image_path,
    suffix,
):
    if not DEBUG_SAVE_IMAGE:
        return

    debug_image = image.copy()

    image_height, image_width = (
        debug_image.shape[:2]
    )

    min_side = min(
        image_width,
        image_height,
    )

    line_thickness = max(
        3,
        int(min_side * 0.001),
    )

    font_scale = max(
        1.0,
        min_side / 1800.0,
    )

    text_thickness = max(
        2,
        int(min_side * 0.0008),
    )

    for number, rect in enumerate(
        candidates,
        start=1,
    ):
        x, y, w, h = rect

        cv2.rectangle(
            debug_image,
            (x, y),
            (x + w, y + h),
            (0, 0, 255),
            line_thickness,
        )

        label = str(
            number
        )

        (
            text_size,
            baseline,
        ) = cv2.getTextSize(
            label,
            cv2.FONT_HERSHEY_SIMPLEX,
            font_scale,
            text_thickness,
        )

        text_w, text_h = text_size

        label_x = x
        label_y = max(
            text_h + 10,
            y,
        )

        cv2.rectangle(
            debug_image,
            (
                label_x,
                label_y - text_h - 10,
            ),
            (
                label_x + text_w + 16,
                label_y + baseline + 6,
            ),
            (0, 0, 0),
            -1,
        )

        cv2.putText(
            debug_image,
            label,
            (
                label_x + 8,
                label_y - 4,
            ),
            cv2.FONT_HERSHEY_SIMPLEX,
            font_scale,
            (255, 255, 255),
            text_thickness,
            cv2.LINE_AA,
        )

    output_dir = (
        Path(__file__).resolve().parent.parent
        / "tests"
        / "output"
    )

    output_dir.mkdir(
        parents=True,
        exist_ok=True,
    )

    image_name = Path(
        image_path
    ).stem

    output_path = (
        output_dir
        / (
            f"{image_name}_"
            f"{suffix}.jpg"
        )
    )

    cv2.imwrite(
        str(output_path),
        debug_image,
    )

    write_detection_log(
        "candidate debug image saved "
        f"path={str(output_path)!r} "
        f"count={len(candidates)}"
    )


def detect_photos(image_path):
    started_at = time.perf_counter()

    path = Path(
        image_path
    )

    write_detection_log(
        "=" * 60
    )

    write_detection_log(
        "detection start"
    )

    write_detection_environment()

    write_detection_log(
        "opencv "
        f"version={cv2.__version__}"
    )

    try:
        resolved_path = path.resolve(
            strict=False
        )
    except Exception:
        resolved_path = path

    write_detection_log(
        "input "
        f"path={str(path)!r} "
        f"resolved={str(resolved_path)!r}"
    )

    path_exists = path.exists()
    path_is_file = path.is_file()

    write_detection_log(
        "file status "
        f"exists={path_exists} "
        f"is_file={path_is_file} "
        f"readable={os.access(path, os.R_OK)}"
    )

    if path_exists and path_is_file:
        try:
            file_size = path.stat().st_size

            write_detection_log(
                "file size "
                f"bytes={file_size}"
            )

        except Exception as e:
            write_detection_log(
                "file stat failed "
                f"exception_type="
                f"{type(e).__name__} "
                f"message={e!r}"
            )

    load_started_at = time.perf_counter()

    write_detection_log(
        "binary image read start"
    )

    try:
        with path.open("rb") as image_file:
            image_bytes = image_file.read()

        write_detection_log(
            "binary image read result "
            "success=True "
            f"bytes={len(image_bytes)}"
        )

    except Exception as e:
        load_elapsed = (
            time.perf_counter()
            - load_started_at
        )

        write_detection_log(
            "binary image read failed "
            f"exception_type={type(e).__name__} "
            f"message={e!r} "
            f"elapsed={load_elapsed:.4f}s"
        )

        total_elapsed = (
            time.perf_counter()
            - started_at
        )

        write_detection_log(
            "detection finished "
            "result=0 "
            f"elapsed={total_elapsed:.4f}s"
        )

        return []

    image_data = np.frombuffer(
        image_bytes,
        dtype=np.uint8,
    )

    write_detection_log(
        "cv2.imdecode start"
    )

    image = cv2.imdecode(
        image_data,
        cv2.IMREAD_COLOR,
    )

    load_elapsed = (
        time.perf_counter()
        - load_started_at
    )

    if image is None:
        write_detection_log(
            "cv2.imdecode result "
            "image=None "
            f"elapsed={load_elapsed:.4f}s"
        )

        total_elapsed = (
            time.perf_counter()
            - started_at
        )

        write_detection_log(
            "detection finished "
            "result=0 "
            f"elapsed={total_elapsed:.4f}s"
        )

        return []

    write_detection_log(
        "cv2.imdecode result "
        "success=True "
        f"shape={image.shape} "
        f"dtype={image.dtype} "
        f"elapsed={load_elapsed:.4f}s"
    )

    width, height, image_area = get_image_info(
        image
    )

    write_detection_log(
        "image info "
        f"width={width} "
        f"height={height} "
        f"area={image_area}"
    )

    gray = create_gray(
        image
    )

    write_detection_log(
        "gray created "
        f"shape={gray.shape} "
        f"dtype={gray.dtype}"
    )

    edges = create_edges(
        gray
    )

    write_detection_log(
        "edges created "
        f"nonzero={cv2.countNonZero(edges)}"
    )

    mask = create_mask(
        gray
    )

    write_detection_log(
        "mask created "
        f"nonzero={cv2.countNonZero(mask)}"
    )

    small_photo_mask = create_small_photo_mask(
        gray
    )

    write_detection_log(
        "small photo mask created "
        f"nonzero="
        f"{cv2.countNonZero(small_photo_mask)}"
    )

    # ---------------------------------
    # デバッグ画像の作成・保存
    # ---------------------------------
    if DEBUG_SAVE_IMAGE:
        output_dir = (
            Path(__file__).resolve().parent.parent
            / "tests"
            / "output"
        )

        output_dir.mkdir(
            parents=True,
            exist_ok=True,
        )

        image_name = Path(
            image_path
        ).stem

        (
            background_mask,
            background_color,
        ) = create_background_separation_mask(
            image
        )

        background_candidates = (
            find_background_separation_candidates(
                background_mask,
                width,
                height,
                image_area,
            )
        )

        write_detection_log(
            "background separation "
            f"lab="
            f"{background_color.tolist()} "
            f"candidates="
            f"{len(background_candidates)}"
        )

        cv2.imwrite(
            str(
                output_dir
                / (
                    f"{image_name}_"
                    "background_mask.png"
                )
            ),
            background_mask,
        )

        save_candidate_debug_image(
            image,
            background_candidates,
            image_path,
            "background_candidates",
        )

        (
            horizontal_runs,
            row_regions,
            row_vertical_runs,
        ) = detect_separator_bands(
            image,
            background_color,
        )

        save_separator_debug_image(
            image,
            horizontal_runs,
            row_regions,
            row_vertical_runs,
            image_path,
        )

        layout_cells = build_layout_cells(
            image,
            row_regions,
            row_vertical_runs,
        )

        save_candidate_debug_image(
            image,
            layout_cells,
            image_path,
            "layout_cells",
        )

        (
            fitted_layout_cells,
            layout_fit_success_ratio,
        ) = fit_layout_cells_to_photos(
            image,
            layout_cells,
            background_color,
        )

        save_candidate_debug_image(
            image,
            fitted_layout_cells,
            image_path,
            "fitted_layout_cells",
        )

        log_layout_border_metrics(
            fitted_layout_cells,
            edges,
        )

        log_layout_regularity(
            fitted_layout_cells,
        )

        (
            bright_frame_mask,
            bright_frame_candidates,
        ) = find_bright_frame_candidates(
            image,
            image_area,
        )

        bright_frame_trusted = (
            log_bright_frame_regularity(
                bright_frame_candidates,
            )
        )

        cv2.imwrite(
            str(
                output_dir
                / (
                    f"{image_name}_"
                    "bright_frame_mask.png"
                )
            ),
            bright_frame_mask,
        )

        save_candidate_debug_image(
            image,
            bright_frame_candidates,
            image_path,
            "bright_frame_candidates",
        )

        (
            dark_hole_mask,
            dark_hole_candidates,
        ) = find_dark_hole_candidates(
            bright_frame_mask,
            image_area,
        )

        cv2.imwrite(
            str(
                output_dir
                / (
                    f"{image_name}_"
                    "dark_hole_mask.png"
                )
            ),
            dark_hole_mask,
        )

        save_candidate_debug_image(
            image,
            dark_hole_candidates,
            image_path,
            "dark_hole_candidates",
        )

        small_photo_lines = (
            create_small_photo_line_debug(
                image,
                edges,
            )
        )

        cv2.imwrite(
            str(
                output_dir
                / (
                    f"{image_name}_"
                    "small_photo_lines.png"
                )
            ),
            small_photo_lines,
        )

        cv2.imwrite(
            str(
                output_dir
                / f"{image_name}_edges.png"
            ),
            edges,
        )

        cv2.imwrite(
            str(
                output_dir
                / f"{image_name}_mask.png"
            ),
            mask,
        )

        cv2.imwrite(
            str(
                output_dir
                / f"{image_name}_mask_test.png"
            ),
            small_photo_mask,
        )

        cv2.imwrite(
            str(
                output_dir
                / (
                    f"{image_name}_"
                    "small_photo_mask.png"
                )
            ),
            small_photo_mask,
        )

    if not DEBUG_SAVE_IMAGE:
        (
            background_mask,
            background_color,
        ) = create_background_separation_mask(
            image
        )

        (
            horizontal_runs,
            row_regions,
            row_vertical_runs,
        ) = detect_separator_bands(
            image,
            background_color,
        )

        layout_cells = build_layout_cells(
            image,
            row_regions,
            row_vertical_runs,
        )

        (
            fitted_layout_cells,
            layout_fit_success_ratio,
        ) = fit_layout_cells_to_photos(
            image,
            layout_cells,
            background_color,
        )

        (
            bright_frame_mask,
            bright_frame_candidates,
        ) = find_bright_frame_candidates(
            image,
            image_area,
        )

        bright_frame_trusted = (
            log_bright_frame_regularity(
                bright_frame_candidates,
            )
        )

    contours = find_all_contours(
        mask,
        edges,
    )

    write_detection_log(
        "contours found "
        f"count={len(contours)}"
    )

    candidates = build_candidates(
        contours,
        image,
        edges,
        image_area,
        width,
        height,
        allow_small=False,
    )

    write_detection_log(
        "normal candidates built "
        f"count={len(candidates)}"
    )

    if DEBUG_SAVE_IMAGE:
        log_candidate_layout_relations(
            candidates,
            fitted_layout_cells,
        )

    layout_trusted = (
        log_layout_trust_candidate(
            candidates,
            fitted_layout_cells,
            layout_fit_success_ratio,
        )
    )

    if DEBUG_SAVE_IMAGE:
        if layout_trusted:
            write_detection_log(
                "layout alternative "
                "selected=True "
                f"count={len(fitted_layout_cells)} "
                f"rects={fitted_layout_cells}"
            )
        else:
            write_detection_log(
                "layout alternative "
                "selected=False "
                "count=0"
            )

    normal_candidate_count = len(
        candidates
    )

    bright_frame_candidate_count = len(
        bright_frame_candidates
    )

    normal_candidates_sparse = (
        normal_candidate_count == 0
        or (
            bright_frame_candidate_count >= 6
            and normal_candidate_count
            <= bright_frame_candidate_count * 0.25
        )
    )

    bright_frame_rescue_selected = (
        bright_frame_trusted
        and not layout_trusted
        and normal_candidates_sparse
    )

    write_detection_log(
        "bright frame rescue candidate "
        f"bright_frame_trusted="
        f"{bright_frame_trusted} "
        f"layout_trusted={layout_trusted} "
        f"normal_candidate_count="
        f"{len(candidates)} "
        f"selected="
        f"{bright_frame_rescue_selected}"
    )

    if bright_frame_rescue_selected:
        candidates = list(
            bright_frame_candidates
        )

        write_detection_log(
            "bright frame candidates applied "
            f"count={len(candidates)} "
            f"rects={candidates}"
        )

    if layout_trusted:
        candidates = list(
            fitted_layout_cells
        )

        write_detection_log(
            "layout candidates applied "
            f"count={len(candidates)} "
            f"rects={candidates}"
        )

    save_candidate_debug_image(
        image,
        candidates,
        image_path,
        "normal_candidates",
    )

    small_contours = find_photo_contours(
        small_photo_mask
    )

    write_detection_log(
        "small photo contours found "
        f"count={len(small_contours)}"
    )

    log_small_candidate_diagnostics(
        small_contours,
        image,
        edges,
        image_area,
        width,
        height,
    )

    small_candidates = build_candidates(
        small_contours,
        image,
        edges,
        image_area,
        width,
        height,
        allow_small=True,
    )

    write_detection_log(
        "small photo candidates built "
        f"count={len(small_candidates)}"
    )

    candidates.extend(
        small_candidates
    )

    write_detection_log(
        "combined candidates "
        f"count={len(candidates)}"
    )

    candidates = postprocess_candidates(
        candidates
    )

    total_elapsed = (
        time.perf_counter()
        - started_at
    )

    write_detection_log(
        "detection finished "
        f"result={len(candidates)} "
        f"elapsed={total_elapsed:.4f}s"
    )

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
    write_detection_log(
        "postprocess start "
        f"count={len(candidates)}"
    )

    if DEBUG:
        print(
            f"postprocess start="
            f"{len(candidates)}"
        )

    candidates = remove_inner_overlaps(
        candidates
    )

    write_detection_log(
        "postprocess "
        "after_remove_inner_overlaps "
        f"count={len(candidates)}"
    )

    if DEBUG:
        print(
            "after remove_inner_overlaps="
            f"{len(candidates)}"
        )

    candidates = split_large_rects(
        candidates
    )

    write_detection_log(
        "postprocess "
        "after_split_large_rects "
        f"count={len(candidates)}"
    )

    if DEBUG:
        print(
            "after split_large_rects="
            f"{len(candidates)}"
        )

    candidates = remove_lower_overlap_rects(
        candidates
    )

    write_detection_log(
        "postprocess "
        "after_remove_lower_overlap_rects "
        f"count={len(candidates)}"
    )

    if DEBUG:
        print(
            "after remove_lower_overlap_rects="
            f"{len(candidates)}"
        )

    candidates = remove_duplicate_rects(
        candidates
    )

    write_detection_log(
        "postprocess "
        "after_remove_duplicate_rects "
        f"count={len(candidates)}"
    )

    if DEBUG:
        print(
            "after remove_duplicate_rects="
            f"{len(candidates)}"
        )

    candidates = sort_rects_reading_order(
        candidates
    )

    write_detection_log(
        "postprocess final "
        f"count={len(candidates)}"
    )

    if DEBUG:
        print(
            f"postprocess final="
            f"{len(candidates)}"
        )

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

def is_photo_like_candidate(
    image,
    edges,
    x,
    y,
    w,
    h,
):
    roi_edges = edges[
        y:y + h,
        x:x + w,
    ]

    if roi_edges.size == 0:
        return False

    edge_ratio = (
        cv2.countNonZero(
            roi_edges
        )
        / roi_edges.size
    )

    if edge_ratio < 0.02:
        return False

    roi_image = image[
        y:y + h,
        x:x + w,
    ]

    if roi_image.size == 0:
        return False

    roi_gray = cv2.cvtColor(
        roi_image,
        cv2.COLOR_BGR2GRAY,
    )

    gray_mean = float(
        np.mean(
            roi_gray
        )
    )

    gray_std = float(
        np.std(
            roi_gray
        )
    )

    roi_hsv = cv2.cvtColor(
        roi_image,
        cv2.COLOR_BGR2HSV,
    )

    saturation = roi_hsv[
        :,
        :,
        1,
    ]

    saturation_std = float(
        np.std(
            saturation
        )
    )

    uniform_bright_region = (
        gray_mean > 180.0
        and gray_std < 30.0
        and saturation_std < 20.0
    )

    if uniform_bright_region:
        write_detection_log(
            "candidate rejected "
            "reason=uniform_bright_region "
            f"x={x} "
            f"y={y} "
            f"w={w} "
            f"h={h} "
            f"gray_mean={gray_mean:.2f} "
            f"gray_std={gray_std:.2f} "
            f"saturation_std="
            f"{saturation_std:.2f}"
        )

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