from pathlib import Path, WindowsPath

import matplotlib
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.gridspec import GridSpec
from mpl_toolkits.axes_grid1 import make_axes_locatable
from ultralytics import YOLO

from gtpost.analyze import classifications
from gtpost.experimental.segmentation_utils import (
    PredictionParams,
    merge_arrays_in_order,
    predict_units,
)
from gtpost.model import ModelResult
from gtpost.visualize import colormaps

default_yolo_model = Path(__file__).parent.joinpath(
    "pretrained_yolo_models/yolo11l-seg.pt"
)

matplotlib.use("TkAgg")

prediction_parameters_dchannel = PredictionParams(
    unit_name="distributary channel",
    string_code="dchannel",
    encoding=classifications.ArchEl.dchannel.value,
    trained_model=YOLO(
        Path(__file__).parent.joinpath("trained_yolo_models/best_dchannel_yolo11l.pt")
    ),
    max_instances=99,
    min_confidence=0.15,
    # constrain_func=constrain_dchannel,
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
    # constrain_func=constrain_beachridge,
)

prediction_parameters_dtundef = PredictionParams(
    unit_name="deltatop",
    string_code="dtundef",
    encoding=classifications.ArchEl.dtundef.value,
    trained_model=YOLO(
        Path(__file__).parent.joinpath("trained_yolo_models/best_dtundef_yolo11l.pt")
    ),
    min_confidence=0.5,
    max_instances=1,
    # constrain_func=constrain_deltatop,
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
    # constrain_func=constrain_tchannel,
)

prediction_parameters_beach = PredictionParams(
    unit_name="Beach",
    string_code="beach",
    encoding=classifications.ArchEl.beach.value,
    trained_model=YOLO(
        Path(__file__).parent.joinpath("trained_yolo_models/best_beach_yolo11l.pt")
    ),
    max_instances=20,
    min_confidence=0.1,
    # constrain_func=constrain_tchannel,
)


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
        epochs=400,
        imgsz=imgsz,
        device="cpu",
        lr0=0.00659,
        lrf=0.01089,
        momentum=0.82058,
        weight_decay=0.00062,
        warmup_epochs=4.07926,
        warmup_momentum=0.71553,
        box=6.19376,
        cls=0.57219,
        dfl=2.23532,
        hsv_h=0.01087,
        hsv_s=0.3918,
        hsv_v=0.45941,
        degrees=0.0,
        translate=0.08485,
        scale=0.52358,
        shear=0.0,
        perspective=0.0,
        flipud=0.0,
        fliplr=0.45541,
        bgr=0.0,
        mosaic=0.97736,
        mixup=0.0,
        copy_paste=0.0,
    )
    return results


def predict(
    image_folder: str | WindowsPath,
    prediction_parameters: PredictionParams | list[PredictionParams],
    imgsz: int,
) -> np.array:
    if isinstance(prediction_parameters, PredictionParams):
        prediction_parameters = [prediction_parameters]
    images = sorted([str(f) for f in Path(image_folder).glob("*.png")])
    prediction = predict_units(images, prediction_parameters, imgsz)
    return prediction


def prediction_bathymetry_figure(prediction_result, d3d_folder, save_folder):
    modelresult = ModelResult.from_folder(
        Path(d3d_folder), post=False, use_copied_trim_file=False
    )
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
            colormaps.ExperimentalArchelColormap.mappable,
            cax=cax2,
            orientation="horizontal",
        )
        colorbar.set_ticks(colormaps.ExperimentalArchelColormap.ticks + 0.5)
        colorbar.set_ticklabels(
            colormaps.ExperimentalArchelColormap.labels, fontsize=12
        )

        plt.savefig(save_folder + f"\\prediction_result_{i}.png")
        plt.close()


if __name__ == "__main__":
    results = train(
        Path(__file__).parent.joinpath(
            r"training_dataset\images_for_masking\YOLODataset_dchannel\dataset.yaml"
        ),
        282,
    )
    results = train(
        Path(__file__).parent.joinpath(
            r"training_dataset\images_for_masking\YOLODataset_beachridge\dataset.yaml"
        ),
        282,
    )
    results = train(
        Path(__file__).parent.joinpath(
            r"training_dataset\images_for_masking\YOLODataset_dtundef\dataset.yaml"
        ),
        282,
    )
    results = train(
        Path(__file__).parent.joinpath(
            r"training_dataset\images_for_masking\YOLODataset_beach\dataset.yaml"
        ),
        282,
    )
    results = train(
        Path(__file__).parent.joinpath(
            r"training_dataset\images_for_masking\YOLODataset_tchannel\dataset.yaml"
        ),
        282,
    )

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
