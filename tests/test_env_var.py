from pathlib import Path
from typing import Iterable, List, Optional, Tuple

import pytest

from cyclopts._env_var import env_var_split


def test_env_var_split_path_windows(mocker):
    mocker.patch("cyclopts._env_var.os.pathsep", ";")

    assert env_var_split(List[Path], r"C:\foo\bar;D:\fizz\buzz") == [
        r"C:\foo\bar",
        r"D:\fizz\buzz",
    ]


@pytest.mark.parametrize(
    "type_",
    [
        List[Path],
        List[Optional[Path]],
        Tuple[Path, ...],
        Tuple[Optional[Path], ...],
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


def test_env_var_split_path_general():
    assert ["foo"] == env_var_split(str, "foo")
    assert ["foo"] == env_var_split(Optional[str], "foo")
    assert ["foo bar"] == env_var_split(str, "foo bar")
    assert ["foo", "bar"] == env_var_split(List[str], "foo bar")
    assert ["foo", "bar"] == env_var_split(Tuple[str, ...], "foo bar")
    assert ["foo", "bar"] == env_var_split(Iterable[str], "foo bar")
    assert ["1"] == env_var_split(int, "1")
