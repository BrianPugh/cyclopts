from pathlib import Path
from typing import Tuple

import pytest

from cyclopts import types as ct
from cyclopts.exceptions import ValidationError


@pytest.fixture
def tmp_file(tmp_path):
    file_path = tmp_path / "file.bin"
    file_path.touch()
    return file_path


# ExistingPath
def test_types_existing_path(convert, tmp_file):
    assert tmp_file == convert(ct.ExistingPath, str(tmp_file))


def test_types_existing_path_validation_error(convert, tmp_path):
    with pytest.raises(ValidationError):
        convert(ct.ExistingPath, str(tmp_path / "foo"))


# ExistingFile
def test_types_existing_file(convert, tmp_file):
    assert tmp_file == convert(ct.ExistingFile, str(tmp_file))


def test_types_existing_file_validation_error(convert, tmp_path):
    with pytest.raises(ValidationError):
        convert(ct.ExistingFile, str(tmp_path))


# ExistingDirectory
def test_types_existing_directory(convert, tmp_path):
    assert tmp_path == convert(ct.ExistingDirectory, str(tmp_path))


def test_types_existing_directory_validation_error(convert, tmp_file):
    with pytest.raises(ValidationError):
        convert(ct.ExistingDirectory, str(tmp_file))


# Directory
def test_types_directory(convert, tmp_path):
    assert tmp_path == convert(ct.Directory, str(tmp_path))


def test_types_directory_validation_error(convert, tmp_file):
    with pytest.raises(ValidationError):
        convert(ct.Directory, str(tmp_file))


# File
def test_types_file(convert, tmp_file):
    assert tmp_file == convert(ct.File, str(tmp_file))


def test_types_file_validation_error(convert, tmp_path):
    with pytest.raises(ValidationError):
        convert(ct.File, str(tmp_path))


# ResolvedExistingPath
@pytest.mark.parametrize("action", ["touch", "mkdir"])
def test_types_resolved_existing_path(convert, tmp_path, action):
    src = tmp_path / ".." / tmp_path.name / "foo"
    getattr(src, action)()
    assert src.resolve() == convert(ct.ResolvedExistingPath, str(src))


def test_types_resolved_existing_path_validation_error(convert, tmp_path):
    with pytest.raises(ValidationError):
        convert(ct.ResolvedExistingPath, str(tmp_path / "foo"))


# ResolvedExistingFile
def test_types_resolved_existing_file(convert, tmp_path):
    src = tmp_path / ".." / tmp_path.name / "foo"
    src.touch()
    assert src.resolve() == convert(ct.ResolvedExistingFile, str(src))


def test_types_resolved_existing_file_validation_error(convert, tmp_path):
    with pytest.raises(ValidationError):
        convert(ct.ResolvedExistingFile, str(tmp_path / "foo"))


# ResolvedExistingDirectory
def test_types_resolved_existing_directory(convert, tmp_path):
    src = tmp_path / ".." / tmp_path.name / "foo"
    src.mkdir()
    assert src.resolve() == convert(ct.ResolvedExistingDirectory, str(src))


def test_types_resolved_existing_directory_validation_error(convert, tmp_path):
    src = tmp_path / ".." / tmp_path.name / "foo"

    with pytest.raises(ValidationError):
        convert(ct.ResolvedExistingDirectory, str(src))


# ResolvedDirectory
def test_types_resolved_directory(convert):
    assert Path("/bar") == convert(ct.ResolvedDirectory, "/foo/../bar/")


def test_types_resolved_directory_validation_error(convert, tmp_file):
    with pytest.raises(ValidationError):
        convert(ct.ResolvedDirectory, str(tmp_file))


# ResolvedFile
def test_types_resolved_file(convert, tmp_path):
    src = tmp_path / ".." / tmp_path.name / "foo"
    src.touch()
    assert src.resolve() == convert(ct.ResolvedFile, str(src))


def test_types_resolved_file_validation_error(convert, tmp_path):
    with pytest.raises(ValidationError):
        convert(ct.ResolvedFile, str(tmp_path))


# Misc
def test_types_path_resolve_converter(convert, tmp_path):
    """Tests that ``_path_resolve_converter`` handles things like tuples correctly."""
    dir1 = tmp_path / "foo"
    dir2 = tmp_path / "bar"

    dir1.mkdir()
    dir2.mkdir()

    assert (dir1, dir2) == convert(Tuple[ct.ResolvedDirectory, ct.ResolvedDirectory], [str(dir1), str(dir2)])
