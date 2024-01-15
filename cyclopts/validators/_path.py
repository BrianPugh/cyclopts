import pathlib
from typing import Type

from attrs import frozen


@frozen(kw_only=True)
class Path:
    """Assertions on properties of :class:`pathlib.Path`."""

    exists: bool = False
    """If ``True``, specified path **must** exist. Defaults to ``False``."""

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

    def __attrs_post_init__(self):
        if not self.file_okay and not self.dir_okay:
            raise ValueError("file_okay and dir_okay cannot both be False.")

    def __call__(self, type_: Type, path: pathlib.Path):
        if not isinstance(path, pathlib.Path):
            raise TypeError

        if path.exists():
            if not self.file_okay and path.is_file():
                raise ValueError(f"Only directory input is allowed but {path} is a file.")

            if not self.dir_okay and path.is_dir():
                raise ValueError(f"Only file input is allowed but {path} is a directory.")
        elif self.exists:
            raise ValueError(f"{path} does not exist.")
