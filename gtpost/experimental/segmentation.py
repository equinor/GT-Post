from pathlib import Path, WindowsPath

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.gridspec import GridSpec
from mpl_toolkits.axes_grid1 import make_axes_locatable
from ultralytics import YOLO

from gtpost.experimental.segmentation_utils import PredictionParams, predict_units
from gtpost.model import ModelResult
from gtpost.visualize import colormaps

default_yolo_model = Path(__file__).parent.joinpath(
    "pretrained_yolo_models/yolov8s-seg.pt"
)

prediction_parameters_wave_dominated = [
    PredictionParams(unit_name="delta", max_instances=1),
    PredictionParams(unit_name="upper_shoreface", max_instances=1),
    PredictionParams(unit_name="main_channel", max_instances=1),
    PredictionParams(unit_name="spit", max_instances=4),
]


def train(
    yolo_dataset: str | WindowsPath,
    imgsz: int,
    pretrained_yolo_model: str | WindowsPath = default_yolo_model,
):
    """
    Main function to train a model

    Parameters
    ----------
    yolo_dataset : str | WindowsPath
        Path to YOLO dataset.yaml file
    imgsz : int
        Input image size
    pretrained_yolo_model : str | WindowsPath, optional
        Path to pre-trained YOLO model (.pt file), by default yolov8s-seg.pt is used.

    Returns
    -------
    _type_
        _description_
    """
    model = YOLO(pretrained_yolo_model)
    results = model.train(
        data=yolo_dataset,
        epochs=100,
        imgsz=imgsz,
    )
    return results


def predict(
    image_folder: str | WindowsPath,
    trained_yolo_model: str | WindowsPath,
    imgsz: int,
    parameter_classes,
) -> np.array:
    images = sorted([str(f) for f in Path(image_folder).glob("*.png")])
    prediction = predict_units(images, trained_yolo_model, imgsz, parameter_classes)
    return prediction


def prediction_bathymetry_figure(prediction_result, d3d_folder, save_folder):
    modelresult = ModelResult.from_folder(Path(d3d_folder), post=False)
    depth = modelresult.bottom_depth

    for i in range(-1, -prediction_result.shape[0] - 1, -1):
        fig = plt.figure(dpi=72)
        gs = GridSpec(1, 2, left=0.05, right=0.95, wspace=0.1)
        ax1 = fig.add_subplot(gs[0, 0])
        ax2 = fig.add_subplot(gs[0, 1], sharex=ax1, sharey=ax1)
        divider1 = make_axes_locatable(ax1)
        divider2 = make_axes_locatable(ax2)
        cax1 = divider1.append_axes("bottom", size="5%", pad="12%")
        cax2 = divider2.append_axes("bottom", size="5%", pad="12%")
        dpi = fig.get_dpi()
        fig.set_size_inches(1400 / float(dpi), 700 / float(dpi))

        ax1.imshow(
            depth[i, :, :],
            cmap=colormaps.BottomDepthColormap.cmap,
            interpolation="antialiased",
            interpolation_stage="rgba",
            vmin=colormaps.BottomDepthColormap.vmin,
            vmax=colormaps.BottomDepthColormap.vmax,
        )
        ax2.imshow(
            prediction_result[i, :, :],
            cmap=colormaps.ArchelColormap.cmap,
            interpolation="antialiased",
            interpolation_stage="rgba",
        )
        fig.colorbar(
            colormaps.BottomDepthColormap.mappable, cax=cax1, orientation="horizontal"
        )
        colorbar = fig.colorbar(
            colormaps.ArchelColormap.mappable, cax=cax2, orientation="horizontal"
        )
        colorbar.set_ticks(colormaps.ArchelColormap.ticks + 0.5)
        colorbar.set_ticklabels(colormaps.ArchelColormap.labels, fontsize=12)

        plt.savefig(save_folder + f"\\prediction_result_{-i}.png")
        plt.close()


if __name__ == "__main__":
    image_folder = r"p:\11210835-002-d3d-gt-wave-dominated\02_postprocessing\Pro_028\prediction_images"
    model = YOLO(
        r"c:\Users\onselen\Development\D3D_Geotool\GT-Post\gtpost\experimental\trained_yolo_models\best.pt"
    )
    # result = None
    result = predict(image_folder, model, 282, prediction_parameters_wave_dominated)
    prediction_bathymetry_figure(
        result,
        r"p:\11210835-002-d3d-gt-wave-dominated\01_modelling\Pro_028",
        r"p:\11210835-002-d3d-gt-wave-dominated\02_postprocessing\Pro_028\segmentation_result",
    )
    print(1)
