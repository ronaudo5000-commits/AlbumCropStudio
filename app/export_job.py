from dataclasses import dataclass, field


@dataclass
class ExportJob:
    image_paths: list
    page_rects: dict
    page_angles: dict
    page_group_ids: dict
    page_mosaic_rects: dict

    output_dir: object

    dpi: int
    margin_px: int
    jpeg_quality: int
    total_crops: int

    export_page_indexes: object = None

    page_mosaic_angles: dict = field(
        default_factory=dict
    )

    selected_export_units: object = None

    individual_export_settings: dict = field(
        default_factory=dict
    )