import pathlib
from typing import Type

from attrs import frozen


@frozen(kw_only=True)
class Path:
    """Assertions on properties of ``pathlib.Path``."""

    exists: bool = False
    """If ``True``, specified path must exist. Defaults to ``False``."""

    file_okay: bool = True
    """
    If ``True``, specified path may be a file.
    If ``False``, then files are not allowed.
    Defaults to ``True``.
    """

    dir_okay: bool = True
    """
    If ``True``, specified path may be a directory.
    If ``False``, then directories are not allowed.
    Defaults to ``True``.
    """

    def __call__(self, type_: Type, path: pathlib.Path):
        if not isinstance(path, pathlib.Path):
            raise TypeError

        if self.exists and not path.exists():
            raise ValueError(f"{path} does not exist.")

        if not self.file_okay and path.is_file():
            raise ValueError(f"{path} is not a file.")

        if not self.dir_okay and path.is_dir():
            raise ValueError(f"{path} is not a directory.")
