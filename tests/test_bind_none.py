from pathlib import Path
from typing import Annotated

import pytest

from cyclopts import Parameter


def test_bind_negative_none(app, assert_parse_args):
    @app.default
    def default(path: Annotated[Path | None, Parameter(negative_none="default-")]):
        pass

    assert_parse_args(default, "--default-path", None)


@pytest.mark.parametrize(
    "cmd_str,expected",
    [
        ("--val 42", 42),
        ("--null", None),
    ],
)
def test_bind_negative_explicit_int(app, cmd_str, expected, assert_parse_args):
    """Test explicit negative flag for int | None sets value to None."""

    @app.default
    def default(val: Annotated[int | None, Parameter(negative="--null")] = 99):
        pass

    assert_parse_args(default, cmd_str, expected)


def test_negative_empty_overrides_all(app):
    """Setting negative=() disables ALL automatic negative generation."""

    @app.default
    def default(
        flag: Annotated[bool | None, Parameter(negative=(), negative_none="none-")] = True,
    ):
        pass

    # Verify that neither --no-flag nor --none-flag are available
    argument = app.assemble_argument_collection()[0]
    assert "--no-flag" not in argument.names
    assert "--none-flag" not in argument.names


def test_negative_bool_empty_preserves_negative_none(app, assert_parse_args):
    """Setting negative_bool='' disables bool negatives but preserves negative_none."""

    @app.default
    def default(
        flag: Annotated[bool | None, Parameter(negative_bool="", negative_none="none-")] = True,
    ):
        pass

    # Verify that --no-flag is NOT available but --none-flag IS available
    argument = app.assemble_argument_collection()[0]
    assert "--no-flag" not in argument.names
    assert "--none-flag" in argument.names

    # Verify the negative_none flag works
    assert_parse_args(default, "--none-flag", None)
