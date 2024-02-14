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
from gtpost.preprocessing.template_preprocess import TemplatePreProcess
from gtpost.utils import numpy_mode

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.WARNING)

compositions = (
    "veryfine-sand",
    "medium-sand",
    "fine-sand",
    "coarse-silt",
    "coarse-sand",
)


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
    basin_slope = 0.04
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
        self.wave_initial_period = 5 * math.sqrt(self.wave_initial_height)
        # Final wave height and period
        self.wave_final_height = float(self.inidata["waveheightfin"]["value"])
        self.wave_final_period = 5 * math.sqrt(self.wave_final_height)
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

        # Remove files associated with other sediment compositions
        compositions_to_remove = [x for x in compositions if self.composition != x]
        for composition_to_remove in compositions_to_remove:
            for file in self.fpath_output.glob(f"{composition_to_remove}*"):
                file.unlink()

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

    def set_bathymetry(self) -> None:
        """Adjust a.dep file with initial bathymetry"""
        builder = BathymetryBuilder(self.bathymetry, coast_angle=45)
        bathy = builder.make_bathymetry()
        basin_bathymetry = self.bathymetry[:, self.river_length :]
        dz_per_cell = self.dx * np.tan(np.deg2rad(self.basin_slope))
        adjustment_array = np.cumsum(
            np.full_like(basin_bathymetry, dz_per_cell), axis=1
        )
        adjustment_array[basin_bathymetry == self.nodata_value] = 0
        basin_bathymetry += adjustment_array
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
        dz_per_cell = (self.dx * self.wave_grid_factor) * np.tan(
            np.deg2rad(self.basin_slope)
        )
        adjustment_array = np.cumsum(np.full_like(wave_bathymetry, dz_per_cell), axis=1)
        adjustment_array[wave_bathymetry == self.nodata_value] = 0
        wave_bathymetry += adjustment_array
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
        ]

        lookup = TemplateLookup(
            directories=self.fpath_template, encoding_errors="replace"
        )
        for file in files2change:
            completename = self.fpath_output.joinpath(file)
            template = lookup.get_template(file)
            result = template.render_unicode(**self.template_context)
            result = result.replace("\r\n", "\r")
            with open(completename, "w") as f:
                f.write(result)

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
        logger.info("Inserting template values in D3D files")
        self.write_template_values()
        logger.info("D3D input files were generated!")


# class PreProcess2(TemplatePreProcess):
#     template_dir = None
#     dest_dir = None
#     src_dir = None
#     mdf_file = None
#     clayvolcomposition = 0
#     sandvolcomposition = 0
#     test = False
#     wave = False
#     waveheight = 0.0
#     baselevel_change = 0.0
#     distal_depth = 50
#     depth_edit_range = 5

#     def __init__(self, fpath_input, fpath_output, fpath_template, inifile="input.ini"):
#         self.dest_dir = fpath_output
#         self.config_dir = fpath_input
#         self.template_root = fpath_template
#         self.set_inifile(os.path.join(fpath_input, inifile))

#     def preprocess(self):
#         logger.info("Start preprocessing: 0% done")
#         logger.info("initialize pre-processing")
#         self.read_ini()
#         # make sure inidata is in the version 0.7.0 format
#         self.inidata = revise(self.inidata)
#         self.process_ini()
#         self.src_dir = self.get_template_dir()
#         self.loadtemplate()
#         self.template_values()
#         self.render_templates()
#         self.generate_depth()
#         self.write_depth()

#     def get_template_dir(self):
#         if self.test:
#             # use testing template
#             logger.info("Using the testing template")
#             template_subdir = "testing_template"
#         else:
#             if self.waveheight == 0.0:
#                 # use basin_fill template
#                 logger.info("Using the basin fill template")
#                 template_subdir = "basin_fill"
#             elif self.waveheight > 0.0 and self.waveheight <= 2:
#                 # use basin_fill_marine_reworking template
#                 logger.info("Using the wave template")
#                 self.wave = True
#                 template_subdir = "basin_fill_marine_reworking"
#             else:
#                 msg = "no template found for test=%s and waveheight=%s" % (
#                     self.test,
#                     self.waveheight,
#                 )
#                 logger.error(msg)
#                 raise SystemExit(0)
#         return os.path.join(self.template_root, template_subdir)

#     def process_ini(self):
#         # model simulation stop time [min]
#         self.set_d3dinput(
#             "t_stop", self.tfactor * float(self.inidata["simstoptime"]["value"])
#         )
#         # output interval [min]
#         self.set_d3dinput(
#             "t_interval", self.tfactor * float(self.inidata["outputinterval"]["value"])
#         )
#         # river width [m]
#         self.set_d3dinput(
#             "river_width", int(float(self.inidata["riverwidth"]["value"]))
#         )
#         # river discharge [m^3/s]
#         self.set_d3dinput(
#             "river_discharge", float(self.inidata["riverdischarge"]["value"])
#         )
#         # basin slope
#         self.set_d3dinput("basin_slope", float(self.inidata["basinslope"]["value"]))
#         # tidal amplitude
#         self.set_d3dinput(
#             "tidalamplitude", float(self.inidata["tidalamplitude"]["value"])
#         )
#         # wave height
#         self.set_d3dinput("waveheight", float(self.inidata["waveheight"]["value"]))
#         # if it still is the slider structure, then read v_clay and v_sand
#         # or else it will be a pre-set structure, then read the predefined label
#         if (
#             "clayvolcomposition" in self.inidata
#             and "value" in self.inidata["clayvolcomposition"]
#         ):
#             # clay volume composition
#             self.set_d3dinput(
#                 "clayvolcomposition",
#                 0.01 * float(self.inidata["clayvolcomposition"]["value"]),
#             )
#             # sand volume composition
#             self.set_d3dinput("sandvolcomposition", 1.0 - self.clayvolcomposition)
#         # composition
#         self.set_d3dinput("composition", str(self.inidata["composition"]["value"]))
#         # time step
#         if "dt" in self.inidata and "value" in self.inidata["dt"]:
#             self.set_d3dinput("dt", float(self.inidata["dt"]["value"]))
#         else:
#             # if there is no dt, dt=0.5
#             self.set_d3dinput("dt", 0.5)
#         # use testing template?
#         if (
#             "test" in self.inidata
#             and "value" in self.inidata["test"]
#             and self.inidata["test"]["value"] == "test"
#         ):
#             self.set_d3dinput("test", True)
#         # base level change
#         if "baselevel" in self.inidata and "value" in self.inidata["baselevel"]:
#             self.set_d3dinput(
#                 "baselevel_change", float(self.inidata["baselevel"]["value"])
#             )

#     def loadtemplate(self):
#         # copy delft3d sed-independent input files from a certain template
#         # into the working directory (or temporary directory)
#         if os.path.isdir(self.dest_dir):
#             # copy individual files
#             logger.info("copy contents of %s to %s" % (self.src_dir, self.dest_dir))
#             src_files = os.listdir(self.src_dir)
#             for file_name in src_files:
#                 full_file_name = os.path.join(self.src_dir, file_name)
#                 if os.path.isfile(full_file_name):
#                     shutil.copy(full_file_name, self.dest_dir)
#         else:
#             # copy parent directory including its files
#             shutil.copytree(self.src_dir, self.dest_dir)
#         # find the mdf file
#         seq = (self.composition, "mdf")
#         s = "."
#         self.mdf_file = s.join(seq)

#     def template_values(self):
#         # replace the model stop time, simulation output interval
#         # and river discharge in the relevant files
#         # f or now Tstop and etc are hard coded values, and they should be
#         # user input parameters
#         # Pre-defined variables to locate the river
#         number_rw = self.river_width / self.dx  # number of cells for the river
#         river_y = self.ny / 2 + 1  # river locates in the middle
#         river_l = river_y - number_rw / 2  # river location
#         river_u = river_y + number_rw / 2  # river location
#         with open(os.path.join(self.dest_dir, self.mdf_file)) as fobj:
#             for line in fobj.readlines():
#                 # read lines until Tstart is found
#                 if "Tstart" in line:
#                     t_ini = float(line.split("=")[-1])  # retreive Tini value
#         # retrieve morstt from the mor file
#         with open(os.path.join(self.dest_dir, "a.mor")) as fobj:
#             # initialize morstt as zero
#             morstt = 0
#             logger.info("reading Tstart from %s" % self.dest_dir)
#             for line in fobj.readlines():
#                 # read lines until MorStt is found
#                 if "MorStt" in line:
#                     morstt = float(line.split()[2])  # retrieve MorStt value
#                     logger.info("MorStt of %s found" % morstt)
#         # calculate the start time for output in minutes
#         tstart = t_ini + morstt
#         # calculate morfac and tstop based on the wave height
#         self.morfac = 30
#         # if self.waveheight <= 1.0:
#         if self.waveheight <= 2.0:
#             self.morfac = 30
#             tstop = self.t_stop
#             t_interval = self.t_interval
#         # elif self.waveheight <= 2.0 and self.waveheight > 1.0:
#         #     self.morfac = 15
#         #     tstop = 2*self.t_stop
#         #     t_interval = self.t_interval * 2
#         else:
#             msg = "wave height %s outside valid range" % self.waveheight
#             logger.error(msg)
#             raise SystemExit(0)
#         # calculate the model stop time including the morstt in min
#         tstop = tstop + t_ini + morstt
#         # calculate the base level degree
#         degree_all = 90
#         # t_stop is in min. and the degree is in per hour
#         min2hr = 60
#         baselevel_degree = degree_all / self.t_stop * min2hr
#         #  calculate absolute base-level change based on the percentage
#         # depth at the offshore end of the basin
#         hbe = self.hre + math.tan(math.radians(self.basin_slope)) * self.dx * (
#             self.nx - self.number_rl
#         )
#         #  the base-level change is in percentage
#         baselevel_value = abs(0.01 * self.baselevel_change * hbe)
#         #  set the phase of the base level and start_level
#         start_level = 0
#         #  if base level rise:
#         if self.baselevel_change >= 0:
#             baselevel_phase = 90
#         #  if base level fall
#         else:
#             baselevel_phase = -90
#         # calculate wave period based on wave height
#         # breaking theroy and dispersion relation
#         # assumption: shallow water and wave steepness of 0.05
#         # Equation: wave period = (wave amplitude / wave steepness) / sqrt(g*water depth)
#         # Wave steepness: calculated from wave height based  on "Measurements of Wind, Wave and Currents at the
#         # Offshore Wind Farm Egmond aan Zee" by  J.W. Wagenaar and P.J. Eecen, 2009
#         # and calibrated such that wave steepness falls betwen 2s and 4s at depth = 9m
#         wavesteepness = (self.waveheight * 0.01842) + 0.00316
#         gravity = 9.81
#         self.waveperiod = (self.waveheight / wavesteepness) / math.sqrt((gravity * hbe))
#         if self.waveperiod < 1:
#             self.waveperiod = 1
#         print(self.waveperiod)

#         self.context = {
#             "t_stop": tstop,
#             "t_interval": t_interval,
#             "river_discharge": self.river_discharge,
#             "river_l": river_l,
#             "river_u": river_u,
#             "T_amplitude": self.tidalamplitude,
#             "t_dt": self.dt,
#             "t_start": tstart,
#             "clayvolcomposition": self.clayvolcomposition,
#             "sandvolcomposition": self.sandvolcomposition,
#             "composition": self.composition,
#             "waveheight": self.waveheight,
#             "morfac": self.morfac,
#             "baselevel_change": baselevel_value,
#             "baselevel_degree": baselevel_degree,
#             "baselevel_phase": baselevel_phase,
#             "startlevel": start_level,
#             "waveperiod": self.waveperiod,
#         }

#     def render_templates(self):
#         logger.info("Start rendering template")
#         files2change = [
#             "a.bct",
#             "a.bcc",
#             "a.bnd",
#             "a.bch",
#             "morlyr.ini",
#             self.mdf_file,
#             "config_d_hydro.xml",
#             "a.mor",
#         ]
#         if self.wave:
#             files2change.append("wave.mdw")
#         mylookup = TemplateLookup(directories=self.src_dir, encoding_errors="replace")
#         for fname in files2change:
#             completename = os.path.join(self.dest_dir, fname)
#             mytemplate = mylookup.get_template(fname)
#             a = mytemplate.render_unicode(**self.context)
#             logger.info("writing %s" % completename)
#             with open(completename, "w") as fobj:
#                 fobj.write(a)
#         logger.info("Finish rendering template")
#         files = os.listdir(self.dest_dir)
#         for file_name in files:
#             if file_name.endswith(".mdf"):
#                 if not file_name.startswith(self.composition):
#                     complete_name = os.path.join(self.dest_dir, file_name)
#                     os.remove(complete_name)
#             if file_name.endswith(".sed"):
#                 if not file_name.startswith(self.composition):
#                     complete_name = os.path.join(self.dest_dir, file_name)
#                     os.remove(complete_name)

#     def generate_depth(self):
#         # generate depth file according to the user-input
#         # In order to build the bathymetry, we need several parameters
#         # Not all of them are user-defined at this stage
#         # Users are only allowed to change river width, and basin slope
#         # Here we first define these hard-coded parameters
#         # for template 1 bathymetry
#         # List of pre-defined parameters
#         logger.info("Start generating depth file")
#         river_y = self.ny / 2 + 1  # river always locates in the middle
#         flood_yu = self.ny / 2 + 20  # upper limit of the floodplain
#         flood_yl = self.ny / 2 - 20  # lower limit of the floodplain
#         # Other parameters
#         number_rw = self.river_width / self.dx  # number of cells for the river width
#         hbe = self.hre + math.tan(math.radians(self.basin_slope)) * self.dx * (
#             self.nx - self.number_rl
#         )  # depth at the offshore end of the basin
#         # Derive bathymetry for river, basin and floodplain
#         hr = np.linspace(self.hrs, self.hre, self.number_rl)  # bathymetry for river
#         hb = np.linspace(
#             self.hre, hbe, self.nx - self.number_rl + 1
#         )  # bathymetry for basin
#         hf = np.linspace(
#             self.hfs, self.hfe, self.number_rl
#         )  # bathymetry for floodplain
#         # Generate bathymetry
#         # create an empty array with the right dimension, filled with the no data value
#         new_dep = np.ones((self.ny + 2, self.nx + 2)) * self.nodata_value
#         for i in range(0, self.ny + 1):
#             new_dep[i, self.number_rl : self.nx + 1] = hb
#         for i in range(
#             int(river_y - number_rw / 2), int(river_y + number_rw / 2)
#         ):  # Comment Erik: float objects in range function changed to integers
#             new_dep[i, 0 : self.number_rl] = hr
#         for i in range(
#             int(flood_yl), int(river_y - number_rw / 2)
#         ):  # Comment Erik: float objects in range function changed to integers
#             new_dep[i, 0 : self.number_rl] = hf
#         for i in range(
#             int(river_y + number_rw / 2), int(flood_yu)
#         ):  # Comment Erik: float objects in range function changed to integers
#             new_dep[i, 0 : self.number_rl] = hf
#         dist_depth = np.max(
#             (new_dep[int(river_y), -2], self.distal_depth)
#         )  # Comment Erik: float object in index changed to integer
#         prox_depth = new_dep[
#             int(river_y), -(self.depth_edit_range + 1)
#         ]  # Comment Erik: float object in index changed to integer
#         for i in range(self.depth_edit_range, 1, -1):
#             new_dep[:, -i] = new_dep[int(river_y), -(i + 1)] + (
#                 (dist_depth - prox_depth) / (self.depth_edit_range - 1)
#             )  # Comment Erik: float object in index changed to integer
#         new_dep[-1, :] = self.nodata_value
#         new_dep[:, -1] = self.nodata_value
#         self.dep = new_dep

#     def write_depth(self):
#         # save bathymetry to dep file
#         logger.info("Start writing depth file")
#         dep_file = os.path.join(self.dest_dir, "a.dep")
#         logger.info("writing %s" % dep_file)
#         np.savetxt(dep_file, self.dep)
#         logger.info("Finish writing depth file")
#         logger.info("Finish preprocessing: 100% done")


# def main(
#     fpath_input="/data/input",
#     fpath_output="/data/output",
#     fpath_template="/data/svn/template",
# ):
#     fpath_template = Path(__file__).parents[2].joinpath("gt_templates")
#     PP = PreProcess(fpath_input, fpath_output, fpath_template)
#     PP.preprocess()


if __name__ == "__main__":

    for template in ["GuleHorn_Neslen", "River_dominated_delta", "Roda", "Sobrarbe"]:

        pp = PreProcess(
            rf"c:\Users\onselen\OneDrive - Stichting Deltares\Development\D3D GeoTool\gtpost\gt_templates\{template}\input.ini",
            rf"p:\11209074-002-Geotool-new-deltas\01_modelling\{template}_preprocessing_test",
        )
        pp.preprocess()
