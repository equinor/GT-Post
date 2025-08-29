from dataclasses import dataclass
from pathlib import Path

from ultralytics import YOLO

from gtpost.analyze import classifications
from gtpost.experimental.prediction_contraints import (
    constrain_beach,
    constrain_beachridge,
    constrain_dchannel,
    constrain_dtundef,
    constrain_mouthbar,
    constrain_tchannel,
)


@dataclass
class PredictionParams:
    """
    A class to hold parameters for the prediction of segmentation masks using a trained
    YOLO model (.pt file).

    Attributes:
    unit_name (str): The name of the Architectural Element (AE)
    string_code (str): A string identifier or code associated with the AE
    encoding (int): Integer code used for this AE
    trained_model (YOLO): The trained YOLO model (.pt file) used for making predictions.
    min_confidence (float): The minimum confidence threshold for predicted instances to be considered valid. Defaults to 0.01.
    max_instances (int): The maximum number of instances to predict in a single image. Defaults to 99.
    constrain_func (callable, optional): An optional function to apply additional constraints to the prediction results. Defaults to None.
    """

    unit_name: str
    string_code: str
    encoding: int
    trained_model: YOLO
    min_confidence: float = 0.01
    max_instances: int = 99
    constrain_func: callable = None


dchannel = PredictionParams(
    unit_name="distributary channel",
    string_code="dchannel",
    encoding=classifications.ArchEl.dchannel.value,
    trained_model=YOLO(
        Path(__file__).parent.joinpath("trained_yolo_models/best_dchannel_yolo11l.pt")
    ),
    max_instances=99,
    min_confidence=0.3,
    constrain_func=constrain_dchannel,
)

beachridge = PredictionParams(
    unit_name="Beach ridge",
    string_code="beachridge",
    encoding=classifications.ArchEl.beachridge.value,
    trained_model=YOLO(
        Path(__file__).parent.joinpath("trained_yolo_models/best_beachridge_yolo11l.pt")
    ),
    max_instances=99,
    min_confidence=0.3,
    constrain_func=constrain_beachridge,
)

beach = PredictionParams(
    unit_name="Beach",
    string_code="beach",
    encoding=classifications.ArchEl.beach.value,
    trained_model=YOLO(
        Path(__file__).parent.joinpath("trained_yolo_models/best_beach_yolo11l.pt")
    ),
    max_instances=99,
    min_confidence=0.2,
    constrain_func=constrain_beach,
)

dtundef = PredictionParams(
    unit_name="deltatop",
    string_code="dtundef",
    encoding=classifications.ArchEl.dtundef.value,
    trained_model=YOLO(
        Path(__file__).parent.joinpath("trained_yolo_models/best_dtundef_yolo11l.pt")
    ),
    min_confidence=0.3,
    max_instances=1,
    constrain_func=constrain_dtundef,
)

tchannel = PredictionParams(
    unit_name="tidal channel",
    string_code="tchannel",
    encoding=classifications.ArchEl.tchannel.value,
    trained_model=YOLO(
        Path(__file__).parent.joinpath("trained_yolo_models/best_tchannel_yolo11l.pt")
    ),
    max_instances=20,
    min_confidence=0.12,
    constrain_func=constrain_tchannel,
)
