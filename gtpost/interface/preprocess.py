import logging
from pathlib import Path

from gtpost.preprocessing.preprocessing import PreProcess

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)


def main(
    inifile: str | Path,
    fpath_output: str | Path,
) -> None:
    """
    main function that interfaces with the Delft3D Geotool backend for preparing the
    Delft3D model input files from one of the templates

    Parameters
    ----------
    inifile : str | Path,
        Location of the input.ini file that contains all the user parameters that
    fpath_output : str | Path, optional
        Relative path within the container folder structure to write results to.
    """
    pp = PreProcess(inifile, fpath_output)
    pp.preprocess()


if __name__ == "__main__":

    for template in [
        "River_dominated_delta",
        "GuleHorn_Neslen",
        "Roda",
        "Sobrarbe",
    ]:

        main(
            rf"c:\Users\onselen\OneDrive - Stichting Deltares\Development\D3D GeoTool\gtpost\gt_templates\{template}\input.ini",
            rf"p:\11209074-002-Geotool-new-deltas\01_modelling\{template}_preprocessing_test_defaultvalues",
        )
