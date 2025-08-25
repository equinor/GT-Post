import json
import logging
from pathlib import Path

import numpy as np

from gtpost.analyze import classifications
from gtpost.model import ModelResult
from gtpost.utils import get_current_time, get_template_name, log_memory_usage
from gtpost.visualize import plot

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)


def main(
    fpath_input: str | Path = "/data/input",
    fpath_output: str | Path = "/data/output",
) -> None:
    """
    main function that interfaces with the Delft3D Geotool backend for postprocessing
    model results.

    Parameters
    ----------
    fpath_input : str | Path, optional
        Path with input, including at least the .sed file, config ini file, and most
        importantly the trim.nc file with model results up to the last exported timstep.
        by default the relative path is "/data/input" within the container folder
        structure.
    fpath_output : str | Path, optional
        Relative path within the container folder structure to write results to,
        by default "/data/output"


    Output for D3D-GT and to be displayed in the postprocessing GUI elements:

    - NetCDF file containing all the postprocessing output.
    - JSON file containing statistics per architectural element (to be displayed in GUI)
    - Figures showing bathymetry and architectural elements (top down).
    - Figures showing median sediment diameter D50 (along a cross-shore profile).
    - Figures showing architectural elements (along a cross-shore profile).
    - Figures showing age of deposition (along a cross-shore profile).
    - Summary figure with histograms (AE distribution and fractions per AE)
    """
    fpath_input = Path(fpath_input)
    fpath_output = Path(fpath_output)
    input_ini_file = fpath_input.joinpath("input.ini")

    template_name = get_template_name(fpath_input)
    settings_file = (
        Path(__file__).parents[2].joinpath(f"config/settings_{template_name}.ini")
    )

    modelresult = ModelResult.from_folder(
        fpath_input, post=True, settings_file=settings_file, use_copied_trim_file=False
    )
    logger.info(
        f"{get_current_time()}: Initialized model results:\n\n{modelresult}\n\n"
    )
    logger.info(f"{get_current_time()}: Starting postprocessing, " + log_memory_usage())
    modelresult.postprocess()
    logger.info(
        f"{get_current_time()}: Postprocessing completed, exporting data. "
        + log_memory_usage()
    )

    # Data export
    modelresult.append_input_ini_file(
        input_ini_file,
        fpath_output.joinpath(modelresult.modelname + "_input_postprocessed.ini"),
    )
    logger.info(
        f"{get_current_time()}: Created {modelresult.modelname}_input_postprocessed.ini, "
        + log_memory_usage()
    )
    # modelresult.export_sediment_and_object_data(
    #     fpath_output.joinpath(modelresult.modelname + "_sed_and_obj_data.nc")
    # )
    # logger.info(
    #     f"{get_current_time()}: Created {modelresult.modelname}_sed_and_obj_data.nc"
    #     + log_memory_usage()
    # )

    # with open(
    #     fpath_output.joinpath(modelresult.modelname + "_statistics_summary.json"), "w"
    # ) as f:
    #     json.dump(
    #         modelresult.delta_stats,
    #         f,
    #     )
    # logger.info(
    #     f"{get_current_time()}: Created {modelresult.modelname}_statistics_summary.json"
    #     + log_memory_usage()
    # )

    # logger.info(
    #     f"{get_current_time()}: Created {modelresult.modelname}_architectural_elements.png"
    #     + log_memory_usage()
    # )

    # # Summary plot
    # logger.info(f"{get_current_time()}: Plotting stats, " + log_memory_usage())
    # stat_plotter = plot.StatPlot(modelresult)
    # stat_plotter.plot_histograms(fpath_output, "archel_summary")

    # Map plots
    logger.info(f"{get_current_time()}: Plotting archel maps, " + log_memory_usage())
    map_plotter = plot.MapPlot(modelresult)
    map_plotter.twopanel_map(
        "bottom_depth",
        "architectural_elements",
        fpath_output,
        "map_bottomdepth_archels",
        only_last_timestep=False,
    )

    # Cross-section plots
    position_tags = ["xshore_7000", "xshore_5000", "xshore_9000", "lshore_3500"]
    xsect_starts = [(30, 140), (30, 100), (30, 180), (70, 20)]
    xsect_ends = [(140, 140), (140, 100), (140, 180), (70, 260)]

    # position_tags = ["xshore_7000"]
    # xsect_starts = [(30, 140)]
    # xsect_ends = [(140, 140)]

    for position_tag, xsect_start, xsect_end in zip(
        position_tags, xsect_starts, xsect_ends
    ):
        xsect_plotter = plot.CrossSectionPlot(modelresult, xsect_start, xsect_end)

        # logger.info(
        #     f"{get_current_time()}: Plotting D50 x-sections, " + log_memory_usage()
        # )
        # xsect_plotter.twopanel_xsection(
        #     "bottom_depth",
        #     "d50",
        #     fpath_output,
        #     f"xsect_diameter_{position_tag}",
        #     only_last_timestep=False,
        # )

        logger.info(
            f"{get_current_time()}: Plotting archel x-sections, " + log_memory_usage()
        )
        xsect_plotter.twopanel_xsection(
            "bottom_depth",
            "architectural_elements",
            fpath_output,
            f"xsect_archels_{position_tag}",
            only_last_timestep=False,
        )

        # logger.info(
        #     f"{get_current_time()}: Plotting deposition age x-sections, "
        #     + log_memory_usage()
        # )
        # xsect_plotter.twopanel_xsection(
        #     "bottom_depth",
        #     "deposition_age",
        #     fpath_output,
        #     f"xsect_depositionage_{position_tag}",
        #     only_last_timestep=False,
        # )


if __name__ == "__main__":
    main(
        r"p:\11210835-002-d3d-gt-wave-dominated\01_modelling\Ret_104",
        r"p:\11210835-002-d3d-gt-wave-dominated\02_postprocessing\Ret_104_high_contrast_training_images_new_ai",
    )
