import shutil
from configparser import ConfigParser
from pathlib import Path
from typing import Self

import numpy as np
import xarray as xr

import gtpost.utils as utils
from gtpost.analyze import classifications, layering, sediment, statistics, surface
from gtpost.analyze.sediment import calculate_diameter
from gtpost.experimental import detect_archels
from gtpost.io import export, read_d3d_input

default_settings_file = (
    Path(__file__).parents[1].joinpath("config/default_settings.ini")
)


class ModelResult:
    def __init__(
        self,
        dataset: xr.Dataset,
        sedfile: str | Path,
        modelname: str = "Unnamed Delft3D Geotool modelresult",
        settings_file: str | Path = default_settings_file,
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
        self.dataset = dataset  # .isel(time=slice(0, 120))  # time slice for testing

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
            + f"Completed timesteps   : {self.timestep}"
        )

    @classmethod
    def from_folder(
        cls,
        delft3d_folder: str | Path,
        settings_file: str | Path = default_settings_file,
        post: bool = True,
        use_copied_trim_file: bool = True,
    ) -> Self:
        """
        Constructor for ModelResult class from Delft3D i/o folder

        Parameters
        ----------
        delft3d_folder : str | Path
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

        if use_copied_trim_file:
            shutil.copyfile(trimfile, folder / "temp.nc")
            dataset = xr.open_dataset(folder / "temp.nc")
        else:
            dataset = xr.open_dataset(trimfile)

        if "flow2d3d" in dataset.attrs["source"].lower():
            return cls(
                dataset,
                sedfile,
                modelname=modelname,
                post=post,
                settings_file=settings_file,
            )
        else:
            raise TypeError("File is not recognized as a Delft3D trim file")

    @property
    def timestep(self):
        return len(self.dataset.time)

    def complete_init_for_process(self):
        """
        Derive additional attributes from the trimfile (self.dataset) for postprocessing
        the final model results. These are:
        """
        self.dx, self.dy = utils.get_dx_dy(self.dataset.XZ[:, 0].values)
        self.mouth_position = utils.get_mouth_midpoint(
            self.dataset["MEAN_H1"][1, :, :].values,
            self.dataset.N.values,
            self.dataset.M.values,
        )
        self.bottom_depth = self.dataset["DPS"].where(self.dataset["DPS"] > -10).values
        subsidence = np.append(
            self.dataset["SDU"].values,
            self.dataset["SDU"].values[-1, :, :][np.newaxis, ...],
            axis=0,
        )
        self.subsidence = np.diff(subsidence, axis=0)
        self.deposit_height = np.zeros_like(self.dataset["MEAN_H1"])
        self.deposit_height[1:, :, :] = -(
            (
                self.dataset["DPS"].values[1:, :, :]
                - self.dataset["DPS"].values[:-1, :, :]
            )
            + self.subsidence[1:, :, :]
        )
        self.deposit_height[np.abs(self.deposit_height) < 1e-5] = 0

    def complete_init_for_postprocess(self):
        """
        Derive additional attributes from the trimfile (self.dataset) for postprocessing
        the final model results. These are:

        dx, dy              :       int: x and y grid resolution
        mouth_position      :       tuple(int, int): x, y position of the delta apex
        mouth_river_width   :       int: width of the river at the delta apex
        model_boundary      :       shapely.Polygon: polygon of model boundary
        deposit_height      :       np.ndarray: array (time, x, y) height of deposit
        slope               :       np.ndarray: array (time, x, y) with surface slope
        foreset_depth       :       np.ndarray: array (time) with time-dependent depth
                                    of the foreset.
        """
        self.dx, self.dy = utils.get_dx_dy(self.dataset.XZ[:, 0].values)
        self.mouth_position = utils.get_mouth_midpoint(
            self.dataset["MEAN_H1"][1, :, :].values,
            self.dataset.N.values,
            self.dataset.M.values,
        )
        self.mouth_river_width = utils.get_river_width_at_mouth(
            self.dataset["MEAN_H1"][1, :, :].values, self.mouth_position
        )
        self.model_boundary = utils.get_model_bound(
            self.dataset["MEAN_H1"][1, :, :].values
        )
        self.model_mask = self.dataset["KCS"] >= 1
        subsidence = np.append(
            self.dataset["SDU"].values,
            self.dataset["SDU"].values[-1, :, :][np.newaxis, ...],
            axis=0,
        )
        self.subsidence = np.diff(subsidence, axis=0)
        self.deposit_height = np.zeros_like(self.dataset["MEAN_H1"])
        self.deposit_height[1:, :, :] = -(
            (
                self.dataset["DPS"].values[1:, :, :]
                - self.dataset["DPS"].values[:-1, :, :]
            )
            + self.subsidence[1:, :, :]
        )
        self.deposit_height[np.abs(self.deposit_height) < 1e-5] = 0
        self.dataset["MEAN_H1"] = self.dataset.MEAN_H1.where(self.dataset.MEAN_H1 > -50)
        self.bottom_depth = self.dataset["DPS"].where(self.dataset["DPS"] > -10).values
        self.slope = surface.slope(self.dataset["MEAN_H1"].values)
        self.foreset_depth = utils.get_deltafront_contour_depth(
            self.bottom_depth, self.slope, self.model_boundary
        )
        self.df_average_width = int(
            self.config["classification"]["deltafront_expected_width"]
        )

    def detect_channel_network(self):
        """
        Detect channels and derived parameters.

        Returns
        -------
        None (attributes channels, channel_skeleton, channel_width and channel_depth
        are created)
        """
        (
            self.channels,
            self.channel_skeleton,
            self.channel_width,
            self.channel_depth,
        ) = surface.detect_channel_network(
            self.dataset,
            self.subenvironment,
            self.dx,
            self.config,
        )

    def detect_architectural_elements(self):
        """
        Detect architectural elements on the delta from previously determined
        depositional environments, channel data and bed level change data. Attribute
        "architectural_elements" is added and contains the following elements:

        1 - Delta top subaerial (overbank deposits/background sedimentation)
        2 - Delta top subaqeous (submerged overbank deposits/background sedimentation)
        3 - Active channel (bed deposits)
        4 - Mouthbars (mouthbar deposits in vicinity of channels and delta front)
        5 - Delta front (background sedimentation around delta edge)
        6 - Prodelta (marine background sedimentation)

        Returns
        -------
        None (attribute architectural_elements is created)
        """
        self.architectural_elements = detect_archels.detect(self)

    def compute_sediment_parameters_postprocessing(self):
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
        self.preserved_thickness, self.deposition_age = layering.preservation(
            self.zcor, self.dataset["SDU"].values, self.deposit_height
        )
        self.vfraction = sediment.calculate_fraction(self.rho_db, self.dmsedcum_final)
        self.sandfraction = sediment.calculate_sand_fraction(
            self.sed_type, self.vfraction
        )
        self.diameters, self.porosity, self.permeability = calculate_diameter(
            np.asarray(self.d50_input, dtype=np.float32),
            np.asarray(percentage2cal, dtype=np.float32),
            self.vfraction,
        )
        self.sorting = sediment.calculate_sorting(self.diameters, percentage2cal)
        self.d50 = self.diameters[:, :, :, 3]

    def compute_sediment_parameters_processing(self):
        """
        Compute sediment parameters. Add the following attributes ModelResult:

        Simplified for the processing step, which only requires D50 as end result.

        diameters           :       np.ndarray: D50 array (time, x, y)

        Returns
        -------
        None (but the above attributes are added to the instance)
        """
        percentage2cal = [50]
        self.dmsedcum_final = self.dataset["DMSEDCUM"].values
        # FUTURE DASK SOLUTION HERE
        # self.dmsedcum_final.map_blocks(
        #     sediment.calculate_fraction,
        # )
        # Only the incoming sediment flux determines the composition of potential
        # deposits, so remove fluxes of sediment classes that are negative.
        self.dmsedcum_final[self.dmsedcum_final < 0] = 0
        self.vfraction = sediment.calculate_fraction(self.rho_db, self.dmsedcum_final)

        self.zcor = -self.dataset["DPS"].values
        self.preserved_thickness, self.deposition_age = layering.preservation(
            self.zcor, self.dataset["SDU"].values, self.deposit_height
        )

        self.diameters, *_ = calculate_diameter(
            np.asarray(self.d50_input, dtype=np.float32),
            np.asarray(percentage2cal, dtype=np.float32),
            self.vfraction,
        )
        self.d50 = self.diameters[:, :, :, 0]

    def statistics_summary(self):
        """
        Get statistics from calculated model results
        """
        (
            self.d50_distributions,
            self.d50_distribution_weights,
        ) = statistics.get_diameter_distributions(
            self.architectural_elements,
            self.preserved_thickness,
            self.d50,
            self.mouth_position[1],
        )

        (
            delta_volume,
            self.archel_volumes,
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
            "delta_top_aerial_volume": self.archel_volumes[0],
            "delta_top_aerial_d50": archel_d50s[0],
            "delta_top_aerial_sandfraction": archel_fractions[0],
            "delta_top_aerial_sorting": classifications.sorting_classifier(
                archel_sorting[0]
            )[0],
            "delta_top_sub_volume": self.archel_volumes[1],
            "delta_top_sub_d50": archel_d50s[1],
            "delta_top_sub_sandfraction": archel_fractions[1],
            "delta_top_sub_sorting": classifications.sorting_classifier(
                archel_sorting[1]
            )[0],
            "active_channel_volume": self.archel_volumes[2],
            "active_channel_d50": archel_d50s[2],
            "active_channel_sandfraction": archel_fractions[2],
            "active_channel_sorting": classifications.sorting_classifier(
                archel_sorting[2]
            )[0],
            "mouthbar_volume": self.archel_volumes[3],
            "mouthbar_d50": archel_d50s[3],
            "mouthbar_sandfraction": archel_fractions[3],
            "mouthbar_sorting": classifications.sorting_classifier(archel_sorting[3])[
                0
            ],
            "delta_front_volume": self.archel_volumes[4],
            "delta_front_d50": archel_d50s[4],
            "delta_front_sandfraction": archel_fractions[4],
            "delta_front_sorting": classifications.sorting_classifier(
                archel_sorting[4]
            )[0],
            "prodelta_volume": self.archel_volumes[5],
            "prodelta_d50": archel_d50s[5],
            "prodelta_sandfraction": archel_fractions[5],
            "prodelta_sorting": classifications.sorting_classifier(archel_sorting[5])[
                0
            ],
        }

    def process(self):
        """
        Run all process methods:

        - Compute sediment parameters
        """
        self.compute_sediment_parameters_processing()

    def postprocess(self):
        """
        Run all postprocess methods in order:

        - Compute sediment parameters
        - Detect subenvironments
        - Detect architectural elements
        """
        self.compute_sediment_parameters_postprocessing()
        # self.detect_subenvironments()
        # self.detect_channel_network()
        self.detect_architectural_elements()
        self.statistics_summary()

    def export_sediment_and_object_data(self, out_file: str | Path):
        """
        Export sediment and object data to a NetCDF file.

        This method creates a dataset containing sediment and object data
        and exports it to a specified NetCDF file.

        Parameters
        ----------
        out_file : str or Path
            The path to the output NetCDF file.

        Returns
        -------
        None

        Notes
        -----
        The dataset is created using the `export.create_sed_and_obj_dataset` method
        and saved to a NetCDF file using the `h5netcdf` engine with specified encodings.
        """
        ds = export.create_sed_and_obj_dataset(self)
        ds.to_netcdf(out_file, engine="h5netcdf", encoding=export.ENCODINGS)

    def append_input_ini_file(self, input_ini_file: str | Path, out_file: str | Path):
        """
        Appends sections and settings for postprocessing settings, subenviroment
        definitions and architectural element definitions to the input.ini configuration
        file and writes the updated configuration to an output file.

        Parameters
        ----------
        input_ini_file : str or Path
            The path to the input INI file to be read and modified.
        out_file : str or Path
            The path to the output file where the modified configuration will be written.
        """
        shutil.copyfile(input_ini_file, out_file)
        config = ConfigParser()
        config.read(out_file)

        # Define new sections
        config.add_section("postprocessing_parameters")
        config.add_section("subenvironments")
        config.add_section("architectural_elements")

        # Fill new sections
        for key, value in self.config.items("classification"):
            config.set("postprocessing_parameters", key, value)
        for code, name in zip(
            classifications.subenvironment_codes, classifications.subenvironment_names
        ):
            config.set("subenvironments", str(code), name)
        for code, name in zip(
            classifications.archel_codes, classifications.archel_names
        ):
            config.set("architectural_elements", str(code), name)
        with open(out_file, "w") as configfile:
            config.write(configfile)
