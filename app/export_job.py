import json

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

    def to_dict(self):
        return {
            "image_paths": list(
                self.image_paths
            ),
            "page_rects": {
                str(page_index): [
                    list(rect)
                    for rect in rects
                ]
                for page_index, rects
                in self.page_rects.items()
            },
            "page_angles": {
                str(page_index): list(angles)
                for page_index, angles
                in self.page_angles.items()
            },
            "page_group_ids": {
                str(page_index): list(group_ids)
                for page_index, group_ids
                in self.page_group_ids.items()
            },
            "page_mosaic_rects": {
                str(page_index): [
                    list(rect)
                    for rect in mosaic_rects
                ]
                for page_index, mosaic_rects
                in self.page_mosaic_rects.items()
            },
            "output_dir": str(
                self.output_dir
            ),
            "dpi": int(
                self.dpi
            ),
            "margin_px": int(
                self.margin_px
            ),
            "jpeg_quality": int(
                self.jpeg_quality
            ),
            "total_crops": int(
                self.total_crops
            ),
            "export_page_indexes": (
                None
                if self.export_page_indexes is None
                else sorted(
                    int(page_index)
                    for page_index
                    in self.export_page_indexes
                )
            ),
            "page_mosaic_angles": {
                str(page_index): list(angles)
                for page_index, angles
                in self.page_mosaic_angles.items()
            },
            "selected_export_units": (
                None
                if self.selected_export_units is None
                else [
                    [
                        int(page_index),
                        int(crop_index),
                    ]
                    for page_index, crop_index
                    in sorted(
                        self.selected_export_units
                    )
                ]
            ),
            "individual_export_settings": [
                {
                    "page_index": int(
                        page_index
                    ),
                    "crop_index": int(
                        crop_index
                    ),
                    "dpi": int(
                        settings["dpi"]
                    ),
                    "jpeg_quality": int(
                        settings["jpeg_quality"]
                    ),
                    "margin_mm": float(
                        settings["margin_mm"]
                    ),
                }
                for (
                    page_index,
                    crop_index,
                ), settings
                in sorted(
                    self.individual_export_settings.items()
                )
            ],
        }

    @classmethod
    def from_dict(
        cls,
        data,
    ):
        return cls(
            image_paths=list(
                data["image_paths"]
            ),
            page_rects={
                int(page_index): [
                    tuple(rect)
                    for rect in rects
                ]
                for page_index, rects
                in data["page_rects"].items()
            },
            page_angles={
                int(page_index): list(angles)
                for page_index, angles
                in data["page_angles"].items()
            },
            page_group_ids={
                int(page_index): list(group_ids)
                for page_index, group_ids
                in data["page_group_ids"].items()
            },
            page_mosaic_rects={
                int(page_index): [
                    tuple(rect)
                    for rect in mosaic_rects
                ]
                for page_index, mosaic_rects
                in data["page_mosaic_rects"].items()
            },
            output_dir=data["output_dir"],
            dpi=int(
                data["dpi"]
            ),
            margin_px=int(
                data["margin_px"]
            ),
            jpeg_quality=int(
                data["jpeg_quality"]
            ),
            total_crops=int(
                data["total_crops"]
            ),
            export_page_indexes=(
                None
                if data["export_page_indexes"] is None
                else {
                    int(page_index)
                    for page_index
                    in data["export_page_indexes"]
                }
            ),
            page_mosaic_angles={
                int(page_index): list(angles)
                for page_index, angles
                in data["page_mosaic_angles"].items()
            },
            selected_export_units=(
                None
                if data["selected_export_units"] is None
                else {
                    (
                        int(page_index),
                        int(crop_index),
                    )
                    for (
                        page_index,
                        crop_index,
                    )
                    in data["selected_export_units"]
                }
            ),
            individual_export_settings={
                (
                    int(
                        settings[
                            "page_index"
                        ]
                    ),
                    int(
                        settings[
                            "crop_index"
                        ]
                    ),
                ): {
                    "dpi": int(
                        settings["dpi"]
                    ),
                    "jpeg_quality": int(
                        settings[
                            "jpeg_quality"
                        ]
                    ),
                    "margin_mm": float(
                        settings[
                            "margin_mm"
                        ]
                    ),
                }
                for settings
                in data[
                    "individual_export_settings"
                ]
            },
        )

    def to_json(self):
        return json.dumps(
            self.to_dict(),
            ensure_ascii=False,
        )

    @classmethod
    def from_json(
        cls,
        json_text,
    ):
        return cls.from_dict(
            json.loads(
                json_text
            )
        )