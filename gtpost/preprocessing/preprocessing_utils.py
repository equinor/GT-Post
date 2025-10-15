import json
import os
from configparser import ConfigParser
from pathlib import Path

import numpy as np


class IniParser(ConfigParser):
    @property
    def as_dict(self):
        d = dict(self._sections)
        for k in d:
            d[k] = dict(self._defaults, **d[k])
            d[k].pop("__name__", None)
        return d


def read_dep_file(dep_file: str | Path, nx: int, ny: int) -> np.ndarray:
    """Load bathymetry as numpy array from the a.dep file

    Parameters
    ----------
    dep_file : str
        Path of the Delft3D .dep file to read
    nx : int
        Number of cells along the x-axis
    ny : int
        Number of cell along the y-axis

    Returns
    -------
    np.ndarray
        The Delft3D .dep file data as a Numpy array.
    """
    with open(dep_file, "r") as f:
        dep_values = f.read()
        dep_values = dep_values.replace("\n", "").split("  ")[1:]
        bathymetry_array = np.array(dep_values, dtype=np.float64).reshape([ny, nx])
    return bathymetry_array


def write_dep_file(file: str | Path, array: np.ndarray) -> None:
    """Write a dep file from a Numpy Array

    Parameters
    ----------
    file : str | Path
        Path to write the Delft3D .dep file to
    array : np.ndarray
        Numpy array to write as Delft3D .dep file
    """
    np.savetxt(file, array, fmt="%.7e", delimiter="  ")


def edit_sdu_file(
    file: str | Path,
    initial_subsidence_array: np.ndarray,
    final_subsidence_array: np.ndarray,
):
    """Function to edit a Delft3D subsidence (.sdu) file

    Parameters
    ----------
    file : str | Path
        Path to the Delft3D .sdu file to write to
    initial_subsidence_array : np.ndarray
        Initial subsidence array
    final_subsidence_array : np.ndarray
        Final subsidence array (amount of subsidence per cell at the last timestep)
    """
    with open(file, "r") as sdu_file:
        header_line = ""
        for i in range(20):
            line = sdu_file.readline()
            header_line += line
            if "TIME = 0" in line:
                break
    header_line = header_line[:-1]
    footer_line = "TIME = ${t_stop} minutes since 2013-12-01 00:00:00 +00:00                   # Fixed format: time unit since date time time difference (time zone)"
    np.savetxt(
        file,
        initial_subsidence_array,
        fmt="%.7e",
        delimiter="  ",
        header=header_line,
        footer=footer_line,
        comments="",
    )

    with open(file, "a") as sdu_file:
        np.savetxt(
            sdu_file,
            final_subsidence_array,
            fmt="%.7e",
            delimiter="  ",
        )


def get_shape_from_grd_file(grd_file: str | Path) -> tuple:
    """Get grid shape information from Delft3D .grd files

    Parameters
    ----------
    grd_file : str | Path
        Path to Delft3D .grd file to extract grid shape information from

    Returns
    -------
    tuple
        Tuple with (nx, ny) grid shape.
    """
    with open(grd_file, "r") as f:
        lines = f.readlines()
        for line in lines:
            if line.startswith("    "):
                data = line.replace("\n", "").split("     ")[1:]
                break
    return (int(data[0]) + 1, int(data[1]) + 1)


def write_ini(root: str | Path = "/data/input"):
    """Write input.ini for containers based on the environment"""

    input = os.environ.get("INPUT", "{}")
    parameters = json.loads(input)
    folders = ["simulation", "preprocess", "process", "postprocess", "export"]

    # Create ini file for containers
    config = ConfigParser(interpolation=None)
    for section in parameters:
        if not config.has_section(section):
            config.add_section(section)
        for key, value in parameters[section].items():
            # TODO: find more elegant solution for this! ugh!
            if not key == "units":
                if not config.has_option(section, key):
                    config.set(*map(str, [section, key, value]))

    for folder in folders:
        try:
            os.makedirs(os.path.join(root, folder), 0o2775)
        # Path already exists, ignore
        except OSError:
            if not os.path.isdir(os.path.join(root, folder)):
                raise

        with open(os.path.join(root, folder, "input.ini"), "w") as f:
            config.write(f)  # Yes, the ConfigParser writes to f
