from pathlib import Path
from typing import Union

from gtpost.model import ModelResult


def main(
    input_folder: Union[str, Path],
    output_folder: Union[str, Path],
    config_file: Union[str, Path],
):
    input_folder = Path(input_folder)
    output_folder = Path(output_folder)
    config_file = Path(config_file)

    modelresult = ModelResult.from_folder(input_folder)
    modelresult.postprocess()
    modelresult.export_sediment_and_object_data(
        output_folder.joinpath("Sed_and_Obj_data.nc")
    )
