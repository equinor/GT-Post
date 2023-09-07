from pathlib import Path
from typing import List, Union

import matplotlib.pyplot as plt
import numpy as np
import xarray as xr
from matplotlib.colors import ListedColormap

import gtpost.utils as utils
from gtpost.analysis import sediment, surface
from gtpost.io import export, read_d3d_input
from gtpost.visualise import plot


class ModelResult:
    __slots__ = [
        "dataset",
        "sed_type",
        "rho_p",
        "rho_db",
        "d50_input",
        "dx",
        "dy",
        "mouth_position",
        "mouth_river_width",
        "model_boundary",
        "bottom_depth",
        "bed_level_change",
        "dep_env",
        "channels",
        "channel_skeleton",
        "channel_depth",
        "channel_width",
        "dmsedcum_final",
        "zcor",
        "vfraction",
        "sandfraction",
        "diameters",
        "porosity",
        "permeability",
        "sorting",
        "d50",
        "architectural_elements",
    ]

    def __init__(self, dataset: xr.Dataset, sedfile: Union[str, Path]):
        """
        Delft3D ModelResult class. Used for postprocessing Delft3D GeoTool model
        results.

        Parameters
        ----------
        dataset : xarray.Dataset
            Dataset of the Delft3D trim file
        sedfile : Pathlike
            Path to the D3D .sed file
        """
        self.dataset = dataset
        self.complete_dataset()
        (
            self.sed_type,
            self.rho_p,
            self.rho_db,
            self.d50_input,
        ) = read_d3d_input.read_sedfile(sedfile)

    @classmethod
    def from_folder(cls, delft3d_folder: Union[str, Path]):
        """
        Constructor for ModelResult class from Delft3D i/o folder

        Parameters
        ----------
        delft3d_folder : Union[str, Path]
            Location of the D3D i/o folder

        Returns
        -------
        ModelResult
            Instance of ModelResult. Contains the dataset attribute, which contains all
            variables in the trim.nc file.

        Raises
        ------
        TypeError if Delft3D folder is invalid/incomplete
        """
        folder = Path(delft3d_folder)
        if not folder.is_dir():
            raise TypeError("This is not a complet Delft3D i/o folder")

        sedfile = [f for f in folder.glob("*.sed")][0]
        trimfile = [f for f in folder.glob("*.nc") if "trim" in f.name][0]

        dataset = xr.open_dataset(trimfile)
        if "flow2d3d" in dataset.attrs["source"].lower():
            return cls(dataset, sedfile)
        else:
            raise TypeError("File is not recognized as a Delft3D trim file")

    def complete_dataset(self):
        """
        Derive additional attributes from the trimfile (self.dataset). These are:

        dx, dy              :       int: x and y grid resolution
        mouth_position      :       tuple(int, int): x, y position of the delta apex
        mouth_river_width   :       int: width of the river at the delta apex
        model_boundary      :       shapely.Polygon: polygon of model boundary
        bed_level_change    :       np.ndarray: array (time, x, y) with bed level change
        """
        self.dx, self.dy = utils.get_dx_dy(self.dataset)
        self.mouth_position = utils.get_mouth_midpoint(self.dataset)
        self.mouth_river_width = utils.get_river_width_at_mouth(
            self.dataset, self.mouth_position
        )
        self.model_boundary = utils.get_model_bound(self.dataset)
        self.bed_level_change = np.zeros_like(self.dataset["MEAN_H1"])
        self.bed_level_change[1:, :, :] = (
            self.dataset["DPS"].values[1:, :, :] - self.dataset["DPS"].values[:-1, :, :]
        )
        self.dataset["MEAN_H1"] = self.dataset.MEAN_H1.where(self.dataset.MEAN_H1 > -50)
        self.bottom_depth = self.dataset["DPS"].where(self.dataset["DPS"] > 0).values

    def detect_depositional_environments(self):
        """
        Detect depositional environments and channel parameters.

        Adds the attribute "dep_env" which is an np.ndarray with time, x and y
        dimensions. It detects the following environments:

        1 - Delta top
        2 - Abandoned channel
        3 - Active channel
        4 - Delta edge area
        5 - Deep marine area

        Returns
        -------
        None (attribute dep_env is created)
        """
        # Initial detection of Delta top, Delta front and Prodelta
        dep_env = surface.detect_depositional_environments(
            self.dataset["STD_SBUV"].values,
            self.mouth_position,
            self.model_boundary,
        )
        # Detection of channel network
        (
            self.dep_env,
            self.channels,
            self.channel_skeleton,
            self.channel_width,
            self.channel_depth,
        ) = surface.detect_channel_network(
            self.dataset, dep_env, self.bed_level_change, self.dx
        )
        # Update of Delta front area to include the mouth of channels that connect to
        # the delta front (mouthbars are expected to form here)

    def detect_architectural_elements(self):
        """
        Detect architectural elements on the delta from previously determined
        depositional environments, channel data and bed level change data. Attribute
        "architectural_elements" is added and contains the following elements:

        1 - Delta top (overbank deposits and background sedimentation)
        2 - Abandoned channel (channel fill deposits)
        3 - Active channel (bed deposits)
        4 - Mouthbars (mouthbar deposits in vicinity of channels and delta front)
        5 - Delta front (background sedimentation around delta edge)
        6 - Prodelta (marine background sedimentation)

        Returns
        -------
        None (attribute architectural_elements is created)
        """
        self.architectural_elements = surface.detect_elements(
            self.dep_env, self.channel_skeleton, self.bed_level_change
        )

    def compute_sediment_parameters(self):
        """
        Compute sediment parameters. Add the following attributes ModelResult:

        dmsedcum_final      :       Cumulative sed ... #TODO
        zcor                :       z coordinate for each time, x, y for stratigraphy
        vfraction           :       sediment type fractions ... #TODO
        sandfraction        :       Fraction of sand sediment types
        diameters           :       np.ndarray: D50 array (time, x, y)
        porosity            :       np.ndarray: Porosity array (time, x, y)
        permeability        :       np.ndarray: Permeability array (time, x, y)

        Returns
        -------
        None (but the above attributes are added to the instance)
        """
        percentage2cal = [5, 10, 16, 50, 84, 90]
        self.dmsedcum_final, self.zcor = sediment.calculate_stratigraphy(
            self.dataset["DMSEDCUM"].values, self.dataset["DPS"].values
        )
        self.vfraction = sediment.calculate_fraction(self.rho_db, self.dmsedcum_final)
        self.sandfraction = sediment.calculate_sand_fraction(
            self.sed_type, self.vfraction
        )
        self.diameters, self.porosity, self.permeability = sediment.calculate_diameter(
            np.asarray(self.d50_input, dtype=np.float32),
            np.asarray(percentage2cal, dtype=np.float32),
            self.vfraction,
        )
        self.sorting = sediment.calculate_sorting(self.diameters, percentage2cal)
        self.d50 = self.diameters[:, :, :, 3]

    def postprocess(self):
        """
        Run all postprocess methods in order:

        - Compute sediment parameters
        - Detect depositional environments
        - Detect architectural elements
        """
        # self.compute_sediment_parameters()
        self.detect_depositional_environments()
        self.detect_architectural_elements()

    def export_sediment_data(self):
        pass

    def export_sediment_and_object_data(self, out_file):
        ds = export.create_sed_and_obj_dataset(self)
        ds.to_netcdf(out_file)


if __name__ == "__main__":
    d3d_folders = Path(r"p:\11209074-002-Geotool-new-deltas\01_modelling").glob("*")

    for d3d_folder in d3d_folders:
        d3d_folder = Path(
            r"p:\11209074-002-Geotool-new-deltas\01_modelling\Roda_010_1x4_triangle"
        )
        folder_name = d3d_folder.stem
        output_folder = Path(
            f"n:\\Projects\\11209000\\11209074\\B. Measurements and calculations\\test_results\\{folder_name}"
        )

        # try:
        test = ModelResult.from_folder(d3d_folder)
        test.postprocess()
        # test.export_sediment_and_object_data(
        #     output_folder.joinpath(f"Sed_and_Obj_data.nc")
        # )
        # except Exception:
        # continue

        if not output_folder.is_dir():
            Path.mkdir(output_folder)

        # mapplotter = plot.MapPlot(test)
        # mapplotter.twopanel_map("bottom_depth", "architectural_elements")
        # mapplotter.save_figures(output_folder, "maps_wd_ae")

        xsectplotter = plot.CrossSectionPlot(test, (100, 130), (240, 140))
        xsectplotter.twopanel_xsection(
            "architectural_elements",
            "architectural_elements",
        )
        xsectplotter.save_figures(output_folder, "archels")

        xsectplotter.twopanel_xsection("d50", "d50")
        xsectplotter.save_figures(output_folder, "d50")

        # test plotting
        alphas = [1, 0.5, 0.7, 0, 0.5, 0, 1]
        alphas = [1, 1, 1, 1, 1, 1, 1]
        cmap = ListedColormap(
            colors=[
                "snow",
                "yellowgreen",
                "peru",
                "deepskyblue",
                "yellow",
                "turquoise",
                "mediumblue",
            ],
            name="archels",
        )
        cmap = cmap(np.arange(cmap.N))
        cmap[:, -1] = alphas
        cmap = ListedColormap(cmap)
        bounds = np.arange(8)
        vals = bounds[:-1]
        # norm = matplotlib.colors.BoundaryNorm(bounds, cmap.N)

        for i in range(len(test.dataset.time)):
            fig = plt.figure(figsize=(10, 10))
            ax = fig.subplots()
            # ax.imshow(
            #     test.channel_width[100, :, :] * test.channel_skeleton[100, :, :],
            #     cmap=plt.cm.YlGnBu,
            #     vmin=0,
            #     vmax=300,
            # )
            # ax.imshow(
            #     test.dataset["STD_SBUV"].values[100, :, :],
            #     cmap=plt.cm.YlGnBu,
            #     vmin=0,
            #     vmax=0.00004,
            # )
            # test.dataset.MEAN_H1[i, :, :].plot.imshow(
            #     ax=ax, vmin=0, vmax=8, cmap=plt.cm.YlGnBu
            # )
            # ax.plot(test.lower_edge[i].xy[1], test.lower_edge[i].xy[0], color="yellow")
            im = ax.imshow(
                test.architectural_elements[i, :, :],
                cmap=cmap,
                interpolation="antialiased",
                interpolation_stage="rgba",
            )
            ax.invert_yaxis()

            ax.set_ylabel("Cross-shore direction (cells)")
            im.set_clim(0, 7)

            bbox = ax.get_position()
            clbounds = bbox.bounds

            ax.set_title("Architectural Elements", loc="left")
            ax_cl = fig.add_axes([clbounds[0], clbounds[1] - 0.1, clbounds[2], 0.02])
            cbar = fig.colorbar(
                ax.images[0],
                cax=ax_cl,
                boundaries=bounds,
                values=vals,
                orientation="horizontal",
            )
            cbar.set_ticks(vals + 0.5)
            cbar.set_ticklabels(["N/A", "AC", "CF", "DT", "MB", "DF", "PD"])
            cbar.ax.tick_params()
            # derive time
            # seconds_since_ref = int(self.timeseries[timestep])
            # date_image_name = self.date_time(seconds_since_ref=seconds_since_ref).strftime("%Y%m%d%H%M%S")
            # self.time = date_image_name
            ax.set_xlabel("Alongshore direction (cells)")
            plt.savefig(output_folder.joinpath(f"{i:04}.png"))
            plt.close()

    print(f"{folder_name} done!")
    plt.imshow(test.bottom_depth[100, :, :])
    # (test.dataset.MAX_UV[100, :, :]).plot.imshow(vmin=0, vmax=1, alpha=1)
    # (test.dataset.STD_SBUV[100, :, :] * test.dataset.STD_SSUV[100, :, :]).plot.imshow(
    #     vmin=1e-14, vmax=1e-14, alpha=0.5
    # )
    # (test.dataset.MEAN_SBUV[100, :, :]).plot.imshow(vmin=0, vmax=1e-4, alpha=1)
    # fig = plt.figure(figsize=(10, 10))
    # ax = fig.subplots()
    # ax.imshow(test.bed_level_change[100,:,:], vmin=-1, vmax=1)
    # ax.invert_yaxis()
