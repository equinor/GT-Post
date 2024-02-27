from pathlib import Path
from typing import NamedTuple, Union

import matplotlib.pyplot as plt
import numpy as np
import xarray as xr
from matplotlib import cm
from matplotlib.colors import (
    BoundaryNorm,
    LinearSegmentedColormap,
    ListedColormap,
    Normalize,
)
from matplotlib.gridspec import GridSpec
from mpl_toolkits.axes_grid1 import make_axes_locatable


def categorical_cmap(alphas, colors, name):
    cmap = ListedColormap(
        colors=colors,
        name=name,
    )
    cmap = cmap(np.arange(cmap.N))
    cmap[:, -1] = alphas

    cmap = ListedColormap(cmap)
    bounds = np.arange(cmap.N + 1)
    vals = bounds[:-1]
    norm = BoundaryNorm(bounds, cmap.N)
    mappable = cm.ScalarMappable(norm=norm, cmap=cmap)
    return cmap, mappable, bounds, vals, norm


def continuous_cmap(colorlist, name, vmin, vmax):
    norm = Normalize(vmin=vmin, vmax=vmax)
    cmap = LinearSegmentedColormap.from_list(name, colorlist)
    mappable = cm.ScalarMappable(norm=norm, cmap=cmap)
    return cmap, mappable, norm


class ArchelColormap(NamedTuple):
    alphas = [1, 1, 1, 1, 1, 1, 1]
    colors = [
        "snow",
        "yellowgreen",
        "mediumseagreen",
        "deepskyblue",
        "yellow",
        "turquoise",
        "mediumblue",
    ]
    labels = ["N/A", "DT-subar", "DT-subaq", "AC", "MB", "DF", "PD"]
    ticks = np.arange(0, 7)
    name = "Architectural elements"
    type = "categorical"
    cmap, mappable, bounds, values, norm = categorical_cmap(alphas, colors, name)


class BottomDepthColormap(NamedTuple):
    c0 = (0, "#182514")
    c1 = (0.143, "#0C672C")
    c2 = (0.286, "#829E06")
    c3 = (0.429, "#E5D37F")
    c4 = (0.5, "#FDFAE6")
    c5 = (0.571, "#C4DAD0")
    c6 = (0.714, "#45A2AE")
    c7 = (0.857, "#1B5A9E")
    c8 = (1, "#172313")
    name = "Bottom depth"
    type = "mappable"
    vmin = -6
    vmax = 8
    cmap, mappable, norm = continuous_cmap(
        [c0, c1, c2, c3, c4, c5, c6, c7, c8], name, vmin, vmax
    )


class SedimentaryLog:
    def __init__(self, sed_and_obj_data: Union[str, Path]):
        self.data = xr.open_dataset(sed_and_obj_data)

    def plot_log_summary_four_locations(self, data_var, xc, yc, bnd):
        fig, ax1, ax2, ax3, ax4, ax5, ax6, cax = self.four_log_figure_base()

        ax1.imshow(
            self.data["zcor"].values[-1, :, :],
            vmin=-15,
            vmax=8,
            cmap=BottomDepthColormap.cmap.reversed(),
        )
        ax2.imshow(self.data["archel"].values[-1, :, :], cmap=ArchelColormap.cmap)

        colorbar = fig.colorbar(
            ArchelColormap.mappable, cax=cax, orientation="horizontal"
        )
        if ArchelColormap.type == "categorical":
            colorbar.set_ticks(ArchelColormap.ticks + 0.5)
            colorbar.set_ticklabels(ArchelColormap.labels, size=8)

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
                    color=ArchelColormap.colors[int(logdata_ae[j])],
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
            labels=ArchelColormap.labels[1:],
            colors=ArchelColormap.colors[1:],
            autopct="%1.1f%%",
        )
        ax.set_title(
            f"Preserved architectural element distribution\nTotal delta volume = {np.round(total_volume*50*50, 0)} $m^3$"
        )
        _, total_volume, volume_percentage = self._get_volume_stats(y1, y2)

    def plot_d50_histograms(self, y1, y2):
        d50_distributions, d50_distribution_weights = self._get_diameter_distributions(
            y1, y2
        )
        _, _, volume_percentage = self._get_volume_stats(y1, y2)
        fig, axs = self.eight_plot_figure_base()

        # Volume distribution in first plot
        aelabels = ["DT-r", "DT-q", "AC", "MB", "DF", "PD"]
        y_pos = np.arange(len(aelabels))
        axs[0, 0].barh(
            y_pos,
            volume_percentage,
            align="center",
            color=ArchelColormap.colors[1:],
        )
        axs[0, 0].set_yticks(y_pos, labels=aelabels)
        axs[0, 0].invert_yaxis()
        axs[0, 0].set_title("Volume distribution between AEs (%)", loc="left")

        # D50
        bins = [0, 0.063, 0.125, 0.25, 0.5, 1, 1.4]
        binlabels = ["s/c", "vf", "f", "m", "c", "vc"]
        for i, ax in enumerate(axs.flat[1:]):
            counts, bins = np.histogram(
                d50_distributions[i],
                bins=bins,
                weights=d50_distribution_weights[i],
            )
            if i != 0:
                ax.bar(binlabels, counts, color=ArchelColormap.colors[i])
                ax.set_title(ArchelColormap.labels[i], y=1, pad=-14, loc="right")
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
        r"n:\Projects\11209000\11209074\B. Measurements and calculations\test_results\Sobrarbe_048_Reference\Sobrarbe_048_Reference - coarse-sand_sed_and_obj_data.nc"
    )
    print(log.data.data_vars)

    log.plot_d50_histograms(20, 100)
    log.plot_log_summary_four_locations(
        "diameter", [120, 120, 120, 120], [10, 30, 50, 70], [0, 1.4]
    )
    plt.show()
