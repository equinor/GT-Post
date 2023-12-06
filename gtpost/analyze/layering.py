import numpy as np
import xarray as xr


def preservation(
    zcor: np.ndarray, subsidence: np.ndarray, deposit_height: np.ndarray
) -> np.ndarray:
    """
    Get preservation potential of each deposit in the final model. i.e. when a deposit
    is (partially) preserved it returns the thickness of the final preserved sediment
    layer. If the layer is not preserved, it returns 0 for the given timestep and
    location.

    Parameters
    ----------
    zcor : np.ndarray
        z-coordinates (depth at each timestep)
    subsidence : np.ndarray
        Array with cumulative subsidence per timestep

    Returns
    -------
    np.ndarray
        Preservation status array: 0 = deposit will disappear later on due to erosion.
        any other positive value indicates the thickness of the preserved layer that
        formed during the given timestep.
    """
    zcor_corrected = zcor - subsidence
    preserved_thickness = np.zeros_like(zcor)
    deposition_age = np.zeros_like(zcor)
    for t in range(zcor.shape[0]):
        if t != zcor.shape[0] - 1:
            z_preserved = (
                zcor_corrected[t, :, :] - np.min(zcor_corrected[t + 1 :, :, :], axis=0)
            ) * -1
        else:
            z_preserved = zcor_corrected[t, :, :] - zcor_corrected[t - 1, :, :]
        z_preserved[z_preserved < 0] = 0
        preserved_thickness[t, :, :] = z_preserved
        if t == 0:
            deposition_age[t, :, :] = np.full_like(z_preserved, t)
        else:
            deposition_age[t, :, :] = deposition_age[t - 1, :, :]
            deposition_age[t, :, :][deposit_height > 1e-5] = t

    return preserved_thickness, deposition_age
