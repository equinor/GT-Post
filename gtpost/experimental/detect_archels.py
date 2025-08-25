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
    # TODO: add condition for dchannel to become tchannel
    prediction_result[
        (prediction_result == classifications.ArchEl.dchannel.value)
        & (modelresult.bottom_depth < -2)
    ] = classifications.ArchEl.undefined.value

    should_be_tchannel = (
        np.max(modelresult.dataset["MAX_UV"][:, 1, :].values, axis=1) < 0.3
    )
    # Only update dchannel to tchannel where should_be_tchannel is True (on time axis)
    for t_idx, should_convert in enumerate(should_be_tchannel):
        if should_convert:
            mask = prediction_result[t_idx] == classifications.ArchEl.dchannel.value
            prediction_result[t_idx][mask] = classifications.ArchEl.tchannel.value

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


def constrain_beach(modelresult: ModelResult, prediction_result: np.ndarray):
    # Beach with more than 1 m water depth should be classified as upper shoreface
    # Below -2 m water depth, beach is undefined.
    prediction_result[
        (prediction_result == classifications.ArchEl.beach.value)
        & (modelresult.bottom_depth > 1.5)
    ] = classifications.ArchEl.ushoreface.value
    prediction_result[
        (prediction_result == classifications.ArchEl.beach.value)
        & (modelresult.bottom_depth < -1.5)
    ] = classifications.ArchEl.dtundef.value
    return prediction_result


def postprocess_result(
    modelresult: ModelResult,
    prediction_result: np.ndarray,
):
    # Apply model mask to the prediction result
    prediction_result *= modelresult.model_mask.values
    prediction_result[
        (prediction_result == classifications.ArchEl.undefined.value)
        & (modelresult.dataset["UORB"] < 0.2)
        & (modelresult.bottom_depth > 6)
    ] = classifications.ArchEl.offshore.value
    prediction_result[
        (prediction_result == classifications.ArchEl.undefined.value)
        & (modelresult.dataset["UORB"] < 0.4)
        & (modelresult.bottom_depth > 2)
    ] = classifications.ArchEl.lshoreface.value
    prediction_result[
        (prediction_result == classifications.ArchEl.undefined.value)
        & (modelresult.bottom_depth > 0)
    ] = classifications.ArchEl.ushoreface.value
    prediction_result[
        (prediction_result == classifications.ArchEl.beach.value)
        & (modelresult.bottom_depth > 0)
    ] = classifications.ArchEl.ushoreface.value
    prediction_result[
        (prediction_result == classifications.ArchEl.undefined.value)
        & (modelresult.bottom_depth <= 0)
    ] = classifications.ArchEl.dtundef.value
    prediction_result[0, 0, 0] = 0
    return prediction_result


prediction_parameters_dchannel = PredictionParams(
    unit_name="distributary channel",
    string_code="dchannel",
    encoding=classifications.ArchEl.dchannel.value,
    trained_model=YOLO(
        Path(__file__).parent.joinpath("trained_yolo_models/best_dchannel_yolo11l.pt")
    ),
    max_instances=99,
    min_confidence=0.3,
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
    min_confidence=0.3,
    constrain_func=constrain_beachridge,
)

prediction_parameters_beach = PredictionParams(
    unit_name="Beach",
    string_code="beach",
    encoding=classifications.ArchEl.beach.value,
    trained_model=YOLO(
        Path(__file__).parent.joinpath("trained_yolo_models/best_beach_yolo11l.pt")
    ),
    max_instances=99,
    min_confidence=0.2,
    constrain_func=constrain_beach,
)

prediction_parameters_dtundef = PredictionParams(
    unit_name="deltatop",
    string_code="dtundef",
    encoding=classifications.ArchEl.dtundef.value,
    trained_model=YOLO(
        Path(__file__).parent.joinpath("trained_yolo_models/best_dtundef_yolo11l.pt")
    ),
    min_confidence=0.3,
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
    min_confidence=0.12,
    constrain_func=constrain_tchannel,
)

ae_to_prediction_params = {
    "dtundef": prediction_parameters_dtundef,
    "dchannel": prediction_parameters_dchannel,
    "tchannel": prediction_parameters_tchannel,
    "beachridge": prediction_parameters_beachridge,
    "beach": prediction_parameters_beach,
}


def generate_prediction_images(modelresult: ModelResult, folder: Path | str):
    for i in range(0, modelresult.timestep, 1):
        fig, ax = plt.subplots()
        contour = ax.contour(
            modelresult.bottom_depth[i, :, :], levels=[0], colors="white"
        )
        pred_image = ax.imshow(
            modelresult.bottom_depth[i, :, :],
            cmap=colormaps.BottomDepthHighContrastColormap.cmap,
            vmin=colormaps.BottomDepthHighContrastColormap.vmin,
            vmax=colormaps.BottomDepthHighContrastColormap.vmax,
        ).make_image("png", unsampled=True)[0]

        # Also add a contour of the 0 m water depth to the training image. This helps
        # in visual interpretation of the masking images.
        for path in contour.get_paths():
            vertices = path.vertices
            for vertex in vertices:
                x, y = vertex
                pred_image[int(y), int(x), :] = [
                    250,
                    250,
                    250,
                    255,
                ]  # Set contour color to white
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
    archels_to_detect: list = [
        "dtundef",
        "dchannel",
        "tchannel",
        "beachridge",
        "beach",
    ],
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
    final_prediction = postprocess_result(modelresult, final_prediction)
    final_prediction = utils.normalize_numpy_array(final_prediction)

    # Remove temporary folder with prediction images
    # if prediction_images_temp_folder.is_dir():
    #     prediction_images_temp_folder.rmdir()

    return final_prediction.astype(np.uint8)
