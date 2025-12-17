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
