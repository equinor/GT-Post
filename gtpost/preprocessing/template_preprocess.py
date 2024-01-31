import configparser
import logging
import os

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.DEBUG)


class TemplatePreProcess:
    inifile = None
    inidata = {}
    data = {}
    dt = 1  # timestep, should be 0.5
    nx = 300  # number of grid cells in x direction
    ny = 280  # number of grid cells in y direction
    dx = 50  # grid resolution in x direction [m]
    dy = 50  # grid resolution in y direction [m]
    nodata_value = -999
    hrs = 3  # River depth at the inflow boundary
    hre = 4  # River depth at the river mouth
    number_rl = 100  # number of grid for the river, river length = 5km
    hfs = -2  # Flood-plain height at the inflow boundary
    hfe = 1  # Flood-plain height at the basin-river boundary
    tfactor = 1440  # factor to change time from days to minutes

    def __init__(self):
        pass

    def read_ini(self):
        if not hasattr(self, "inifile") or self.inifile is None:
            logger.warning("inifile not set, nothing to read")
        elif os.path.exists(self.inifile):
            p = IniParser()
            p.read(self.inifile)
            self.inidata = p.as_dict
        else:
            logger.warning('inifile "%s" not found, nothing to read' % self.inifile)

    def _set_file(self, filename, attribute="ncfile", required=True):
        file_exists = os.path.exists(filename)
        if file_exists:
            setattr(self, attribute, os.path.abspath(filename))
        elif not required:
            setattr(self, attribute, None)
            msg = 'File "%s" NOT found; %s set to None' % (filename, attribute)
            logger.warning(msg)
        else:
            msg = 'File "%s" NOT found' % filename
            logger.error(msg)
            raise SystemExit(0)

    def set_inifile(self, inifile):
        self._set_file(filename=inifile, attribute="inifile")

    def set_d3dinput(self, attribute, value):
        logger.info("setting %s to %s" % (attribute, value))
        setattr(self, attribute, value)
