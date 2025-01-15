import json
import logging
from pathlib import Path

from gtpost.model import ModelResult
from gtpost.utils import get_current_time, get_template_name
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
        fpath_input, post=True, settings_file=settings_file
    )
    logger.info(
        f"{get_current_time()}: Initialized model results:\n\n{modelresult}\n\n"
    )
    logger.info(f"{get_current_time()}: Starting postprocessing")
    modelresult.postprocess()
    logger.info(f"{get_current_time()}: Postprocessing completed, exporting data...")

    # Data export
    modelresult.append_input_ini_file(
        input_ini_file,
        fpath_output.joinpath(modelresult.modelname + "_input_postprocessed.ini"),
    )
    logger.info(
        f"{get_current_time()}: Created {modelresult.modelname + '_input_postprocessed.ini'}"
    )
    # modelresult.export_sediment_and_object_data(
    #     fpath_output.joinpath(modelresult.modelname + "_sed_and_obj_data.nc")
    # )
    # logger.info(
    #     f"{get_current_time()}: Created {modelresult.modelname + '_sed_and_obj_data.nc'}"
    # )

    # with open(
    #     fpath_output.joinpath(modelresult.modelname + "_statistics_summary.json"), "w"
    # ) as f:
    #     json.dump(
    #         modelresult.delta_stats,
    #         f,
    #     )
    # logger.info(
    #     f"{get_current_time()}: Created {modelresult.modelname + '_statistics_summary.json'}"
    # )

    # # Summary plot
    logger.info(f"{get_current_time()}: Plotting stats")
    stat_plotter = plot.StatPlot(modelresult)
    stat_plotter.plot_histograms()
    stat_plotter.save_figures(fpath_output, "archel_summary")

    # Map plots
    logger.info(f"{get_current_time()}: Plotting archel maps")
    map_plotter = plot.MapPlot(modelresult)
    map_plotter.twopanel_map("bottom_depth", "architectural_elements")
    map_plotter.save_figures(fpath_output, "map_bottomdepth_archels")

    # Cross-section plots
    xsect_start = (modelresult.mouth_position[1], modelresult.mouth_position[0])
    xsect_end = (
        modelresult.mouth_position[1] + 120,
        modelresult.mouth_position[0],
    )
    xsect_start = (90, 130)
    xsect_end = (160, 130)
    xsect_plotter = plot.CrossSectionPlot(modelresult, xsect_start, xsect_end)

    logger.info(f"{get_current_time()}: Plotting D50 x-sections")
    xsect_plotter.twopanel_xsection("bottom_depth", "d50", only_last_timestep=True)
    xsect_plotter.save_figures(fpath_output, "xsect_diameter")

    logger.info(f"{get_current_time()}: Plotting archel x-sections")
    xsect_plotter.twopanel_xsection(
        "bottom_depth", "architectural_elements", only_last_timestep=True
    )
    xsect_plotter.save_figures(fpath_output, "xsect_archels")

    logger.info(f"{get_current_time()}: Plotting deposition age x-sections")
    xsect_plotter.twopanel_xsection(
        "bottom_depth", "deposition_age", only_last_timestep=True
    )
    xsect_plotter.save_figures(fpath_output, "xsect_depositionage")


if __name__ == "__main__":
    main(
        r"p:\11210835-002-d3d-gt-wave-dominated\01_modelling\Pro_054_test_lastdimr_netcdf",
        r"p:\11210835-002-d3d-gt-wave-dominated\02_postprocessing\Pro_054_test_lastdimr_netcdf",
    )
