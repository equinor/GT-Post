__author__ = 'Liang'

import os
import unittest
import preprocessing
import preprocess
from template_preprocess import IniParser
from test_preprocess_helper import PreProcessHelper
import numpy as np
import math
import ConfigParser
import random
import glob
import copy


def write_ini(inidata, inifile):
    with open(inifile, 'wb') as configfile:
        config = ConfigParser.RawConfigParser()
        for section, contents in inidata.items():
            config.add_section(section)
            for key, val in contents.items():
                config.set(section, key, val)
        config.write(configfile)


def empty_dir(path, pattern='*', exclude=('.ini',)):
    for filename in glob.glob(os.path.join(path, pattern)):
        if os.path.splitext(filename)[-1] not in exclude:
            os.remove(filename)


class PreProcessTests(unittest.TestCase):
    template_dir = os.path.join('/', 'data', 'svn', 'template')
    src = os.path.join(template_dir, 'basin_fill')
    destination = os.path.join('/', 'data', 'output')
    config_dir = os.path.join('/', 'data', 'output')

    tfactor = 1440  # factor to change time from days to minutes
    tstop = random.randint(30, 90)  # days
    tint = random.randint(1, 3)  # days
    q = random.randint(200, 2000)  # m3/s
    r_width = 100*random.randint(1, 3)  # m
    b_slope = random.uniform(0.01, 0.1)  # degrees
    t_a = random.randint(1, 4)
    clayvolcomposition = random.randint(1, 100)
    sandvolcomposition = 100-clayvolcomposition
    composition = 'medium-sand'
    waveheight = random.randint(0, 2)
    # find tstart value from the mdf file
    fname = '%s.mdf' % composition
    with open(os.path.join(src, fname)) as fobj:
        for line in fobj.readlines():
            # read lines until Tstart is found
            if 'Tstart' in line:
                tstart = float(line.split('=')[-1])
    with open(os.path.join(src, 'a.mor')) as fobj:
        for line in fobj.readlines():
            # read lines until Tstart is found
            if 'MorStt' in line:
                tmp = line.split('=')[-1]
                morstt = float(tmp.strip().split(' ')[0])
    inifile = os.path.join(config_dir, 'input2.ini')
    with open(inifile, 'wb') as configfile:
        config = ConfigParser.RawConfigParser()
        config.add_section('simstoptime')
        config.set('simstoptime', 'value', tstop)
        config.add_section('outputinterval')
        config.set('outputinterval', 'value', tint)
        config.add_section('riverwidth')
        config.set('riverwidth', 'value', r_width)
        config.add_section('riverdischarge')
        config.set('riverdischarge', 'value', q)
        config.add_section('basinslope')
        config.set('basinslope', 'value', b_slope)
        config.add_section('tidalamplitude')
        config.set('tidalamplitude', 'value', t_a)
        config.add_section('clayvolcomposition')
        config.set('clayvolcomposition', 'value', clayvolcomposition)
        config.add_section('sandvolcomposition')
        config.set('sandvolcomposition', 'value', sandvolcomposition)
        config.add_section('composition')
        config.set('composition', 'value', composition)
        config.add_section('waveheight')
        config.set('waveheight', 'value', waveheight)
        config.write(configfile)
    p = IniParser()
    p.read(inifile)
    inidata = p.as_dict()

    def setUp(self):
        self.PreProcess = preprocess.PreProcess()

    def test_preprocess(self):

        PH = PreProcessHelper()

        # test waveheight
        PP = preprocess.PreProcess()
        PP.preprocess()
        PP.read_ini = lambda *args: None
        for waveheight in (-1, 0, 1, 2, 3):
            PP.inidata['waveheight'] = {'value': waveheight}
            if waveheight > 2 or waveheight < 0:
                with self.assertRaises(SystemExit):
                    PP.preprocess()
            else:
                PP.preprocess()
                if waveheight == 0:
                    wave_files = glob.glob(os.path.join(self.destination, 'wave.*'))
                    self.assertEqual(len(wave_files), 0)
                else:
                    mdw = PH.getmdw()
                    self.assertEqual(mdw['waveheight'], waveheight)
            empty_dir(self.destination)

        for waveheight in (0, 1):
            # test all rendered variables both for waveheight=0 (basin fill template) and waveheight=1 (marine reworking template)

            # test t_stop
            PP = preprocess.PreProcess()
            PP.preprocess()
            PP.read_ini = lambda *args: None
            for t_stop in (30, 60, 120):
                PP.inidata['simstoptime'] = {'value': t_stop}
                PP.inidata['waveheight'] = {'value': waveheight}
                PP.preprocess()
                self.assertEqual(PP.inidata['simstoptime']['value'], t_stop)
                # mdf
                mdf = PH.getmdf()
                duration = float(mdf['t_stop'][0]) / PP.tfactor - float(mdf['t_start'][0]) / PP.tfactor
                self.assertEqual(duration, t_stop)
                # bcc
                bcc = PH.getbcc()
                self.assertEqual(bcc['t_stop'][0], mdf['t_stop'][0])
                # bct
                bct = PH.getbct()
                self.assertEqual(bct['t_stop'], mdf['t_stop'][0])
                empty_dir(self.destination)

            # test t_interval
            PP = preprocess.PreProcess()
            PP.preprocess()
            PP.read_ini = lambda *args: None
            for t_interval in (.5, 1, 5, 10.):
                PP.inidata['outputinterval'] = {'value': t_interval}
                PP.inidata['waveheight'] = {'value': waveheight}
                PP.preprocess()
                self.assertEqual(PP.inidata['outputinterval']['value'], t_interval)
                # mdf
                mdf = PH.getmdf()
                self.assertEqual(float(mdf['t_interval'][0]) / PP.tfactor, t_interval)
                empty_dir(self.destination)

            # test river_width
            PP = preprocess.PreProcess()
            PP.preprocess()
            PP.read_ini = lambda *args: None
            for river_width in (200, 400, 500, ):
                PP.inidata['riverwidth'] = {'value': river_width}
                PP.inidata['waveheight'] = {'value': waveheight}
                # get the river width from the bnd file
                PP.preprocess()
                bnd = PH.getbnd()
                grid_resolution = 50
                riverwidth = grid_resolution*(float(bnd['River_u']-bnd['River_l']))
                self.assertEqual(riverwidth, river_width)
                #self.assertEqual(PP.inidata['riverwidth']['value'], river_width)
                # TODO: retrieve river width from dep file
                # PH.getdep()
                empty_dir(self.destination)

            # test river_discharge
            PP = preprocess.PreProcess()
            PP.preprocess()
            PP.read_ini = lambda *args: None
            for river_discharge in (0, 100, 500., 1000, 2000):
                PP.inidata['riverdischarge'] = {'value': river_discharge}
                PP.inidata['waveheight'] = {'value': waveheight}
                PP.preprocess()
                self.assertEqual(PP.inidata['riverdischarge']['value'], river_discharge)
                # bct
                bct = PH.getbct()
                print(bct)
                self.assertEqual(float(bct['river_discharge'][0]), river_discharge)
                empty_dir(self.destination)

            # test basin_slope
            PP = preprocess.PreProcess()
            PP.preprocess()
            PP.read_ini = lambda *args: None
            for basin_slope in (0.01, 0.05):
                PP.inidata['basinslope'] = {'value': basin_slope}
                PP.inidata['waveheight'] = {'value': waveheight}
                PP.preprocess()
                self.assertEqual(PP.inidata['basinslope']['value'], basin_slope)
                dep = PH.getdep()
                depth_basin_end = dep[-2, -2]
                depth_basin_start = 4
                basin_length = 50*200
                basinslope = math.degrees(math.atan2(depth_basin_end - depth_basin_start, basin_length))
                self.assertAlmostEqual(basinslope, basin_slope)
                empty_dir(self.destination)

            # test composition
            PP = preprocess.PreProcess()
            PP.preprocess()
            PP.read_ini = lambda *args: None
            for composition in ('fine-sand', 'medium-sand', 'coarse-sand', 'veryfine-sand', 'coarse-silt'):
                PP.inidata['composition'] = {'value': composition}
                PP.inidata['waveheight'] = {'value': waveheight}
                PP.preprocess()
                self.assertEqual(PP.inidata['composition']['value'], composition)
                # mdf
                mdf = glob.glob(os.path.join(PP.dest_dir, '*.mdf'))
                self.assertEqual(len(mdf), 1)
                self.assertIn(composition, mdf[0])
                # sed
                sed = glob.glob(os.path.join(PP.dest_dir, '*.sed'))
                self.assertEqual(len(sed), 1)
                self.assertIn(composition, sed[0])
                empty_dir(self.destination)

            # test dt
            PP = preprocess.PreProcess()
            PP.preprocess()
            PP.read_ini = lambda *args: None
            for dt in (0.5, 1, 2.):
                PP.inidata['dt'] = {'value': dt}
                PP.inidata['waveheight'] = {'value': waveheight}
                PP.preprocess()
                self.assertEqual(PP.inidata['dt']['value'], dt)
                # mdf
                mdf = PH.getmdf()
                self.assertEqual(float(mdf['t_dt']), dt)
                empty_dir(self.destination)

            # test baselevel
            PP = preprocess.PreProcess()
            PP.preprocess()
            PP.read_ini = lambda *args: None
            for baselevel in (-0.5, 0, 0.5):
                PP.inidata['baselevel'] = {'value': baselevel}
                PP.inidata['waveheight'] = {'value': waveheight}
                PP.preprocess()
                self.assertEqual(PP.inidata['baselevel']['value'], baselevel)
                # bch
                bch = PH.getbch()
                self.assertEqual(bch['baselevel_phase'][0], 90)
                baselevel_degree = 90./float(PP.inidata['simstoptime']['value'])/PP.tfactor * 60.
                self.assertEqual(bch['baselevel_degree'], baselevel_degree)
                empty_dir(self.destination)


    def test_revise(self):
        self.PreProcess.read_ini()
        inidata_orig = self.PreProcess.inidata.copy()

        inidata_templ = inidata_orig.copy()
        inidata_templ['template'] = dict(value='Basin fill')
        inidata_rev = preprocess.revise(inidata_templ)
        self.assertFalse('template' in inidata_rev)
        self.assertTrue('test' in inidata_rev)

    def test_get_template_dir(self):
        PP = preprocess.PreProcess()
        PP.config_dir = os.path.dirname(self.inifile)
        PP.set_inifile(self.inifile)
        PP.preprocess()

        # by default, the test template should NOT be used
        if PP.waveheight == 0:
            # basin_fill template in case of no waves
            self.assertEqual(PP.get_template_dir(), '/data/svn/template/basin_fill')
        else:
            # basin_fill_marine_reworking otherwise
            self.assertEqual(PP.get_template_dir(), '/data/svn/template/basin_fill_marine_reworking')

        # use testing_template if test attribute is True
        PP.test = True
        self.assertEqual(PP.get_template_dir(), '/data/svn/template/testing_template')
        empty_dir(self.destination)

    def test_process_ini(self):
        PP = preprocess.PreProcess()
        PP.config_dir = os.path.dirname(self.inifile)
        PP.set_inifile(self.inifile)
        PP.read_ini()
        # make sure inidata is in the version 0.7.0 format
        PP.inidata = preprocess.revise(PP.inidata)
        PP.process_ini()

        self.assertEqual(PP.t_stop, self.tstop * PP.tfactor)
        self.assertEqual(PP.t_interval, self.tint * PP.tfactor)
        self.assertEqual(PP.river_width, self.r_width)
        self.assertEqual(PP.river_discharge, self.q)
        self.assertEqual(PP.tidalamplitude, self.t_a)
        self.assertEqual(PP.waveheight, self.waveheight)
        self.assertAlmostEqual(PP.clayvolcomposition, self.clayvolcomposition / 100., places=2)
        self.assertAlmostEqual(PP.sandvolcomposition, self.sandvolcomposition / 100., places=2)
        self.assertEqual(PP.composition, self.composition)
        self.assertEqual(PP.dt, 0.5)
        self.assertEqual(PP.test, False)

    def test_loadtemplate(self):
        PP = preprocess.PreProcess()
        PP.config_dir = os.path.dirname(self.inifile)
        PP.set_inifile(self.inifile)
        PP.preprocess()
        self.assertEqual(PP.mdf_file, '%s.mdf' % self.composition)
        empty_dir(self.destination)

    def test_template_values(self):
        PP = preprocess.PreProcess()
        PP.config_dir = os.path.dirname(self.inifile)
        PP.set_inifile(self.inifile)
        PP.preprocess()
        for key in ['T_amplitude', 'baselevel_degree', 'river_l', 'baselevel_change', 'clayvolcomposition', 'waveheight', 't_start', 'sandvolcomposition', 'river_discharge', 't_stop', 't_interval', 't_dt', 'composition', 'baselevel_phase', 'river_u', 'morfac']:
            self.assertTrue(key in PP.context.keys(), msg='"%s" not found in context attribute' % key)
        empty_dir(self.destination)

    def test_render_templates(self):
        PP = preprocess.PreProcess()
        PP.config_dir = os.path.dirname(self.inifile)
        PP.set_inifile(self.inifile)
        PP.preprocess()
        rendered_files = ['a.bct',
                          'a.bcc',
                          'a.bnd',
                          'a.bch',
                          'morlyr.ini',
                          PP.mdf_file,
                          'config_d_hydro.xml',
                          'a.mor']
        for fname in rendered_files:
            self.assertTrue(os.path.exists(os.path.join(PP.output_path, fname)))

        for pattern in ('*.mdf', '*.sed'):
            path_pattern = os.path.join(PP.output_path, pattern)
            files_found = glob.glob(path_pattern)
            self.assertEqual(len(files_found), 1, msg='%s found with pattern %s' % (len(files_found), path_pattern))
        empty_dir(self.destination)

    def test_generate_depth(self):
        PP = preprocess.PreProcess()
        PP.config_dir = os.path.dirname(self.inifile)
        PP.set_inifile(self.inifile)
        PP.preprocess()
        # test whether th shape is as expected
        self.assertEqual(PP.dep.shape, (282, 302))
        empty_dir(self.destination)

    def test_write_depth(self):
        depfile = os.path.join(self.destination, 'a.dep')
        if os.path.exists(depfile):
            os.remove(depfile)

        PP = preprocess.PreProcess()
        PP.config_dir = os.path.dirname(self.inifile)
        PP.set_inifile(self.inifile)
        PP.preprocess()

        self.assertTrue(os.path.exists(depfile))
        empty_dir(self.destination)

if __name__ == '__main__':
    unittest.main()