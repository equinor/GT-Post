import logging
from pathlib import Path

from gtpost.preprocessing.preprocessing import PreProcess
from gtpost.preprocessing.preprocessing_utils import write_ini

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)


def main(
    inifile: str | Path = "/data/input/preprocess/input.ini",
    fpath_output: str | Path = "/data/output",
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
    write_ini()
    pp = PreProcess(inifile, fpath_output)
    pp.preprocess()


if __name__ == "__main__":
    main()

    # for template in [
    #     "River_dominated_1",
    #     "River_dominated_2",
    #     "GuleHorn_Neslen_1",
    #     "GuleHorn_Neslen_2",
    #     "Roda_1",
    #     "Roda_2",
    #     "Sobrarbe_1",
    #     "Sobrarbe_2",
    # ]:

    #     main(
    #         rf"p:\11209074-002-Geotool-new-deltas\04_input_for_templates\Input_ini_test\{template}\input.ini",
    #         rf"p:\11209074-002-Geotool-new-deltas\01_modelling\{template}_preprocessing_initest",
    #     )
