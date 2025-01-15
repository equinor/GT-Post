from dataclasses import dataclass
from pathlib import Path
from typing import NamedTuple

import numpy as np
from tqdm import tqdm
from ultralytics import YOLO


@dataclass
class PredictionImageParams:
    is_postprocessing_result: bool
    param_red: str
    param_green: str
    param_blue: str
    param_red_min: float
    param_green_min: float
    param_blue_min: float
    param_red_max: float
    param_green_max: float
    param_blue_max: float


@dataclass
class PredictionParams:
    unit_name: str
    string_code: str
    encoding: int
    trained_model: YOLO
    min_confidence: float = 0.01
    max_instances: int = 99


def predict_units(
    images: list[str],
    prediction_parameters: list[PredictionParams],
    imgsz: int,
):
    mask_arrays = []
    for pp in tqdm(prediction_parameters):
        unit_index = [
            n[0] for n in pp.trained_model.names.items() if n[1] == pp.unit_name
        ]
        results = pp.trained_model.predict(
            images,
            save=False,
            imgsz=imgsz,
            iou=1.0,
            conf=pp.min_confidence,
            max_det=pp.max_instances,
            show_boxes=False,
            retina_masks=True,
            augment=True,
            agnostic_nms=True,
            classes=unit_index,
            device="cpu",
        )
        mask_array = np.zeros([len(results)] + list(results[-1].masks.data.shape[1:]))
        for i, result in enumerate(results):
            if result.masks is not None:
                array = result.masks.data.max(axis=0).values
                mask_array[i, :, :][array == 1.0] = pp.encoding
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
        variable = variable.copy()
        variable[variable < min_value] = min_value
        variable[variable > max_value] = max_value
        variable_normalized = np.floor(
            (variable - min_value) / (max_value - min_value) * 255
        )
        normalized_variables.append(variable_normalized.astype(np.uint8))
    rgb_image = np.stack(normalized_variables, axis=2)
    return rgb_image


def merge_arrays_in_order(list_of_arrays):
    result = list_of_arrays[0].copy()
    for next_layer in list_of_arrays[1:]:
        result[next_layer != 0] = next_layer[next_layer != 0]
    return result


def export_image():
    pass
