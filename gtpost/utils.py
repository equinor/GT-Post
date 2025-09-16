import gc
from configparser import ConfigParser
from datetime import datetime
from pathlib import Path

# from typing import List
import numpy as np
import psutil


def log_memory_usage():
    """
    Logs the memory usage of the current process.

    Returns
    -------
    str
        A string representing the memory usage in megabytes (MB).
    """
    process = psutil.Process()
    mem_info = process.memory_info()
    return f"Memory usage: {mem_info.rss / (1024**2):.2f} MB"


def release_memory(obj):
    """
    Releases memory by deleting the specified object.

    Parameters
    ----------
    obj : object
        The object to be deleted.

    Returns
    -------
    None
    """
    obj = None
    del obj
    gc.collect()


def get_current_time():
    time_now = datetime.now()
    return f"{time_now.hour}:{time_now.minute}:{time_now.second}"


def get_last_processed_timestep():
    pass


def get_template_name(input_path: str | Path) -> str:
    """
    Get the name of a D3D-GT template from the input.ini file.

    Parameters
    ----------
    input_path : str | Path
        Input D3D-GT folder, where input.ini is located.

    Returns
    -------
    str
        Name of the D3D-GT template.
    """
    input_ini = ConfigParser(interpolation=None)
    input_ini.read(Path(input_path).joinpath("input.ini"))
    template_name = (
        input_ini["template"]["value"].lower().replace(" ", "_").replace("/", "_")
    )
    return template_name


def get_dx_dy(xvalues: np.ndarray) -> tuple[int, int]:
    """
    Get grid spacing. Assumes spacing is the same along x and y dimensions.

    Parameters
    ----------
    xvalues : np.ndarray
        (y) array with x-coordinates

    Returns
    -------
    int, int
        Grid resolution along x and y axis
    """
    diff = np.diff(xvalues[xvalues > 0])[0]
    return diff, diff


def numpy_mode(array: np.ndarray):
    vals, counts = np.unique(array, return_counts=True)
    index = np.argmax(counts)
    return vals[index]


def normalize_numpy_array(array: np.ndarray):
    unique_values = np.unique(array)
    value_to_int = {val: idx for idx, val in enumerate(unique_values)}
    ae_mapping = {value: key for key, value in value_to_int.items()}
    return np.vectorize(value_to_int.get)(array), ae_mapping


def describe_data_vars(dataset, output_file="data_vars_description.txt"):
    """
    Print a description of the data variables in a D3D-GT ModelResult dataset.

    Parameters
    ----------
    dataset : xr.Dataset
        Dataset object with D3D-GT data variables.

    Returns
    -------
    None
    """
    with open("data_vars_description.txt", "w") as file:
        for var in dataset.data_vars:
            file.write(f"Variable: {var}\n")
            file.write(f"Description: {dataset[var].attrs}\n")
            file.write(f"Data type: {dataset[var].dtype}\n")
            try:
                shape = dataset[var].shape
                file.write(f"Shape: {shape}\n")
                if len(shape) < 4:
                    file.write(f"Min: {dataset[var].min().values}\n")
                    file.write(f"Max: {dataset[var].max().values}\n")
                    file.write(f"Mean: {dataset[var].mean().values}\n")
                    file.write(f"Std: {dataset[var].std().values}\n")
            except TypeError:
                pass
            file.write("\n")
