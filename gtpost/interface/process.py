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
    logger.info(log_memory_usage())

    template_name = get_template_name(fpath_input)
    settings_file = (
        Path(__file__).parents[2].joinpath(f"config/settings_{template_name}.ini")
    )

    try:
        modelresult = ModelResult.from_folder(
            fpath_input, post=False, settings_file=settings_file
        )
    except Exception as e:
        logger.error(f"Failed to initialize model results: {e}")
        return
    logger.info(
        f"{get_current_time()}: Initialized model results:\n\n{modelresult}\n\n"
    )
    logger.info(f"{get_current_time()}: Starting processing")
    modelresult.process()

    # Map plots
    logger.info(f"{get_current_time()}: Plotting maps")
    map_plotter = plot.MapPlot(modelresult)
    map_plotter.twopanel_map("bottom_depth", "deposit_height", only_last_timestep=True)
    map_plotter.save_figures(fpath_output, "map_bottomdepth_deposition")

    # Cross-section plots
    xsect_start = (modelresult.mouth_position[1], modelresult.mouth_position[0])
    xsect_end = (modelresult.mouth_position[1] + 120, modelresult.mouth_position[0])
    # xsect_start = (160, 160)
    # xsect_end = (280, 160)
    xsect_plotter = plot.CrossSectionPlot(modelresult, xsect_start, xsect_end)

    logger.info(f"{get_current_time()}: Plotting D50 x-sections")
    xsect_plotter.twopanel_xsection("bottom_depth", "d50", only_last_timestep=True)
    xsect_plotter.save_figures(fpath_output, "xsect_diameter")
    (fpath_input / "temp.nc").unlink(missing_ok=True)


if __name__ == "__main__":
    main()
