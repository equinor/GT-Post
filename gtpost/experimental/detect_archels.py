from pathlib import Path, WindowsPath

import matplotlib.pyplot as plt
import numpy as np
from ultralytics import YOLO

from gtpost import utils
from gtpost.analyze import classifications
from gtpost.experimental import segmentation_utils
from gtpost.experimental.segmentation_utils import PredictionParams
from gtpost.visualize import colormaps

ModelResult = None

prediction_images_temp_folder = Path(__file__).parent.joinpath(
    "training_dataset/prediction_images_temp"
)


def constrain_dchannel(modelresult: ModelResult, prediction_result: np.ndarray):
    # Water depth must be > 0 m to justify a channel prediction
    prediction_result[
        (prediction_result == classifications.ArchEl.dchannel.value)
        & (modelresult.bottom_depth < -2)
    ] = classifications.ArchEl.undefined.value
    return prediction_result


def constrain_tchannel(modelresult: ModelResult, prediction_result: np.ndarray):
    # Water depth must be > 0 m to justify a channel prediction
    prediction_result[
        (prediction_result == classifications.ArchEl.tchannel.value)
        & (modelresult.bottom_depth < 0)
    ] = classifications.ArchEl.undefined.value
    return prediction_result


def constrain_mouthbar(modelresult: ModelResult, prediction_result: np.ndarray):
    # Limit the depth at which mouth bars are expected, based on the delta front depth
    prediction_result[
        (prediction_result == classifications.ArchEl.mouthbar.value)
        & (modelresult.bottom_depth > 4)
        & (modelresult.deposit_height < 0.05)
    ] = classifications.ArchEl.undefined.value
    return prediction_result


def constrain_dtundef(modelresult: ModelResult, prediction_result: np.ndarray):
    # split delta top into an undefined and bay fill unit
    prediction_result[
        (prediction_result == classifications.ArchEl.dtundef.value)
        & (modelresult.bottom_depth > 0)
    ] = classifications.ArchEl.dtbayfill.value
    return prediction_result


def constrain_beachridge(modelresult: ModelResult, prediction_result: np.ndarray):
    # A beach ridge must lie above the water level for it to be valid
    prediction_result[
        (prediction_result == classifications.ArchEl.beachridge.value)
        & (modelresult.bottom_depth > 0)
    ] = classifications.ArchEl.undefined.value
    return prediction_result


def postprocess_result(
    modelresult: ModelResult,
    prediction_result: np.ndarray,
):
    # Apply model mask to the prediction result
    prediction_result *= modelresult.model_mask.values
    prediction_result[
        (prediction_result == classifications.ArchEl.undefined.value)
        & (modelresult.bottom_depth > 12)
    ] = classifications.ArchEl.offshore.value
    prediction_result[
        (prediction_result == classifications.ArchEl.undefined.value)
        & (modelresult.bottom_depth <= 12)
        & (modelresult.bottom_depth > 4)
    ] = classifications.ArchEl.lshoreface.value
    prediction_result[
        (prediction_result == classifications.ArchEl.undefined.value)
        & (modelresult.bottom_depth <= 4)
        & (modelresult.bottom_depth > -2)
    ] = classifications.ArchEl.ushoreface.value
    return prediction_result


prediction_parameters_dchannel = PredictionParams(
    unit_name="distributary channel",
    string_code="dchannel",
    encoding=classifications.ArchEl.dchannel.value,
    trained_model=YOLO(
        Path(__file__).parent.joinpath("trained_yolo_models/best_dchannel_yolo11l.pt")
    ),
    max_instances=99,
    min_confidence=0.08,
    constrain_func=constrain_dchannel,
)

prediction_parameters_beachridge = PredictionParams(
    unit_name="Beach ridge",
    string_code="beachridge",
    encoding=classifications.ArchEl.beachridge.value,
    trained_model=YOLO(
        Path(__file__).parent.joinpath("trained_yolo_models/best_beachridge_yolo11l.pt")
    ),
    max_instances=99,
    min_confidence=0.1,
    constrain_func=constrain_beachridge,
)

prediction_parameters_dtundef = PredictionParams(
    unit_name="deltatop",
    string_code="dtundef",
    encoding=classifications.ArchEl.dtundef.value,
    trained_model=YOLO(
        Path(__file__).parent.joinpath("trained_yolo_models/best_dtundef_yolo11l.pt")
    ),
    min_confidence=0.2,
    max_instances=1,
    constrain_func=constrain_dtundef,
)

prediction_parameters_tchannel = PredictionParams(
    unit_name="tidal channel",
    string_code="tchannel",
    encoding=classifications.ArchEl.tchannel.value,
    trained_model=YOLO(
        Path(__file__).parent.joinpath("trained_yolo_models/best_tchannel_yolo11l.pt")
    ),
    max_instances=20,
    min_confidence=0.1,
    constrain_func=constrain_tchannel,
)

ae_to_prediction_params = {
    "dtundef": prediction_parameters_dtundef,
    "dchannel": prediction_parameters_dchannel,
    "tchannel": prediction_parameters_tchannel,
    "beachridge": prediction_parameters_beachridge,
}


def generate_prediction_images(modelresult: ModelResult, folder: Path | str):
    for i in range(0, modelresult.timestep, 1):
        pred_image = plt.imshow(
            modelresult.bottom_depth[i, :, :],
            cmap=colormaps.BottomDepthHighContrastColormap.cmap,
            vmin=colormaps.BottomDepthHighContrastColormap.vmin,
            vmax=colormaps.BottomDepthHighContrastColormap.vmax,
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
    archels_to_detect: list = ["dtundef", "dchannel", "tchannel", "beachridge"],
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
    final_prediction = utils.normalize_numpy_array(final_prediction)

    # Remove temporary folder with prediction images
    # if prediction_images_temp_folder.is_dir():
    #     prediction_images_temp_folder.rmdir()

    return final_prediction.astype(np.uint8)
