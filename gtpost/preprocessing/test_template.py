__author__ = 'heijer'


import os
import unittest
from template_preprocess import TemplatePreProcess
import configparser


def write_ini(inidata, inifile):
    with open(inifile, 'wb') as configfile:
        config = configparser.RawConfigParser()
        for section, contents in inidata.items():
            config.add_section(section)
            for key, val in contents.items():
                config.set(section, key, val)
        config.write(configfile)


class TemplatePreProcessTests(unittest.TestCase):

    def setUp(self):
        self.TemplatePreProcess = TemplatePreProcess()

    def test_read_ini(self):
        self.TemplatePreProcess.read_ini()
        self.assertEqual(self.TemplatePreProcess.inidata, {})

        self.TemplatePreProcess.inifile = 'input-not-exists.ini'
        self.TemplatePreProcess.read_ini()
        self.assertEqual(self.TemplatePreProcess.inidata, {})

        inifile = os.path.join(self.TemplatePreProcess.input_path, 'input.ini')
        self.TemplatePreProcess.inifile = inifile
        self.TemplatePreProcess.read_ini()
        self.assertNotEqual(self.TemplatePreProcess.inidata, {})

        inidata_firstread = self.TemplatePreProcess.inidata.copy()
        reproduced_ini = os.path.join(self.TemplatePreProcess.output_path, 'input_reprocuded.ini')
        write_ini(self.TemplatePreProcess.inidata, reproduced_ini)
        self.TemplatePreProcess.inifile = reproduced_ini
        self.TemplatePreProcess.read_ini()
        self.assertDictEqual(self.TemplatePreProcess.inidata, inidata_firstread)

    def test_set_inifile(self):
        inifile_not_existing = 'input-not-exists.ini'
        with self.assertRaises(SystemExit):
            self.TemplatePreProcess.set_inifile(inifile_not_existing)

        inifile = os.path.join(self.TemplatePreProcess.input_path, 'input.ini')
        self.TemplatePreProcess.set_inifile(inifile)
        self.assertEqual(self.TemplatePreProcess.inifile, inifile)

if __name__ == '__main__':
    unittest.main()