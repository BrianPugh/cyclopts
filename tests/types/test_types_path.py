from pathlib import Path
from typing import Optional, Tuple

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


def test_types_existing_file_app(app):
    """https://github.com/BrianPugh/cyclopts/issues/287"""

    @app.default
    def main(f: ct.ExistingFile):
        pass

    with pytest.raises(ValidationError):
        app(["this-file-does-not-exist"], exit_on_error=False)


def test_types_existing_file_app_signature_default(app):
    @app.default
    def main(f: ct.ExistingFile = Path("this-file-does-not-exist")):
        pass

    with pytest.raises(ValidationError):
        app([""], exit_on_error=False)


def test_types_optional_existing_file_app_signature_default(app):
    @app.default
    def main(f: Optional[ct.ExistingFile] = Path("this-file-does-not-exist")):
        pass

    with pytest.raises(ValidationError):
        app([""], exit_on_error=False)


def test_types_optional_existing_file_app_signature_default_none(app, assert_parse_args):
    @app.default
    def main(f: Optional[ct.ExistingFile] = None):
        pass

    assert_parse_args(main, "")


def test_types_existing_file_app_list(app):
    """https://github.com/BrianPugh/cyclopts/issues/287"""

    @app.default
    def main(f: list[ct.ExistingFile]):
        pass

    with pytest.raises(ValidationError):
        app(["this-file-does-not-exist"], exit_on_error=False)


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


def test_types_resolved_existing_path_list(app, assert_parse_args):
    @app.default
    def main(f: list[ct.ResolvedFile]):
        pass

    expected = Path("foo.bin").resolve()
    assert_parse_args(main, "foo.bin", [expected])


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


# File extensions
@pytest.mark.parametrize(
    "annotation, ext",
    [
        (ct.BinPath, "bin"),
        (ct.CsvPath, "csv"),
        (ct.TxtPath, "txt"),
        (ct.ImagePath, "jpg"),
        (ct.ImagePath, "jpeg"),
        (ct.ImagePath, "png"),
        (ct.Mp4Path, "mp4"),
        (ct.JsonPath, "json"),
        (ct.TomlPath, "toml"),
        (ct.YamlPath, "yaml"),
    ],
)
def test_types_file_extensions_good(annotation, ext, convert, tmp_path):
    path = tmp_path / f"foo.{ext}"
    convert(annotation, path)


# File extensions
@pytest.mark.parametrize(
    "annotation, ext",
    [
        (ct.ExistingBinPath, "bin"),
        (ct.ExistingCsvPath, "csv"),
        (ct.ExistingTxtPath, "txt"),
        (ct.ExistingImagePath, "jpg"),
        (ct.ExistingImagePath, "jpeg"),
        (ct.ExistingImagePath, "png"),
        (ct.ExistingMp4Path, "mp4"),
        (ct.ExistingJsonPath, "json"),
        (ct.ExistingTomlPath, "toml"),
        (ct.ExistingYamlPath, "yaml"),
    ],
)
def test_types_file_extensions_exist_good(annotation, ext, convert, tmp_path):
    path = tmp_path / f"foo.{ext}"
    with pytest.raises(ValidationError):
        # File has not been created yet
        convert(annotation, path)

    path.touch()
    convert(annotation, path)


@pytest.mark.parametrize(
    "annotation",
    [
        ct.BinPath,
        ct.CsvPath,
        ct.TxtPath,
        ct.ImagePath,
        ct.Mp4Path,
        ct.JsonPath,
        ct.TomlPath,
        ct.YamlPath,
    ],
)
def test_types_file_extensions_bad(annotation, convert, tmp_path):
    path = tmp_path / "foo.bar"
    with pytest.raises(ValidationError):
        convert(annotation, path)
