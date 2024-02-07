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
    dep_file : _type_
        _description_
    nx : _type_
        _description_
    ny : _type_
        _description_

    Returns
    -------
    _type_
        _description_
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
    file : _type_
        _description_
    array : _type_
        _description_
    """
    np.savetxt(file, array, fmt="%.7e", delimiter="  ")


def edit_sdu_file(
    file: str | Path,
    initial_subsidence_array: np.ndarray,
    final_subsidence_array: np.ndarray,
):
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
    """_summary_

    Parameters
    ----------
    grd_file : _type_
        _description_

    Returns
    -------
    _type_
        _description_
    """
    with open(grd_file, "r") as f:
        lines = f.readlines()
        for line in lines:
            if line.startswith("    "):
                data = line.replace("\n", "").split("     ")[1:]
                break
    return (int(data[0]) + 1, int(data[1]) + 1)
