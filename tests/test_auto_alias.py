from typing import Annotated

from cyclopts import App, Parameter
from cyclopts.argument import ArgumentCollection


def _arg_named(collection, name: str):
    return next(arg for arg in collection if arg.field_info.name == name)


def test_auto_alias_on_command():
    app = App(result_action="return_value")

    @app.command(auto_alias=True)
    def deploy(*, env: str, replicas: int = 10):
        return env, replicas

    assert app("deploy -e prod -r 5") == ("prod", 5)
    assert app("deploy --env staging --replicas 3") == ("staging", 3)


def test_auto_alias_not_on_other_commands():
    app = App(result_action="return_value")

    @app.command(auto_alias=True)
    def aliased(*, env: str):
        return env

    @app.command
    def plain(*, env: str):
        return env

    assert app("aliased -e prod") == "prod"

    aliased_collection = app["aliased"].assemble_argument_collection()
    plain_collection = app["plain"].assemble_argument_collection()
    assert "-e" in _arg_named(aliased_collection, "env").parameter.name
    assert "-e" not in _arg_named(plain_collection, "env").parameter.name


def test_auto_alias_explicit_alias_overrides():
    app = App(result_action="return_value")

    @app.command(default_parameter=Parameter(auto_alias=True))
    def deploy(
        *,
        env: Annotated[str, Parameter(alias="-E")],
        replicas: int = 10,
    ):
        return env, replicas

    assert app("deploy -E prod -r 5") == ("prod", 5)


def test_auto_alias_skips_collision():
    app = App(result_action="return_value")

    @app.command(default_parameter=Parameter(auto_alias=True))
    def deploy(*, env: str, endpoint: str):
        return env, endpoint

    collection = app["deploy"].assemble_argument_collection()
    env_arg = _arg_named(collection, "env")
    endpoint_arg = _arg_named(collection, "endpoint")

    assert "-e" in env_arg.parameter.name
    assert "-e" not in endpoint_arg.parameter.name


def test_auto_alias_skips_positional():
    app = App(result_action="return_value")

    @app.command(default_parameter=Parameter(auto_alias=True))
    def deploy(env, /, *, replicas: int = 10):
        return env, replicas

    collection = app["deploy"].assemble_argument_collection()
    env_arg = _arg_named(collection, "env")
    replicas_arg = _arg_named(collection, "replicas")

    assert "-e" not in env_arg.parameter.name
    assert "-r" in replicas_arg.parameter.name


def test_auto_alias_from_argument_collection():
    def deploy(*, env: str, replicas: int = 10):
        pass

    collection = ArgumentCollection._from_callable(deploy, Parameter(auto_alias=True))
    assert "-e" in _arg_named(collection, "env").parameter.name
    assert "-r" in _arg_named(collection, "replicas").parameter.name


def test_auto_alias_on_app_default():
    app = App(result_action="return_value", auto_alias=True)

    @app.default
    def main(*, env: str):
        return env

    assert app("-e prod") == "prod"


def test_auto_alias_command_kwarg_combines_with_default_parameter():
    app = App(result_action="return_value")

    @app.command(auto_alias=True, default_parameter=Parameter(negative=""))
    def deploy(*, env: str, flag: bool = False):
        return env, flag

    collection = app["deploy"].assemble_argument_collection()
    env_arg = _arg_named(collection, "env")
    flag_arg = _arg_named(collection, "flag")

    assert "-e" in env_arg.parameter.name
    assert "-f" in flag_arg.parameter.name
    assert not flag_arg.negatives


def test_auto_alias_help(app, console):

    @app.command(auto_alias=True)
    def deploy(*, env: str, replicas: int = 10):
        """Deploy."""

    with console.capture() as capture:
        app("deploy --help", console=console)

    output = capture.get()
    assert "--env -e" in output
    assert "--replicas -r" in output
