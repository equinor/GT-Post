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


class Fractions:
    bounds = np.array([0, 0.063, 0.125, 0.25, 0.5, 1, 2])
    labels = np.array(["s/c", "vf", "f", "m", "c", "vc", "g"])

    def classify(self, value):
        return self.labels[np.digitize(value, self.bounds) - 1]
