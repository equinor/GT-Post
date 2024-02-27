from pathlib import Path

import pytest

from gtpost.preprocessing import preprocessing


class TestPreprocess:
    test_templates_folder = Path(__file__).parents[1].joinpath("gt_templates")
    temp_output_folder = Path(__file__).parent.joinpath("data")
    mandatory_files = (
        "a.bch",
        "a.bct",
        "a.bnd",
        "a.dep",
        "a.enc",
        "a.grd",
        "a.mor",
        "a.obs",
        "a.fil",
        "wave.dep",
        "wave.enc",
        "wave.grd",
        "wave.mdw",
        "dioconfig.ini",
        "input.ini",
        "run_docker.sh",
        "Base_Lyr.thk",
        "md-tran.tr1",
        "md-tran.tr2",
        "md-tran.tr3",
        "md-tran.tr4",
        "md-tran.tr5",
        "wavecon.wave",
        "config_d_hydro.xml",
    )

    @pytest.mark.integrationtest
    @pytest.mark.parametrize(
        "template",
        (
            "GuleHorn_Neslen",
            "River_dominated_delta",
            "Roda",
            "Sobrarbe",
        ),
    )
    def test_preprocessing(self, template):
        """Integration tests for preprocessing the GT templates, based on their default
        ini files.


        Parameters
        ----------
        template : str
            GT template name used for parameterizing this test.

        """
        template_folder = self.test_templates_folder.joinpath(template)
        ini_file = template_folder.joinpath("input.ini")
        fpath_output = self.temp_output_folder.joinpath(template)

        # Create preprocessing object
        preprocessor = preprocessing.PreProcess(ini_file, fpath_output)
        assert preprocessor.template_name == template
        mandatory_files = self.mandatory_files + (
            f"{preprocessor.composition}.bcc",
            f"{preprocessor.composition}.mdf",
            f"{preprocessor.composition}.ini",
            f"{preprocessor.composition}.sed",
            f"{preprocessor.template_name}.sdu",
        )

        # Run entire pre-process
        preprocessor.preprocess()

        # Assert file presence and end with cleanup
        for file in fpath_output.glob("*"):
            assert file.name in mandatory_files
            file.unlink()
        fpath_output.rmdir()
