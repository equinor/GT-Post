import configparser
import logging
import math
import os
import shutil

import numpy as np
from mako.lookup import TemplateLookup
from skimage.draw import polygon

# import matplotlib.pyplot as plt

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.DEBUG)


class Bathymetry:
    dep = None
    nx = 300  # number of grid cells in x direction
    ny = 280  # number of grid cells in y direction
    dx = 50  # grid resolution in x direction [m]
    dy = 50  # grid resolution in y direction [m]
    river_polygon = None
    river_length = 5000
    river_width = 300
    river_depth_mouth = 6
    river_depth_upstream = 3
    river_slope = float(river_depth_mouth - river_depth_upstream) / float(river_length)
    floodplain_polygon = None
    floodplain_width = 200
    basin_polygon = None
    basin_length = nx * dx - river_length
    basin_slope = 0.06
    basin_depth_offshore = basin_length * basin_slope + river_depth_mouth
    fill_value = -999

    def __init__(self):
        pass

    def make_dep(self):
        self.dep_init()
        self.set_basin_polygon()
        self.dep_basin()
        self.set_river_polygon()
        self.dep_river()

    def dep_init(self):
        # create a masked array
        self.dep = np.ma.masked_array(
            np.ones((self.nx, self.ny)) * self.fill_value, fill_value=self.fill_value
        )

    def dep_basin(self):
        cells = self.basin_length / self.dx
        logger.debug("basin cells: %s" % cells)
        # cross-shore bathymetry for basin
        basin_profile = np.linspace(
            self.river_depth_mouth, self.basin_depth_offshore, cells
        )
        logger.info("basin_profile shape %s" % basin_profile.shape)
        # repeat the basin profile to fit the polygon
        basin_dep = np.repeat(basin_profile, self.ny)
        logger.debug("basin_dep shape: %s" % basin_dep.shape)
        # get the polygon indices
        rr, cc = polygon(*self.basin_polygon)
        logger.debug("rr shape: %s" % rr.shape)
        logger.debug("rr max: %s" % rr.max())
        # update the depth in the polygon
        self.dep[rr, cc] = basin_dep

    def dep_river(self):
        cells = self.river_length / self.dx
        river_profile = np.linspace(
            self.river_depth_upstream, self.river_depth_mouth, cells
        )
        river_dep = np.repeat(river_profile, self.river_width / self.dx)
        # get the polygon indices
        rr, cc = polygon(*self.river_polygon)
        logger.debug("rr shape: %s" % rr.shape)
        logger.debug("rr max: %s" % rr.max())
        # update the depth in the polygon
        self.dep[rr, cc] = river_dep

    def set_basin_polygon(self):
        cells = self.basin_length / self.dx
        x = np.array(
            [self.nx - cells, self.nx, self.nx, self.nx - cells, self.nx - cells]
        )
        y = np.array([0, 0, self.ny, self.ny, 0])
        self.basin_polygon = (x, y)

    def set_river_polygon(self):
        cells = self.river_width / self.dy
        yy = (self.ny + cells * np.array([-1, 1])) / 2
        logger.debug("yy: %s" % yy)
        cells = self.river_length / self.dx
        x = np.array([0, cells, cells, 0, 0])
        y = np.array([yy[0], yy[0], yy[1], yy[1], yy[0]])
        self.river_polygon = (x, y)

    # def plot(self, filename='dep.png'):
    #     fig, ax = plt.subplots(nrows=1, ncols=1)
    #     ax.pcolor(-self.dep)
    #     fig.savefig(filename)
    #     plt.close(fig)


class PreProcessing:
    data = {}
    dt = 1  # timestep, should be 0.5
    nx = 300  # number of grid cells in x direction
    ny = 280  # number of grid cells in y direction
    dx = 50  # grid resolution in x direction [m]
    dy = 50  # grid resolution in y direction [m]
    nodata_value = -999
    hrs = 3  # River depth at the inflow boundary
    hre = 6  # River depth at the river mouth
    number_rl = 100  # number of grid for the river, river length = 5km
    hfs = -2  # Flood-plain height at the inflow boundary
    hfe = 1  # Flood-plain height at the basin-river boundary
    tfactor = 1440  # factor to change time from days to minutes

    def __init__(self, src_dir, dest_dir, config_dir):
        logger.info("Start preprocessing: 0% done")
        logger.info("initialize pre-processing")
        self.src_dir = src_dir
        self.dest_dir = dest_dir
        self.config_dir = config_dir
        delft3d_input = self.read_config()
        for key in delft3d_input:
            logger.info("setting %s to %s" % (key, delft3d_input[key]))
            setattr(self, key, delft3d_input[key])

    def read_config(self):
        config = configparser.ConfigParser()
        inifile = os.path.join(self.config_dir, "input.ini")
        logger.info("Start reading %s" % inifile)
        config.read(inifile)
        delft3d_input = {}
        # for the model simulation stop time, half day is added in order to account for
        # the morphological spin up
        delft3d_input["t_stop"] = self.tfactor * (
            float(config.get("simstoptime", "value"))
        )  # model simulation stop time [min]
        delft3d_input["t_interval"] = self.tfactor * float(
            config.get("outputinterval", "value")
        )  # output interval [min]
        delft3d_input["river_width"] = int(
            float(config.get("riverwidth", "value"))
        )  # river width [m]
        delft3d_input["river_discharge"] = float(
            config.get("riverdischarge", "value")
        )  # river discharge [m^3/s]
        delft3d_input["basin_slope"] = float(
            config.get("basinslope", "value")
        )  # basin slope
        delft3d_input["tidalamplitude"] = float(
            config.get("tidalamplitude", "value")
        )  # tidal amplitude
        # if it still is the slider structure, then read v_clay and v_sand
        # or else it will be a pre-set structure, then read the predefined label
        if config.has_option("clayvolcomposition", "value"):
            delft3d_input["clayvolcomposition"] = 0.01 * float(
                config.get("clayvolcomposition", "value")
            )  # clay volume composition
            delft3d_input["sandvolcomposition"] = (
                1 - delft3d_input["clayvolcomposition"]
            )
        else:
            # if the key work clayvolcomposition is not found, then set them to zero
            # which will not have any effect on the preprocessing
            delft3d_input["clayvolcomposition"] = 0  # clay volume composition
            delft3d_input["sandvolcomposition"] = 0
        if config.has_option("composition", "value"):
            delft3d_input["composition"] = str(config.get("composition", "value"))
        if config.has_option("dt", "value"):
            delft3d_input["dt"] = float(config.get("dt", "value"))  # time step
        else:
            delft3d_input["dt"] = 0.5  # if there is no dt, dt=1
        logger.info("Finish reading %s" % inifile)
        return delft3d_input

    def loadtemplate(self, sed_class):
        # copy delft3d sed-independent input files from a certain template
        # into the working directory (or temporary directory)
        if os.path.isdir(self.dest_dir):
            # copy individual files
            logger.info("copy contents of %s to %s" % (self.src_dir, self.dest_dir))
            src_files = os.listdir(self.src_dir)
            for file_name in src_files:
                full_file_name = os.path.join(self.src_dir, file_name)
                if os.path.isfile(full_file_name):
                    shutil.copy(full_file_name, self.dest_dir)
        else:
            # copy parent directory including its files
            shutil.copytree(self.src_dir, self.dest_dir)
        # find the mdf file
        seq = (sed_class, "mdf")
        s = "."
        return s.join(seq)

    def template_values(self, fname):
        # replace the model stop time, simulation output interval
        # and river discharge in the relevant files
        # for now Tstop and etc are hard coded values, and they should be
        # user input parameters
        # Pre-defined variables to locate the river
        number_rw = self.river_width / self.dx  # number of cells for the river
        river_y = self.ny / 2 + 1  # river locates in the middle
        river_l = river_y - number_rw / 2  # river location
        river_u = river_y + number_rw / 2  # river location
        with open(os.path.join(self.dest_dir, fname)) as fobj:
            for line in fobj.readlines():
                # read lines until Tstart is found
                if "Tstart" in line:
                    t_ini = float(line.split("=")[-1])  # retreive Tini value
        # retrieve morstt from the mor file
        with open(os.path.join(self.dest_dir, "a.mor")) as fobj:
            # initialize morstt as zero
            morstt = 0
            logger.info("reading Tstart from %s" % self.dest_dir)
            for line in fobj.readlines():
                # read lines until MorStt is found
                if "MorStt" in line:
                    morstt = float(line.split()[2])  # retrieve MorStt value
                    logger.info("MorStt of %s found" % morstt)
        # calculate the start time for output in minutes
        tstart = t_ini + morstt
        # calculate the model stop time including the morstt in min
        tstop = self.t_stop + t_ini + morstt
        context = {
            "t_stop": tstop,
            "t_interval": self.t_interval,
            "river_discharge": self.river_discharge,
            "river_l": river_l,
            "river_u": river_u,
            "T_amplitude": self.tidalamplitude,
            "t_dt": self.dt,
            "t_start": tstart,
            "clayvolcomposition": self.clayvolcomposition,
            "sandvolcomposition": self.sandvolcomposition,
            "composition": self.composition,
        }
        return context

    def render_templates(self, context, fname, sed_class):
        logger.info("Start rendering template")
        files2change = (
            "a.bct",
            "a.bcc",
            "a.bnd",
            "a.bch",
            "morlyr.ini",
            fname,
            "config_d_hydro.xml",
        )
        mylookup = TemplateLookup(directories=self.src_dir, encoding_errors="replace")
        for fname in files2change:
            completename = os.path.join(self.dest_dir, fname)
            mytemplate = mylookup.get_template(fname)
            a = mytemplate.render_unicode(**context)
            logger.info("writing %s" % completename)
            with open(completename, "w") as fobj:
                fobj.write(a)
        logger.info("Finish rendering template")
        files = os.listdir(self.dest_dir)
        for file_name in files:
            if file_name.endswith(".mdf"):
                if not file_name.startswith(sed_class):
                    complete_name = os.path.join(self.dest_dir, file_name)
                    os.remove(complete_name)
            if file_name.endswith(".sed"):
                if not file_name.startswith(sed_class):
                    complete_name = os.path.join(self.dest_dir, file_name)
                    os.remove(complete_name)

    def generate_depth(self):
        # generate depth file according to the user-input
        # In order to build the bathymetry, we need several parameters
        # Not all of them are user-defined at this stage
        # Users are only allowed to change river width, and basin slope
        # Here we first define these hard-coded parameters
        # for template 1 bathymetry
        # List of pre-defined parameters
        logger.info("Start generating depth file")
        river_y = self.ny / 2 + 1  # river always locates in the middle
        flood_yu = self.ny / 2 + 20  # upper limit of the floodplain
        flood_yl = self.ny / 2 - 20  # lower limit of the floodplain
        # Other parameters
        number_rw = self.river_width / self.dx  # number of cells for the river width
        hbe = self.hre + math.tan(math.radians(self.basin_slope)) * self.dx * (
            self.nx - self.number_rl
        )  # depth at the offshore end of the basin
        # Derive bathymetry for river, basin and floodplain
        hr = np.linspace(self.hrs, self.hre, self.number_rl)  # bathymetry for river
        hb = np.linspace(
            self.hre, hbe, self.nx - self.number_rl + 1
        )  # bathymetry for basin
        hf = np.linspace(
            self.hfs, self.hfe, self.number_rl
        )  # bathymetry for floodplain
        # Generate bathymetry
        # create an empty array with the right dimension, filled with the no data value
        new_dep = np.ones((self.ny + 2, self.nx + 2)) * self.nodata_value
        for i in range(0, self.ny + 1):
            new_dep[i, self.number_rl : self.nx + 1] = hb
        for i in range(river_y - number_rw / 2, river_y + number_rw / 2):
            new_dep[i, 0 : self.number_rl] = hr
        for i in range(flood_yl, river_y - number_rw / 2):
            new_dep[i, 0 : self.number_rl] = hf
        for i in range(river_y + number_rw / 2, flood_yu):
            new_dep[i, 0 : self.number_rl] = hf
        new_dep[-1, :] = self.nodata_value
        new_dep[:, -1] = self.nodata_value
        return new_dep
        logger.info("Finish generating depth file")

    def write_depth(self, dep):
        # save bathymetry to dep file
        logger.info("Start writing depth file")
        dep_file = os.path.join(self.dest_dir, "a.dep")
        logger.info("writing %s" % dep_file)
        np.savetxt(dep_file, dep)
        logger.info("Finish writing depth file")
        logger.info("Finish preprocessing: 100% done")


if __name__ == "__main__":
    configdir = os.path.join("/", "data", "input")
    inifile = os.path.join(configdir, "input.ini")
    logger.info("Start reading %s" % inifile)
    config = configparser.ConfigParser()
    config.read(inifile)
    # according to the ini file, select the right template directory
    if config.has_option("template", "value"):
        template = str(
            config.get("template", "value")
        )  # get the template value from the input.ini file
        if template.endswith("Basin fill"):
            logger.info("Using the basin fill template")
            src = os.path.join("/", "data", "svn", "template", "basin_fill")
        if "marine" in template:
            logger.info("Using the basin marine template")
            src = os.path.join(
                "/", "data", "svn", "template", "basin_fill_marine_reworking"
            )
        if "Testing" in template:
            logger.info("Using testing template")
            src = os.path.join("/", "data", "svn", "template", "testing_template")
    else:
        src = os.path.join("/", "data", "svn", "template", "basin_fill")
    if config.has_option("composition", "value"):
        sed = str(
            config.get("composition", "value")
        )  # ge the template value from the input.ini file
    destination = os.path.join("/", "data", "output")
    logger.info("use user-defined input")
    P = PreProcessing(src_dir=src, dest_dir=destination, config_dir=configdir)
    fname = P.loadtemplate(sed_class=sed)
    context = P.template_values(fname)
    P.render_templates(context, fname, sed_class=sed)
    dep = P.generate_depth()
    P.write_depth(dep)
