from pathlib import Path

import numpy as np
import pandas as pd
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
            np.array([4.0, 4.0, 3.59, 2.41, 1.41, 2.41, 3.59, 4.0]),
            atol=10e-1,
        )
        assert_allclose(
            model_bound.exterior.xy[1],
            np.array([2.59, 1.41, 1.0, 1.0, 2.0, 3.0, 3.0, 2.59]),
            atol=10e-1,
        )
