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
from gtpost.visualize import colormaps

ModelResult = None

prediction_images_temp_folder = Path(__file__).parent.joinpath(
    "training_dataset/prediction_images_temp"
)


def constrain_channel(modelresult: ModelResult, prediction_result: np.ndarray):
    # Water depth must be > 0 m to justify a channel prediction
    prediction_result[
        (prediction_result == classifications.ArchEl.channel.value)
        & (modelresult.bottom_depth < 0)
    ] = 0
    return prediction_result


def constrain_mouthbar(modelresult: ModelResult, prediction_result: np.ndarray):
    # Limit the depth at which mouth bars are expected, based on the delta front depth
    prediction_result[
        (prediction_result == classifications.ArchEl.mouthbar.value)
        & (modelresult.bottom_depth > 4)
        & (modelresult.deposit_height < 0.05)
    ] = 0
    return prediction_result


def constrain_deltatop(modelresult: ModelResult, prediction_result: np.ndarray):
    # split delta top into a subaerial and subaqeous part
    prediction_result[(prediction_result == 1) & (modelresult.d50 < 0.07)] = (
        classifications.ArchEl.dtaqua.value
    )
    return prediction_result


def constrain_spit(modelresult: ModelResult, prediction_result: np.ndarray):
    # A spit prediction must lie above the water level for it to be valid
    pass
    return prediction_result


def postprocess_result(
    modelresult: ModelResult,
    prediction_result: np.ndarray,
):
    # Apply model mask to the prediction result
    prediction_result *= modelresult.model_mask.values
    prediction_result[(prediction_result == 0) & (modelresult.bottom_depth > 2)] = (
        classifications.ArchEl.prodelta.value
    )
    return prediction_result


prediction_parameters_deltatop = PredictionParams(
    unit_name="deltatop",
    string_code="dt",
    encoding=classifications.ArchEl.dtair.value,
    trained_model=YOLO(
        Path(__file__).parent.joinpath("trained_yolo_models/best_deltatop_yolo11l.pt")
    ),
    min_confidence=0.5,
    max_instances=1,
    constrain_func=constrain_deltatop,
)

prediction_parameters_ch = PredictionParams(
    unit_name="channel",
    string_code="ch",
    encoding=classifications.ArchEl.channel.value,
    trained_model=YOLO(
        Path(__file__).parent.joinpath("trained_yolo_models/best_channel_yolo11l.pt")
    ),
    max_instances=99,
    min_confidence=0.2,
    constrain_func=constrain_channel,
)

prediction_parameters_mb = PredictionParams(
    unit_name="mouthbar",
    string_code="mb",
    encoding=classifications.ArchEl.mouthbar.value,
    trained_model=YOLO(
        Path(__file__).parent.joinpath("trained_yolo_models/best_mouthbar_yolo11l.pt")
    ),
    max_instances=99,
    min_confidence=0.25,
    constrain_func=constrain_mouthbar,
)

ae_to_prediction_params = {
    "deltatop": prediction_parameters_deltatop,
    "channel": prediction_parameters_ch,
    "mouthbar": prediction_parameters_mb,
}


def generate_prediction_images(modelresult: ModelResult, folder: Path | str):
    for i in range(0, modelresult.timestep, 1):
        pred_image = plt.imshow(
            modelresult.bottom_depth[i, :, :],
            cmap=colormaps.BottomDepthColormap.cmap,
            vmin=colormaps.BottomDepthColormap.vmin,
            vmax=colormaps.BottomDepthColormap.vmax,
        ).make_image("png", unsampled=True)[0]
        plt.imsave(
            folder.joinpath(f"{i:04d}_pred_image.png"),
            pred_image,
            format="png",
        )

    return pred_image.shape[-2]


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


def detect(
    modelresult: ModelResult,
    archels_to_detect: list = ["deltatop", "channel", "mouthbar"],
):
    if not prediction_images_temp_folder.is_dir():
        Path.mkdir(prediction_images_temp_folder, exist_ok=True)

    imgsz = generate_prediction_images(modelresult, prediction_images_temp_folder)

    results = []
    for archel_to_detect in archels_to_detect:
        prediction_params = ae_to_prediction_params[archel_to_detect]
        result = predict(prediction_images_temp_folder, prediction_params, imgsz)
        result = prediction_params.constrain_func(modelresult, result)
        results.append(result)

    # Stack results and apply final postprocessing
    final_prediction = segmentation_utils.merge_arrays_in_order(results)
    del results
    final_prediction = postprocess_result(modelresult, final_prediction)

    # Remove temporary folder with prediction images
    # if prediction_images_temp_folder.is_dir():
    #     prediction_images_temp_folder.rmdir()

    return final_prediction.astype(np.uint8)
