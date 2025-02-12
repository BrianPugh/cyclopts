from pathlib import Path

import pytest

from cyclopts import validators


def test_path_type(tmp_path):
    validator = validators.Path()
    validator(Path, Path(tmp_path) / "does-not-exist")  # default configuration doesn't really check much.

    with pytest.raises(TypeError):
        validator(Path, "this is a string.")  # pyright: ignore[reportArgumentType]


def test_path_exists(tmp_path):
    validator = validators.Path(exists=True)
    validator(Path, tmp_path)

    with pytest.raises(ValueError):
        validator(Path, tmp_path / "foo")


def test_path_exists_sequence(tmp_path):
    validator = validators.Path()
    validator(tuple[Path, Path], (tmp_path, tmp_path))
    validator(list[Path], [tmp_path, tmp_path])


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
        validators.Path(exists=True, dir_okay=False, file_okay=False)


@pytest.mark.parametrize(
    "ext",
    ["mp4", ".mp4", "Mp4", ".Mp4"],
)
def test_path_extension_match_single(ext):
    validator = validators.Path(ext=ext)
    validator(Path, Path("foo.mp4"))


@pytest.mark.parametrize(
    "ext",
    ["png", ".png"],
)
def test_path_extension_not_match_single(ext):
    validator = validators.Path(ext=ext)
    with pytest.raises(ValueError) as e:
        validator(Path, Path("foo.mp4"))
    assert str(e.value) == '"foo.mp4" must have extension "png".'


@pytest.mark.parametrize(
    "ext",
    [
        ("mp4", "avi"),
        (".mp4", ".avi"),
        ("Mp4", ".AVI"),
        (".Mp4", ".avi"),
    ],
)
def test_path_extension_match_multiple(ext):
    validator = validators.Path(ext=ext)
    validator(Path, Path("foo.mp4"))
    validator(Path, Path("foo.avi"))


@pytest.mark.parametrize(
    "ext",
    [(".png", ".jpg"), ("png", "jPG")],
)
def test_path_extension_not_match_multi(ext):
    validator = validators.Path(ext=ext)
    with pytest.raises(ValueError) as e:
        validator(Path, Path("foo.mp4"))
    assert str(e.value) == '"foo.mp4" does not match one of supported extensions {"png", "jpg"}.'
