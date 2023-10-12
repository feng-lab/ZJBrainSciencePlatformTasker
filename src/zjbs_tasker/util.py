import tarfile
import zipfile
from pathlib import Path
from tempfile import SpooledTemporaryFile
from typing import BinaryIO

from zjbs_tasker.model import CompressMethod

TASKER_BASE_DIR: str = "/tasker"
TASK_BASE_DIR: str = f"{TASKER_BASE_DIR}/task"
TASK_TEMPLATE_BASE_DIR: str = f"{TASKER_BASE_DIR}/template"


def get_task_template_pack(task_template_id: int, task_template_name: str) -> str:
    return f"{TASK_TEMPLATE_BASE_DIR}/{task_template_id}_{task_template_name}.tar.xz"


def get_task_dir(task_id: int, task_name: str) -> str:
    return f"{TASK_BASE_DIR}/{task_id}_{task_name}"


def get_task_source_file_pack(task_id: int, task_name: str) -> str:
    task_dir = get_task_dir(task_id, task_name)
    return f"{task_dir}/source.tar.xz"


def get_task_run_dir(task_id: int, task_name: str, task_run_index: int) -> str:
    task_dir = get_task_dir(task_id, task_name)
    return f"{task_dir}/run_{task_run_index}"


def decompress_file(
    file_path_or_obj: Path | str | BinaryIO | SpooledTemporaryFile,
    compress_method: CompressMethod,
    target_parent_directory: Path | str,
) -> None:
    target_parent_directory.mkdir(parents=True, exist_ok=True)
    match compress_method:
        case CompressMethod.zip:
            with zipfile.ZipFile(file_path_or_obj, "r") as zip_file:
                zip_file.extractall(target_parent_directory)
        case CompressMethod.tgz | CompressMethod.txz:
            tar_open_args = {"mode": "r:gz" if compress_method is CompressMethod.tgz else "r:xz"}
            if isinstance(file_path_or_obj, Path | str):
                tar_open_args["name"] = file_path_or_obj
            else:
                tar_open_args["fileobj"] = file_path_or_obj
            with tarfile.open(**tar_open_args) as tar_file:
                tar_file.extractall(target_parent_directory)
        case CompressMethod.not_compressed:
            raise ValueError("cannot decompress not compressed file")


def compress_directory(
    directory: Path | str, target_parent_directory: Path | str | None = None, arcname: str | None = None
) -> Path:
    target_parent_directory = Path(target_parent_directory) if target_parent_directory else directory.parent
    arcname = directory.name if arcname is None else arcname
    with tarfile.open(target_parent_directory / f"{arcname}.tar.xz", "w:xz") as tar_file:
        tar_file.add(directory, arcname=arcname)
    return target_parent_directory / f"{arcname}.tar.xz"
