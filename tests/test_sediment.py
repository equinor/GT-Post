from pathlib import Path

import numpy as np
import pandas as pd
import pytest
from numpy.testing import (
    assert_allclose,
    assert_almost_equal,
    assert_array_equal,
    assert_equal,
)

from gtpost.analyze import sediment


class TestSediment:
    test_sedfile = Path(__file__).parent / "data/coarse-sand.sed"

    @pytest.fixture
    def rho_p(self):
        return [2650.0, 2650.0, 2650.0, 2650.0, 2650.0, 2650.0]

    @pytest.fixture
    def sedfile_line(self):
        return [9, 24, 39, 54, 69, 84]

    @pytest.fixture
    def sedtype(self):
        return ["sand", "sand", "sand", "sand", "sand", "mud"]

    @pytest.fixture
    def dmsedcum_final(self):
        rng = np.random.default_rng(seed=1)
        return rng.random((2, 6, 2, 2))

    @pytest.fixture
    def rho_db(self):
        return [1600.0, 1600.0, 1600.0, 1600.0, 1600.0, 1600.0]

    @pytest.fixture
    def d50input(self):
        return [0.00141, 0.000707, 0.000354, 0.000111, 0.0001, 0.000043988]

    @pytest.fixture
    def vfraction(self):
        return np.array(
            [
                [
                    [[0.19781426, 0.3307917], [0.05305415, 0.2640609]],
                    [[0.12051993, 0.14733111], [0.30461417, 0.11390245]],
                    [[0.21241281, 0.00959145], [0.27731068, 0.14979465]],
                    [[0.12743822, 0.27439835], [0.11158288, 0.12623321]],
                    [[0.05180586, 0.14029618], [0.07487635, 0.07301612]],
                    [[0.29000891, 0.0975912], [0.17856177, 0.27299268]],
                ],
                [
                    [[0.29439073, 0.16615557], [0.16738296, 0.11607106]],
                    [[0.04918017, 0.22235202], [0.15960236, 0.04857014]],
                    [[0.19086802, 0.1780519], [0.18958096, 0.38452546]],
                    [[0.01212051, 0.12117725], [0.14205688, 0.02613655]],
                    [[0.19632886, 0.19546311], [0.18337638, 0.10903122]],
                    [[0.25711172, 0.11680016], [0.15800046, 0.31566556]],
                ],
            ]
        )

    @pytest.mark.unittest
    def test_get_d50input(self, rho_p, sedfile_line, sedtype):
        d50_input = sediment.get_d50input(
            self.test_sedfile, sedtype, rho_p, sedfile_line
        )
        assert_allclose(
            d50_input,
            [0.00141, 0.000707, 0.000354, 0.000111, 0.0001, 0.000043988],
            rtol=1e-5,
        )

    @pytest.mark.unittest
    def test_calculate_fraction_and_sandfraction(self, sedtype, rho_db, dmsedcum_final):
        volumefraction = sediment.calculate_fraction(rho_db, dmsedcum_final)
        # The sum of volume fractions must be 1 for every t, x and y coordinate. So take
        # sum over the sedimenttype axis (axis 1) and check if correct.
        frac_sum = np.sum(volumefraction, axis=1)
        sandfraction = sediment.calculate_sand_fraction(sedtype, volumefraction)
        assert_allclose(frac_sum, 1.0)
        assert_allclose(
            sandfraction,
            np.array(
                [
                    [[0.7099911, 0.9024088], [0.82143825, 0.7270073]],
                    [[0.7428883, 0.8831999], [0.84199953, 0.68433446]],
                ]
            ),
        )

    @pytest.mark.unittest
    def test_calculate_sorting(self):
        pass

    @pytest.mark.unittest
    def test_calculate_distribution(self):
        pass

    @pytest.mark.unittest
    def test_calculate_diameter(self, d50input, vfraction):
        diameters, porosity, permeability = sediment.calculate_diameter(
            np.asarray(d50input, dtype=np.float32),
            np.array([5, 10, 16, 50, 84, 90], dtype=np.float32),
            vfraction,
        )

        pass
