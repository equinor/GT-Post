from pathlib import Path
from typing import Union

import matplotlib.pyplot as plt
import numpy as np
import xarray as xr
from matplotlib.gridspec import GridSpec
from mpl_toolkits.axes_grid1 import make_axes_locatable

from gtpost.analyse import colormaps


class SedimentaryLog:
    def __init__(self, sed_and_obj_data: Union[str, Path]):
        self.data = xr.open_dataset(sed_and_obj_data)

    def plot_single_log(self, data_var, x, y):
        logdepth, logdata = self._get_log_data(data_var, x, y)
        logdepth_ae, logdata_ae = self._get_log_data("archel", x, y)

        fig = plt.figure(dpi=72)
        gs = GridSpec(12, 12)
        ax1 = fig.add_subplot(gs[0:5, 0:8])
        ax2 = fig.add_subplot(gs[6:12, 0:8])
        ax3 = fig.add_subplot(gs[0:12, 9:12])
        divider2 = make_axes_locatable(ax2)
        cax2 = divider2.append_axes("bottom", size="5%", pad="8%")
        dpi = fig.get_dpi()
        fig.set_size_inches(1000.0 / float(dpi), 1000.0 / float(dpi))

        ax1.imshow(self.data["zcor"].values[-1, :, :], vmin=-6, vmax=1)
        ax1.scatter(x, y, color="red")
        ax2.imshow(
            self.data["archel"].values[-1, :, :], cmap=colormaps.ArchelColormap.cmap
        )
        ax2.scatter(x, y, color="red")
        ax3.plot(logdata, logdepth, color="darkred")
        ax3.set_xlabel(data_var)
        ax3.set_ylabel("Depth (m)")

        # Add architectural element background
        xmin, xmax = ax3.get_xbound()
        for i in np.arange(0, len(logdepth), 2):
            xs = [xmin, xmax]
            y1 = [logdepth_ae[i], logdepth_ae[i]]
            y2 = [logdepth_ae[i + 1], logdepth_ae[i + 1]]
            ax3.fill_between(
                xs, y1, y2, color=colormaps.ArchelColormap.colors[int(logdata_ae[i])]
            )
        colorbar = fig.colorbar(
            colormaps.ArchelColormap.mappable, cax=cax2, orientation="horizontal"
        )
        if colormaps.ArchelColormap.type == "categorical":
            colorbar.set_ticks(colormaps.ArchelColormap.ticks + 0.5)
            colorbar.set_ticklabels(colormaps.ArchelColormap.labels, size=8)

    def plot_log_summary(self):
        pass

    def _get_log_data(self, data_var, x, y):
        logdepth = [-999, -999]
        logdata = [0, 0]
        for t in range(len(self.data["dimen_t"])):
            data_t = self.data[data_var].sel(dimen_x=y, dimen_y=x, dimen_t=t).values
            depth_t = self.data["zcor"].sel(dimen_x=y, dimen_y=x, dimen_t=t).values
            if logdepth[-1] < depth_t:
                logdepth.append(float(logdepth[-1]))
                logdepth.append(float(depth_t))
                logdata += [float(data_t), float(data_t)]
            elif logdepth[-1] >= depth_t:
                logdepth = [l for l in logdepth if l < depth_t]
                logdata = [d for d, l in zip(logdata, logdepth) if l < depth_t]
                logdepth.append(float(depth_t))
                logdata.append(logdata[-1])
        logdepth = np.array(logdepth)
        logdepth = logdepth[4:]
        logdata = np.array(logdata)
        logdata = logdata[4:]
        return logdepth, logdata


if __name__ == "__main__":
    log = SedimentaryLog(
        r"n:\Projects\11209000\11209074\B. Measurements and calculations\test_results\Sobrabre_039\Sed_and_Obj_data.nc"
    )
    log.plot_single_log("diameter", 205, 50)
    # log.plot_single_log("diameter", 188, 36)
