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
    assert tmp_file == convert(ct.ExistingPath, tmp_file)


def test_types_existing_path_validation_error(convert, tmp_path):
    with pytest.raises(ValidationError):
        convert(ct.ExistingPath, tmp_path / "foo")


# ExistingFile
def test_types_existing_file(convert, tmp_file):
    assert tmp_file == convert(ct.ExistingFile, tmp_file)


def test_types_existing_file_validation_error(convert, tmp_path):
    with pytest.raises(ValidationError):
        convert(ct.ExistingFile, tmp_path)


# ExistingDirectory
def test_types_existing_directory(convert, tmp_path):
    assert tmp_path == convert(ct.ExistingDirectory, tmp_path)


def test_types_existing_directory_validation_error(convert, tmp_file):
    with pytest.raises(ValidationError):
        convert(ct.ExistingDirectory, tmp_file)


# Directory
def test_types_directory(convert, tmp_path):
    assert tmp_path == convert(ct.Directory, tmp_path)


def test_types_directory_validation_error(convert, tmp_file):
    with pytest.raises(ValidationError):
        convert(ct.Directory, tmp_file)


# File
def test_types_file(convert, tmp_file):
    assert tmp_file == convert(ct.File, tmp_file)


def test_types_file_validation_error(convert, tmp_path):
    with pytest.raises(ValidationError):
        convert(ct.File, tmp_path)


# ResolvedExistingPath
@pytest.mark.parametrize("action", ["touch", "mkdir"])
def test_types_resolved_existing_path(convert, tmp_path, action):
    src = tmp_path / ".." / tmp_path.name / "foo"
    getattr(src, action)()
    assert src.resolve() == convert(ct.ResolvedExistingPath, src)


def test_types_resolved_existing_path_validation_error(convert, tmp_path):
    with pytest.raises(ValidationError):
        convert(ct.ResolvedExistingPath, tmp_path / "foo")


# ResolvedExistingFile
def test_types_resolved_existing_file(convert, tmp_path):
    src = tmp_path / ".." / tmp_path.name / "foo"
    src.touch()
    assert src.resolve() == convert(ct.ResolvedExistingFile, src)


def test_types_resolved_existing_file_validation_error(convert, tmp_path):
    with pytest.raises(ValidationError):
        convert(ct.ResolvedExistingFile, tmp_path / "foo")


# ResolvedExistingDirectory
def test_types_resolved_existing_directory(convert, tmp_path):
    src = tmp_path / ".." / tmp_path.name / "foo"
    src.mkdir()
    assert src.resolve() == convert(ct.ResolvedExistingDirectory, src)


def test_types_resolved_existing_directory_validation_error(convert, tmp_path):
    src = tmp_path / ".." / tmp_path.name / "foo"

    with pytest.raises(ValidationError):
        convert(ct.ResolvedExistingDirectory, src)


# ResolvedDirectory
def test_types_resolved_directory(convert, tmp_path):
    assert tmp_path == convert(ct.ResolvedDirectory, tmp_path / "foo" / "..")


def test_types_resolved_directory_validation_error(convert, tmp_file):
    with pytest.raises(ValidationError):
        convert(ct.ResolvedDirectory, tmp_file)


# ResolvedFile
def test_types_resolved_file(convert, tmp_path):
    src = tmp_path / ".." / tmp_path.name / "foo"
    src.touch()
    assert src.resolve() == convert(ct.ResolvedFile, src)


def test_types_resolved_file_validation_error(convert, tmp_path):
    with pytest.raises(ValidationError):
        convert(ct.ResolvedFile, tmp_path)


# Misc
def test_types_path_resolve_converter(convert, tmp_path):
    """Tests that ``_path_resolve_converter`` handles things like tuples correctly."""
    dir1 = tmp_path / "foo"
    dir2 = tmp_path / "bar"

    dir1.mkdir()
    dir2.mkdir()

    actual = convert(Tuple[ct.ResolvedDirectory, ct.ResolvedDirectory], [dir1.as_posix(), dir2.as_posix()])
    assert (dir1, dir2) == actual
