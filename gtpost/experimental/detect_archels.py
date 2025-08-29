from pathlib import Path, WindowsPath

import matplotlib.pyplot as plt
import numpy as np

from gtpost import utils
from gtpost.analyze import classifications
from gtpost.experimental import prediction_parameters, segmentation_utils
from gtpost.experimental.prediction_parameters import PredictionParams
from gtpost.visualize import colormaps

ModelResult = None

prediction_images_temp_folder = Path(__file__).parent.joinpath(
    "training_dataset/prediction_images_temp"
)


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


ae_to_prediction_params = {
    "dtundef": prediction_parameters.dtundef,
    "dchannel": prediction_parameters.dchannel,
    "tchannel": prediction_parameters.tchannel,
    "beachridge": prediction_parameters.beachridge,
    "beach": prediction_parameters.beach,
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
    if prediction_images_temp_folder.is_dir():
        for file in prediction_images_temp_folder.glob("*"):
            file.unlink()
        prediction_images_temp_folder.rmdir()

    return final_prediction.astype(np.uint8)
