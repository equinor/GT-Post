import json
import logging
from pathlib import Path

import matplotlib
import matplotlib.pyplot as plt
import numpy as np

from gtpost.analyze import surface
from gtpost.experimental import segmentation_utils
from gtpost.model import ModelResult
from gtpost.utils import describe_data_vars, get_current_time, get_template_name
from gtpost.visualize import colormaps

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

    Path.mkdir(fpath_output, exist_ok=True)
    Path.mkdir(fpath_masking_images, exist_ok=True)
    # Path.mkdir(fpath_training_images, exist_ok=True)
    Path.mkdir(fpath_prediction_images, exist_ok=True)

    template_name = get_template_name(fpath_input)
    settings_file = (
        Path(__file__).parents[2].joinpath(f"config/settings_{template_name}.ini")
    )

    modelresult = ModelResult.from_folder(
        fpath_input, post=False, settings_file=settings_file, use_copied_trim_file=False
    )
    # describe_data_vars(modelresult.dataset, fpath_output / "data_vars.txt")
    logger.info(
        f"{get_current_time()}: Initialized model results:\n\n{modelresult}\n\n"
    )
    logger.info(f"{get_current_time()}: Starting processing")
    # modelresult.process()
    logger.info(
        f"{get_current_time()}: Processing completed, creating training images..."
    )

    for i in range(0, modelresult.timestep, 1):
        # masking_img is an image of the bathymetry that will be used to draw the training
        # image segmentation masks.
        fig, ax = plt.subplots()
        contour = ax.contour(
            modelresult.bottom_depth[i, :, :], levels=[0], colors="white"
        )
        rgb_image = ax.imshow(
            modelresult.bottom_depth[i, :, :],
            cmap=colormaps.BottomDepthHighContrastColormap.cmap,
            vmin=colormaps.BottomDepthHighContrastColormap.vmin,
            vmax=colormaps.BottomDepthHighContrastColormap.vmax,
        ).make_image("png", unsampled=True)[0]
        for path in contour.get_paths():
            vertices = path.vertices
            for vertex in vertices:
                x, y = vertex
                rgb_image[int(y), int(x), :] = [
                    250,
                    250,
                    250,
                    255,
                ]  # Set contour color to white
        plt.imsave(
            fpath_prediction_images.joinpath(f"seg_image_{i}.png"),
            rgb_image,
            format="png",
        )
        if i % every_nth_image == 0:
            plt.imsave(
                fpath_masking_images.joinpath(f"seg_image_{i}.png"),
                rgb_image,
                format="png",
            )
        plt.close(fig)


if __name__ == "__main__":
    main(
        r"p:\11210835-002-d3d-gt-wave-dominated\01_modelling\Pro_097",
        r"c:\Users\onselen\Development\GT-Post\gtpost\experimental\training_dataset",
    )
