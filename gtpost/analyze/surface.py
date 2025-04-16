import numpy as np


def slope(array: np.ndarray):
    """
    Calculate the slope of a given array.

    Parameters
    ----------
    array : np.ndarray
        Input array for which the slope is to be calculated.

    Returns
    -------
    np.ndarray
        Array representing the slope.
    """
    slopex = np.gradient(array, axis=1)
    slopey = np.gradient(array, axis=2)
    slope = np.abs(slopex * slopey)
    return slope
