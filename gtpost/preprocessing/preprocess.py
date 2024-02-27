import logging
import math
import shutil
from pathlib import Path

import numpy as np
from mako.lookup import TemplateLookup

from gtpost.preprocessing.bathymetry_builder import BathymetryBuilder
from gtpost.preprocessing.inidata import revise
from gtpost.preprocessing.preprocessing_utils import (
    IniParser,
    edit_sdu_file,
    get_shape_from_grd_file,
    read_dep_file,
    write_dep_file,
)

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.WARNING)

composition_options = (
    "veryfine-sand",
    "medium-sand",
    "fine-sand",
    "coarse-silt",
    "coarse-sand",
)

channel_width_options = (500, 1000, 1500)


class PreProcess:
    # Constants
    g = 9.81
    nx_bathymetry = 302
    ny_bathymetry = 282
    nx_wave = 102
    ny_wave = 162
    dx = 50
    dy = 50
    nodata_value = -999
    tfactor = 1440
    distal_depth = 50
    depth_edit_range = 5
    river_length = 100  # TODO: read from ini file
    clayvolcomposition = 0
    sandvolcomposition = 0

    # Default values for parameters derived from the input.ini
    template_name = "test"
    simulation_start_t = 0
    simulation_stop_t = 320.5
    output_interval = 1
    basin_slope = 0.1
    default_basin_slope = 0.1
    river_initial_discharge = 1000
    river_final_discharge = 1000
    tidal_amplitude = 3
    wave_initial_height = 1
    wave_final_height = 1
    wave_initial_period = 5
    wave_final_period = 5
    wave_direction = 0
    subsidence_land = 5
    subsidence_sea = 5
    composition = "coarse-sand"

    # Default folders
    templates_folder = Path(__file__).parents[2].joinpath("gt_templates")
    parameter_file = Path(__file__).parent.joinpath("model_builder_defaults.json")

    def __init__(self, inifile: str | Path, fpath_output: str | Path):
        self.inifile = Path(inifile)
        self.read_ini()
        self.load_ini_parameters()
        self.fpath_template = self.templates_folder.joinpath(self.template_name)
        self.fpath_output = Path(fpath_output)
        self.template_context = {
            "t_stop": self.simulation_stop_t,
            "t_interval": self.output_interval,
            "T_amplitude": self.tidal_amplitude,
            "riverdischargeini": self.river_initial_discharge,
            "riverdischargefin": self.river_final_discharge,
            "composition": self.composition,
            "waveheightini": self.wave_initial_height,
            "waveheightfin": self.wave_final_height,
            "waveperiodini": self.wave_initial_period,
            "waveperiodfin": self.wave_final_period,
            "wavedirection": self.wave_direction,
        }

    def read_ini(self) -> None:
        """Read inifile and parse as dict"""
        if self.inifile.exists():
            parser = IniParser()
            parser.read(self.inifile)
            self.inidata = parser.as_dict
        else:
            logger.warning(f'inifile "{self.inifile}" not found, nothing to read')

    def load_ini_parameters(self) -> None:
        # Template name
        self.template_name = str(self.inidata["template"]["value"])
        # Model simulation stop time [min]
        self.simulation_stop_t = self.tfactor * float(
            self.inidata["simstoptime"]["value"]
        )
        # Output interval
        self.output_interval = self.tfactor * float(
            self.inidata["outputinterval"]["value"]
        )
        # River length (this is a fixed value in the input.ini)
        self.river_length = int(self.inidata["riverlength"]["value"])
        # channel width
        self.channel_width = int(self.inidata["channelwidth"]["value"])
        if self.channel_width not in channel_width_options:
            logger.warning(
                f"Channel width of {self.channel_width} m is not an option, using 500 m"
            )
            self.channel_width = 500
        # Basin slope
        self.basin_slope = float(self.inidata["basinslope"]["value"])
        # Initial river discharge
        self.river_initial_discharge = float(self.inidata["riverdischargeini"]["value"])
        # Final river discharge
        self.river_final_discharge = float(self.inidata["riverdischargefin"]["value"])
        # Tidal amplitude
        self.tidal_amplitude = float(self.inidata["tidalamplitude"]["value"])
        # Initial wave height and period
        self.wave_initial_height = float(self.inidata["waveheightini"]["value"])
        self.wave_initial_period = np.round(5 * math.sqrt(self.wave_initial_height), 2)
        # Final wave height and period
        self.wave_final_height = float(self.inidata["waveheightfin"]["value"])
        self.wave_final_period = np.round(5 * math.sqrt(self.wave_final_height), 2)
        # Wave direction
        self.wave_direction = 90 + float(self.inidata["wavedirection"]["value"])
        # Subsidence in fluvial domain
        self.subsidence_land = float(self.inidata["subsidenceland"]["value"])
        # Subsidence in delta/marine domain
        self.subsidence_sea = float(self.inidata["subsidencesea"]["value"])
        # Sediment composition type
        self.composition = str(self.inidata["composition"]["value"])

    def load_template(self) -> None:
        """Move all template files to the output folder

         Raises
         ------
        FileNotFoundError
             If the folder in which to create the preprocessing output folder does not
             exist

        """
        if self.fpath_output.parent.is_dir():
            shutil.copytree(self.fpath_template, self.fpath_output, dirs_exist_ok=True)
        else:
            raise FileNotFoundError(
                f"Cannot create a new folder in {self.fpath_output.parent}"
            )

        self.__remove_obsolete_files()

        # Define filenames and initialize additional template data
        self.mdf_file = self.fpath_output.joinpath(f"{self.composition}.mdf")
        self.dep_file = self.fpath_output.joinpath("a.dep")
        self.wave_dep_file = self.fpath_output.joinpath("wave.dep")
        self.sdu_file = self.fpath_output.joinpath(f"{self.template_name}.sdu")

        self.nx_bathymetry, self.ny_bathymetry = get_shape_from_grd_file(
            self.fpath_output.joinpath("a.grd")
        )
        self.nx_wave, self.ny_wave = get_shape_from_grd_file(
            self.fpath_output.joinpath("wave.grd")
        )
        self.bathymetry = read_dep_file(
            self.dep_file, self.nx_bathymetry, self.ny_bathymetry
        )
        self.wave_bathymetry = read_dep_file(
            self.wave_dep_file, self.nx_wave, self.ny_wave
        )
        self.wave_grid_factor = int(np.round(self.nx_bathymetry / self.nx_wave))

    def __remove_obsolete_files(self):
        # Remove files associated with other sediment compositions
        compositions_to_remove = [
            x for x in composition_options if self.composition != x
        ]
        for composition_to_remove in compositions_to_remove:
            for file in self.fpath_output.glob(f"{composition_to_remove}*"):
                file.unlink()

        # Remove files associated with other channel widths and rename to a- or wave.dep
        # This is a temporary workaround to give the user a choice of channel width
        # until we use the bathymetry builder for full flexibility.
        channelwidths_to_remove = [
            x for x in channel_width_options if self.channel_width != x
        ]
        if self.template_name not in ("Roda", "Sobrarbe"):
            for channelwidth_to_remove in channelwidths_to_remove:
                for file in self.fpath_output.glob("*.dep"):
                    width_in_filename = file.name.split("_")[-1].split(".")[0]
                    if str(channelwidth_to_remove) + "m" == width_in_filename:
                        file.unlink()

            Path(self.fpath_output / "a.dep").unlink(missing_ok=True)
            Path(self.fpath_output / f"a_00deg_slope_{self.channel_width}m.dep").rename(
                self.fpath_output / "a.dep"
            )
            Path(self.fpath_output / "wave.dep").unlink(missing_ok=True)
            Path(
                self.fpath_output / f"wave_00deg_slope_{self.channel_width}m.dep"
            ).rename(self.fpath_output / "wave.dep")

    def set_bathymetry(self) -> None:
        """Adjust a.dep file with initial bathymetry"""
        # builder = BathymetryBuilder(
        #     self.bathymetry,
        #     coast_angle=30,
        #     channel_count=3,
        #     fluvial_width=25,
        #     fluvial_length=50,
        #     channel_separation=True,
        # )
        # bathy = builder.make_bathymetry()
        basin_bathymetry = self.bathymetry[:, self.river_length :]

        # At the seaward boundary the depth is equal, but close to the shore depth
        # isolines follow the coastline. So the further the coast extends seawards, the
        # higher the basin slope has to become to reach equal seaward boundary depth.
        bathymetry_cell_counts = np.count_nonzero(basin_bathymetry > 0, axis=1)
        bathymetry_slope_factor = (
            np.max(bathymetry_cell_counts) / bathymetry_cell_counts
        )
        dz_per_cell = (
            self.dx * np.tan(np.deg2rad(self.basin_slope)) * bathymetry_slope_factor
        )

        # Create the adjustment array and apply to the initial (zero-slope) bathymetry
        adjustment_array = np.zeros_like(basin_bathymetry)
        for i in range(self.ny_bathymetry):
            cell_count = bathymetry_cell_counts[i]
            adjustment_array[i, adjustment_array.shape[1] - cell_count :] = np.cumsum(
                np.full(cell_count, dz_per_cell[i])
            )

        adjustment_array[basin_bathymetry == self.nodata_value] = 0
        basin_bathymetry += adjustment_array

        # Adjust seaward boundary such that it has a gentle slope towards 50 m depth
        most_seaward_value = basin_bathymetry[1, -3 - self.wave_grid_factor]
        seaward_boundary_dz = (50 - most_seaward_value) / self.wave_grid_factor
        for i in range(self.wave_grid_factor):
            basin_bathymetry[:-1, -1 - self.wave_grid_factor + i] = (
                most_seaward_value + (i + 1) * seaward_boundary_dz
            )
        self.bathymetry[:, self.river_length :] = basin_bathymetry

    def set_wave_bathymetry(self) -> None:
        """Adjust wave.dep file with initial bathymetry"""
        wave_grid_river_length = int(
            np.round(self.river_length / self.wave_grid_factor)
        )
        wave_bathymetry = self.wave_bathymetry[:, wave_grid_river_length:]

        # At the seaward boundary the depth is equal, but close to the shore depth
        # isolines follow the coastline. So the further the coast extends seawards, the
        # higher the basin slope has to become to reach equal seaward boundary depth.
        wavebath_cell_counts = np.count_nonzero(wave_bathymetry > 0, axis=1)
        wavebath_slope_factor = np.max(wavebath_cell_counts) / wavebath_cell_counts
        dz_per_cell = (
            self.dx
            * self.wave_grid_factor
            * np.tan(np.deg2rad(self.basin_slope))
            * wavebath_slope_factor
        )

        # Create the adjustment array and apply to the initial (zero-slope) bathymetry
        adjustment_array = np.zeros_like(wave_bathymetry)
        for i in range(self.ny_wave):
            cell_count = wavebath_cell_counts[i]
            adjustment_array[i, adjustment_array.shape[1] - cell_count :] = np.cumsum(
                np.full(cell_count, dz_per_cell[i])
            )

        adjustment_array[wave_bathymetry == self.nodata_value] = 0
        wave_bathymetry += adjustment_array

        # Adjust seaward boundary such that it has a gentle slope towards 50 m depth
        wave_bathymetry[:-1, -2] = 50
        wave_bathymetry[:-1, -3] = (50 + wave_bathymetry[1, -3]) / 2
        self.wave_bathymetry[:, wave_grid_river_length:] = wave_bathymetry

    def set_subsidence_bathymetry(self) -> None:
        """Adjust .sdu file with subsidence information"""
        initial_subsidence_array = np.zeros_like(self.bathymetry)
        initial_subsidence_array[self.bathymetry == self.nodata_value] = (
            self.nodata_value
        )
        final_subsidence_array = np.zeros_like(initial_subsidence_array)
        final_subsidence_array[:, : self.river_length] = self.subsidence_land
        sea_length = self.nx_bathymetry - self.river_length
        dsubsidence_dx = (self.subsidence_sea - self.subsidence_land) / sea_length
        subsidence_sea_array = (
            np.cumsum(
                np.full_like(
                    final_subsidence_array[:, self.river_length :], dsubsidence_dx
                ),
                axis=1,
            )
            + self.subsidence_land
        )
        final_subsidence_array[:, self.river_length :] = subsidence_sea_array
        final_subsidence_array[self.bathymetry == self.nodata_value] = self.nodata_value
        self.initial_subsidence_array = initial_subsidence_array
        self.final_subsidence_array = final_subsidence_array

    def write_template_values(self) -> None:
        """Write template values to the respective files"""
        files2change = [
            "a.bct",
            f"{self.composition}.bcc",
            "a.bnd",
            "a.bch",
            f"{self.composition}.mdf",
            "config_d_hydro.xml",
            "a.mor",
            "wave.mdw",
            "wavecon.wave",
            f"{self.template_name}.sdu",
        ]

        lookup = TemplateLookup(
            directories=self.fpath_output,
            output_encoding="utf-8",
            encoding_errors="replace",
        )
        for file in files2change:
            completename = self.fpath_output.joinpath(file)
            template = lookup.get_template(file)
            result = template.render_unicode(**self.template_context).encode(
                "utf-8", "replace"
            )
            # result = result.replace("\r\n", "\r")
            with open(completename, "wb") as f:
                f.write(result)
                logger.info(file)

    def preprocess(self):
        logger.info("Copying template files into new folder")
        self.load_template()
        logger.info("Generating bathymetric grid")
        self.set_bathymetry()
        logger.info("Writing bathymetric grid to a.dep file")
        write_dep_file(self.dep_file, self.bathymetry)
        logger.info("Generating bathymetric grid for waves")
        self.set_wave_bathymetry()
        logger.info("Writing wave bathymetric grid to wave.dep file")
        write_dep_file(self.wave_dep_file, self.wave_bathymetry)
        logger.info("Generating subsidence grids")
        self.set_subsidence_bathymetry()
        logger.info("Writing subsidence grids to SDU file")
        edit_sdu_file(
            self.sdu_file, self.initial_subsidence_array, self.final_subsidence_array
        )
        logger.info("Inserting template values in D3D files...")
        self.write_template_values()
        logger.info("D3D input files were generated!")


if __name__ == "__main__":

    for template in [
        "River_dominated_delta",
        "GuleHorn_Neslen",
        "Roda",
        "Sobrarbe",
    ]:

        pp = PreProcess(
            rf"c:\Users\onselen\OneDrive - Stichting Deltares\Development\D3D GeoTool\gtpost\gt_templates\{template}\input.ini",
            rf"p:\11209074-002-Geotool-new-deltas\01_modelling\{template}_preprocessing_test_newbathymetry",
        )
        pp.preprocess()
