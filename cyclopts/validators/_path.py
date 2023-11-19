import pathlib

from attrs import frozen


@frozen
class Path:
    """Validator for ``pathlib.Path``.

    Parameters
    ----------
    exists: bool
        If ``True``, specified path must exist.
        Defaults to ``False``.
    file_okay: bool
        If ``True``, specified path may be a file.
        If ``False``, then files are not allowed.
        Defaults to ``True``.
    dir_okay: bool
        If ``True``, specified path may be a directory.
        If ``False``, then directories are not allowed.
        Defaults to ``True``.
    """

    exists: bool = False
    file_okay: bool = True
    dir_okay: bool = True
    writable: bool = False
    readable: bool = True

    def __call__(self, type_: type, path: pathlib.Path):
        if not isinstance(path, pathlib.Path):
            raise TypeError

        if self.exists and not path.exists():
            raise ValueError

        if not self.file_okay and path.is_file():
            raise ValueError

        if not self.dir_okay and path.is_dir():
            raise ValueError
