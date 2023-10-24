import tarfile
import tempfile
import zipfile
from pathlib import Path
from tempfile import SpooledTemporaryFile
from typing import BinaryIO

from fastapi import HTTPException
from zjbs_file_client import upload

from zjbs_tasker.model import CompressMethod


def invalid_request_exception(message: str) -> HTTPException:
    return HTTPException(status_code=400, detail=f"invalid request: {message}")


def decompress_file(
    file_path_or_obj: Path | str | BinaryIO | SpooledTemporaryFile,
    compress_method: CompressMethod,
    target_parent_directory: Path | str,
) -> None:
    target_parent_directory = Path(target_parent_directory)
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


async def upload_file(
    file: BinaryIO, filename: str, compress_method: CompressMethod, base_dir: str, target_basename: str
) -> None:
    with tempfile.TemporaryDirectory() as working_dir, tempfile.SpooledTemporaryFile() as recompressed_file:
        if compress_method == CompressMethod.not_compressed:
            not_compressed_path = Path(working_dir) / filename
            with open(not_compressed_path, "wb") as not_compressed_file:
                while chunk := file.read(1024 * 1024):
                    not_compressed_file.write(chunk)
        else:
            decompress_file(file, compress_method, working_dir)

        with tarfile.open(fileobj=recompressed_file, mode="w:xz") as recompressed_tar:
            recompressed_tar.add(working_dir, arcname=target_basename)
        recompressed_file.seek(0)
        await upload(base_dir, recompressed_file, f"{target_basename}.txz", mkdir=True, allow_overwrite=False)
