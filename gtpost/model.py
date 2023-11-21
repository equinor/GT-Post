from configparser import ConfigParser
from pathlib import Path
from typing import List, Union

import numpy as np
import xarray as xr

import gtpost.utils as utils
from gtpost.analyze import sediment, statistics, surface
from gtpost.io import ENCODINGS, export, read_d3d_input
from gtpost.visualize import plot

default_settings_file = (
    Path(__file__).parents[1].joinpath(r"config\default_settings.ini")
)


class ModelResult:
    # __slots__ = [
    #     "config",
    #     "dataset",
    #     "sed_type",
    #     "rho_p",
    #     "rho_db",
    #     "d50_input",
    #     "dx",
    #     "dy",
    #     "mouth_position",
    #     "mouth_river_width",
    #     "model_boundary",
    #     "bottom_depth",
    #     "slope",
    #     "foreset_depth",
    #     "toeset_depth",
    #     "delta_fringe",
    #     "df_average_width",
    #     "bed_level_change",
    #     "dep_env",
    #     "channels",
    #     "channel_skeleton",
    #     "channel_depth",
    #     "channel_width",
    #     "dmsedcum_final",
    #     "zcor",
    #     "vfraction",
    #     "sandfraction",
    #     "diameters",
    #     "porosity",
    #     "permeability",
    #     "sorting",
    #     "d50",
    #     "architectural_elements",
    # ]

    def __init__(
        self,
        dataset: xr.Dataset,
        sedfile: Union[str, Path],
        modelname: str = "Unnamed Delft3D Geotool modelresult",
        settings_file: Union[str, Path] = default_settings_file,
        post: bool = True,
    ):
        """
        Delft3D ModelResult class. Used for postprocessing Delft3D GeoTool model
        results.

        Parameters
        ----------
        dataset : xarray.Dataset
            Dataset of the Delft3D trim file
        sedfile : Pathlike
            Path to the D3D .sed file
        settings_file : Pathlike
            Path to settings .ini file
        post : Boolean
            Postprocessing or processing

        """
        self.modelname = modelname
        self.config = ConfigParser()
        self.config.read(settings_file)
        self.dataset = dataset
        # self.dataset = dataset.isel(
        #     time=slice(
        #         int(0),
        #         int(50),
        #     )
        # )
        if post:
            self.complete_init_for_postprocess()
            self.processing_state = "postprocessing"
        else:
            self.complete_init_for_process()
            self.processing_state = "processing"
        (
            self.sed_type,
            self.rho_p,
            self.rho_db,
            self.d50_input,
        ) = read_d3d_input.read_sedfile(sedfile)

    def __repr__(self):
        return (
            f"< {self.modelname} >\n---------------------------\n"
            + f"Processing state      : {self.processing_state}\n"
            + f"Completed timesteps   : {len(self.dataset.time)}"
        )

    @classmethod
    def from_folder(
        cls,
        delft3d_folder: Union[str, Path],
        settings_file: Union[str, Path] = default_settings_file,
    ):
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
            raise TypeError("This is not a complete Delft3D i/o folder")

        sedfile = [f for f in folder.glob("*.sed")][0]
        trimfile = [f for f in folder.glob("*.nc") if "trim" in f.name][0]
        modelname = delft3d_folder.stem + f" - {sedfile.stem}"

        dataset = xr.open_dataset(trimfile)
        if "flow2d3d" in dataset.attrs["source"].lower():
            return cls(
                dataset, sedfile, modelname=modelname, settings_file=settings_file
            )
        else:
            raise TypeError("File is not recognized as a Delft3D trim file")

    def complete_init_for_process(self):
        """
        Derive additional attributes from the trimfile (self.dataset) for postprocessing
        the final model results. These are:
        """
        self.bottom_depth = self.dataset["DPS"].where(self.dataset["DPS"] > -10).values
        self.subsidence_per_t = np.diff(self.dataset["SDU"].values, axis=0)[0, :, :]

    def complete_init_for_postprocess(self):
        """
        Derive additional attributes from the trimfile (self.dataset) for postprocessing
        the final model results. These are:

        dx, dy              :       int: x and y grid resolution
        mouth_position      :       tuple(int, int): x, y position of the delta apex
        mouth_river_width   :       int: width of the river at the delta apex
        model_boundary      :       shapely.Polygon: polygon of model boundary
        bed_level_change    :       np.ndarray: array (time, x, y) with bed level change
        slope               :       np.ndarray: array (time, x, y) with surface slope
        foreset_depth       :       np.ndarray: array (time) with time-dependent depth
                                    of the foreset.
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
        self.subsidence_per_t = np.diff(self.dataset["SDU"].values, axis=0)[0, :, :]
        self.dataset["MEAN_H1"] = self.dataset.MEAN_H1.where(self.dataset.MEAN_H1 > -50)
        self.bottom_depth = self.dataset["DPS"].where(self.dataset["DPS"] > -10).values
        self.slope = surface.slope(self.dataset["MEAN_H1"].values)
        self.foreset_depth = utils.get_deltafront_contour_depth(
            self.bottom_depth, self.slope, self.model_boundary
        )
        self.df_average_width = int(
            self.config["classification"]["deltafront_expected_width"]
        )

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
        dep_env, self.delta_fringe = surface.detect_depositional_environments(
            self.bottom_depth,
            self.mouth_position,
            self.mouth_river_width,
            self.model_boundary,
            self.foreset_depth,
            self.df_average_width,
        )
        # Detection of channel network
        (
            self.dep_env,
            self.channels,
            self.channel_skeleton,
            self.channel_width,
            self.channel_depth,
        ) = surface.detect_channel_network(
            self.dataset,
            dep_env,
            self.d50,
            self.dx,
            self.config,
        )
        # Update of Delta front area to include the mouth of channels that connect to
        # the delta front (mouthbars are expected to form here)

    def detect_architectural_elements(self):
        """
        Detect architectural elements on the delta from previously determined
        depositional environments, channel data and bed level change data. Attribute
        "architectural_elements" is added and contains the following elements:

        1 - Delta top subaerial (overbank deposits/background sedimentation)
        2 - Delta top subaqeous (submerged overbank deposits/background sedimentation)
        3 - Abandoned channel (channel fill deposits)
        4 - Active channel (bed deposits)
        5 - Mouthbars (mouthbar deposits in vicinity of channels and delta front)
        6 - Delta front (background sedimentation around delta edge)
        7 - Prodelta (marine background sedimentation)

        Returns
        -------
        None (attribute architectural_elements is created)
        """
        self.architectural_elements = surface.detect_elements(
            self.dep_env,
            self.channel_skeleton,
            self.bottom_depth,
            self.bed_level_change,
            self.sandfraction,
            self.foreset_depth,
            self.config,
        )

    def compute_sediment_parameters(self):
        """
        Compute sediment parameters. Add the following attributes ModelResult:

        dmsedcum_final      :       Mass flux per sediment class (time, f, x, y)
        zcor                :       z coordinate for each time, x, y for stratigraphy
        vfraction           :       Volume fraction per sediment class (time, f, x, y)
        sandfraction        :       Fraction of sand sediment types (time, x, y)
        diameters           :       np.ndarray: D50 array (time, x, y)
        porosity            :       np.ndarray: Porosity array (time, x, y)
        permeability        :       np.ndarray: Permeability array (time, x, y)

        Returns
        -------
        None (but the above attributes are added to the instance)
        """
        percentage2cal = [5, 10, 16, 50, 84, 90]
        self.dmsedcum_final = self.dataset["DMSEDCUM"].values
        # Only the incoming sediment flux determines the composition of potential
        # deposits, so remove fluxes of sediment classes that are negative.
        self.dmsedcum_final[self.dmsedcum_final < 0] = 0
        self.zcor = -self.dataset["DPS"].values
        self.preserved_thickness = sediment.preservation(
            self.zcor, self.dataset["SDU"].values
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

    def statistics_summary(self):
        (
            delta_volume,
            archel_volumes,
            archel_d50s,
            archel_fractions,
            archel_sorting,
        ) = statistics.get_stats_per_archel(
            self.architectural_elements,
            self.preserved_thickness,
            self.d50,
            self.sandfraction,
            self.sorting,
            self.mouth_position[1],
        )
        self.delta_stats = {
            "delta_volume": delta_volume,
            "delta_top_aerial_volume": archel_volumes[0],
            "delta_top_aerial_d50": archel_d50s[0],
            "delta_top_aerial_sandfraction": archel_fractions[0],
            "delta_top_aerial_sorting": archel_sorting[0],
            "delta_top_sub_volume": archel_volumes[1],
            "delta_top_sub_d50": archel_d50s[1],
            "delta_top_sub_sandfraction": archel_fractions[1],
            "delta_top_sub_sorting": archel_sorting[1],
            "abandoned_channel_volume": archel_volumes[2],
            "abandoned_channel_d50": archel_d50s[2],
            "abandoned_channel_sandfraction": archel_fractions[2],
            "abandoned_channel_sorting": archel_sorting[2],
            "active_channel_volume": archel_volumes[3],
            "active_channel_d50": archel_d50s[3],
            "active_channel_sandfraction": archel_fractions[3],
            "active_channel_sorting": archel_sorting[3],
            "mouthbar_volume": archel_volumes[4],
            "mouthbar_d50": archel_d50s[4],
            "mouthbar_sandfraction": archel_fractions[4],
            "mouthbar_sorting": archel_sorting[4],
            "delta_front_volume": archel_volumes[5],
            "delta_front_d50": archel_d50s[5],
            "delta_front_sandfraction": archel_fractions[5],
            "delta_front_sorting": archel_sorting[5],
            "prodelta_volume": archel_volumes[6],
            "prodelta_d50": archel_d50s[6],
            "prodelta_sandfraction": archel_fractions[6],
            "prodelta_sorting": archel_sorting[6],
        }

    def process(self):
        """
        Run all process methods:

        - Compute sediment parameters
        """
        self.compute_sediment_parameters()

    def postprocess(self):
        """
        Run all postprocess methods in order:

        - Compute sediment parameters
        - Detect depositional environments
        - Detect architectural elements
        """
        self.compute_sediment_parameters()
        self.detect_depositional_environments()
        self.detect_architectural_elements()
        self.statistics_summary()

    def export_sediment_and_object_data(self, out_file: Union[str, Path]):
        ds = export.create_sed_and_obj_dataset(self)
        ds.to_netcdf(out_file, engine="h5netcdf", encoding=ENCODINGS)


if __name__ == "__main__":
    d3d_folders = Path(r"p:\11209074-002-Geotool-new-deltas\01_modelling").glob("*")

    for d3d_folder in d3d_folders:
        d3d_folder = Path(
            r"p:\11209074-002-Geotool-new-deltas\01_modelling\Sobrabre_045_Reference"
        )
        folder_name = d3d_folder.stem
        config_file = (
            Path(__file__).parents[1].joinpath(r"config\settings_sobrarbe.ini")
        )
        output_folder = Path(
            f"n:\\Projects\\11209000\\11209074\\B. Measurements and calculations\\test_results\\{folder_name}"
        )

        if not output_folder.is_dir():
            Path.mkdir(output_folder)

        test = ModelResult.from_folder(d3d_folder, settings_file=config_file)
        test.postprocess()
        test.export_sediment_and_object_data(
            output_folder.joinpath("Sed_and_Obj_data.nc")
        )

        # mapplotter = plot.MapPlot(test)
        # mapplotter.twopanel_map("bottom_depth", "architectural_elements")
        # mapplotter.save_figures(output_folder, "maps_wd_ae")

        # xsectplotter_xshore = plot.CrossSectionPlot(test, (10, 155), (80, 155))
        xsectplotter_xshore = plot.CrossSectionPlot(test, (100, 140), (200, 140))
        xsectplotter_xshore.twopanel_xsection(
            "architectural_elements",
            "architectural_elements",
        )
        xsectplotter_xshore.save_figures(output_folder, "archels_xshore")

        xsectplotter_xshore.twopanel_xsection("d50", "d50")
        xsectplotter_xshore.save_figures(output_folder, "d50_xshore")

        xsectplotter_lshore = plot.CrossSectionPlot(test, (10, 60), (70, 240))
        # xsectplotter_lshore = plot.CrossSectionPlot(test, (115, 80), (115, 220))
        xsectplotter_lshore.twopanel_xsection(
            "architectural_elements",
            "architectural_elements",
        )
        xsectplotter_lshore.save_figures(output_folder, "archels_lshore")

        xsectplotter_lshore.twopanel_xsection("d50", "d50")
        xsectplotter_lshore.save_figures(output_folder, "d50_lshore")
        print("stop")
