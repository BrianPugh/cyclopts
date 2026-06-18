from dataclasses import dataclass, field
from enum import Flag, auto
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
def test_short_alias_parses(app, assert_parse_args, cmd, kwargs):
    @app.command(short_alias=True)
    def deploy(env: str = "staging", replicas: int = 10):
        pass

    assert_parse_args(deploy, cmd, **kwargs)


def test_short_alias_opt_out(app, assert_parse_args):
    @app.command(short_alias=True)
    def aliased(env: str = "prod"):
        pass

    @app.command
    def plain(env: str = "prod"):
        pass

    assert_parse_args(aliased, "aliased -e prod", env="prod")
    assert_parse_args(plain, "plain --env prod", env="prod")
    collection = app["plain"].assemble_argument_collection()
    assert collection[0].parameter.name == ("--env",)


def test_short_alias_explicit_alias(app, assert_parse_args):
    @app.command(short_alias=True)
    def deploy(env: Annotated[str, Parameter(alias="-E")] = "prod", replicas: int = 10):
        pass

    assert_parse_args(deploy, "deploy -E prod -r 5", env="prod", replicas=5)


def test_short_alias_same_letter(app, assert_parse_args):
    @app.command(short_alias=True)
    def deploy(env: str = "dev", endpoint: str = "api"):
        pass

    assert_parse_args(deploy, "deploy -e dev -E api", env="dev", endpoint="api")


def test_short_alias_callable():
    def fn(host: str = "localhost", port: int = 8080):
        pass

    collection = ArgumentCollection._from_callable(
        fn,
        Parameter(short_alias=lambda field_info, _: f"-{field_info.names[0][0].upper()}"),
    )
    assert collection[0].parameter.name == ("--host", "-H")
    assert collection[1].parameter.name == ("--port", "-P")


def test_short_alias_assignment():
    def keyword(env: str = "a", endpoint: str = "b", extra: str = "c", replicas: int = 10):
        pass

    def positional(env, /, *, replicas: int = 10):
        pass

    collection = ArgumentCollection._from_callable(keyword, Parameter(short_alias=True))
    assert collection[0].parameter.name == ("--env", "-e")
    assert collection[1].parameter.name == ("--endpoint", "-E")
    assert collection[2].parameter.name == ("--extra",)
    assert collection[3].parameter.name == ("--replicas", "-r")

    positional_collection = ArgumentCollection._from_callable(positional, Parameter(short_alias=True))
    assert positional_collection[0].parameter.name == ("ENV",)
    assert positional_collection[1].parameter.name == ("--replicas", "-r")


def test_short_alias_on_app_default():
    app = App(short_alias=True, result_action="return_value")

    @app.default
    def main(env: str = "prod"):
        return env

    assert app("-e prod") == "prod"


def test_short_alias_combines_with_default_parameter(app):
    @app.command(short_alias=True, default_parameter=Parameter(negative=""))
    def deploy(env: str = "prod", flag: bool = False):
        pass

    collection = app["deploy"].assemble_argument_collection()
    assert collection[1].parameter.name == ("--flag", "-f")
    assert not collection[1].negatives


def test_short_alias_skips_help_flag(app, assert_parse_args):
    @app.command(short_alias=True)
    def connect(host: str = "localhost", port: int = 8080):
        pass

    collection = app["connect"].assemble_argument_collection()
    assert collection[0].parameter.name == ("--host", "-H")
    assert_parse_args(connect, "connect -H localhost -p 9000", host="localhost", port=9000)


def test_short_alias_uses_help_flag_when_unreserved(app):
    @app.command(short_alias=True, help_flags=["--help"])
    def connect(host: str = "localhost"):
        pass

    collection = app["connect"].assemble_argument_collection()
    assert collection[0].parameter.name == ("--host", "-h")


def test_short_alias_skips_version_flag(app):
    @app.command(short_alias=True, version_flags=["-v", "--version"])
    def main(verbose: bool = False):
        pass

    collection = app["main"].assemble_argument_collection()
    assert collection[0].parameter.name == ("--verbose", "-V")


def test_short_alias_nested_dataclass_top_level_only(app, assert_parse_args):
    """Containers and their promoted fields get no auto short by default; only top-level scalars do."""

    @dataclass
    class Color:
        red: int = 0
        green: int = 0

    @dataclass
    class User:
        name: str = ""
        color: Color = field(default_factory=Color)

    @app.command(short_alias=True)
    def foo(*, user: User | None = None, upload: bool = False):
        pass

    collection = app["foo"].assemble_argument_collection()
    names = {c.parameter.name[0]: c.parameter.name for c in collection}
    # The container and every promoted field get no short (no ``-u``, no ``-u.name``, no ``-n``).
    assert names["--user"] == ("--user",)
    assert names["--user.name"] == ("--user.name",)
    assert names["--user.color.red"] == ("--user.color.red",)
    # Only the top-level scalar gets a short.
    assert names["--upload"] == ("--upload", "-u")
    assert_parse_args(foo, "foo -u", upload=True)


def test_short_alias_nested_field_explicit_opt_in(app, assert_parse_args):
    """A nested leaf field opts in explicitly and surfaces a standalone (not dotted) short."""

    @dataclass
    class User:
        name: Annotated[str, Parameter(short_alias=True)] = ""
        color: str = ""

    @app.command(short_alias=True)
    def foo(*, user: User):
        pass

    collection = app["foo"].assemble_argument_collection()
    names = {c.parameter.name[0]: c.parameter.name for c in collection}
    assert names["--user.name"] == ("--user.name", "-n")
    assert names["--user.color"] == ("--user.color",)
    assert_parse_args(foo, "foo -n Bob", user=User(name="Bob"))


def test_short_alias_letter_from_transformed_name(app):
    """The short letter follows the transformed long flag, not the raw python identifier."""

    @app.command(short_alias=True)
    def foo(*, _private: str = "", verbose: bool = False):
        pass

    collection = app["foo"].assemble_argument_collection()
    names = {c.parameter.name[0]: c.parameter.name for c in collection}
    assert names["--private"] == ("--private", "-p")  # not "-_"
    assert names["--verbose"] == ("--verbose", "-v")


def test_short_alias_letter_respects_custom_name_transform(app):
    """A custom name_transform drives both the long name and the short letter."""

    @app.command(short_alias=True, default_parameter=Parameter(name_transform=lambda s: "x" + s))
    def foo(*, my_flag: bool = False):
        pass

    collection = app["foo"].assemble_argument_collection()
    assert collection[0].parameter.name == ("--xmy_flag", "-x")


def test_short_alias_help(app, console):
    @app.command(short_alias=True)
    def deploy(env: str = "staging", replicas: int = 10):
        """Deploy."""

    with console.capture() as capture:
        app("deploy --help", console=console)

    output = capture.get()
    assert "--env -e" in output
    assert "--replicas -r" in output


def test_short_alias_rejects_string():
    """A string is a footgun (looks like an explicit flag); reject it with a clear error."""
    with pytest.raises(TypeError, match="does not accept a string"):
        Parameter(short_alias="-z")  # pyright: ignore[reportArgumentType]


def test_short_alias_combined_flags(app, assert_parse_args):
    """Two generated boolean shorts can be combined GNU-style (``-vf``)."""
    app.default_parameter = Parameter(short_alias=True)

    @app.default
    def main(*, verbose: bool = False, force: bool = False):
        pass

    assert_parse_args(main, "-vf", verbose=True, force=True)


def test_short_alias_no_negative_for_short(app):
    """A boolean's short flag does not get a negated form (negatives are long-only)."""

    @app.command(short_alias=True)
    def main(*, verbose: bool = False):
        pass

    arg = app["main"].assemble_argument_collection()[0]
    assert arg.parameter.name == ("--verbose", "-v")
    assert "--no-verbose" in arg.names
    assert "--no-v" not in arg.names
    assert "-no-v" not in arg.names


def test_short_alias_enum_flag_gets_short(app):
    """An enum.Flag binds tokens directly, so it receives a short; its members do not."""

    class Perm(Flag):
        read = auto()
        write = auto()

    @app.command(short_alias=True)
    def main(*, perm: Perm = Perm.read):
        pass

    names = {c.parameter.name[0]: c.parameter.name for c in app["main"].assemble_argument_collection()}
    assert names["--perm"] == ("--perm", "-p")
    assert names["--perm.read"] == ("--perm.read",)


def test_short_alias_accepts_keys_false_gets_short(app):
    """A class with accepts_keys=False consumes tokens directly, so it gets a short."""

    @dataclass
    class Point:
        x: int = 0
        y: int = 0

    @app.command(short_alias=True)
    def main(*, pt: Annotated[Point, Parameter(accepts_keys=False)]):
        pass

    assert app["main"].assemble_argument_collection()[0].parameter.name == ("--pt", "-p")


def test_short_alias_callable_none_skips():
    """A callable returning None generates no short for that parameter."""

    def fn(host: str = "", port: int = 0):
        pass

    collection = ArgumentCollection._from_callable(fn, Parameter(short_alias=lambda fi, used: None))
    assert collection[0].parameter.name == ("--host",)
    assert collection[1].parameter.name == ("--port",)


def test_short_alias_callable_can_dedupe_via_used():
    """A well-behaved callable consults ``used`` to avoid collisions."""

    def unique(field_info, used):
        letter = field_info.names[0][0]
        for candidate in (f"-{letter}", f"-{letter.upper()}"):
            if candidate not in used:
                return candidate
        return None

    def fn(alpha: str = "", apex: str = ""):
        pass

    collection = ArgumentCollection._from_callable(fn, Parameter(short_alias=unique))
    assert collection[0].parameter.name == ("--alpha", "-a")
    assert collection[1].parameter.name == ("--apex", "-A")


def test_short_alias_callable_collision_not_deduped():
    """KNOWN LIMITATION: a callable that ignores ``used`` produces duplicate shorts.

    Unlike the bool form (lowercase -> uppercase -> drop), cyclopts does not dedupe
    callable-returned shorts. This locks in the documented current behavior.
    """

    def fn(alpha: str = "", beta: str = ""):
        pass

    collection = ArgumentCollection._from_callable(fn, Parameter(short_alias=lambda fi, used: "-a"))
    assert collection[0].parameter.name == ("--alpha", "-a")
    assert collection[1].parameter.name == ("--beta", "-a")


def test_short_alias_propagates_to_subapp_at_runtime():
    """``short_alias=True`` on a root app reaches commands registered on a subapp at parse time."""
    root = App(name="root", short_alias=True, result_action="return_value")
    sub = App(name="sub")
    root.command(sub)

    @sub.command
    def deploy(env: str = "x"):
        return env

    assert root(["sub", "deploy", "-e", "prod"]) == "prod"


def test_short_alias_does_not_affect_env_var(app, assert_parse_args, monkeypatch):
    """Adding a short flag leaves the canonical-name-derived env var lookup intact."""
    monkeypatch.setenv("MYAPP_ENV", "from_env")

    @app.default
    def main(env: Annotated[str, Parameter(env_var="MYAPP_ENV", short_alias=True)] = "default"):
        pass

    assert app.assemble_argument_collection()[0].parameter.name == ("--env", "-e")
    assert_parse_args(main, "", env="from_env")
