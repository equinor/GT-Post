from pathlib import Path

import numpy as np
import pandas as pd
import pytest
from numpy.testing import assert_allclose

from gtpost.analyze import sediment


class TestSediment:
    test_sedfile = Path(__file__).parent / "data/coarse-sand.sed"

    @pytest.fixture
    def rho_p(self):
        return np.array([2650.0, 2650.0, 2650.0, 2650.0, 2650.0, 2650.0])

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
        return np.array([1600.0, 1600.0, 1600.0, 1600.0, 1600.0, 1600.0])

    @pytest.fixture
    def d50input(self):
        return np.array([0.00141, 0.000707, 0.000354, 0.0002, 0.0001, 0.000043988])

    @pytest.fixture
    def vfraction(self):
        # Some interesting distributions to test. From heavily skewed to nicely
        # distributed to weird two-topped distributions.
        return np.array(
            [
                [
                    [[0.30, 0.02], [0.05, 0.05]],
                    [[0.35, 0.08], [0.15, 0.15]],
                    [[0.15, 0.10], [0.30, 0.30]],
                    [[0.10, 0.15], [0.30, 0.30]],
                    [[0.08, 0.35], [0.15, 0.15]],
                    [[0.02, 0.30], [0.05, 0.05]],
                ],
                [
                    [[1.00, 0.00], [0.50, 0.00]],
                    [[0.00, 0.00], [0.00, 0.00]],
                    [[0.00, 0.00], [0.00, 0.00]],
                    [[0.00, 0.00], [0.00, 0.30]],
                    [[0.00, 0.00], [0.00, 0.70]],
                    [[0.00, 1.00], [0.50, 0.00]],
                ],
            ]
        )

    @pytest.fixture
    def diameters_target(self):
        return np.array(
            [
                [
                    [
                        [0.14358729, 0.2030631, 0.65975396, 1.41421356, 1.62450479],
                        [0.04123462, 0.04736614, 0.10153155, 0.35355339, 0.5],
                    ],
                    [
                        [0.08246924, 0.11662912, 0.26794337, 0.61557221, 0.8122524],
                        [0.08246924, 0.11662912, 0.26794337, 0.61557221, 0.8122524],
                    ],
                ],
                [
                    [
                        [1.07177346, 1.14869835, 1.41421356, 1.74110113, 1.86606598],
                        [0.03349292, 0.03589682, 0.04419417, 0.05440941, 0.05831456],
                    ],
                    [
                        [0.04736614, 0.0625, 0.25, 1.0, 1.31950791],
                        [0.07694653, 0.08246924, 0.11662912, 0.18946457, 0.21763764],
                    ],
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
    def test_calculate_sorting(self, diameters_target):
        sorting = sediment.calculate_sorting(diameters_target, [10, 16, 50, 84, 90])
        assert_allclose(
            sorting,
            np.array(
                [
                    [[1.23030303, 1.27045458], [1.10000003, 1.10000003]],
                    [[0.27121212, 0.27121215], [1.72727274, 0.52727273]],
                ]
            ),
        )

    @pytest.mark.unittest
    def test_calculate_diameter_porosity_permeability(
        self, d50input, vfraction, diameters_target
    ):
        diameters, porosity, permeability = sediment.calculate_diameter(
            np.asarray(d50input, dtype=np.float32),
            np.array([10, 16, 50, 84, 90], dtype=np.float32),
            vfraction,
        )

        # Lower D-values must always be a smaller grain size.
        assert (diameters[:, :, :, 0] < diameters[:, :, :, 1]).all()
        assert (diameters[:, :, :, 1] < diameters[:, :, :, 2]).all()
        assert (diameters[:, :, :, 2] < diameters[:, :, :, 3]).all()
        assert (diameters[:, :, :, 3] < diameters[:, :, :, 4]).all()

        assert_allclose(diameters, diameters_target, atol=1e-7)
        assert_allclose(
            porosity,
            np.array(
                [
                    [[0.28738403, 0.28597625], [0.29219721, 0.29219721]],
                    [[0.34669999, 0.34424062], [0.27189716, 0.32539888]],
                ]
            ),
        )
        assert_allclose(
            permeability,
            np.array(
                [
                    [
                        [1.01514711e-09, 6.19265668e-11],
                        [2.44974538e-10, 2.44974538e-10],
                    ],
                    [
                        [5.68450212e-09, 1.73186250e-12],
                        [2.29137137e-10, 1.69956940e-11],
                    ],
                ]
            ),
        )
        pass
