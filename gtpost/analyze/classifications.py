from enum import Enum


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


print("")
