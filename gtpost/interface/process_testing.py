import logging
from pathlib import Path

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
    main function that interfaces with the Delft3D Geotool backend for processing during
    a model run.

    Parameters
    ----------
    fpath_input : str | Path, optional
        Path with input, including at least the .sed file, config ini file, and most
        importantly the trim.nc file with model results up to the last exported timestep.
        by default the relative path is "/data/input" within the container folder
        structure.
    fpath_output : str | Path, optional
        Relative path within the container folder structure to write results to,
        by default "/data/output"


    Output for D3D-GT and to be displayed in the processing GUI elements:

    - Figures showing bathymetry and sedimentation/erosion rate (top down)
    - Figures showing median sediment diameter D50 (along a cross-shore profile)
    """
    fpath_input = Path(fpath_input)
    fpath_output = Path(fpath_output)

    template_name = get_template_name(fpath_input)
    settings_file = (
        Path(__file__).parents[2].joinpath(f"config/settings_{template_name}.ini")
    )

    try:
        modelresult = ModelResult.from_folder(
            fpath_input,
            post=False,
            settings_file=settings_file,
            use_copied_trim_file=False,
        )
    except Exception as e:
        logger.error(f"Failed to initialize model results: {e}")
        return
    logger.info(
        f"{get_current_time()}: Initialized model results:\n\n{modelresult}\n\n"
    )
    logger.info(
        f"{get_current_time()}: >>> ModelResult initialized, " + log_memory_usage()
    )
    logger.info(f"{get_current_time()}: Starting processing")
    modelresult.process()
    logger.info(f"{get_current_time()}: >>> Processing complete, " + log_memory_usage())

    # Map plots
    logger.info(f"{get_current_time()}: Plotting maps")
    map_plotter = plot.MapPlot(modelresult)
    map_plotter.twopanel_map(
        "bottom_depth",
        "deposit_height",
        fpath_output,
        "map_bottomdepth_deposition",
        only_last_timestep=True,
    )
    logger.info(
        f"{get_current_time()}: >>> Plotting maps complete, " + log_memory_usage()
    )

    # Cross-section plots
    position_tags = ["xshore_7000", "xshore_6000", "xshore_8000", "lshore_1500"]
    xsect_starts = [(18, 140), (20, 120), (20, 160), (30, 0)]
    xsect_ends = [(100, 140), (90, 120), (90, 160), (30, 280)]

    for position_tag, xsect_start, xsect_end in zip(
        position_tags, xsect_starts, xsect_ends
    ):
        xsect_plotter = plot.CrossSectionPlot(modelresult, xsect_start, xsect_end)

        logger.info(
            f"{get_current_time()}: Plotting D50 x-sections, " + log_memory_usage()
        )
        xsect_plotter.twopanel_xsection(
            "bottom_depth",
            "d50",
            fpath_output,
            f"xsect_diameter_{position_tag}",
            only_last_timestep=False,
        )
        logger.info(
            f"{get_current_time()}: >>> D50 x-sections plotting complete, "
            + log_memory_usage()
        )

    (fpath_input / "temp.nc").unlink(missing_ok=True)
    logger.info(
        f"{get_current_time()}: >>> Processing steps complete, " + log_memory_usage()
    )


if __name__ == "__main__":
    main(
        r"p:\11210835-002-d3d-gt-wave-dominated\01_modelling\Pro_067",
        r"p:\11210835-002-d3d-gt-wave-dominated\02_postprocessing\Pro_067",
    )
