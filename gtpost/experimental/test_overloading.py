from functools import singledispatch


@singledispatch
def normalize(array: int | float | str):
    """
    Normalize the input array based on its type.

    Parameters
    ----------
    array : int, float, or str
        The input array to be normalized. The type of the array determines the normalization process.

    Raises
    ------
    TypeError
        If the type of the input array is not supported.

    Notes
    -----
    This function uses `singledispatch` to handle different types of input arrays. Specific implementations
    for each type should be registered separately.
    """
    raise TypeError(f"Unsupported type {type(array)}")


@normalize.register(int | float)
def _(array):
    return array + 1


@normalize.register(str)
def _(array):
    return array + "ok"


if __name__ == "__main__":
    print(normalize(1))
    print(normalize(1.0))
    print(normalize("1"))
    print(normalize(list("1")))
    normalize
