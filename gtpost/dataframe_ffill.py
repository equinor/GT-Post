from typing import List, Union

import numpy as np
import pandas as pd


def forward_fill_multiple(
    dataframe: pd.DataFrame, columns: Union[str, List[str]]
) -> pd.DataFrame:
    """
    Removes any negative values from specified dataframe columns and apply forward fill.
    Apply backward fill for any remaining NaN values.

    Parameters
    ----------
    dataframe : pd.DataFrame
        dataframe with data that is to be filled
    columns : Union[str, List[str]]
        A string or list of strings with column names to be affected

    Returns
    -------
    pd.DataFrame
        Resulting dataframe with 1filled values
    """
    if isinstance(columns, str):
        columns = [columns]

    for column in columns:
        dataframe[column][dataframe[column] < 0] = np.nan
        dataframe.ffill(inplace=True)
        dataframe.bfill(inplace=True)

    return dataframe


if __name__ == "__main__":
    # Random tabelletje met wat negatieve waarden die eruit moeten. Je kan Excel inlezen
    # met pandas.
    df = pd.DataFrame(
        {
            "getallen": [-1, 1, 3, 4, -2, 1, -2, -3, 5, -4, 1, 1, 3, 4],
            "getallen_1": [-1, 1, 3, 4, -2, 1, -2, -3, 5, -4, 1, 1, 3, 4],
            "getallen_2": [-1, 1, 3, 4, -2, 1, -2, -3, 5, -4, 1, 1, 3, 4],
        }
    )

    df_out = forward_fill_multiple(df, ["getallen", "getallen_1", "getallen_2"])

    forward_fill_multiple()
    # Check je dataframe
    print(df_out)
