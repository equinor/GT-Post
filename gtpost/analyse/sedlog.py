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

    def plot_log_summary_four_locations(self, data_var, xc, yc, bnd):
        fig, ax1, ax2, ax3, ax4, ax5, ax6, cax = self.four_log_figure_base()

        ax1.imshow(self.data["zcor"].values[-1, :, :], vmin=-6, vmax=1)
        ax2.imshow(
            self.data["archel"].values[-1, :, :], cmap=colormaps.ArchelColormap.cmap
        )

        colorbar = fig.colorbar(
            colormaps.ArchelColormap.mappable, cax=cax, orientation="horizontal"
        )
        if colormaps.ArchelColormap.type == "categorical":
            colorbar.set_ticks(colormaps.ArchelColormap.ticks + 0.5)
            colorbar.set_ticklabels(colormaps.ArchelColormap.labels, size=8)

        for i, (ax, x, y) in enumerate(zip([ax3, ax4, ax5, ax6], xc, yc)):
            ax1.scatter(x, y, color="red")
            ax2.scatter(x, y, color="red")

            logdepth, logdata = self._get_log_data(data_var, x, y)
            logdepth_ae, logdata_ae = self._get_log_data("archel", x, y)

            ax.plot(logdata, logdepth, color="darkred")
            ax.set_xlabel(data_var)
            ax.xaxis.set_tick_params(labeltop=True, top=True)

            # Add architectural element background
            for j in np.arange(0, len(logdepth), 2):
                y1 = [logdepth_ae[j], logdepth_ae[j]]
                y2 = [logdepth_ae[j + 1], logdepth_ae[j + 1]]
                ax.fill_between(
                    bnd,
                    y1,
                    y2,
                    color=colormaps.ArchelColormap.colors[int(logdata_ae[j])],
                )

            ax1.text(x + 2, y, f"{i+1}", color="black")
            ax2.text(x + 2, y, f"{i+1}", color="black")

        ybnd = (np.min([b.get_ybound()[0] for b in [ax3, ax4, ax5, ax6]]), 1)
        ax3.set_ybound(ybnd)
        ax4.set_ybound(ybnd)
        ax5.set_ybound(ybnd)
        ax6.set_ybound(ybnd)

        ax3.set_xbound(bnd)
        ax4.set_xbound(bnd)
        ax5.set_xbound(bnd)
        ax6.set_xbound(bnd)

        ax3.set_ylabel("Depth (m)")
        ax4.set_yticks([])
        ax5.set_yticks([])
        ax6.set_yticks([])

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

    @staticmethod
    def four_log_figure_base():
        fig = plt.figure(dpi=72)
        gs = GridSpec(12, 8)
        ax1 = fig.add_subplot(gs[0:5, 0:4])
        ax2 = fig.add_subplot(gs[6:12, 0:4])
        ax3 = fig.add_subplot(gs[0:12, 4:5])
        ax4 = fig.add_subplot(gs[0:12, 5:6])
        ax5 = fig.add_subplot(gs[0:12, 6:7])
        ax6 = fig.add_subplot(gs[0:12, 7:8])
        divider2 = make_axes_locatable(ax2)
        cax = divider2.append_axes("bottom", size="5%", pad="8%")
        dpi = fig.get_dpi()
        fig.set_size_inches(1600.0 / float(dpi), 1000.0 / float(dpi))
        return fig, ax1, ax2, ax3, ax4, ax5, ax6, cax


if __name__ == "__main__":
    log = SedimentaryLog(
        r"n:\Projects\11209000\11209074\B. Measurements and calculations\test_results\Sobrabre_045\Sed_and_Obj_data.nc"
    )
    # log.plot_log_summary_four_locations(
    #     "diameter", [158, 158, 158, 158], [10, 30, 50, 70], [0, 1.4]
    # )
    log.plot_log_summary_four_locations(
        "diameter", [120, 120, 120, 120], [10, 30, 50, 70], [0, 1.2]
    )
    plt.show()
    # log.plot_single_log("diameter", 188, 36)
