from collections.abc import Iterable
from pathlib import Path
from typing import Annotated, Optional

import pytest

from cyclopts._env_var import env_var_split


def test_env_var_split_path_windows(mocker):
    mocker.patch("cyclopts._env_var.os.pathsep", ";")

    assert env_var_split(list[Path], r"C:\foo\bar;D:\fizz\buzz") == [
        r"C:\foo\bar",
        r"D:\fizz\buzz",
    ]


@pytest.mark.parametrize(
    "type_",
    [
        list[Path],
        list[Path | None],
        tuple[Path, ...],
        tuple[Path | None, ...],
        Annotated[list[Path], "test annotation"],
    ],
)
def test_env_var_split_path_posix_multiple(mocker, type_):
    mocker.patch("cyclopts._env_var.os.pathsep", ":")

    assert env_var_split(type_, "/foo/bar;:/fizz/buzz") == [
        "/foo/bar;",
        "/fizz/buzz",
    ]


def test_env_var_split_path_posix_single(mocker):
    """Dont split when a single Path is desired."""
    mocker.patch("cyclopts._env_var.os.pathsep", ":")
    assert ["foo:bar"] == env_var_split(Path, "foo:bar")


@pytest.mark.parametrize("pathsep", [":", ";"])
@pytest.mark.parametrize(
    "type_, expected",
    [
        (list[Path], ["one", "two"]),
        (list[Path | None], ["one", "two"]),
        (tuple[Path, ...], ["one", "two"]),
        (tuple[Path | None, ...], ["one", "two"]),
        (Annotated[list[Path], "test annotation"], ["one", "two"]),
        (list[str], ["one", "two"]),
        (Path, ["one,two"]),
    ],
)
def test_env_var_split_explicit_delimiter(mocker, pathsep, type_, expected):
    mocker.patch("cyclopts._env_var.os.pathsep", pathsep)

    assert env_var_split(type_, "one,two", delimiter=",") == expected


def test_env_var_split_path_general():
    assert ["foo"] == env_var_split(str, "foo")
    assert ["foo"] == env_var_split(Optional[str], "foo")
    assert ["foo bar"] == env_var_split(str, "foo bar")
    assert ["foo", "bar"] == env_var_split(list[str], "foo bar")
    assert ["foo", "bar"] == env_var_split(tuple[str, ...], "foo bar")
    assert ["foo", "bar"] == env_var_split(Iterable[str], "foo bar")
    assert ["1"] == env_var_split(int, "1")
