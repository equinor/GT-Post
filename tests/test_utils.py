from pathlib import Path

import numpy as np
import pytest
from numpy.testing import assert_allclose

from gtpost import utils
from gtpost.analyze.surface import slope


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

    @pytest.fixture
    def mean_depth_t(self):
        # Generate a depth array with 10 timesteps that becomes steeper over time.
        result = np.zeros([10, 6, 8])
        result[0, :, :] = np.array(
            [
                [-999, -999, -999, -999, -999, -999, -999, -999],
                [-999, 4, 4, 3.5, 3.5, 4, 4, -999],
                [-999, 5, 5, 4, 4, 5, 5, -999],
                [-999, 6, 6, 5, 5, 6, 6, -999],
                [-999, 7, 7, 6, 6, 7, 7, -999],
                [-999, -999, -999, -999, -999, -999, -999, -999],
            ]
        )
        adjustment_array = np.array(
            [
                [0, 0, 0, 0, 0, 0, 0, 0],
                [0, 0, 0, 0, 0, 0, 0, 0],
                [0, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0],
                [0, 0.3, 0.3, 0.3, 0.3, 0.3, 0.3, 0],
                [0, 0.6, 0.6, 0.6, 0.6, 0.6, 0.6, 0],
                [0, 0, 0, 0, 0, 0, 0, 0],
            ]
        )
        for i in range(1, len(result)):
            result[i, :, :] = result[i - 1, :, :] + adjustment_array
        return result

    @pytest.mark.unittest
    def test_get_template_name(self):
        template_name = utils.get_template_name(Path(__file__).parents[0] / "data")
        assert template_name == "river_dominated_delta"

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

    @pytest.mark.unittest
    def test_get_deltafront_contour_depth(self, mean_depth_t):
        model_bound = utils.get_model_bound(mean_depth_t[0, :, :])
        slope_t = slope(mean_depth_t)
        interpolated_df_depth = utils.get_deltafront_contour_depth(
            mean_depth_t,
            slope_t,
            model_bound,
            contour_depths=[4, 4.5, 5, 5.5, 6, 6.5],
            first_timestep=0,
            timestep_resolution=1,
            buffersize=1,
        )

        assert_allclose(
            interpolated_df_depth,
            np.array(
                [
                    4.93181818,
                    5.04090909,
                    5.16893939,
                    5.31590909,
                    5.48181818,
                    5.66666667,
                    5.87045455,
                    6.09318182,
                    6.33484848,
                    6.59545455,
                ]
            ),
        )
