import json
import logging
from pathlib import Path

import matplotlib
import matplotlib.pyplot as plt

from gtpost.experimental import segmentation_utils
from gtpost.model import ModelResult
from gtpost.utils import get_current_time, get_template_name
from gtpost.visualize import colormaps
from gtpost.analyze import surface

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)
matplotlib.use("TkAgg")


def main(
    fpath_input: str | Path = "/data/input",
    fpath_output: str | Path = "/data/output",
    every_nth_image: int = 20,
) -> None:
    """
    Function that prepares training images for a YOLO instance segmentation model

    Produces three folders:

    images_for_masking: images that can be labelled using the labelme software
    images_for_training: non-user interpretable images with RGB channels representing
    different D3D output and post-processing parameters.
    prediction_images: full set of D3D output timesteps with the same RGb channels as
    the training images. The trained model can be applied to these images.

    For the masking and training images every n-th D3D result is exported according to
    the every_nth_image parameter.
    """
    fpath_input = Path(fpath_input)
    fpath_output = Path(fpath_output)
    fpath_masking_images = fpath_output / "images_for_masking"
    fpath_training_images = fpath_output / "images_for_training"
    fpath_prediction_images = fpath_output / "prediction_images"

    if not fpath_output.is_dir():
        Path.mkdir(fpath_output, exist_ok=True)
        Path.mkdir(fpath_masking_images, exist_ok=True)
        Path.mkdir(fpath_training_images, exist_ok=True)
        Path.mkdir(fpath_prediction_images, exist_ok=True)

    template_name = get_template_name(fpath_input)
    settings_file = (
        Path(__file__).parents[2].joinpath(f"config/settings_{template_name}.ini")
    )

    modelresult = ModelResult.from_folder(
        fpath_input, post=False, settings_file=settings_file
    )
    logger.info(
        f"{get_current_time()}: Initialized model results:\n\n{modelresult}\n\n"
    )
    logger.info(f"{get_current_time()}: Starting processing")
    modelresult.slope = surface.slope(modelresult.bottom_depth)
    # modelresult.process()
    logger.info(
        f"{get_current_time()}: Processing completed, creating training images..."
    )

    for i in range(0, modelresult.timestep, every_nth_image):
        # masking_img is an image of the bathymetry that will be used to draw the training
        # image segmentation masks.
        masking_image = plt.imshow(
            modelresult.bottom_depth[i, :, :],
            cmap=colormaps.BottomDepthColormap.cmap,
            vmin=colormaps.BottomDepthColormap.vmin,
            vmax=colormaps.BottomDepthColormap.vmax,
        ).make_image("png", unsampled=True)[0]

        # training_image is an image where the RGB channels are chosen to represent three
        # different D3D output parameters. These channels will be used for training the
        # YOLO instance segmentation model.
        training_image = segmentation_utils.arrays_to_8bit_rgb(
            [
                modelresult.bottom_depth[i, :, :],
                modelresult.dataset["DM"].values[i, :, :],
                modelresult.dataset["MAX_UV"].values[i, :, :],
            ],
            [0, 0, 0],
            [12, 0.0005, 1],
        )
        plt.imsave(
            fpath_masking_images.joinpath(f"seg_image_{i}.png"),
            masking_image,
            format="png",
        )
        plt.imsave(
            fpath_training_images.joinpath(f"seg_image_{i}.png"),
            training_image,
            format="png",
        )

    for i in range(0, modelresult.timestep, 1):
        # seg_img is an image of the bathymetry that will be used to draw the training
        # image segmentation masks.
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
            fpath_prediction_images.joinpath(f"seg_image_{i}.png"),
            pred_image,
            format="png",
        )


if __name__ == "__main__":
    main(
        r"p:\11209074-002-Geotool-new-deltas\01_modelling\Sobrarbe_048_Reference",
        r"p:\11209074-002-Geotool-new-deltas\02_postprocessing\Sobrarbe_048_Reference",
    )
