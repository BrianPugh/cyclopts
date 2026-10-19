from dataclasses import dataclass, field
from enum import Flag, auto
from pathlib import Path
from textwrap import dedent
from typing import Annotated, Literal, NamedTuple, NewType, TypedDict, Union

import pytest
from attrs import define

from cyclopts import Parameter
from cyclopts.exceptions import CoercionError, MissingArgumentError, RepeatArgumentError
from cyclopts.validators import Number


@pytest.mark.parametrize(
    "cmd_str,expected",
    [
        ("foo 1", 1),
        ("foo --a=1", 1),
        ("foo --a 1", 1),
        ("foo bar", "bar"),
        ("foo --a=bar", "bar"),
        ("foo --a bar", "bar"),
    ],
)
@pytest.mark.parametrize("annotated", [False, True])
def test_union_required_implicit_coercion(app, cmd_str, expected, annotated, assert_parse_args):
    """
    For a union without an explicit coercion, the first non-None type annotation
    should be used. In this case, it's ``int``.
    """
    if annotated:

        @app.command
        def foo(a: Annotated[None | int | str, Parameter(help="help for a")]):
            pass

    else:

        @app.command
        def foo(a: None | int | str):
            pass

    assert_parse_args(foo, cmd_str, expected)


def test_union_coercion_cannot_coerce_error(app, console):
    @app.default
    def default(a: None | int | float):
        pass

    with console.capture() as capture, pytest.raises(CoercionError):
        app.parse_args("foo", error_console=console, exit_on_error=False)

    actual = capture.get()

    expected = dedent(
        """\
        ╭─ Error ────────────────────────────────────────────────────────────╮
        │ Invalid value for A: unable to convert "foo" into None|int|float.  │
        ╰────────────────────────────────────────────────────────────────────╯
        """
    )

    assert actual == expected


@pytest.mark.parametrize(
    "cmd_str,expected",
    [
        ("bar", ["bar"]),
        ("bar baz", ["bar", "baz"]),
    ],
)
def test_union_of_list_types(app, cmd_str, expected, assert_parse_args):
    """list[str] | list[Path] should work as a union of list types (issue #780)."""

    @app.default
    def foo(paths: list[str] | list[Path]):
        pass

    assert_parse_args(foo, cmd_str, expected)


@pytest.mark.parametrize(
    "cmd_str,expected",
    [
        ("bar", ["bar"]),
        ("bar baz", ["bar", "baz"]),
    ],
)
def test_union_of_list_types_optional(app, cmd_str, expected, assert_parse_args):
    """list[str] | list[Path] | None should work as a union of list types."""

    @app.default
    def foo(paths: list[str] | list[Path] | None = None):
        pass

    assert_parse_args(foo, cmd_str, expected)


@dataclass
class _TimeRange:
    start: int
    end: int


@dataclass
class _Live:
    live: Annotated[bool, Parameter(negative=())]


def test_union_of_dataclasses_branch_selection(app, assert_parse_args):
    """A ``Union`` of keyword-accepting types instantiates the branch matching supplied fields.

    Each branch's requiredness is evaluated independently, so supplying one member's fields
    does not demand a sibling member's required fields (issue #839 follow-up / PR #840).
    """

    @app.command
    def cli(*, time_period: Union[_TimeRange, _Live]):
        pass

    # ``_Live`` branch: ``start``/``end`` from ``_TimeRange`` are not demanded.
    assert_parse_args(cli, "cli --time-period.live", time_period=_Live(live=True))
    # ``_TimeRange`` branch: ``live`` from ``_Live`` is not demanded.
    assert_parse_args(
        cli,
        "cli --time-period.start 1 --time-period.end 2",
        time_period=_TimeRange(start=1, end=2),
    )


def test_union_of_dataclasses_missing_active_branch_field(app):
    """A partially-supplied branch still reports its own missing required field."""

    @app.command
    def cli(*, time_period: Union[_TimeRange, _Live]):
        pass

    with pytest.raises(MissingArgumentError) as e:
        app.parse_args("cli --time-period.start 1", print_error=False, exit_on_error=False)
    assert e.value.argument is not None
    assert e.value.argument.name == "--time-period.end"


@dataclass
class _Cat:
    kind: str
    meow: int


@dataclass
class _Dog:
    kind: str
    bark: int


def test_union_of_dataclasses_overlapping_fields(app, assert_parse_args):
    """Branches sharing a field name resolve by which branch fully accounts for the input."""

    @app.command
    def cli(*, pet: Union[_Cat, _Dog]):
        pass

    assert_parse_args(cli, "cli --pet.kind x --pet.bark 2", pet=_Dog(kind="x", bark=2))
    assert_parse_args(cli, "cli --pet.kind x --pet.meow 5", pet=_Cat(kind="x", meow=5))


@dataclass
class _Small:
    a: int


@dataclass
class _Big:
    a: int
    b: int


@pytest.mark.parametrize("hint", [Union[_Small, _Big], Union[_Big, _Small]])
def test_union_of_dataclasses_subset_branch_reachable(app, assert_parse_args, hint):
    """A branch whose fields are a subset of another's is still selectable (order-independent)."""

    @app.command
    def cli(*, x: hint):  # pyright: ignore[reportInvalidTypeForm]
        pass

    # Only the subset branch's field -> the subset branch.
    assert_parse_args(cli, "cli --x.a 1", x=_Small(a=1))
    # Both fields -> the superset branch.
    assert_parse_args(cli, "cli --x.a 1 --x.b 2", x=_Big(a=1, b=2))


def test_union_of_dataclasses_ambiguous_fields_error(app):
    """Supplying fields spanning multiple branches yields a clean CoercionError, not a TypeError."""

    @app.command
    def cli(*, time_period: Union[_TimeRange, _Live]):
        pass

    with pytest.raises(CoercionError):
        app.parse_args(
            "cli --time-period.start 1 --time-period.end 2 --time-period.live 3",
            print_error=False,
            exit_on_error=False,
        )


def test_union_scalar_and_consume_all_member_multiple_tokens(app, assert_parse_args):
    """A union of a scalar and a list type must convert repeated tokens as ONE
    list value (a member of the union), not element-wise into a list of scalars.
    """

    @app.default
    def default(*, a: str | list[int] = "d"):
        pass

    assert_parse_args(default, "--a 1 --a 2", a=[1, 2])


def test_union_member_order_is_per_parameter(app, assert_parse_args):
    """``int | str`` and ``str | int`` compare equal but convert differently; each
    parameter must get its own order-respecting conversion for the same token.
    """

    @app.default
    def default(a: int | str = 0, b: str | int = "", y: None | str = "d", z: str | None = "d"):
        pass

    assert_parse_args(default, "--a 5 --b 5 --y none --z none", 5, "5", None, "none")


def test_same_type_same_tokens_do_not_alias(app):
    @app.default
    def default(a: list[int], b: list[int]):
        return a is b

    assert app("--a 1 --a 2 --b 1 --b 2") is False


_Metadata = Literal["subtitles", "thumbnail", "info-json"]


@pytest.mark.parametrize("consume_multiple", [False, True])
@pytest.mark.parametrize(
    "hint,cmd,expected",
    [
        (bool | tuple[_Metadata, ...], "--write-metadata", True),
        (bool | tuple[_Metadata, ...], "--write-metadata --other 1", True),
        (bool | tuple[_Metadata, ...], "--write-metadata=false", False),
        (bool | tuple[_Metadata, ...], "--write-metadata true", True),
        (bool | tuple[_Metadata, ...], "--write-metadata subtitles", ("subtitles",)),
        (bool | tuple[_Metadata, ...], "--no-write-metadata", False),
        (bool | tuple[_Metadata, ...], "--no-write-metadata=false", True),
        (bool | tuple[_Metadata, ...], "--empty-write-metadata", ()),
        (tuple[_Metadata, ...] | bool, "--write-metadata", True),
        (tuple[_Metadata, ...] | bool, "--no-write-metadata", False),
        (tuple[_Metadata, ...] | bool, "--empty-write-metadata", ()),
        (bool | list[str], "--write-metadata", True),
        (bool | list[str], "--write-metadata foo", ["foo"]),
        (bool | list[str], "--no-write-metadata", False),
        (bool | list[str], "--empty-write-metadata", []),
        (bool | int, "--write-metadata", True),
        (bool | int, "--write-metadata 5", 5),
        (bool | int, "--no-write-metadata", False),
    ],
)
def test_union_bool_and_value_flag(app, assert_parse_args, hint, cmd, expected, consume_multiple):
    """A union containing ``bool`` acts as a flag when given no value (#972)."""

    @app.default
    def default(
        *,
        write_metadata: Annotated[hint, Parameter(consume_multiple=consume_multiple)] = False,  # pyright: ignore
        other: int = 0,
    ):
        pass

    if "--other" in cmd:
        assert_parse_args(default, cmd, write_metadata=expected, other=1)
    else:
        assert_parse_args(default, cmd, write_metadata=expected)


def test_union_bool_and_tuple_custom_negative(app, assert_parse_args):
    @app.default
    def default(
        *,
        write_metadata: Annotated[
            bool | tuple[_Metadata, ...],
            Parameter(negative="--no-write", consume_multiple=True),
        ] = False,
    ):
        pass

    assert_parse_args(default, "--no-write", write_metadata=False)


_Name = NewType("_Name", str)


class _FlagTypedDict(TypedDict):
    a: int


@dataclass
class _FlagDataclass:
    a: int


class _FlagNamedTuple(NamedTuple):
    a: int


@pytest.mark.parametrize(
    "hint",
    [
        # Unique Literal values: typing caches unions, so reusing ``bool | Literal[...]``'s members
        # would silently return the bool-first ordering and mask a failure.
        Literal["lit-first-a", "lit-first-b"] | bool,
        _Name | bool,
    ],
)
@pytest.mark.parametrize("cmd,expected", [("--x", True), ("--no-x", False)])
def test_union_bool_non_class_member_first(app, assert_parse_args, hint, cmd, expected):
    @app.default
    def default(*, x: hint = False):  # pyright: ignore
        pass

    assert_parse_args(default, cmd, x=expected)


@pytest.mark.parametrize("hint", [_FlagTypedDict | bool, _FlagDataclass | bool, _FlagNamedTuple | bool])
@pytest.mark.parametrize("cmd,expected", [("--x", True), ("--no-x", False)])
def test_union_bool_class_member_first(app, assert_parse_args, hint, cmd, expected):
    @app.default
    def default(*, x: hint = False):  # pyright: ignore
        pass

    assert_parse_args(default, cmd, x=expected)


@define
class _FlagAttrs:
    a: int
    b: int = 2


@pytest.mark.parametrize(
    "hint,cls",
    [
        (_FlagDataclass | bool, _FlagDataclass),
        (bool | _FlagDataclass, _FlagDataclass),
        (_FlagAttrs | bool, _FlagAttrs),
        (bool | _FlagAttrs, _FlagAttrs),
    ],
)
def test_union_bool_class_member_keys(app, assert_parse_args, hint, cls):
    """``--x.<field>`` options build the class member of a union with ``bool`` (#990)."""

    @app.default
    def default(*, x: hint = False):  # pyright: ignore
        pass

    assert_parse_args(default, "--x.a 1", x=cls(a=1))
    assert_parse_args(default, "--x", x=True)


@pytest.mark.parametrize("hint", [_FlagAttrs | bool, bool | _FlagAttrs])
def test_union_bool_class_member_keys_missing_field(app, hint):
    @app.default
    def default(*, x: hint = False):  # pyright: ignore
        pass

    with pytest.raises(MissingArgumentError):
        app.parse_args("--x.b 3", print_error=False, exit_on_error=False)


@pytest.mark.parametrize("hint", [_FlagDataclass | bool, _FlagAttrs | bool])
@pytest.mark.parametrize("cmd", ["--x --x.a 1", "--x.a 1 --x", "--no-x --x.a 1", "--x=false --x.a 1"])
def test_union_bool_class_member_flag_mixed_with_keys(app, hint, cmd):
    """A bool value alongside ``--x.<field>`` is rejected, not silently dropped."""

    @app.default
    def default(*, x: hint = False):  # pyright: ignore
        pass

    with pytest.raises(CoercionError):
        app.parse_args(cmd, print_error=False, exit_on_error=False)


@pytest.mark.parametrize("hint", [_FlagDataclass | bool, _FlagAttrs | bool])
@pytest.mark.parametrize("cmd,expected", [("--x", True), ("--no-x", False)])
def test_union_bool_class_member_required_flag(app, assert_parse_args, hint, cmd, expected):
    @app.default
    def default(*, x: hint):  # pyright: ignore
        pass

    assert_parse_args(default, cmd, x=expected)


@dataclass
class _DefaultsA:
    a: int = 1


@dataclass
class _DefaultsB:
    b: int = 2


@pytest.mark.parametrize(
    "hint,expected",
    [
        (_DefaultsA | bool, _DefaultsA()),
        (bool | _DefaultsA, _DefaultsA()),
        (_DefaultsA | _DefaultsB, _DefaultsA()),
    ],
)
@pytest.mark.parametrize("cmd", ["--x={}", "--x {}"])
def test_union_class_member_explicit_empty_mapping(app, assert_parse_args, hint, expected, cmd):
    @app.default
    def default(*, x: hint = False):  # pyright: ignore
        pass

    assert_parse_args(default, cmd, x=expected)


@pytest.mark.parametrize("hint", [_FlagAttrs | bool, bool | _FlagAttrs])
def test_union_class_member_explicit_empty_mapping_missing_field(app, hint):
    @app.default
    def default(*, x: hint = False):  # pyright: ignore
        pass

    with pytest.raises(MissingArgumentError) as e:
        app.parse_args("--x={}", print_error=False, exit_on_error=False)
    assert e.value.argument is not None
    assert e.value.argument.name == "--x.a"


class _FlagTypedDictPair(TypedDict):
    a: int
    b: int


@pytest.mark.parametrize("hint", [_FlagTypedDictPair | bool, bool | _FlagTypedDictPair])
def test_union_bool_typeddict_keys(app, assert_parse_args, hint):
    @app.default
    def default(*, x: hint = False):  # pyright: ignore
        pass

    assert_parse_args(default, "--x.a 1 --x.b 2", x={"a": 1, "b": 2})
    with pytest.raises(MissingArgumentError):
        app.parse_args("--x.a 1", print_error=False, exit_on_error=False)


@pytest.mark.parametrize(
    "hint,cmd",
    [
        (_FlagTypedDict | bool, "--x --x"),
        (bool | list[str], "--x --x"),
        (bool | list[str], "--x a --no-x"),
        (bool | list[str], "--no-x --x a"),
        (bool | list[str], "--empty-x --x a"),
        (list[str], "--empty-x --x a"),
        (list[str], "--x a --empty-x"),
    ],
)
def test_union_bool_flag_repeat_error(app, hint, cmd):
    @app.default
    def default(*, x: hint = False):  # pyright: ignore
        pass

    with pytest.raises(RepeatArgumentError):
        app.parse_args(cmd, print_error=False, exit_on_error=False)


@pytest.mark.parametrize(
    "cmd,expected",
    [
        ("--x --x", True),
        ("--x a --no-x", False),
        ("--no-x --x a", ["a"]),
        ("--x --x a --x b", ["a", "b"]),
    ],
)
def test_union_bool_flag_allow_repeating_last_wins(app, assert_parse_args, cmd, expected):
    @app.default
    def default(*, x: Annotated[bool | list[str], Parameter(allow_repeating=True)] = False):
        pass

    assert_parse_args(default, cmd, x=expected)


@pytest.mark.parametrize(
    "cmd,expected",
    [
        ("--x a b --no-x", False),
        ("--x a b --x", True),
        ("--no-x --x a b", ["a", "b"]),
        ("--x a b --x c", ["a", "b", "c"]),
    ],
)
def test_union_bool_flag_allow_repeating_consume_multiple(app, assert_parse_args, cmd, expected):
    @app.default
    def default(*, x: Annotated[bool | list[str], Parameter(allow_repeating=True, consume_multiple=True)] = False):
        pass

    assert_parse_args(default, cmd, x=expected)


@pytest.mark.parametrize("cmd,expected", [("--x --x", True), ("--x --no-x", False)])
def test_union_bool_flag_allow_repeating_typeddict(app, assert_parse_args, cmd, expected):
    @app.default
    def default(*, x: Annotated[_FlagTypedDict | bool, Parameter(allow_repeating=True)] = False):
        pass

    assert_parse_args(default, cmd, x=expected)


@pytest.mark.parametrize("consume_multiple", [False, True])
@pytest.mark.parametrize(
    "hint",
    [
        bool | tuple[_Metadata, ...],
        tuple[_Metadata, ...] | bool,
        _Metadata | bool,
        bool | tuple[_Metadata, ...] | None,
        _Metadata | None | bool,
    ],
)
def test_union_bool_invalid_value_reports_member_error(app, hint, consume_multiple):
    """With ``bool`` as the only other member, a bad value reports the value member's error (#972)."""

    @app.default
    def default(*, x: Annotated[hint, Parameter(consume_multiple=consume_multiple)] = False):  # pyright: ignore
        pass

    with pytest.raises(CoercionError) as e:
        app.parse_args("--x sub", print_error=False, exit_on_error=False)
    assert 'Invalid value "sub" for --x. Choose from: "subtitles", "thumbnail", "info-json".' in str(e.value)


def test_union_bool_consume_multiple_invalid_later_value(app):
    """A bad value after a good one is a choices error, not an unused token (#972)."""

    @app.default
    def default(*, x: Annotated[bool | tuple[_Metadata, ...], Parameter(consume_multiple=True)] = False):
        pass

    with pytest.raises(CoercionError) as e:
        app.parse_args("--x subtitles info-jsonn", print_error=False, exit_on_error=False)
    assert 'Invalid value "info-jsonn" for --x.' in str(e.value)
    assert 'Did you mean "info-json"?' in str(e.value)


def test_union_multiple_value_members_keeps_generic_error(app):
    @app.default
    def default(*, x: int | _Metadata = 0):
        pass

    with pytest.raises(CoercionError) as e:
        app.parse_args("--x sub", print_error=False, exit_on_error=False)
    assert "unable to convert" in str(e.value)


@pytest.mark.parametrize("consume_multiple", [False, True])
@pytest.mark.parametrize(
    "hint",
    [bool | tuple[_Metadata, ...], bool | list[int], bool | tuple[int, int], bool | list[int] | None],
)
@pytest.mark.parametrize("cmd,expected", [("--x true pos", True), ("--x false pos", False), ("--x=yes pos", True)])
def test_union_bool_explicit_value_leaves_trailing_positional(
    app, assert_parse_args, hint, consume_multiple, cmd, expected
):
    @app.default
    def default(pos: str, *, x: Annotated[hint, Parameter(consume_multiple=consume_multiple)] = False):  # pyright: ignore
        pass

    assert_parse_args(default, cmd, "pos", x=expected)


@dataclass
class _Point:
    a: int
    b: int


@pytest.mark.parametrize(
    "hint",
    [
        bool | tuple[int, int],
        bool | list[tuple[int, int]],
        bool | tuple[tuple[int, int], int],
        bool | _Point,
        bool | tuple[Annotated[int, Parameter(validator=Number(gt=5))], int],
    ],
)
def test_union_bool_value_member_element_missing_token(app, hint):
    """``"1"`` is a bool word, but it is also a valid first token of the value member."""

    @app.default
    def default(*, x: hint = False):  # pyright: ignore
        pass

    with pytest.raises(MissingArgumentError):
        app.parse_args("--x 1", print_error=False, exit_on_error=False)


@pytest.mark.parametrize("cmd,expected", [("true", True), ("1 2 3", [1, 2, 3])])
def test_union_bool_positional_list(app, assert_parse_args, cmd, expected):
    @app.default
    def default(x: bool | list[int]):
        pass

    assert_parse_args(default, cmd, expected)


def test_union_bool_positional_list_invalid_later_value(app):
    @app.default
    def default(x: bool | list[int]):
        pass

    with pytest.raises(CoercionError) as e:
        app.parse_args("1 2 foo", print_error=False, exit_on_error=False)
    assert 'unable to convert "foo" into int' in str(e.value)


class _Perm(Flag):
    READ = auto()
    WRITE = auto()


@pytest.mark.parametrize(
    "cmd,expected",
    [
        ("--x", True),
        ("--no-x", False),
        ("--x true", True),
        ("--x=false", False),
        ("--x read", _Perm.READ),
        ("--x.read", _Perm.READ),
        ("--x.read --x.write", _Perm.READ | _Perm.WRITE),
    ],
)
def test_union_bool_enum_flag(app, assert_parse_args, cmd, expected):
    @app.default
    def default(*, x: bool | _Perm = False):
        pass

    assert_parse_args(default, cmd, x=expected)


def test_union_bool_enum_flag_invalid_value(app):
    @app.default
    def default(*, x: bool | _Perm = False):
        pass

    with pytest.raises(CoercionError) as e:
        app.parse_args("--x reed", print_error=False, exit_on_error=False)
    assert 'Invalid value "reed" for --x. Choose from: "read", "write".' in str(e.value)


@pytest.mark.parametrize("cmd", ["--x true --x.write", "--x --x.write"])
def test_union_bool_enum_flag_mixed_with_keys(app, cmd):
    """A bool value alongside ``--x.<member>`` is rejected, not silently dropped."""

    @app.default
    def default(*, x: bool | _Perm = False):
        pass

    with pytest.raises(CoercionError):
        app.parse_args(cmd, print_error=False, exit_on_error=False)


def test_union_enum_flag_keyless_and_keyed_combine(app, assert_parse_args):
    @app.default
    def default(*, x: _Perm | str = "default"):
        pass

    assert_parse_args(default, "--x read --x.write", x=_Perm.READ | _Perm.WRITE)


@pytest.mark.parametrize("cmd,expected", [("--x read", _Perm.READ), ("--x foo", "foo")])
def test_union_enum_flag_other_member(app, assert_parse_args, cmd, expected):
    @app.default
    def default(*, x: _Perm | str = "default"):
        pass

    assert_parse_args(default, cmd, x=expected)


@dataclass
class _SourceUser:
    a: int = 1
    b: str = "s"


@pytest.mark.parametrize(
    "config, cmd, expected",
    [
        ({"x": {"a": 2}}, ["--no-x"], False),
        ({"x": {"a": 2}}, ["--x"], True),
        ({"x": False}, ["--x.a", "9"], _SourceUser(a=9)),
        ({"x": {"a": 2}}, ["--x.b", "q"], _SourceUser(a=2, b="q")),
    ],
)
def test_union_bool_class_cli_replaces_config(config, cmd, expected):
    """A keyless value and ``--x.<field>`` from different sources: the CLI replaces the config."""
    from cyclopts import App
    from cyclopts.config import Dict

    app = App(config=Dict(config), result_action="return_value")

    @app.default
    def main(*, x: _SourceUser | bool = False):
        return x

    assert app(cmd, exit_on_error=False) == expected


def test_union_bool_class_cli_replaces_env(monkeypatch):
    """A keyless env var value doesn't combine with ``--x.<field>`` from the CLI."""
    from cyclopts import App

    app = App(result_action="return_value")

    @app.default
    def main(*, x: Annotated[_SourceUser | bool, Parameter(env_var="X")] = False):
        return x

    monkeypatch.setenv("X", "true")
    assert app(["--x.a", "9"], exit_on_error=False) == _SourceUser(a=9)


def test_union_bool_class_same_source_mix_errors():
    """A keyless value and ``--x.<field>`` from the same source still error."""
    from cyclopts import App

    app = App(result_action="return_value")

    @app.default
    def main(*, x: _SourceUser | bool = False):
        return x

    with pytest.raises(CoercionError, match="Cannot combine"):
        app(["--x", "--x.a", "9"], exit_on_error=False)


def _source_app(*configs):
    from cyclopts import App

    app = App(config=list(configs), result_action="return_value")

    @app.default
    def main(*, x: _SourceUser | bool = False):
        return x

    return app


@pytest.mark.parametrize(
    "first, second, expected",
    [
        ({"x": False}, {"x": {"a": 2}}, False),
        ({"x": {"a": 2}}, {"x": False}, _SourceUser(a=2)),
    ],
)
def test_union_bool_class_earlier_config_wins_same_source_label(first, second, expected):
    """2 ``Dict`` configs share the ``"dict"`` source label but are still separate sources."""
    from cyclopts.config import Dict

    assert _source_app(Dict(first), Dict(second))([], exit_on_error=False) == expected


@pytest.mark.parametrize(
    "configs, env, cmd, expected",
    [
        ((), {"APP_X": "false"}, ["--x.a", "9"], _SourceUser(a=9)),
        ((), {"APP_X_A": "2"}, ["--no-x"], False),
        (({"x": {"a": 2}},), {"APP_X": "false"}, [], _SourceUser(a=2)),
        (({"x": False},), {"APP_X_A": "2"}, [], False),
    ],
)
def test_union_bool_class_config_env_precedence(monkeypatch, configs, env, cmd, expected):
    """``config.Env`` follows the same whole-parameter precedence as the other sources."""
    from cyclopts.config import Dict, Env

    for k, v in env.items():
        monkeypatch.setenv(k, v)
    app = _source_app(*(Dict(c) for c in configs), Env("APP_"))
    assert app(cmd, exit_on_error=False) == expected


def test_union_bool_class_config_env_same_source_mix_errors(monkeypatch):
    from cyclopts.config import Env

    monkeypatch.setenv("APP_X", "false")
    monkeypatch.setenv("APP_X_A", "2")
    with pytest.raises(CoercionError, match="Cannot combine"):
        _source_app(Env("APP_"))([], exit_on_error=False)


@pytest.mark.parametrize("hint", [_SourceUser, _SourceUser | None])
def test_class_json_merges_fields_from_other_source(hint):
    """A JSON object for a plain class still merges with field values from another source."""
    from cyclopts import App
    from cyclopts.config import Dict

    app = App(config=Dict({"x": {"b": "q"}}), result_action="return_value")

    @app.default
    def main(*, x: hint = None):  # pyright: ignore[reportInvalidTypeForm]
        return x

    assert app(["--x", '{"a": 9}'], exit_on_error=False) == _SourceUser(a=9, b="q")


def test_class_env_var_json_merges_cli_field(monkeypatch):
    from cyclopts import App

    app = App(result_action="return_value")

    @app.default
    def main(*, x: Annotated[_SourceUser, Parameter(env_var="X")]):
        return x

    monkeypatch.setenv("X", '{"b": "q"}')
    assert app(["--x.a", "9"], exit_on_error=False) == _SourceUser(a=9, b="q")


def test_class_config_json_string_merges_cli_field():
    from cyclopts import App
    from cyclopts.config import Dict

    app = App(config=Dict({"x": '{"b": "q"}'}), result_action="return_value")

    @app.default
    def main(*, x: _SourceUser):
        return x

    assert app(["--x.a", "9"], exit_on_error=False) == _SourceUser(a=9, b="q")


class _SourcePermission(Flag):
    READ = auto()
    WRITE = auto()


@pytest.mark.parametrize(
    "cmd, config, env",
    [
        (["--x", "read"], {"x": {"write": True}}, {}),
        (["--x.write"], {"x": "read"}, {}),
        (["--x.write"], {}, {"X": "read"}),
    ],
)
def test_enum_flag_combines_across_sources(monkeypatch, cmd, config, env):
    """A plain ``enum.Flag`` keeps OR-ing values from different sources."""
    from cyclopts import App
    from cyclopts.config import Dict

    for k, v in env.items():
        monkeypatch.setenv(k, v)
    app = App(config=Dict(config), result_action="return_value")

    @app.default
    def main(*, x: Annotated[_SourcePermission, Parameter(env_var="X")] = _SourcePermission(0)):  # noqa: B008
        return x

    assert app(cmd, exit_on_error=False) == _SourcePermission.READ | _SourcePermission.WRITE


@pytest.mark.parametrize("hint", [_SourceUser, _SourceUser | bool, _SourceUser | None])
def test_class_extra_positional_token_is_unused(hint):
    """An extra value after ``--x 1`` is reported as unused, not as a ``--x.<field>`` conflict."""
    from cyclopts import App
    from cyclopts.exceptions import UnusedCliTokensError

    app = App(result_action="return_value")

    @app.default
    def main(x: hint = None):  # pyright: ignore[reportInvalidTypeForm]
        return x

    with pytest.raises(UnusedCliTokensError, match=r"\['2'\]"):
        app(["--x", "1", "2"], exit_on_error=False)


def test_class_extra_positional_token_parse_known_args():
    """``parse_known_args`` hands back a stray value after ``--x 1`` instead of raising."""
    from cyclopts import App

    app = App(result_action="return_value")

    @app.default
    def main(x: _SourceUser | None = None):
        return x

    _, bound, unused, _ = app.parse_known_args(["--x", "1", "2"])
    assert bound.arguments == {"x": _SourceUser(a=1)}
    assert unused == ["2"]


@dataclass
class _SourceRequired:
    a: int


def test_class_cli_value_replaces_config_fields():
    """A keyless CLI value for a plain class replaces the config's ``--x.<field>`` values."""
    from cyclopts import App
    from cyclopts.config import Dict

    app = App(config=Dict({"x": {"a": 2}}), result_action="return_value")

    @app.default
    def main(x: _SourceRequired = _SourceRequired(0)):  # noqa: B008
        return x

    assert app(["--x", "1"], exit_on_error=False) == _SourceRequired(1)


@pytest.mark.parametrize("via", ["config", "env"])
def test_union_bool_class_json_merges_cli_field(monkeypatch, via):
    """A later source's JSON object merges into ``--x.<field>`` values, like a nested config table does."""
    from cyclopts import App
    from cyclopts.config import Dict

    if via == "env":
        monkeypatch.setenv("X", '{"b": "q"}')
    app = App(config=Dict({"x": '{"b": "q"}'} if via == "config" else {}), result_action="return_value")

    @app.default
    def main(*, x: Annotated[_SourceUser | bool, Parameter(env_var="X")] = False):
        return x

    assert app(["--x.a", "9"], exit_on_error=False) == _SourceUser(a=9, b="q")


def test_union_enum_flag_combines_across_sources():
    from cyclopts import App
    from cyclopts.config import Dict

    app = App(config=Dict({"x": {"write": True}}), result_action="return_value")

    @app.default
    def main(*, x: _Perm | str = "default"):
        return x

    assert app(["--x", "read"], exit_on_error=False) == _Perm.READ | _Perm.WRITE


@dataclass
class _SourceOuter:
    inner: _SourceUser | bool = False


def test_union_bool_class_nested_cli_json_replaces_config():
    """CLI JSON for an outer class keeps precedence over config values for the fields it sets."""
    from cyclopts import App
    from cyclopts.config import Dict

    app = App(config=Dict({"x": {"inner": {"a": 2}}}), result_action="return_value")

    @app.default
    def main(*, x: _SourceOuter = _SourceOuter()):  # noqa: B008
        return x

    assert app(["--x", '{"inner": false}'], exit_on_error=False) == _SourceOuter(inner=False)


def test_class_cli_json_field_beats_config_field():
    """CLI JSON wins over config for the same field; the config's other fields still merge."""
    from cyclopts import App
    from cyclopts.config import Dict

    app = App(config=Dict({"x": {"a": 2, "b": "c"}}), result_action="return_value")

    @app.default
    def main(*, x: _SourceUser = _SourceUser()):  # noqa: B008
        return x

    assert app(["--x", '{"a": 1}'], exit_on_error=False) == _SourceUser(a=1, b="c")


@pytest.mark.parametrize("value", ['{"literal": 9}', "{text"])
def test_union_str_class_cli_string_replaces_config_fields(value):
    """A ``{``-leading value that a ``str`` member takes whole isn't JSON; it replaces the config's fields."""
    from cyclopts import App
    from cyclopts.config import Dict

    app = App(config=Dict({"x": {"a": 2}}), result_action="return_value")

    @app.default
    def main(*, x: str | _SourceUser = ""):
        return x

    assert app(["--x", value], exit_on_error=False) == value


@dataclass
class _SourceOptions:
    options: dict[str, int]


@pytest.mark.parametrize("hint", [_SourceOptions, _SourceOptions | bool])
@pytest.mark.parametrize("config_options", [{"b": 2}, {"a": 5, "b": 2}])
def test_class_cli_json_dict_field_replaces_config_dict(hint, config_options):
    """Like ``--x.options.a 1``, CLI JSON entries replace the config's whole ``dict`` field."""
    from cyclopts import App
    from cyclopts.config import Dict

    app = App(config=Dict({"x": {"options": config_options}}), result_action="return_value")

    @app.default
    def main(*, x: hint = None):  # pyright: ignore[reportInvalidTypeForm]
        return x

    assert app(["--x", '{"options": {"a": 1}}'], exit_on_error=False) == _SourceOptions({"a": 1})


def test_union_bool_class_nested_cli_json_field_beats_config_json():
    """A later source's JSON string for a nested field merges per field under the CLI's JSON."""
    from cyclopts import App
    from cyclopts.config import Dict

    app = App(config=Dict({"x": {"inner": '{"a": 2, "b": "q"}'}}), result_action="return_value")

    @app.default
    def main(*, x: _SourceOuter = _SourceOuter()):  # noqa: B008
        return x

    assert app(["--x", '{"inner": {"a": 9}}'], exit_on_error=False) == _SourceOuter(inner=_SourceUser(a=9, b="q"))


def test_union_bool_class_nested_cli_json_field_beats_config_env_json(monkeypatch):
    from cyclopts import App
    from cyclopts.config import Env

    monkeypatch.setenv("APP_X_INNER", '{"a": 2, "b": "q"}')
    app = App(config=Env("APP_"), result_action="return_value")

    @app.default
    def main(*, x: _SourceOuter = _SourceOuter()):  # noqa: B008
        return x

    assert app(["--x", '{"inner": {"a": 9}}'], exit_on_error=False) == _SourceOuter(inner=_SourceUser(a=9, b="q"))


def test_class_env_var_json_beats_later_config_env_json(monkeypatch):
    """An ``env_var`` JSON keeps precedence over a later ``config.Env`` JSON for the fields it sets."""
    from cyclopts import App
    from cyclopts.config import Env

    monkeypatch.setenv("OUTER_JSON", '{"inner": {"a": 9}}')
    monkeypatch.setenv("APP_X_INNER", '{"a": 2, "b": "q"}')
    app = App(config=Env("APP_"), result_action="return_value")

    @app.default
    def main(*, x: Annotated[_SourceOuter, Parameter(env_var="OUTER_JSON")] = _SourceOuter()):  # noqa: B008
        return x

    assert app([], exit_on_error=False) == _SourceOuter(inner=_SourceUser(a=9, b="q"))


@dataclass
class _SourceEnvVarOuter:
    inner: Annotated[_SourceUser | bool, Parameter(env_var="INNER")] = False


@dataclass
class _SourceEnvVarPlainOuter:
    inner: Annotated[_SourceUser, Parameter(env_var="INNER")] = field(default_factory=_SourceUser)


def test_nested_env_var_json_merges_with_cli_json(monkeypatch):
    """CLI JSON for an outer class beats a nested field's ``env_var`` JSON for the fields it sets."""
    from cyclopts import App

    monkeypatch.setenv("INNER", '{"a": 2, "b": "q"}')
    app = App(result_action="return_value")

    @app.default
    def main(*, x: _SourceEnvVarOuter = _SourceEnvVarOuter()):  # noqa: B008
        return x

    assert app(["--x", '{"inner": {"a": 9}}'], exit_on_error=False) == _SourceEnvVarOuter(inner=_SourceUser(a=9, b="q"))


def test_nested_env_var_json_merges_with_cli_json_plain_class(monkeypatch):
    from cyclopts import App

    monkeypatch.setenv("INNER", '{"a": 2, "b": "q"}')
    app = App(result_action="return_value")

    @app.default
    def main(*, x: _SourceEnvVarPlainOuter = _SourceEnvVarPlainOuter()):  # noqa: B008
        return x

    assert app(["--x", '{"inner": {"a": 9}}'], exit_on_error=False) == _SourceEnvVarPlainOuter(
        inner=_SourceUser(a=9, b="q")
    )


@dataclass
class _SourceFlagOuter:
    perms: _SourcePermission = _SourcePermission(0)


@pytest.mark.parametrize(
    "config, expected",
    [
        ({"x": {"perms": {"write": True}}}, _SourcePermission.READ | _SourcePermission.WRITE),
        ({"x": {"perms": "write"}}, _SourcePermission.READ),
    ],
)
def test_enum_flag_in_outer_json_combines_across_sources(config, expected):
    """A whole ``enum.Flag`` in CLI JSON combines with config members, and beats a whole config value."""
    from cyclopts import App
    from cyclopts.config import Dict

    app = App(config=Dict(config), result_action="return_value")

    @app.default
    def main(*, x: _SourceFlagOuter = _SourceFlagOuter()):  # noqa: B008
        return x

    assert app(["--x", '{"perms": "read"}'], exit_on_error=False) == _SourceFlagOuter(perms=expected)


@dataclass
class _DictUser:
    a: int
    b: str = "x"


@pytest.mark.parametrize("hint", [_DictUser | dict[str, int] | None, _DictUser | dict[str, int]])
@pytest.mark.parametrize(
    "cmd, expected",
    [
        (["--x.a", "1"], _DictUser(a=1)),
        (["--x.a", "1", "--x.b", "q"], _DictUser(a=1, b="q")),
        (["--x.z", "1"], {"z": 1}),
        (["--x.a", "1", "--x.z", "2"], {"a": 1, "z": 2}),
        (["--x.b", "2"], {"b": 2}),
        (["--x", '{"z": 1}'], {"z": 1}),
        (["--x", '{"a": 1, "z": 2}'], {"a": 1, "z": 2}),
        (["--x", '{"a": 1}'], _DictUser(a=1)),
    ],
)
def test_union_class_or_dict_cli(hint, cmd, expected):
    """Keys the class doesn't take (or a partial class) bind to the ``dict`` member instead of being dropped."""
    from cyclopts import App

    app = App(result_action="return_value")

    @app.default
    def main(*, x: hint = None):  # pyright: ignore[reportInvalidTypeForm]
        return x

    assert app(cmd, exit_on_error=False) == expected


@pytest.mark.parametrize(
    "config, expected",
    [
        ({"x": {"a": 1}}, _DictUser(a=1)),
        ({"x": {"z": 1}}, {"z": 1}),
        ({"x": {"a": 1, "z": 2}}, {"a": 1, "z": 2}),
    ],
)
def test_union_class_or_dict_config(config, expected):
    from cyclopts import App
    from cyclopts.config import Dict

    app = App(config=Dict(config), result_action="return_value")

    @app.default
    def main(*, x: _DictUser | dict[str, int] | None = None):
        return x

    assert app([], exit_on_error=False) == expected
