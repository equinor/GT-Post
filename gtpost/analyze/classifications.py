from enum import Enum

import numpy as np


class SubEnv(Enum):
    undefined = 0
    deltatop = 1
    deltafront = 2
    prodelta = 3


class ArchEl(Enum):
    undefined = 0
    dtair = 1
    dtaqua = 2
    channel = 3
    mouthbar = 4
    deltafront = 5
    prodelta = 6


class Classifier:
    def __init__(self, bounds: list | np.ndarray, labels: list | np.ndarray):
        """
        Class to create custom classifiers used for labelling values.

        Parameters
        ----------
        bounds : list | np.ndarray
            Array of bounding values for classes. e.g. [0, 1, 2, 3].
        labels : list | np.ndarray
            Associated labels. e.g. [label1, label2, label3].
        """
        self.bounds = np.array(bounds)
        self.labels = np.array(labels)

        if not len(self.bounds) - len(self.labels) == 1:
            raise ValueError(
                "Lenght of bounds array must be one position longer than labels array"
                + "e.g. bounds = [0, 1, 2, 3] and labels = [label1, label2, label3]."
            )

    @property
    def max_value(self):
        return self.bounds[-1]

    @property
    def min_value(self):
        return self.bounds[0]

    def classify(self, value: np.ndarray) -> np.ndarray:
        """
        Classify values to labels.

        Parameters
        ----------
        value : np.ndarray
            Array of values to be labelled.

        Returns
        -------
        np.ndarray
            Array of labelled data.

        Raises
        ------
        ValueError
            If a value was outside of the bounds range was queried.
        """
        value = np.array([value])
        if all(value < self.max_value) and all(value > self.min_value):
            return self.labels[np.digitize(value, self.bounds) - 1]
        else:
            raise ValueError(
                "One or more values are outside of the range of the classifier."
            )


def fraction_classifier(values: list | np.ndarray) -> np.ndarray:
    """
    Classifier for sediment fractions. Labels and bounds are:

    s/c (0 - 63 mu)     : Silt/clay
    vf (63 - 125 mu)    : Very fine sand
    f (125 - 250 mu)    : Fine sand
    m (250 - 500 mu)    : Medium sand
    c (500 - 1000 mu)   : Coarse sand
    vc (1000 - 2000 mu) : Very coarse sand

    Parameters
    ----------
    values : list | np.ndarray
        Grain size values to classify into sediment classes.

    Returns
    -------
    np.ndarray
        Classified result.
    """
    fraction_classes = Classifier(
        [-1, 0.063, 0.125, 0.25, 0.5, 1, 2], ["s/c", "vf", "f", "m", "c", "vc"]
    )
    return fraction_classes.classify(values)


def sorting_classifier(values: list | np.ndarray) -> np.ndarray:
    """
    Classifier for the Folks (1968) sorting parameter. Labels and bounds are:

    Very well (0 - 0.35)
    Well (0.35 - 0.5)
    Moderately well (0.5 - 0.71)
    Moderate (0.71 - 1)
    Poor (1 - 2)
    Very poor (2 - 4)
    Extremely poor (> 4)

    Parameters
    ----------
    values : list | np.ndarray
        Folks sorting values to classify into sorting classes.

    Returns
    -------
    np.ndarray
        Classified result.
    """
    sorting_classes = Classifier(
        [-1, 0.35, 0.5, 0.71, 1, 2, 4, 999],
        [
            "Very well",
            "Well",
            "Moderately well",
            "Moderate",
            "Poor",
            "Very poor",
            "Extremely poor",
        ],
    )
    return sorting_classes.classify(values)
