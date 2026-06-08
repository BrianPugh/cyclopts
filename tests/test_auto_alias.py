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
    def deploy(env: str = "staging", replicas: int = 10):
        pass

    assert_parse_args(deploy, cmd, **kwargs)


def test_auto_alias_opt_out(app, assert_parse_args):
    @app.command(auto_alias=True)
    def aliased(env: str = "prod"):
        pass

    @app.command
    def plain(env: str = "prod"):
        pass

    assert_parse_args(aliased, "aliased -e prod", env="prod")
    assert_parse_args(plain, "plain --env prod", env="prod")
    assert "-e" not in app["plain"].assemble_argument_collection()["--env"].parameter.name


def test_auto_alias_explicit_alias(app, assert_parse_args):
    @app.command(auto_alias=True)
    def deploy(env: Annotated[str, Parameter(alias="-E")] = "prod", replicas: int = 10):
        pass

    assert_parse_args(deploy, "deploy -E prod -r 5", env="prod", replicas=5)


def test_auto_alias_same_letter(app, assert_parse_args):
    @app.command(auto_alias=True)
    def deploy(env: str = "dev", endpoint: str = "api"):
        pass

    assert_parse_args(deploy, "deploy -e dev -E api", env="dev", endpoint="api")


def test_auto_alias_assignment():
    def keyword(env: str = "a", endpoint: str = "b", extra: str = "c", replicas: int = 10):
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
    def main(env: str = "prod"):
        return env

    assert app("-e prod") == "prod"


def test_auto_alias_combines_with_default_parameter(app):
    @app.command(auto_alias=True, default_parameter=Parameter(negative=""))
    def deploy(env: str = "prod", flag: bool = False):
        pass

    collection = app["deploy"].assemble_argument_collection()
    assert "-f" in collection["--flag"].parameter.name
    assert not collection["--flag"].negatives


def test_auto_alias_skips_help_flag(app, assert_parse_args):
    @app.command(auto_alias=True)
    def connect(host: str = "localhost", port: int = 8080):
        pass

    collection = app["connect"].assemble_argument_collection()
    assert "-h" not in collection["--host"].parameter.name
    assert "-H" in collection["--host"].parameter.name
    assert_parse_args(connect, "connect -H localhost -p 9000", host="localhost", port=9000)


def test_auto_alias_uses_help_flag_when_unreserved(app):
    @app.command(auto_alias=True, help_flags=["--help"])
    def connect(host: str = "localhost"):
        pass

    collection = app["connect"].assemble_argument_collection()
    assert "-h" in collection["--host"].parameter.name


def test_auto_alias_skips_version_flag(app):
    @app.command(auto_alias=True, version_flags=["-v", "--version"])
    def main(verbose: bool = False):
        pass

    collection = app["main"].assemble_argument_collection()
    assert "-v" not in collection["--verbose"].parameter.name


def test_auto_alias_help(app, console):
    @app.command(auto_alias=True)
    def deploy(env: str = "staging", replicas: int = 10):
        """Deploy."""

    with console.capture() as capture:
        app("deploy --help", console=console)

    output = capture.get()
    assert "--env -e" in output
    assert "--replicas -r" in output
