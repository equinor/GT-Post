import numpy as np
from time import time


def row_major_loop(array):
    for n in range(array.shape[2]):
        for m in range(array.shape[1]):
            for t in range(array.shape[0]):
                array[t, m, n] = 2 + t
    return array


def column_major_loop(array):
    for t in range(array.shape[0]):
        for m in range(array.shape[1]):
            for n in range(array.shape[2]):
                array[t, m, n] = 2 + t
    return array


if __name__ == "__main__":
    n = 50
    m = 50
    t = 30
    array = np.ones((t, m, n), dtype="float64")

    t = time()
    for i in range(300):
        s = row_major_loop(array)
    print(time() - t)

    t = time()
    for i in range(300):
        s = column_major_loop(array)
    print(time() - t)
