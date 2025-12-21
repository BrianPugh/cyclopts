from pathlib import Path
from typing import Annotated

import pytest

from cyclopts import Parameter

# Case variations of "none" and "null" strings that should be parsed as None
NONE_STRINGS = ["none", "null", "NONE", "NULL", "None", "Null"]


def test_bind_negative_none(app, assert_parse_args):
    @app.default
    def default(path: Annotated[Path | None, Parameter(negative_none="default-")]):
        pass

    assert_parse_args(default, "--default-path", None)


@pytest.mark.parametrize("none_str", NONE_STRINGS)
def test_bind_none_string_int_or_none(app, assert_parse_args, none_str):
    """Test that 'none' and 'null' strings are converted to None for int | None."""

    @app.default
    def default(value: int | None = 2):
        pass

    assert_parse_args(default, f"--value={none_str}", None)


@pytest.mark.parametrize("none_str", NONE_STRINGS)
def test_bind_none_string_none_or_path(app, assert_parse_args, none_str):
    """Test that 'none' and 'null' strings are converted to None for None | Path.

    Union ordering matters: None comes before Path, so 'none' becomes None.
    """

    @app.default
    def default(path: None | Path):
        pass

    assert_parse_args(default, f"--path={none_str}", None)


@pytest.mark.parametrize("none_str", ["none", "null"])
def test_bind_none_string_path_or_none(app, assert_parse_args, none_str):
    """Test that 'none' and 'null' strings become Path for Path | None.

    Union ordering matters: Path comes before None, and Path("none") is valid.
    """

    @app.default
    def default(path: Path | None):
        pass

    assert_parse_args(default, f"--path={none_str}", Path(none_str))


@pytest.mark.parametrize("none_str", NONE_STRINGS)
def test_bind_none_string_none_first_in_union(app, assert_parse_args, none_str):
    """When None comes before str in union, 'none' should become None."""

    @app.default
    def default(value: None | str):
        pass

    assert_parse_args(default, f"--value={none_str}", None)


def test_bind_none_string_str_first_in_union(app, assert_parse_args):
    """When str comes before None in union, 'none' should stay as string 'none'."""

    @app.default
    def default(value: str | None):
        pass

    assert_parse_args(default, "--value=none", "none")


@pytest.mark.parametrize("none_str", NONE_STRINGS)
def test_bind_none_string_int_none_str_union(app, assert_parse_args, none_str):
    """For int | None | str, 'none' should become None (int fails, None succeeds)."""

    @app.default
    def default(value: int | None | str):
        pass

    assert_parse_args(default, f"--value={none_str}", None)


def test_bind_none_string_int_str_none_union(app, assert_parse_args):
    """For int | str | None, 'none' should become 'none' string (int fails, str succeeds)."""

    @app.default
    def default(value: int | str | None):
        pass

    assert_parse_args(default, "--value=none", "none")


@pytest.mark.parametrize("none_str", NONE_STRINGS)
def test_bind_none_string_positional(app, assert_parse_args, none_str):
    """Test that 'none' works for positional arguments too."""

    @app.default
    def default(value: int | None):
        pass

    assert_parse_args(default, none_str, None)
