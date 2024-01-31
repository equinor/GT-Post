from configparser import ConfigParser

import numpy as np


class IniParser(ConfigParser):
    @property
    def as_dict(self):
        d = dict(self._sections)
        for k in d:
            d[k] = dict(self._defaults, **d[k])
            d[k].pop("__name__", None)
        return d


def read_dep_file(dep_file, nx, ny):
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


def get_shape_from_grd_file(grd_file):
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
