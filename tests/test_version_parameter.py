"""From issue #219."""

import pytest


@pytest.mark.parametrize(
    "cmd",
    [
        "foo --version 1.2.3",
        "foo --version=1.2.3",
    ],
)
def test_version_subapp_version_parameter(app, assert_parse_args, cmd):
    @app.command(version_flags=[])
    def foo(version: str):
        pass

    assert_parse_args(foo, cmd, version="1.2.3")


@pytest.mark.parametrize(
    "cmd",
    [
        "foo --help 1.2.3",
        "foo --help=1.2.3",
    ],
)
def test_version_subapp_help_parameter(app, assert_parse_args, cmd):
    @app.command(help_flags=[])
    def foo(help: str):
        pass

    assert_parse_args(foo, cmd, help="1.2.3")
