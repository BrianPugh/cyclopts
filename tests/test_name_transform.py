from dataclasses import dataclass
from enum import Enum, auto
from textwrap import dedent
from typing import Annotated

import pytest

from cyclopts import App, Parameter, default_name_transform, name_transforms
from cyclopts.exceptions import CoercionError, UnknownOptionError, UnusedCliTokensError


def _short(s):
    """Transform yielding the default long name plus a single-dash short flag."""
    return (default_name_transform(s), "-" + s[0])


@pytest.mark.parametrize(
    "before,after",
    [
        ("FOO", "foo"),
        ("_FOO", "foo"),
        ("_FOO_", "foo"),
        ("_F_O_O_", "f-o-o"),
    ],
)
def test_default_name_transform(before, after):
    assert default_name_transform(before) == after


def test_app_name_transform_default(app):
    @app.command
    def _F_O_O_():  # noqa: N802
        pass

    assert "f-o-o" in app


def test_app_name_transform_custom(app):
    def name_transform(s: str) -> str:
        return "my-custom-name-transform"

    app.name_transform = name_transform

    @app.command
    def foo():
        pass

    assert "my-custom-name-transform" in app


def test_subapp_name_transform_custom(app):
    """A subapp with an explicitly set ``name_transform`` should NOT inherit from parent."""

    def name_transform_1(s: str) -> str:
        return "my-custom-name-transform-1"

    def name_transform_2(s: str) -> str:
        return "my-custom-name-transform-2"

    app.name_transform = name_transform_1

    app.command(subapp := App(name="bar", name_transform=name_transform_2))

    @subapp.command
    def foo():
        pass

    assert "my-custom-name-transform-2" in subapp


def test_subapp_name_transform_custom_inherited(app):
    """A subapp without an explicitly set ``name_transform`` should inherit it from the first parent."""

    def name_transform(s: str) -> str:
        return "my-custom-name-transform"

    app.name_transform = name_transform

    app.command(subapp := App(name="bar"))

    @subapp.command
    def foo():
        pass

    assert "my-custom-name-transform" in subapp


def test_parameter_name_transform_default(app, assert_parse_args):
    @app.default
    def foo(*, b_a_r: int):
        pass

    assert_parse_args(foo, "--b-a-r 5", b_a_r=5)


def test_parameter_name_transform_custom(app, assert_parse_args):
    app.default_parameter = Parameter(name_transform=lambda s: s)

    @app.default
    def foo(*, b_a_r: int):
        pass

    assert_parse_args(foo, "--b_a_r 5", b_a_r=5)


@pytest.mark.parametrize("transform", [None, lambda s: s])
def test_parameter_name_transform_kwargs(app, assert_parse_args, transform):
    """Both custom and non-custom transforms should result in the same kwargs."""
    app.default_parameter = Parameter(name_transform=transform)

    @app.default
    def foo(**kwargs: int):
        pass

    assert_parse_args(foo, "--hy-phen=1 --under_score=2", **{"hy-phen": 1, "under_score": 2})


def test_parameter_name_transform_custom_name_override(app, assert_parse_args):
    app.default_parameter = Parameter(name_transform=lambda s: s)

    @app.default
    def foo(*, b_a_r: Annotated[int, Parameter(name="--buzz")]):
        pass

    assert_parse_args(foo, "--buzz 5", b_a_r=5)


def test_parameter_name_transform_custom_enum(app, assert_parse_args):
    """name_transform should also be applied to enum options."""
    app.default_parameter = Parameter(name_transform=lambda s: s)

    class SoftwareEnvironment(Enum):
        DEV = auto()
        STAGING = auto()
        PROD = auto()
        _PROD_OLD = auto()

    @app.default
    def foo(*, b_a_r: SoftwareEnvironment = SoftwareEnvironment.STAGING):
        pass

    assert_parse_args(foo, "--b_a_r PROD", b_a_r=SoftwareEnvironment.PROD)


def test_parameter_name_transform_help(app, console):
    app.default_parameter = Parameter(name_transform=lambda s: s)

    @app.default
    def foo(*, b_a_r: int):
        pass

    with console.capture() as capture:
        app.help_print([], console=console)

    actual = capture.get()
    expected = dedent(
        """\
        Usage: test_name_transform --b_a_r INT

        ╭─ Commands ─────────────────────────────────────────────────────────╮
        │ --help (-h)  Display this message and exit.                        │
        │ --version    Display application version.                          │
        ╰────────────────────────────────────────────────────────────────────╯
        ╭─ Parameters ───────────────────────────────────────────────────────╮
        │ *  --b_a_r  [required]                                             │
        ╰────────────────────────────────────────────────────────────────────╯
        """
    )
    assert actual == expected


def test_parameter_name_transform_help_enum(app, console):
    """name_transform should also be applied to enum options on help page."""
    app.default_parameter = Parameter(name_transform=lambda s: s)

    class CompSciProblem(Enum):
        FIZZ = "bleep bloop blop"
        BUZZ = "blop bleep bloop"

    @app.command
    def cmd(
        foo: Annotated[CompSciProblem, Parameter(help="Docstring for foo.")] = CompSciProblem.FIZZ,
        bar: Annotated[CompSciProblem, Parameter(help="Docstring for bar.")] = CompSciProblem.BUZZ,
    ):
        pass

    with console.capture() as capture:
        app.help_print(["cmd"], console=console)

    actual = capture.get()
    expected = dedent(
        """\
        Usage: test_name_transform cmd [ARGS]

        ╭─ Parameters ───────────────────────────────────────────────────────╮
        │ FOO --foo  Docstring for foo. [choices: FIZZ, BUZZ] [default:      │
        │            FIZZ]                                                   │
        │ BAR --bar  Docstring for bar. [choices: FIZZ, BUZZ] [default:      │
        │            BUZZ]                                                   │
        ╰────────────────────────────────────────────────────────────────────╯
        """
    )
    assert actual == expected


def test_parameter_name_transform_dataclass(app, assert_parse_args):
    app.default_parameter = Parameter(name_transform=lambda s: s.upper())

    @dataclass
    class Color:
        red: int
        green: int
        blue: int

    @dataclass
    class User:
        name: str
        favorite_color: Color

    @app.default
    def default(user: Annotated[User, Parameter(name="--user")]):
        pass

    assert_parse_args(
        default,
        "Bob --user.FAVORITE_COLOR.RED=100 --user.FAVORITE_COLOR.GREEN=200 --user.FAVORITE_COLOR.BLUE=255",
        User("Bob", Color(100, 200, 255)),
    )


# ---------------------------------------------------------------------------
# Multi-name ``name_transform`` returning ``str | Iterable[str]``.
# ---------------------------------------------------------------------------


def test_name_transform_short_flag(app, assert_parse_args):
    """A transform returning a tuple generates an additional short flag."""

    @app.default
    def foo(*, verbose: Annotated[bool, Parameter(name_transform=_short)] = False):
        pass

    assert_parse_args(foo, "--verbose", verbose=True)
    assert_parse_args(foo, "-v", verbose=True)
    assert_parse_args(foo, "")


def test_name_transform_short_flag_help(app, console):
    """The generated short flag is shown on the help page."""

    @app.default
    def foo(*, verbose: Annotated[bool, Parameter(name_transform=_short)] = False):
        pass

    with console.capture() as capture:
        app.help_print([], console=console)

    actual = capture.get()
    assert "--verbose" in actual
    assert "-v" in actual


def test_name_transform_one_tuple_equivalent(app, assert_parse_args):
    """A 1-tuple return is equivalent to returning a plain ``str``."""

    @app.default
    def foo(*, b_a_r: Annotated[int, Parameter(name_transform=lambda s: (default_name_transform(s),))]):
        pass

    assert_parse_args(foo, "--b-a-r 5", b_a_r=5)


def test_name_transform_collision_first_wins(app, assert_parse_args):
    """A secondary name colliding with an earlier argument's name is dropped."""
    app.default_parameter = Parameter(name_transform=_short)

    @app.default
    def foo(*, verbose: bool = False, value: int = 0):
        pass

    # ``-v`` belongs to ``verbose`` (registered first); ``value`` keeps only ``--value``.
    assert_parse_args(foo, "-v --value 5", verbose=True, value=5)
    assert_parse_args(foo, "--value 7", value=7)

    # ``-v`` is a boolean flag for ``verbose``; it must not set ``value``.
    with pytest.raises(UnusedCliTokensError):
        app.parse_args("-v 5", print_error=False, exit_on_error=False)


def test_name_transform_collision_with_earlier_canonical(app, assert_parse_args):
    """A secondary colliding with an earlier *canonical* name is dropped; canonical intact."""
    # Secondary is the bare first letter (no dash) -> becomes ``--<letter>``.
    app.default_parameter = Parameter(name_transform=lambda s: (default_name_transform(s), s[0]))

    @app.default
    def foo(*, v: int = 0, verbose: bool = False):
        pass

    # ``--v`` is ``v``'s canonical name; ``verbose``'s secondary ``--v`` is dropped.
    assert_parse_args(foo, "--v 5 --verbose", v=5, verbose=True)


def test_name_transform_nested_dataclass_short_flag(app, assert_parse_args):
    """A nested field's short flag surfaces globally (not dotted) and respects first-wins."""
    app.default_parameter = Parameter(name_transform=_short)

    @dataclass
    class Color:
        red: int = 0
        rate: int = 0

    @dataclass
    class User:
        color: Color

    @app.default
    def foo(*, user: User):
        pass

    # ``-r`` is the global short flag for ``red`` (registered before ``rate``).
    assert_parse_args(
        foo,
        "-r 5 --user.color.rate 3",
        user=User(Color(red=5, rate=3)),
    )
    # The long dotted name still works.
    assert_parse_args(
        foo,
        "--user.color.red 9 --user.color.rate 8",
        user=User(Color(red=9, rate=8)),
    )


def test_name_transform_secondary_not_namespace_prefix(app, assert_parse_args):
    """Generated secondary names are leaf-level aliases only — never dotted prefixes for children.

    Children are built before collection-wide collision resolution, so a propagated prefix
    (e.g. ``-u.color.red``) could outlive a parent secondary (``-u``) dropped via first-wins.
    """
    app.default_parameter = Parameter(name_transform=_short)

    @dataclass
    class Color:
        red: int = 0

    @dataclass
    class User:
        color: Color

    @app.default
    def foo(*, upload: bool = False, user: User | None = None):
        pass

    arguments = app.assemble_argument_collection()
    assert arguments["--upload"].parameter.name == ("--upload", "-u")
    assert arguments["--user"].parameter.name == ("--user",)  # "-u" dropped (claimed by upload)
    assert arguments["--user.color.red"].parameter.name == ("--user.color.red", "-r")

    assert_parse_args(foo, "-u --user.color.red 5", upload=True, user=User(Color(5)))
    assert_parse_args(foo, "-r 5", user=User(Color(5)))


def test_name_transform_enum_alias_and_canonical(app, assert_parse_args):
    """Enum tokens match by raw alias and by canonical transform."""
    app.default_parameter = Parameter(name_transform=lambda s: (default_name_transform(s), s[0].lower()))

    class Color(Enum):
        RED = auto()
        GREEN = auto()

    @app.default
    def foo(*, color: Color = Color.RED):
        pass

    assert_parse_args(foo, "--color red", color=Color.RED)  # canonical
    assert_parse_args(foo, "--color RED", color=Color.RED)  # canonical via transform
    assert_parse_args(foo, "--color r", color=Color.RED)  # raw alias
    assert_parse_args(foo, "--color green", color=Color.GREEN)


def test_name_transform_enum_display_canonical_only(app, console):
    """Help choices/default and CoercionError show the canonical enum name only."""
    app.default_parameter = Parameter(name_transform=lambda s: (default_name_transform(s), s[0].lower()))

    class Color(Enum):
        RED = auto()
        GREEN = auto()

    @app.default
    def foo(*, color: Color = Color.RED):
        pass

    with console.capture() as capture:
        app.help_print([], console=console)
    actual = capture.get()
    assert "red" in actual
    assert "green" in actual
    assert "[default: red]" in actual

    with pytest.raises(CoercionError) as e:
        app.parse_args("--color bogus", print_error=False, exit_on_error=False)
    message = str(e.value)
    assert "red" in message
    assert "green" in message


def test_name_transform_gnu_combined_shorts(app, assert_parse_args):
    """Two generated boolean short flags can be combined GNU-style."""
    app.default_parameter = Parameter(name_transform=_short)

    @app.default
    def foo(*, verbose: bool = False, force: bool = False):
        pass

    assert_parse_args(foo, "-vf", verbose=True, force=True)


def test_name_transform_negatives(app, assert_parse_args):
    """Short flags get no negative; the long flag still does."""
    app.default_parameter = Parameter(name_transform=_short)

    @app.default
    def foo(*, verbose: bool = True):
        pass

    assert_parse_args(foo, "-v", verbose=True)
    assert_parse_args(foo, "--no-verbose", verbose=False)
    with pytest.raises(UnknownOptionError):
        app.parse_args("--no-v", print_error=False, exit_on_error=False)


def test_name_transform_empty_return_raises(app):
    """A transform returning no names raises ValueError."""
    app.default_parameter = Parameter(name_transform=lambda s: ())

    @app.default
    def foo(*, bar: int = 0):
        pass

    with pytest.raises(ValueError):
        app.parse_args("--bar 5", print_error=False, exit_on_error=False)


def test_name_transform_non_str_return_raises(app):
    """A transform returning a non-str element raises TypeError."""
    app.default_parameter = Parameter(name_transform=lambda s: (default_name_transform(s), 5))  # pyright: ignore[reportArgumentType]

    @app.default
    def foo(*, bar: int = 0):
        pass

    with pytest.raises(TypeError):
        app.parse_args("--bar 5", print_error=False, exit_on_error=False)


def test_name_transform_intra_parameter_duplicates_deduped(app, assert_parse_args):
    """Duplicate names returned for a single parameter are silently deduped."""

    @app.default
    def foo(
        *,
        bar: Annotated[
            int, Parameter(name_transform=lambda s: (default_name_transform(s), default_name_transform(s)))
        ] = 0,
    ):
        pass

    assert_parse_args(foo, "--bar 5", bar=5)


def test_name_transform_env_var_canonical(app, assert_parse_args, monkeypatch):
    """The canonical env var is unaffected by the secondary short flag."""

    @app.default
    def foo(
        *,
        verbose: Annotated[bool, Parameter(name_transform=_short, env_var="MY_VERBOSE")] = False,
    ):
        pass

    monkeypatch.setenv("MY_VERBOSE", "true")
    assert_parse_args(foo, "", verbose=True)


def test_name_transform_list_of_callables(app, assert_parse_args):
    """A list of callables is composed: each generates names, results concatenated."""
    app.default_parameter = Parameter(name_transform=[default_name_transform, lambda s: "-" + s[0]])

    @app.default
    def foo(*, verbose: bool = False, force: bool = False):
        pass

    assert_parse_args(foo, "--verbose", verbose=True)
    assert_parse_args(foo, "-v", verbose=True)
    assert_parse_args(foo, "-vf", verbose=True, force=True)
    assert_parse_args(foo, "--force", force=True)


def test_name_transform_list_canonical_is_first(app):
    """The first callable's first name is canonical (drives usage/env/help)."""
    p = Parameter(name_transform=[default_name_transform, lambda s: "-" + s[0]])
    assert p.name_transform("verbose") == ["verbose", "-v"]


def test_name_transform_empty_list_uses_default(app, assert_parse_args):
    """An empty list falls back to the default transform."""
    app.default_parameter = Parameter(name_transform=[])

    @app.default
    def foo(*, b_a_r: int = 0):
        pass

    assert_parse_args(foo, "--b-a-r 5", b_a_r=5)


def test_name_transform_list_non_callable_raises(app):
    """A non-callable element in the list raises TypeError."""
    with pytest.raises(TypeError):
        Parameter(name_transform=[default_name_transform, "not-callable"])  # pyright: ignore[reportArgumentType]


def test_name_transform_module_default_backwards_compatible():
    """``name_transforms.default`` is the same object as ``default_name_transform``."""
    assert name_transforms.default is default_name_transform


def test_name_transform_module_short():
    """``name_transforms.short`` returns only a single-letter short flag."""
    assert name_transforms.short("verbose") == "-v"
    # Short flag letter comes from the transformed long name (robust for PascalCase).
    assert name_transforms.short("HelloWorld") == "-h"


def test_name_transform_module_short_end_to_end(app, assert_parse_args):
    """``[name_transforms.default, name_transforms.short]`` works as a drop-in app-wide transform."""
    app.default_parameter = Parameter(name_transform=[name_transforms.default, name_transforms.short])

    @app.default
    def foo(*, verbose: bool = False, force: bool = False):
        pass

    assert_parse_args(foo, "--verbose", verbose=True)
    assert_parse_args(foo, "-v", verbose=True)
    assert_parse_args(foo, "-vf", verbose=True, force=True)


def test_name_transform_kwargs_multi_name(app, assert_parse_args):
    """``**kwargs`` parsing works with a multi-name transform."""
    app.default_parameter = Parameter(name_transform=_short)

    @app.default
    def foo(**kwargs: int):
        pass

    assert_parse_args(foo, "--hy-phen=1 --under_score=2", **{"hy-phen": 1, "under_score": 2})
