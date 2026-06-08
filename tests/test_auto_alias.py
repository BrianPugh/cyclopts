from typing import Annotated

import pytest

from cyclopts import App, Parameter
from cyclopts.argument import ArgumentCollection


@pytest.mark.parametrize(
    "cmd, kwargs",
    [
        ("deploy -e prod -r 5", {"env": "prod", "replicas": 5}),
        ("deploy --env staging --replicas 3", {"env": "staging", "replicas": 3}),
    ],
)
def test_auto_alias_parses(app, assert_parse_args, cmd, kwargs):
    @app.command(auto_alias=True)
    def deploy(*, env: str, replicas: int = 10):
        pass

    assert_parse_args(deploy, cmd, **kwargs)


def test_auto_alias_opt_out(app, assert_parse_args):
    @app.command(auto_alias=True)
    def aliased(*, env: str):
        pass

    @app.command
    def plain(*, env: str):
        pass

    assert_parse_args(aliased, "aliased -e prod", env="prod")
    assert_parse_args(plain, "plain --env prod", env="prod")
    assert "-e" not in app["plain"].assemble_argument_collection()["--env"].parameter.name


def test_auto_alias_explicit_alias(app, assert_parse_args):
    @app.command(auto_alias=True)
    def deploy(*, env: Annotated[str, Parameter(alias="-E")], replicas: int = 10):
        pass

    assert_parse_args(deploy, "deploy -E prod -r 5", env="prod", replicas=5)


def test_auto_alias_same_letter(app, assert_parse_args):
    @app.command(auto_alias=True)
    def deploy(*, env: str, endpoint: str):
        pass

    assert_parse_args(deploy, "deploy -e dev -E api", env="dev", endpoint="api")


def test_auto_alias_assignment():
    def keyword(*, env: str, endpoint: str, extra: str, replicas: int = 10):
        pass

    def positional(env, /, *, replicas: int = 10):
        pass

    collection = ArgumentCollection._from_callable(keyword, Parameter(auto_alias=True))
    assert "-e" in collection["--env"].parameter.name
    assert "-E" in collection["--endpoint"].parameter.name
    assert "-e" not in collection["--extra"].parameter.name
    assert "-r" in collection["--replicas"].parameter.name

    positional_collection = ArgumentCollection._from_callable(positional, Parameter(auto_alias=True))
    assert "-e" not in positional_collection["ENV"].parameter.name
    assert "-r" in positional_collection["--replicas"].parameter.name


def test_auto_alias_on_app_default():
    app = App(auto_alias=True, result_action="return_value")

    @app.default
    def main(*, env: str):
        return env

    assert app("-e prod") == "prod"


def test_auto_alias_combines_with_default_parameter(app):
    @app.command(auto_alias=True, default_parameter=Parameter(negative=""))
    def deploy(*, env: str, flag: bool = False):
        pass

    collection = app["deploy"].assemble_argument_collection()
    assert "-f" in collection["--flag"].parameter.name
    assert not collection["--flag"].negatives


def test_auto_alias_help(app, console):
    @app.command(auto_alias=True)
    def deploy(*, env: str, replicas: int = 10):
        """Deploy."""

    with console.capture() as capture:
        app("deploy --help", console=console)

    output = capture.get()
    assert "--env -e" in output
    assert "--replicas -r" in output
