from pathlib import Path
from typing import Union

import matplotlib.pyplot as plt
import xarray as xr


class SedimentaryLog:
    def __init__(self, sed_and_obj_data: Union[str, Path]):
        self.data = xr.open_dataset(sed_and_obj_data)

    def get_log_data(self, data_var, t, x, y):
        self.data[data_var].sel(dimen_x=y, dimen_y=x).values


if __name__ == "__main__":
    log = SedimentaryLog(
        r"n:\Projects\11209000\11209074\B. Measurements and calculations\test_results\Sobrabre_039\Sed_and_Obj_data.nc"
    )
    log.get_log_data("diameter", -1, 80, 40)

    plt.plot(self.data[data_var].sel(dimen_x=y, dimen_y=x).values)
    plt.plot(self.data["archel"].sel(dimen_x=y, dimen_y=x).values)
    plt.show()
