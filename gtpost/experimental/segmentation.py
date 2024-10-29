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
    PredictionParams(unit_name="main_channel", max_instances=2),
    PredictionParams(unit_name="spit", max_instances=4, min_confidence=0.1),
]

prediction_parameters_sobrarbe = [
    PredictionParams(unit_name="Delta area", max_instances=1),
    PredictionParams(unit_name="Delta front", max_instances=1),
    PredictionParams(unit_name="Channel", max_instances=99, min_confidence=0.05),
    PredictionParams(unit_name="Mouth bar", max_instances=10, min_confidence=0.02),
]


def tune():
    pass


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
    trained_yolo_model: YOLO,
    imgsz: int,
    parameter_classes,
) -> np.array:
    images = sorted([str(f) for f in Path(image_folder).glob("*.png")])
    prediction = predict_units(images, trained_yolo_model, imgsz, parameter_classes)
    return prediction


def prediction_bathymetry_figure(prediction_result, d3d_folder, save_folder):
    modelresult = ModelResult.from_folder(Path(d3d_folder), post=False)
    depth = modelresult.bottom_depth

    for i in range(0, prediction_result.shape[0], 1):
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
            cmap=colormaps.ExperimentalArchelColormap.cmap,
            interpolation="antialiased",
            interpolation_stage="rgba",
        )
        fig.colorbar(
            colormaps.BottomDepthColormap.mappable, cax=cax1, orientation="horizontal"
        )
        colorbar = fig.colorbar(
            colormaps.WaveArchelColormap.mappable, cax=cax2, orientation="horizontal"
        )
        colorbar.set_ticks(colormaps.WaveArchelColormap.ticks + 0.5)
        colorbar.set_ticklabels(colormaps.WaveArchelColormap.labels, fontsize=12)

        plt.savefig(save_folder + f"\\prediction_result_{i}.png")
        plt.close()


if __name__ == "__main__":
    # model = YOLO(
    #     r"c:\Users\onselen\Development\D3D_Geotool\GT-Post\gtpost\experimental\pretrained_yolo_models\yolo11m-seg.pt"
    # )
    # # results = model.tune(
    # #     data=r"p:\11210835-002-d3d-gt-wave-dominated\02_postprocessing\Pro_030\training_images_customrgb_4classes\YOLODataset\dataset.yaml",
    # #     epochs=30,
    # #     iterations=80,
    # #     imgsz=282,
    # #     device="cpu",
    # #     save=False,
    # #     optimizer="AdamW",
    # #     plots=False,
    # #     val=False,
    # # )
    # results = model.train(
    #     data=r"p:\11209074-002-geotool-new-deltas\02_postprocessing\Sobrarbe_048_Reference\images_for_training\YOLODataset\dataset.yaml",
    #     epochs=100,
    #     imgsz=282,
    #     device="cpu",
    #     lr0=0.00659,
    #     lrf=0.01089,
    #     momentum=0.82058,
    #     weight_decay=0.00062,
    #     warmup_epochs=4.07926,
    #     warmup_momentum=0.71553,
    #     box=6.19376,
    #     cls=0.57219,
    #     dfl=2.23532,
    #     hsv_h=0.01087,
    #     hsv_s=0.3918,
    #     hsv_v=0.45941,
    #     degrees=0.0,
    #     translate=0.08485,
    #     scale=0.52358,
    #     shear=0.0,
    #     perspective=0.0,
    #     flipud=0.0,
    #     fliplr=0.45541,
    #     bgr=0.0,
    #     mosaic=0.97736,
    #     mixup=0.0,
    #     copy_paste=0.0,
    # )
    image_folder = r"p:\11209074-002-geotool-new-deltas\02_postprocessing\Sobrarbe_048_Reference\prediction_images"
    model = YOLO(
        r"c:\Users\onselen\Development\GT-Post\runs\segment\train2\weights\best.pt"
    )
    # result = None
    result = predict(image_folder, model, 282, prediction_parameters_sobrarbe)
    prediction_bathymetry_figure(
        result,
        r"p:\11209074-002-geotool-new-deltas\01_modelling\Sobrarbe_048_Reference",
        r"p:\11209074-002-Geotool-new-deltas\02_postprocessing\Sobrarbe_048_Reference\segmentation_results",
    )
    print(1)
