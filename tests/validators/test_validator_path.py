from pathlib import Path

import pytest

from cyclopts import validators


def test_path_type(tmp_path):
    validator = validators.Path()
    with pytest.raises(TypeError):
        validator(Path, "this is a string.")  # pyright: ignore[reportArgumentType]


def test_path_exists(tmp_path):
    validator = validators.Path(exists=True)
    validator(Path, tmp_path)

    with pytest.raises(ValueError):
        validator(Path, tmp_path / "foo")


def test_path_file_okay(tmp_path):
    validator = validators.Path(file_okay=False)

    folder = tmp_path / "directory"
    folder.mkdir()
    validator(Path, folder)

    file = tmp_path / "file"
    file.touch()

    with pytest.raises(ValueError):
        validator(Path, file)


def test_path_dir_okay(tmp_path):
    validator = validators.Path(dir_okay=False)

    folder = tmp_path / "directory"
    folder.mkdir()
    with pytest.raises(ValueError):
        validator(Path, folder)

    file = tmp_path / "file"
    file.touch()
    validator(Path, file)


def test_path_invalid_values():
    with pytest.raises(ValueError):
        validators.Path(dir_okay=False, file_okay=False)
