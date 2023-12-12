from pathlib import Path

import numpy as np
import pytest
from numpy.testing import assert_allclose

from gtpost import utils


class TestUtils:
    @pytest.fixture
    def mean_depth(self):
        return np.array(
            [
                [-999, -999, -999, -999, -999],
                [-999, -999, 5, -999, -999],
                [-999, -999, 5, -999, -999],
                [-999, 6, 6, 6, -999],
                [-999, 7, 7, 7, -999],
                [-999, 8, 8, 8, -999],
                [-999, -999, -999, -999, -999],
            ]
        )

    @pytest.mark.unittest
    def test_get_dx_dy(self):
        xvalues = np.array([0, 0, 0, 50, 100, 150, 200])
        xres, yres = utils.get_dx_dy(xvalues)
        assert xres == 50
        assert yres == 50

    @pytest.mark.unittest
    def test_get_model_bound(self, mean_depth):
        model_bound = utils.get_model_bound(mean_depth)
        assert_allclose(
            model_bound.exterior.xy[0],
            np.array(
                [
                    2.0,
                    2.1,
                    2.2,
                    2.3,
                    2.4,
                    2.5,
                    2.6,
                    2.6,
                    2.7,
                    3.4,
                    4.6,
                    5.0,
                    5.0,
                    4.6,
                    3.4,
                    2.7,
                    2.6,
                    2.6,
                    2.5,
                    2.4,
                    2.3,
                    2.2,
                    2.1,
                    2.0,
                ]
            ),
            atol=10e-1,
        )

    @pytest.mark.unittest
    def test_get_mouth_midpoint(self, mean_depth):
        array_n = np.arange(0, mean_depth.shape[1])
        array_m = np.arange(0, mean_depth.shape[0])
        midpoint = utils.get_mouth_midpoint(mean_depth, array_n, array_m)
        assert mean_depth[midpoint[1], midpoint[0]] == 5

    @pytest.mark.unittest
    def test_get_river_width(self, mean_depth):
        river_width = utils.get_river_width_at_mouth(mean_depth, [2, 2])
        assert river_width == 1
