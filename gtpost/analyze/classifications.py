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
    def __init__(self, bounds: list, labels: list):
        self.bounds = np.array(bounds)
        self.labels = np.array(labels)

    @property
    def max_value(self):
        return self.bounds[-1]

    @property
    def min_value(self):
        return self.bounds[0]

    def classify(self, value):
        value = np.array([value])
        if all(value < self.max_value) and all(value > self.min_value):
            return self.labels[np.digitize(value, self.bounds) - 1]
        else:
            raise ValueError(
                "One or more values are outside of the range of the classifier"
            )


def fraction_classifier(values: list) -> np.array:
    fraction_classes = Classifier(
        [0, 0.063, 0.125, 0.25, 0.5, 1, 2], ["s/c", "vf", "f", "m", "c", "vc"]
    )
    return fraction_classes.classify(values)


def sorting_classifier(values: list) -> np.array:
    sorting_classes = Classifier(
        [0, 0.35, 0.5, 0.71, 1, 2, 4, 999],
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
