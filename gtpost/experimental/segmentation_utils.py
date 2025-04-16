from dataclasses import dataclass
from pathlib import Path
from typing import List, NamedTuple

import numpy as np
from tqdm import tqdm
from ultralytics import YOLO


@dataclass
class PredictionParams:
    """
    A class to hold parameters for the prediction of segmentation masks using a trained
    YOLO model (.pt file).
    """

    unit_name: str
    string_code: str
    encoding: int
    trained_model: YOLO
    min_confidence: float = 0.01
    max_instances: int = 99
    constrain_func: callable = None


def predict_units(
    images: list[str],
    prediction_parameters: list[PredictionParams],
    imgsz: int,
):
    """
    Generates a final segmentation mask by predicting and combining masks
    from multiple instance segmentation models and parameters.

    Parameters
    ----------
    images : list[str]
        A list of file paths to the input images to be processed.
    prediction_parameters : list[PredictionParams]
        A list of PredictionParams objects, each containing a trained model
        and associated parameters for prediction.
    imgsz : int
        The size to which the input images should be resized for prediction.

    Returns
    -------
    numpy.ndarray
        A 3D array representing the final combined segmentation mask. The
        array dimensions correspond to the number of images and their
        corrected spatial dimensions.

    Notes
    -----
    - The function uses the ultralytics YOLO `predict` method of the trained models to
      generate masks for each image.
    - Masks are combined by stacking and flipping them, followed by taking
      the maximum value along the stacking axis.
    - Corrections are applied to align the final masks such that they correctly fit the
      Delft3D model grid.
    """
    mask_arrays = []
    for pp in tqdm(prediction_parameters):
        results = pp.trained_model.predict(
            images,
            save=True,
            imgsz=imgsz,
            iou=1.0,
            conf=pp.min_confidence,
            max_det=pp.max_instances,
            show_boxes=False,
            # visualize=True,
            retina_masks=True,
            augment=False,
            agnostic_nms=True,
            device="cpu",
        )
        mask_array = np.zeros(
            [len(results)] + list(results[0].orig_shape), dtype=np.uint8
        )
        for i, result in enumerate(results):
            if result.masks is not None:
                array = result.masks.data.max(axis=0).values
                mask_array[i, :, :][array == 1] = pp.encoding
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


def arrays_to_8bit_rgb(
    variables: List[np.ndarray], min_values: List[float], max_values: List[float]
) -> np.ndarray:
    """
    Convert a list of arrays into an 8-bit RGB image by normalizing each array
    to the range [0, 255] based on provided minimum and maximum values.

    Parameters
    ----------
    variables : List[np.ndarray]
        A list of 2D arrays representing the input variables to be normalized.
    min_values : List[float]
        A list of minimum values for normalization, one for each variable.
    max_values : List[float]
        A list of maximum values for normalization, one for each variable.

    Returns
    -------
    np.ndarray
        A 3D array representing the RGB image, where each channel corresponds
        to a normalized input variable.

    Notes
    -----
    - The input variables must be 2D arrays of the same shape.
    - The number of variables, min_values, and max_values must match.
    - Values outside the specified range are clipped to the range [min_value, max_value].
    """
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


def merge_arrays_in_order(list_of_arrays: list[np.ndarray]) -> np.ndarray:
    """
    Merge a list of arrays in order, prioritizing non-zero values from later arrays.
    This is used to combine segmentation masks in order. (e.g. a channel detection
    overwrites a deltya top detection etc.)

    Parameters
    ----------
    list_of_arrays : list of numpy.ndarray
        A list of 2D or 3D arrays of the same shape. Each array is merged in order,
        with non-zero values from later arrays overwriting values in earlier arrays.

    Returns
    -------
    numpy.ndarray
        A single array of the same shape as the input arrays, where non-zero values
        from later arrays in the list overwrite values in earlier arrays.

    Examples
    --------
    >>> import numpy as np
    >>> arr1 = np.array([[1, 0], [0, 2]])
    >>> arr2 = np.array([[0, 3], [4, 0]])
    >>> arr3 = np.array([[0, 0], [5, 0]])
    >>> merge_arrays_in_order([arr1, arr2, arr3])
    array([[1, 3],
           [5, 2]])
    """

    result = list_of_arrays[0].copy()
    for next_layer in list_of_arrays[1:]:
        result[next_layer != 0] = next_layer[next_layer != 0]
    return result


def export_image():
    pass
