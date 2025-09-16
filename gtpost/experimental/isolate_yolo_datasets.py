import shutil
import subprocess
from pathlib import Path

import yaml


def get_yolo_class_names(dataset_file: str | Path) -> None:
    with open(dataset_file) as f:
        dataset = yaml.safe_load(f)
        dataset_names = dataset["names"]

    return dataset_names


def make_new_yolo_folders(dataset_folder: str | Path, dataset_names: dict):
    new_dataset_folders = {}
    for dataset_key, dataset_name in dataset_names.items():
        destination = Path(dataset_folder).parent.joinpath(
            f"YOLODataset_{dataset_name}"
        )
        destination.mkdir(exist_ok=True)
        new_dataset_folders[dataset_key] = destination
        for item in Path(dataset_folder).iterdir():
            if item.is_dir():
                shutil.copytree(
                    item, destination.joinpath(item.name), dirs_exist_ok=True
                )
            else:
                shutil.copy(item, destination.joinpath(item.name))

    return new_dataset_folders


def update_datasets(new_dataset_folders: dict):
    for dataset_key, dataset_folder in new_dataset_folders.items():
        # Update dataset.yaml
        dataset_yaml = dataset_folder.joinpath("dataset.yaml")
        with open(dataset_yaml) as f:
            dataset = yaml.safe_load(f)
            original_names = dataset["names"]
            dataset["names"] = {0: dataset["names"][dataset_key]}
            dataset["path"] = str(dataset_folder)
        with open(dataset_yaml, "w") as f:
            yaml.safe_dump(dataset, f)

        # Update training labels to match the single class in dataset.yaml
        for training_label_file in dataset_folder.joinpath("labels/train").glob(
            "*.txt"
        ):
            update_label_text_file(
                training_label_file, dataset_key, 0, original_names[dataset_key]
            )

        # Update validation labels to match the single class in dataset.yaml
        for validation_label_file in dataset_folder.joinpath("labels/val").glob(
            "*.txt"
        ):
            update_label_text_file(
                validation_label_file, dataset_key, 0, original_names[dataset_key]
            )


def update_label_text_file(label_file, key_to_update, new_key, new_label):
    with open(label_file) as f:
        labels = f.readlines()
        ok_labels = [
            label.replace(str(key_to_update), str(new_key), 1)
            for label in labels
            if label.startswith(str(key_to_update))
        ]

    with open(label_file, "w") as f:
        f.writelines(ok_labels)


if __name__ == "__main__":
    # Run labelme2yolo in the command line to convert to a YOLO dataset
    subprocess.run(
        [
            "labelme2yolo",
            "--json_dir",
            str(Path(__file__).parent.joinpath("training_dataset/images_for_masking")),
            "--output_format",
            "polygon",
        ],
        check=True,
    )

    # Split up the YOLO dataset into individual datasets for each Architectural Element
    yolo_class_names = get_yolo_class_names(
        Path(__file__).parent.joinpath(
            "training_dataset/images_for_masking/YOLODataset/dataset.yaml"
        )
    )
    new_dataset_folders = make_new_yolo_folders(
        Path(__file__).parent.joinpath(
            "training_dataset/images_for_masking/YOLODataset"
        ),
        yolo_class_names,
    )
    update_datasets(new_dataset_folders)
