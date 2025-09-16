from pathlib import Path, WindowsPath

from ultralytics import YOLO

default_yolo_model = Path(__file__).parent.joinpath(
    "pretrained_yolo_models/yolo11l-seg.pt"
)


def tune():
    pass


def train(
    yolo_dataset: str | WindowsPath,
    imgsz: int,
    pretrained_yolo_model: str | WindowsPath = default_yolo_model,
):
    """
    Main function to train a model

    Parameters
    ----------
    yolo_dataset : str | WindowsPath
        Path to YOLO dataset.yaml file
    imgsz : int
        Input image size
    pretrained_yolo_model : str | WindowsPath, optional
        Path to pre-trained YOLO model (.pt file), by default yolov8s-seg.pt is used.

    Returns
    -------
    dict
        Training results
    """
    model = YOLO(pretrained_yolo_model)
    results = model.train(
        data=yolo_dataset,
        epochs=500,
        imgsz=imgsz,
        device="cpu",
        lr0=0.00659,
        lrf=0.01089,
        momentum=0.82058,
        weight_decay=0.00062,
        warmup_epochs=4.07926,
        warmup_momentum=0.71553,
        box=6.19376,
        cls=0.57219,
        dfl=2.23532,
        hsv_h=0.01087,
        hsv_s=0.3918,
        hsv_v=0.45941,
        degrees=0.0,
        translate=0.08485,
        scale=0.52358,
        shear=0.0,
        perspective=0.0,
        flipud=0.0,
        fliplr=0.45541,
        bgr=0.0,
        mosaic=0.97736,
        mixup=0.0,
        copy_paste=0.0,
    )
    return results


if __name__ == "__main__":
    results = train(
        Path(__file__).parent.joinpath(
            r"training_dataset\images_for_masking\YOLODataset_dchannel\dataset.yaml"
        ),
        282,
    )
    results = train(
        Path(__file__).parent.joinpath(
            r"training_dataset\images_for_masking\YOLODataset_beachridge\dataset.yaml"
        ),
        282,
    )
    results = train(
        Path(__file__).parent.joinpath(
            r"training_dataset\images_for_masking\YOLODataset_dtundef\dataset.yaml"
        ),
        282,
    )
    results = train(
        Path(__file__).parent.joinpath(
            r"training_dataset\images_for_masking\YOLODataset_beach\dataset.yaml"
        ),
        282,
    )
    results = train(
        Path(__file__).parent.joinpath(
            r"training_dataset\images_for_masking\YOLODataset_tchannel\dataset.yaml"
        ),
        282,
    )
