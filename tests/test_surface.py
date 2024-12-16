import numpy as np
import pytest

from gtpost.analyze.surface import slope


@pytest.fixture
def flat_array():
    return np.expand_dims(np.array([[1, 1, 1], [1, 1, 1], [1, 1, 1]]), axis=0)


@pytest.fixture
def increasing_array():
    return np.expand_dims(np.array([[1, 2, 3], [4, 5, 6], [7, 8, 9]]), axis=0)


@pytest.fixture
def decreasing_array():
    return np.expand_dims(np.array([[9, 8, 7], [6, 5, 4], [3, 2, 1]]), axis=0)


@pytest.fixture
def random_array():
    return np.expand_dims(np.random.rand(5, 5), axis=0)


def test_slope_with_flat_array(flat_array):
    expected_slope = np.zeros_like(flat_array)
    result = slope(flat_array)
    assert np.array_equal(
        result, expected_slope
    ), f"Expected {expected_slope}, but got {result}"


def test_slope_with_increasing_array(increasing_array):
    result = slope(increasing_array)
    assert (
        result.shape == increasing_array.shape
    ), f"Expected shape {increasing_array.shape}, but got {result.shape}"
    assert np.all(result >= 0), "Slope values should be non-negative"


def test_slope_with_decreasing_array(decreasing_array):
    result = slope(decreasing_array)
    assert (
        result.shape == decreasing_array.shape
    ), f"Expected shape {decreasing_array.shape}, but got {result.shape}"
    assert np.all(result >= 0), "Slope values should be non-negative"


def test_slope_with_random_array(random_array):
    result = slope(random_array)
    assert (
        result.shape == random_array.shape
    ), f"Expected shape {random_array.shape}, but got {result.shape}"
    assert np.all(result >= 0), "Slope values should be non-negative"
