from pathlib import Path
from typing import Union

import matplotlib.pyplot as plt
import numpy as np
import xarray as xr
from matplotlib.gridspec import GridSpec
from mpl_toolkits.axes_grid1 import make_axes_locatable

from gtpost.visualize import colormaps


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

            ax.plot(logdata, logdepth, color="black", linewidth=0.5)
            ax.set_xlabel(data_var)
            ax.xaxis.set_tick_params(labeltop=True, top=True)

            # Add architectural element background
            for j in np.arange(0, len(logdepth), 2):
                y1 = [logdepth_ae[j], logdepth_ae[j]]
                y2 = [logdepth_ae[j + 1], logdepth_ae[j + 1]]
                xbnd = [bnd[0], logdata[j]]
                ax.fill_between(
                    xbnd,
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
        subsidence = self.data["subsidence"].sel(dimen_x=y, dimen_y=x).values
        for t in range(len(self.data["dimen_t"])):
            data_t = self.data[data_var].sel(dimen_x=y, dimen_y=x, dimen_t=t).values
            depth_t = self.data["zcor"].sel(dimen_x=y, dimen_y=x, dimen_t=t).values
            # Account for subsidence of previously preserved layers by lowering the
            # depth of saved layer boundaries with the subsidence per timestep at (x, y)
            logdepth = [d + subsidence for d in logdepth]
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

    @staticmethod
    def eight_plot_figure_base():
        fig, axs = plt.subplots(nrows=4, ncols=2, dpi=72)
        dpi = fig.get_dpi()
        fig.set_size_inches(650.0 / float(dpi), 1000.0 / float(dpi))
        return fig, axs

    def plot_volume_piechart(self, y1, y2):
        _, total_volume, volume_percentage = self._get_volume_stats(y1, y2)
        fig, ax = plt.subplots()
        ax.pie(
            volume_percentage,
            labels=colormaps.ArchelColormap.labels[1:],
            colors=colormaps.ArchelColormap.colors[1:],
            autopct="%1.1f%%",
        )
        ax.set_title(
            f"Preserved architectural element distribution\nTotal delta volume = {np.round(total_volume*50*50, 0)} $m^3$"
        )

    def plot_d50_histograms(self, y1, y2):
        d50_distributions, d50_distribution_weights = self._get_diameter_distributions(
            y1, y2
        )
        fig, axs = self.eight_plot_figure_base()
        # axes = [ax1, ax2, ax3, ax4, ax5, ax6, ax7, ax8]
        bins = [0, 0.063, 0.125, 0.25, 0.5, 1, 1.4]
        binlabels = ["s/c", "vf", "f", "m", "c", "vc"]
        for i, ax in enumerate(axs.flat):
            counts, bins = np.histogram(
                d50_distributions[i],
                bins=bins,
                weights=d50_distribution_weights[i],
            )
            if i != 0:
                ax.bar(binlabels, counts, color=colormaps.ArchelColormap.colors[i])
                ax.set_title(
                    colormaps.ArchelColormap.labels[i], y=1, pad=-14, loc="right"
                )
            else:
                ax.bar(binlabels, counts)
                ax.set_title("All AEs", y=1, pad=-14, loc="right")

            ax.set_yticks([])
            fig.suptitle(
                "D50 distribution per preserved architectural element", fontsize=16
            )

    def _get_volume_stats(self, y1, y2):
        volumes = np.zeros(6)
        for i in range(1, 7):
            idxs = (self.data["preserved_thickness"].values[:, y1:y2, :] > 0) & (
                self.data["archel"].values[:, y1:y2, :] == i
            )
            preserved_thickness = self.data["preserved_thickness"].values[:, y1:y2, :][
                idxs
            ]
            volumes[i - 1] = np.sum(preserved_thickness)
        total_deposited_volume = np.sum(volumes)
        volume_percentage = (volumes / total_deposited_volume) * 100
        return volumes, total_deposited_volume, volume_percentage

    def _get_diameter_distributions(self, y1, y2):
        d50_distributions = []
        d50_distribution_weights = []
        for i in range(1, 7):
            idxs = (self.data["preserved_thickness"].values[:, y1:y2, :] > 0) & (
                self.data["archel"].values[:, y1:y2, :] == i
            )
            d50_distr = self.data["diameter"].values[:, y1:y2, :][idxs]
            d50_distr_weights = self.data["preserved_thickness"].values[:, y1:y2, :][
                idxs
            ]
            d50_distributions.append(d50_distr)
            d50_distribution_weights.append(d50_distr_weights)

        idxs_total = self.data["preserved_thickness"].values[:, y1:y2, :] > 0
        d50_total = self.data["diameter"].values[:, y1:y2, :][idxs_total]
        d50_total_weights = self.data["preserved_thickness"].values[:, y1:y2, :][
            idxs_total
        ]
        d50_distributions.insert(0, d50_total)
        d50_distribution_weights.insert(0, d50_total_weights)

        return d50_distributions, d50_distribution_weights


if __name__ == "__main__":
    log = SedimentaryLog(
        r"n:\Projects\11209000\11209074\B. Measurements and calculations\test_results\Sobrabre_045_Reference\Sed_and_Obj_data.nc"
    )
    # log = SedimentaryLog(
    #     r"n:\Projects\11209000\11209074\B. Measurements and calculations\test_results\Roda_049\Sed_and_Obj_data.nc"
    # )
    log.plot_d50_histograms(20, 100)
    log.plot_log_summary_four_locations(
        "diameter", [120, 120, 120, 120], [10, 30, 50, 70], [0, 1.4]
    )
    # log.plot_log_summary_four_locations(
    #     "diameter", [120, 155, 120, 155], [160, 160, 150, 170], [0, 1.4]
    # )
    plt.show()

    log.plot_volume_piechart(20, 100)
    # log.plot_volume_piechart(100, 220)

    ds = xr.open_dataset(
        r"n:\Projects\11209000\11209074\B. Measurements and calculations\test_results\Sed_And_Obj_Data.nc"
    )

    for data_var in ds.data_vars.variables:
        print(type(ds[data_var].attrs["long_name"]))
