from dataclasses import dataclass
from pathlib import Path
from textwrap import dedent
from typing import Annotated, Union

import pytest

from cyclopts import Parameter
from cyclopts.exceptions import CoercionError, MissingArgumentError


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
