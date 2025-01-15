from pathlib import Path, WindowsPath

import matplotlib
import matplotlib.pyplot as plt
import numpy as np
from ultralytics import YOLO

from gtpost.analyze import classifications
from gtpost.experimental import segmentation_utils
from gtpost.experimental.segmentation_utils import (
    PredictionImageParams,
    PredictionParams,
)

type ModelResult = None

prediction_images_temp_folder = Path(__file__).parent.joinpath(
    "training_dataset/prediction_images_temp"
)

prediction_parameters_delta_top = [
    PredictionParams(
        unit_name="Delta area",
        string_code="dt",
        encoding=1,
        trained_model=YOLO(
            Path(__file__).parent.joinpath("trained_yolo_models/best_deltatop.pt")
        ),
        min_confidence=0.01,
        max_instances=1,
    ),
]

prediction_parameters_delta_front = [
    PredictionParams(
        unit_name="Delta front",
        string_code="df",
        encoding=5,
        trained_model=YOLO(
            Path(__file__).parent.joinpath("trained_yolo_models/best_deltafront.pt")
        ),
        max_instances=4,
        min_confidence=0.25,
    ),
]

prediction_parameters_ch_mb = [
    PredictionParams(
        unit_name="Channel",
        string_code="ch",
        encoding=3,
        trained_model=YOLO(
            Path(__file__).parent.joinpath("trained_yolo_models/best_ch_mb.pt")
        ),
        max_instances=99,
        min_confidence=0.25,
    ),
    PredictionParams(
        unit_name="Mouth bar",
        string_code="mb",
        encoding=4,
        trained_model=YOLO(
            Path(__file__).parent.joinpath("trained_yolo_models/best_ch_mb.pt")
        ),
        max_instances=99,
        min_confidence=0.25,
    ),
]


def generate_prediction_images(modelresult: ModelResult, folder: Path | str):
    for i in range(0, modelresult.timestep, 1):
        pred_image = segmentation_utils.arrays_to_8bit_rgb(
            [
                modelresult.bottom_depth[i, :, :],
                modelresult.dataset["DM"].values[i, :, :],
                modelresult.dataset["MAX_UV"].values[i, :, :],
            ],
            [0, 0, 0],
            [12, 0.0005, 1],
        )
        plt.imsave(
            folder.joinpath(f"{i:04d}_pred_image.png"),
            pred_image,
            format="png",
        )

    return list(pred_image.shape[:-1])


def predict(
    image_folder: str | WindowsPath,
    prediction_parameters: PredictionParams | list[PredictionParams],
    imgsz: int,
) -> np.array:
    if isinstance(prediction_parameters, PredictionParams):
        prediction_parameters = [prediction_parameters]
    images = sorted([str(f) for f in Path(image_folder).glob("*.png")])
    prediction = segmentation_utils.predict_units(images, prediction_parameters, imgsz)
    return prediction


def constrain_ch_mb(modelresult: ModelResult, prediction_result: np.ndarray):
    # Water depth must be > 1 m to justify a channel prediction
    prediction_result[
        (prediction_result == classifications.ArchEl.channel.value)
        & (modelresult.bottom_depth < 0.5)
    ] = 0

    # Limit the depth at which mouth bars are expected, based on the delta front depth
    prediction_result[
        (prediction_result == classifications.ArchEl.mouthbar.value)
        & (modelresult.bottom_depth > 5)
    ] = 0
    return prediction_result


def postprocess_result(
    modelresult: ModelResult, prediction_result: np.ndarray, delta_top_division=1
):
    # Apply model mask to the prediction result
    prediction_result *= modelresult.model_mask.values
    # split delta top into a subaerial and subaqeous part
    prediction_result[
        (prediction_result == 1) & (modelresult.bottom_depth > delta_top_division)
    ] = classifications.ArchEl.dtaqua.value

    # Turn the rest of the domain below a certain depth to prodelta
    prediction_result[(prediction_result == 0) & (modelresult.bottom_depth > 4)] = (
        classifications.ArchEl.prodelta.value
    )
    return prediction_result


def detect(modelresult: ModelResult):
    if not prediction_images_temp_folder.is_dir():
        Path.mkdir(prediction_images_temp_folder, exist_ok=True)

    imgsz = generate_prediction_images(modelresult, prediction_images_temp_folder)
    result_dt = predict(
        prediction_images_temp_folder, prediction_parameters_delta_top, imgsz
    )
    result_df = predict(
        prediction_images_temp_folder, prediction_parameters_delta_front, imgsz
    )
    result_ch_mb = predict(
        prediction_images_temp_folder, prediction_parameters_ch_mb, imgsz
    )
    result_ch_mb = constrain_ch_mb(modelresult, result_ch_mb)
    result = segmentation_utils.merge_arrays_in_order(
        [result_dt, result_df, result_ch_mb]
    )

    result = postprocess_result(modelresult, result)

    # if prediction_images_temp_folder.is_dir():
    #     prediction_images_temp_folder.rmdir()
    return result.astype(np.int64)
