import json
from pathlib import Path

from gtpost.model import ModelResult
from gtpost.utils import get_template_name
from gtpost.visualize import plot


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

    template_name = get_template_name(fpath_input)
    settings_file = (
        Path(__file__).parents[2].joinpath(f"config\\settings_{template_name}.ini")
    )

    modelresult = ModelResult.from_folder(
        fpath_input, post=True, settings_file=settings_file
    )
    modelresult.postprocess()
    modelresult.export_sediment_and_object_data(
        fpath_output.joinpath(modelresult.modelname + "_sed_and_obj_data.nc")
    )

    with open(
        fpath_output.joinpath(modelresult.modelname + "_statistics_summary.json"), "w"
    ) as f:
        json.dump(
            modelresult.delta_stats,
            f,
        )

    # Summary plot
    stat_plotter = plot.StatPlot(modelresult)
    stat_plotter.plot_histograms()
    stat_plotter.save_figures(fpath_output, "archel_summary")

    # Map plots
    map_plotter = plot.MapPlot(modelresult)
    map_plotter.twopanel_map("bottom_depth", "architectural_elements")
    map_plotter.save_figures(fpath_output, "map_bottomdepth_archels")

    # Cross-section plots
    xsect_start = (modelresult.mouth_position[1], modelresult.mouth_position[0])
    xsect_end = (modelresult.mouth_position[1] + 100, modelresult.mouth_position[0])
    xsect_plotter = plot.CrossSectionPlot(modelresult, xsect_start, xsect_end)

    xsect_plotter.twopanel_xsection("bottom_depth", "d50")
    xsect_plotter.save_figures(fpath_output, "xsect_diameter")

    xsect_plotter.twopanel_xsection("bottom_depth", "architectural_elements")
    xsect_plotter.save_figures(fpath_output, "xsect_archels")

    xsect_plotter.twopanel_xsection("bottom_depth", "deposition_age")
    xsect_plotter.save_figures(fpath_output, "xsect_depositionage")


if __name__ == "__main__":
    # main(
    #     r"p:\11209074-002-Geotool-new-deltas\01_modelling\Sobrabre_045_Reference",
    #     r"n:\Projects\11209000\11209074\B. Measurements and calculations\test_results\Sobrabre_045_Reference_new",
    #     Path(__file__).parents[2].joinpath(r"config\settings_sobrarbe.ini"),
    # )
    # main(
    #     r"p:\11209074-002-Geotool-new-deltas\01_modelling\Sobrabre_048",
    #     r"n:\Projects\11209000\11209074\B. Measurements and calculations\test_results\Sobrabre_048",
    #     Path(__file__).parents[2].joinpath(r"config\settings_sobrarbe.ini"),
    # )
    # main(
    #     r"p:\11209074-002-Geotool-new-deltas\01_modelling\Sobrabre_049",
    #     r"n:\Projects\11209000\11209074\B. Measurements and calculations\test_results\Sobrabre_049",
    #     Path(__file__).parents[2].joinpath(r"config\settings_sobrarbe.ini"),
    # )
    # main(
    #     r"p:\11209074-002-Geotool-new-deltas\01_modelling\Sobrabre_050",
    #     r"n:\Projects\11209000\11209074\B. Measurements and calculations\test_results\Sobrabre_050",
    #     Path(__file__).parents[2].joinpath(r"config\settings_sobrarbe.ini"),
    # )
    main(
        r"p:\11209074-002-Geotool-new-deltas\01_modelling\Roda_058_Reference",
        r"n:\Projects\11209000\11209074\B. Measurements and calculations\test_results\Roda_058",
        Path(__file__).parents[2].joinpath(r"config\settings_roda.ini"),
    )
    main(
        r"p:\11209074-002-Geotool-new-deltas\01_modelling\Roda_059",
        r"n:\Projects\11209000\11209074\B. Measurements and calculations\test_results\Roda_059",
        Path(__file__).parents[2].joinpath(r"config\settings_roda.ini"),
    )
    main(
        r"p:\11209074-002-Geotool-new-deltas\01_modelling\Roda_060",
        r"n:\Projects\11209000\11209074\B. Measurements and calculations\test_results\Roda_060",
        Path(__file__).parents[2].joinpath(r"config\settings_roda.ini"),
    )

    # main()
