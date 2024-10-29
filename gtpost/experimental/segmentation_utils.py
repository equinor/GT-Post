from dataclasses import dataclass
from pathlib import Path
from typing import NamedTuple

import numpy as np
from tqdm import tqdm
from ultralytics import YOLO


@dataclass
class PredictionParams:
    unit_name: str
    min_confidence: float = 0.01
    max_instances: int = 99


def predict_units(
    images: list[str],
    trained_model: YOLO,
    imgsz: int,
    parameter_classes: list[PredictionParams],
):
    mask_arrays = []
    for pc in tqdm(parameter_classes):
        unit_index = [n[0] for n in trained_model.names.items() if n[1] == pc.unit_name]
        results = trained_model.predict(
            images,
            save=False,
            imgsz=imgsz,
            conf=pc.min_confidence,
            max_det=pc.max_instances,
            show_boxes=False,
            retina_masks=True,
            classes=unit_index,
            device="cpu",
        )
        mask_array = np.zeros([len(results)] + list(results[-1].masks.data.shape[1:]))
        for i, result in enumerate(results):
            if result.masks is not None:
                array = result.masks.data.max(axis=0).values
                mask_array[i, :, :][array == 1.0] = unit_index[0] + 1
        mask_arrays.append(mask_array)
    stacked_arrays = np.stack(mask_arrays)
    result = np.flip(stacked_arrays, axis=0)
    final_array = np.max(result, axis=0)
    x_idx_correction = final_array.shape[1] - results[0].orig_img.shape[0]
    y_idx_correction = final_array.shape[2] - results[0].orig_img.shape[1]
    return final_array[
        :,
        int(x_idx_correction / 2) : results[0].orig_img.shape[0]
        + int(x_idx_correction / 2),
        y_idx_correction:,
    ]


def arrays_to_8bit_rgb(variables, min_values, max_values):
    normalized_variables = []
    for variable, min_value, max_value in zip(variables, min_values, max_values):
        variable[variable < min_value] = min_value
        variable[variable > max_value] = max_value
        variable_normalized = np.floor(
            (variable - min_value) / (max_value - min_value) * 255
        )
        normalized_variables.append(variable_normalized.astype(np.uint8))
    rgb_image = np.stack(normalized_variables, axis=2)
    return rgb_image


def export_image():
    pass
