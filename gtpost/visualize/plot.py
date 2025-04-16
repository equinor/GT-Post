from itertools import chain
from pathlib import Path

import matplotlib.patches as patches
import matplotlib.pyplot as plt
import numpy as np
import xarray as xr
from matplotlib.collections import PatchCollection
from matplotlib.gridspec import GridSpec
from mpl_toolkits.axes_grid1 import make_axes_locatable
from scipy import spatial

from gtpost.analyze.classifications import ArchEl
from gtpost.visualize import colormaps


# from gtpost.model import ModelResult
class PlotBase:
    colormaps = {
        "d50": colormaps.GrainsizeColormap(),
        "architectural_elements": colormaps.GenericCategoricalColormap(
            ArchEl,
            [
                "undefined",
                "dtundef",
                "dtbayfill",
                "dchannel",
                "tchannel",
                "ushoreface",
                "lshoreface",
                "offshore",
                "beachridge",
                "beach",
            ],
            "Architectural elements",
        ),
        # "architectural_elements": colormaps.ArchelColormap(),
        "deposit_height": colormaps.BedlevelchangeColormap(),
        "porosity": colormaps.PorosityColormap(),
        "bottom_depth": colormaps.BottomDepthColormap(),
        "deposition_age": colormaps.DepositionageColormap(),
    }
    axlabelsize = 14
    axtitlesize = 16
    ticksize = 12
    titlesize = 18

    def __init__(self, modelresult):
        self.model = modelresult
        self.tickfactor = self.model.dx / 1000
        self.xticks_map = np.arange(0, len(self.model.dataset.N), 50)
        self.yticks_map = np.arange(0, len(self.model.dataset.M), 50)

    def __new__(cls, *args, **kwargs):
        if cls is PlotBase:
            raise TypeError(
                f"Cannot construct {cls.__name__} directly: construct class from its",
                "children instead",
            )
        else:
            return object.__new__(cls)

    def create_figure(self, figtype):
        """
        Prepare the figure by defining size, subplots and axes to work with

        Arguments:
            figtype =   see main function for explanation

        Determines figure object and axes object(s)

        """

        self.figtype = figtype.lower()

        if self.figtype == "single":
            self.fig, ax = plt.subplots(1, 1)
            self.fig.dpi = 72
            self.ax = ax
            divider1 = make_axes_locatable(ax)
            cax = divider1.append_axes("bottom", size="5%", pad="12%")
            self.cax = cax
            dpi = self.fig.get_dpi()
            self.fig.set_size_inches(800.0 / float(dpi), 600.0 / float(dpi))

        if self.figtype == "double":
            self.shared = True
            self.fig = plt.figure(dpi=72)
            gs = GridSpec(1, 2, left=0.05, right=0.95, wspace=0.1)
            ax1 = self.fig.add_subplot(gs[0, 0])
            ax2 = self.fig.add_subplot(gs[0, 1], sharex=ax1, sharey=ax1)
            divider1 = make_axes_locatable(ax1)
            divider2 = make_axes_locatable(ax2)
            cax1 = divider1.append_axes("bottom", size="5%", pad="12%")
            cax2 = divider2.append_axes("bottom", size="5%", pad="12%")
            self.ax = [ax1, ax2]
            self.cax = [cax1, cax2]
            dpi = self.fig.get_dpi()
            self.fig.set_size_inches(1400 / float(dpi), 700 / float(dpi))

        if self.figtype == "x-2panels":
            self.fig = plt.figure(dpi=72)
            gs = GridSpec(1, 3)
            ax1 = self.fig.add_subplot(gs[0, 0])
            ax2 = self.fig.add_subplot(gs[0, 1:])
            divider1 = make_axes_locatable(ax1)
            divider2 = make_axes_locatable(ax2)
            cax1 = divider1.append_axes("bottom", size="5%", pad="12%")
            cax2 = divider2.append_axes("bottom", size="5%", pad="12%")
            self.ax = [ax1, ax2]
            self.cax = [cax1, cax2]
            dpi = self.fig.get_dpi()
            self.fig.set_size_inches(2000.0 / float(dpi), 800.0 / float(dpi))

        if self.figtype == "x-3panels":
            self.fig = plt.figure(dpi=72)
            gs = GridSpec(8, 12)
            ax1 = self.fig.add_subplot(gs[0:7, 0:4])
            ax2 = self.fig.add_subplot(gs[0:3, 4:12])
            ax3 = self.fig.add_subplot(gs[4:7, 4:12])
            divider1 = make_axes_locatable(ax1)
            divider2 = make_axes_locatable(ax2)
            divider3 = make_axes_locatable(ax3)
            cax1 = divider1.append_axes("bottom", size="5%", pad="12%")
            cax2 = divider2.append_axes("bottom", size="5%", pad="12%")
            cax3 = divider3.append_axes("bottom", size="5%", pad="12%")
            self.ax = [ax1, ax2, ax3]
            self.cax = [cax1, cax2, cax3]
            dpi = self.fig.get_dpi()
            self.fig.set_size_inches(1400.0 / float(dpi), 500.0 / float(dpi))

        if self.figtype == "x-6panels":
            self.fig = plt.figure(dpi=72)
            gs = GridSpec(6, 30)
            # ax1 is the top-down view
            ax1 = self.fig.add_subplot(gs[0:2, 0:6])
            # ax2-7 are the cross sections
            ax2 = self.fig.add_subplot(gs[0:2, 7:17])
            ax3 = self.fig.add_subplot(gs[0:2, 18:28])
            ax4 = self.fig.add_subplot(gs[2:4, 7:17])
            ax5 = self.fig.add_subplot(gs[2:4, 18:28])
            ax6 = self.fig.add_subplot(gs[4:6, 7:17])
            ax7 = self.fig.add_subplot(gs[4:6, 18:28])
            # cax is the colorbar subplot
            cax = self.fig.add_subplot(gs[3:5, 4])
            self.ax = [ax1, [ax2, ax3, ax4, ax5, ax6, ax7], cax]
            dpi = self.fig.get_dpi()
            self.fig.set_size_inches(2000.0 / float(dpi), 1000.0 / float(dpi))

        if self.figtype == "histograms":
            self.fig, self.axs = plt.subplots(nrows=4, ncols=2, dpi=72)
            dpi = self.fig.get_dpi()
            self.fig.set_size_inches(650.0 / float(dpi), 1000.0 / float(dpi))

    def draw_xsection(self, axis_idx, timestep, data, colormap):
        """


        Parameters
        ----------
        axis_idx : _type_
            _description_
        timestep : _type_
            _description_
        data : _type_
            _description_
        colormap : _type_
            _description_
        """
        axis = self.ax[axis_idx]
        caxis = self.cax[axis_idx]

        for i, x in enumerate(self.anchor_x[1:-1]):
            i += 1
            x_left = x - self.width / 2
            x_right = x + self.width / 2
            subsidence_left = (self.dsub[timestep, i - 1] + self.dsub[timestep, i]) / 2
            subsidence_middle = self.dsub[timestep, i]
            subsidence_right = (self.dsub[timestep, i] + self.dsub[timestep, i + 1]) / 2
            bed_chg_left = max((self.dh[timestep, i - 1] + self.dh[timestep, i]) / 2, 0)
            bed_chg_middle = max(self.dh[timestep, i], 0)
            bed_chg_right = max(
                (self.dh[timestep, i] + self.dh[timestep, i + 1]) / 2, 0
            )
            surface_left = (
                self.anchor_y[timestep, i - 1] + self.anchor_y[timestep, i]
            ) / 2
            surface_middle = self.anchor_y[timestep, i]
            surface_right = (
                self.anchor_y[timestep, i] + self.anchor_y[timestep, i + 1]
            ) / 2

            # First update existing polygons with the subsidence that took place since
            # the last timestep:
            xy_update = np.array(
                [
                    subsidence_left,
                    subsidence_left,
                    subsidence_middle,
                    subsidence_right,
                    subsidence_right,
                    subsidence_middle,
                    subsidence_left,
                ]
            )
            [
                p.set_xy(np.array([p.get_xy()[:, 0], p.get_xy()[:, 1] + xy_update]).T)
                for p in self.patches_per_position[i]
            ]
            # Remove polygons that were fully eroded. i.e. if their bottom is above the
            # current surface level:
            self.patches_per_position[i] = [
                p
                for p in self.patches_per_position[i]
                if not (
                    (p.get_xy()[0, 1] >= surface_left)
                    & (p.get_xy()[4, 1] >= surface_middle)
                    & (p.get_xy()[5, 1] >= surface_right)
                )
            ]

            # Update the top of the polygons that extend above the current surface:
            for p in self.patches_per_position[i]:
                xy = p.get_xy()
                xy[:2, 1] = xy[:2, 1].clip(max=surface_left)
                xy[2, 1] = xy[2, 1].clip(max=surface_middle)
                xy[5, 1] = xy[5, 1].clip(max=surface_middle)
                xy[3:5, 1] = xy[3:5, 1].clip(max=surface_right)
                xy[-1, 1] = xy[0, 1]
                p.set_xy(xy)

            # Make sure that the top polygon (self.patches_per_position[i][-1]) still
            # reaches the current surface:
            if len(self.patches_per_position[i]) > 0:
                xy_last = self.patches_per_position[i][-1].xy
                if bed_chg_left == 0.0:
                    xy_last[1, 1] = surface_left
                if bed_chg_middle == 0.0:
                    xy_last[2, 1] = surface_middle
                if bed_chg_right == 0.0:
                    xy_last[3, 1] = surface_right
                self.patches_per_position[i][-1].set_xy(xy_last)

            # Draw a new polygon if any deposition took place at the left, middle and
            # and right x-positions of the potential polygon and append it to the list of
            # polygons for this position:
            if colormap.type == "mappable":
                color = colormap.mappable.to_rgba(data[timestep, i])
            elif colormap.type == "categorical":
                color = colormap.colors[data[timestep, i]]

            if bed_chg_left > 0.0 or bed_chg_middle > 0.0 or bed_chg_right > 0.0:
                self.patches_per_position[i].append(
                    patches.Polygon(
                        xy=(
                            (x_left, surface_left - bed_chg_left),
                            (x_left, surface_left),
                            (x, surface_middle),
                            (x_right, surface_right),
                            (x_right, surface_right - bed_chg_right),
                            (x, surface_middle - bed_chg_middle),
                        ),
                        color=color,
                        linewidth=0,
                        closed=True,
                    )
                )

        selected_patches = list(
            chain.from_iterable(
                [value for key, value in self.patches_per_position.items()]
            )
        )
        p = PatchCollection(selected_patches)
        p.set_color([p.get_facecolor() for p in selected_patches])
        axis.add_collection(p)
        axis.plot(self.anchor_y[timestep, :])

        # # Additional timelines to plot:
        # for timeline_to_draw in np.arange(5, timestep, 10):
        #     timeline_to_draw_y = np.minimum(
        #         self.anchor_y[timeline_to_draw, :], self.anchor_y[timestep, :]
        #     )
        #     axis.plot(timeline_to_draw_y, linestyle="--", linewidth=0.6, color="black")

        # Finally update the axis limits, labels, titles etc.
        axis.set_xlim(self.xlim)
        axis.set_ylim(self.ylim)
        axis.set_xticks(axis.get_xticks())
        axis.set_yticks(axis.get_yticks())
        axis.set_xticklabels(
            axis.get_xticks() * self.tickfactor, fontsize=self.ticksize
        )
        axis.set_yticklabels(axis.get_yticks(), fontsize=self.ticksize)

        axis.set_xlabel("Distance along profile line (km)", fontsize=self.axlabelsize)
        axis.set_ylabel("Vertical position (m)", fontsize=self.axlabelsize)
        axis.set_title(
            colormap.name + f" (t = {timestep})", fontsize=self.titlesize, loc="left"
        )

        colorbar = self.fig.colorbar(
            colormap.mappable, cax=caxis, orientation="horizontal"
        )
        if colormap.type == "categorical":
            colorbar.set_ticks(colormap.ticks + 0.5)
            colorbar.set_ticklabels(colormap.labels, fontsize=self.ticksize)

    def draw_last_xsection(self, axis_idx, timestep, data, colormap):
        axis = self.ax[axis_idx]
        caxis = self.cax[axis_idx]

        for i, x in enumerate(self.anchor_x):
            current_surface = self.anchor_y[timestep, i]
            preserved = self.preserved[:-1, i]

            if colormap.type == "mappable":
                color = colormap.mappable.to_rgba(data[1:, i])
            elif colormap.type == "categorical":
                color = [colormap.colors[c] for c in data[1:, i]]

            accumulated_thickness = 0
            for lyr_number, layer_thickness in enumerate(preserved[::-1]):
                if layer_thickness > 0:
                    self.patches_per_position[i].append(
                        patches.Rectangle(
                            xy=(x, current_surface - accumulated_thickness),
                            width=self.width,
                            height=-layer_thickness,
                            color=color[-lyr_number - 1],
                            linewidth=0,
                        )
                    )
                    accumulated_thickness += layer_thickness

        selected_patches = list(
            chain.from_iterable(
                [value for key, value in self.patches_per_position.items()]
            )
        )
        p = PatchCollection(selected_patches)
        p.set_color([p.get_facecolor() for p in selected_patches])
        axis.add_collection(p)
        axis.plot(self.anchor_y[timestep, :])

        axis.set_xlim(self.xlim)
        axis.set_ylim(self.ylim)
        axis.set_xticks(axis.get_xticks())
        axis.set_yticks(axis.get_yticks())
        axis.set_xticklabels(
            axis.get_xticks() * self.tickfactor, fontsize=self.ticksize
        )
        axis.set_yticklabels(axis.get_yticks(), fontsize=self.ticksize)

        axis.set_xlabel("Distance along profile line (km)", fontsize=self.axlabelsize)
        axis.set_ylabel("Vertical position (m)", fontsize=self.axlabelsize)
        axis.set_title(
            colormap.name + f" (t = {timestep})", fontsize=self.titlesize, loc="left"
        )

        colorbar = self.fig.colorbar(
            colormap.mappable, cax=caxis, orientation="horizontal"
        )
        if colormap.type == "categorical":
            colorbar.set_ticks(colormap.ticks + 0.5)
            colorbar.set_ticklabels(colormap.labels, fontsize=self.ticksize)

    def draw_map(self, axis_idx, timestep, data, colormap):
        axis = self.ax[axis_idx]
        caxis = self.cax[axis_idx]

        if colormap.type == "mappable":
            axis.imshow(
                data[timestep, :, :],
                cmap=colormap.cmap,
                interpolation="antialiased",
                interpolation_stage="rgba",
                vmin=colormap.vmin,
                vmax=colormap.vmax,
            )
        elif colormap.type == "categorical":
            axis.imshow(
                data[timestep, :, :],
                cmap=colormap.cmap,
                norm=colormap.norm,
                interpolation="antialiased",
                interpolation_stage="rgba",
            )

        axis.invert_yaxis()

        axis.set_xticks(self.xticks_map)
        axis.set_yticks(self.yticks_map)
        axis.set_xticklabels(self.xticks_map * self.tickfactor, fontsize=self.ticksize)
        axis.set_yticklabels(self.yticks_map * self.tickfactor, fontsize=self.ticksize)

        axis.set_xlabel("Alongshore direction (km)", fontsize=self.axlabelsize)
        axis.set_ylabel("Cross-shore direction (km)", fontsize=self.axlabelsize)
        axis.set_title(
            colormap.name + f" (t = {timestep})",
            fontsize=self.titlesize,
            loc="left",
        )

        colorbar = self.fig.colorbar(
            colormap.mappable, cax=caxis, orientation="horizontal"
        )
        if colormap.type == "categorical":
            colorbar.set_ticks(colormap.ticks + 0.5)
            colorbar.set_ticklabels(colormap.labels, fontsize=self.ticksize)

    def draw_profile_line(self, axis_idx, start, finish):
        """
        Plot a profile line (based on self.m and self.n)
        """
        axis = self.ax[axis_idx]

        axis.plot(
            [start[1], finish[1]],
            [start[0], finish[0]],
            linewidth=1.5,
            color="r",
        )

        if start[1] < finish[1]:
            axis.text(
                start[1] - 10,
                start[0],
                "Left",
                color="red",
                ha="right",
            )
            axis.text(finish[1] + 10, finish[0], "Right", color="red")
        else:
            axis.text(start[1] + 10, start[0], "Left", color="red")
            axis.text(finish[1] - 10, finish[0], "Right", color="red", ha="right")

    def draw_colorbar(self, axis):
        pass

    def save_figure(self, path, name, t):
        self.fig.savefig(Path(path) / f"{name}_{t:04}.png")


class CrossSectionPlot(PlotBase):
    def __init__(self, modelresult, start, finish):
        super().__init__(modelresult)
        self.start = start
        self.finish = finish
        self.anchor_x, self.xc, self.yc, self.dxdy = self.profile_line_coordinates(
            start, finish
        )
        self.anchor_y = np.diagonal(
            -self.model.dataset["DPS"][:, self.xc, self.yc].values, axis1=1, axis2=2
        )
        self.dh = self.model.deposit_height[:, self.xc, self.yc]
        self.dsub = self.model.subsidence[:, self.xc, self.yc]
        self.preserved = self.model.preserved_thickness[:, self.xc, self.yc]
        self.width = 1
        self.xlim = [self.anchor_x[0], self.anchor_x[-1]]
        self.ylim = [
            np.round(self.anchor_y.min() - 1),
            np.round(self.anchor_y.max() + 1),
        ]

    def twopanel_xsection(
        self,
        variable_basemap,
        variable_xsect,
        path,
        name,
        add_timelines=False,
        timeline_interval=10,
        timeline_start=5,
        only_last_timestep=False,
    ):
        data_xsect = self.model.__dict__[variable_xsect][:, self.xc, self.yc]
        data_base = self.model.__dict__[variable_basemap]
        colormap_xsect = self.colormaps[variable_xsect]
        colormap_base = self.colormaps[variable_basemap]

        self.patchlist = []
        self.colorlist = []

        self.patches_per_position = dict(
            zip(
                [i for i in range(len(self.anchor_x))],
                [[] for i in range(len(self.anchor_x))],
            )
        )

        # if add_timelines:
        #     anchor_y_subsidence_corrected = self.anchor_y - np.cumsum(self.dsub, axis=0)
        #     anchor_y_subsidence = [
        #         np.min(anchor_y_subsidence_corrected[i:, :], axis=0)
        #         <= anchor_y_subsidence_corrected[i, :]
        #         for i in range(anchor_y_subsidence_corrected.shape[0])
        #     ]
        #     anchor_y_subsidence = np.array(anchor_y_subsidence)

        #     anchor_y = self.anchor_y[
        #         np.arange(timeline_start, data_xsect.shape[0], timeline_interval)
        #     ]
        #     self.anchor_y

        self.create_figure("x-2panels")
        if only_last_timestep:
            t = data_base.shape[0] - 1
            self.draw_map(0, t, data_base, colormap_base)
            self.draw_profile_line(0, self.start, self.finish)
            self.draw_last_xsection(1, t, data_xsect, colormap_xsect)
            self.save_figure(path, name, t)
            [ax.clear() for ax in self.ax]
        else:
            for t in range(data_xsect.shape[0]):
                self.draw_map(0, t, data_base, colormap_base)
                self.draw_profile_line(0, self.start, self.finish)
                self.draw_xsection(1, t, data_xsect, colormap_xsect)
                self.save_figure(path, name, t)
                [ax.clear() for ax in self.ax]

    @staticmethod
    def profile_line_coordinates(start, finish):
        start = np.array(start)
        finish = np.array(finish)
        dist = spatial.distance.euclidean(start, finish)
        dxdy_per_cell = (finish - start) / dist

        profilevector = np.arange(0, dist - dist % 1 + 2, 1)

        xcoordinates = np.int16(np.round(start[0] + profilevector * dxdy_per_cell[0]))
        ycoordinates = np.int16(np.round(start[1] + profilevector * dxdy_per_cell[1]))

        return profilevector, xcoordinates, ycoordinates, dxdy_per_cell


class MapPlot(PlotBase):
    def __init__(self, modelresult):
        super().__init__(modelresult)

    def twopanel_map(
        self, variable_1, variable_2, path, name, only_last_timestep=False
    ):
        data_1 = self.model.__dict__[variable_1]
        data_2 = self.model.__dict__[variable_2]
        colormap_1 = self.colormaps[variable_1]
        colormap_2 = self.colormaps[variable_2]

        self.create_figure("double")
        if only_last_timestep:
            t = data_1.shape[0] - 1
            self.draw_map(0, t, data_1, colormap_1)
            self.draw_map(1, t, data_2, colormap_2)
            self.save_figure(path, name, t)
            [ax.clear() for ax in self.ax]
        else:
            for t in range(data_1.shape[0]):
                self.draw_map(0, t, data_1, colormap_1)
                self.draw_map(1, t, data_2, colormap_2)
                self.save_figure(path, name, t)
                [ax.clear() for ax in self.ax]


class StatPlot(PlotBase):
    def __init__(self, modelresult):
        super().__init__(modelresult)

    def plot_histograms(self, path, name):
        self.create_figure("histograms")

        # Volume distribution in first plot
        aelabels = ["DT-r", "DT-q", "AC", "MB", "DF", "PD"]
        y_pos = np.arange(len(aelabels))
        self.axs[0, 0].barh(
            y_pos,
            self.model.archel_volumes,
            align="center",
            color=colormaps.ArchelColormap.colors[1:],
        )
        self.axs[0, 0].set_yticks(y_pos, labels=aelabels)
        self.axs[0, 0].invert_yaxis()
        self.axs[0, 0].set_title("Volume distribution between AEs (%)", loc="left")

        # D50
        bins = [0, 0.063, 0.125, 0.25, 0.5, 1, 1.4]
        binlabels = ["s/c", "vf", "f", "m", "c", "vc"]
        for i, ax in enumerate(self.axs.flat[1:]):
            counts, bins = np.histogram(
                self.model.d50_distributions[i],
                bins=bins,
                weights=self.model.d50_distribution_weights[i],
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
            self.fig.suptitle(
                "D50 distribution per preserved architectural element", fontsize=16
            )

        self.save_figure(path, name, "")
        plt.close()
