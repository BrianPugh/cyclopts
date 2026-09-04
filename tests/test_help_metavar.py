"""Tests for ``HelpEntry.metavar`` (value placeholder), ``HelpEntry.positional_label`` (positional identifier), and ``Parameter.metavar``."""

from pathlib import Path
from textwrap import dedent
from typing import Annotated, Literal

import pytest
from rich.console import Console

from cyclopts import App, Parameter


def _parameter_entries(app: App):
    """All ``HelpEntry`` from ``app``'s parameter panels, in display order."""
    out = []
    for _, panel in app._assemble_help_panels((), "restructuredtext"):
        if panel.format == "parameter":
            out.extend(panel.entries)
    return out


def test_positional_or_keyword_label_from_name_metavar_from_type(app):
    """A positional-or-keyword parameter is labeled by its name; the metavar comes from its type."""

    @app.default
    def main(count: int = 3):
        pass

    (entry,) = _parameter_entries(app)
    assert entry.positive_names == ("--count",)
    assert entry.positional_label == "COUNT"  # from the name
    assert entry.metavar == "INT"  # from the type
    assert entry.all_options == ("--count",)
    assert entry.display_labels == ("COUNT", "--count")


def test_positional_only_label_from_name_metavar_from_type(app):
    """A positional-only parameter has no option names; its label is name-derived."""

    @app.default
    def main(url: str, /):
        pass

    (entry,) = _parameter_entries(app)
    assert entry.positive_names == ()
    assert entry.positional_label == "URL"
    assert entry.metavar == "STR"
    assert entry.all_options == ()
    assert entry.display_labels == ("URL",)


def test_keyword_only_has_no_label(app):
    """Keyword-only parameters are identified by their option names, so they have no label."""

    @app.default
    def main(*, cookies: Path | None = None):
        pass

    (entry,) = _parameter_entries(app)
    assert entry.positive_names == ("--cookies",)
    assert entry.positional_label is None
    assert entry.metavar == "PATH"  # type-derived, Optional's None stripped
    # Builtin panels show option names only for keyword parameters.
    assert entry.display_labels == ("--cookies",)


def test_metavar_derives_from_type_label_from_name(app):
    """``metavar`` uses the type name; ``label`` uses the parameter name."""

    @app.default
    def main(name: str = "", cfg: Path = Path(), num: int = 0):
        pass

    assert [(e.positional_label, e.metavar) for e in _parameter_entries(app)] == [
        ("NAME", "STR"),
        ("CFG", "PATH"),
        ("NUM", "INT"),
    ]


def test_metavar_tuple_renders_one_placeholder_per_token(app):
    """Tuples render argparse-style, matching how the values are typed on the CLI."""

    @app.default
    def main(
        *,
        size: tuple[int, int] = (1, 2),
        nested: tuple[int, tuple[float, float]] = (0, (0.0, 0.0)),
        var: tuple[int, ...] = (),
        opt: tuple[int | None, str] | None = None,
        pts: list[tuple[int, str]] = [],  # noqa: B006
    ):
        pass

    assert [e.metavar for e in _parameter_entries(app)] == [
        "INT INT",
        "INT FLOAT FLOAT",
        "INT...",
        "INT STR",
        "LIST[TUPLE[INT, STR]]",
    ]


def test_label_uses_long_name(app):
    """The positional label derives from the first long name, not a short flag."""

    @app.default
    def main(output_directory: Annotated[str, Parameter(name=["-o", "--output-directory"])] = "."):
        pass

    (entry,) = _parameter_entries(app)
    assert entry.positional_label == "OUTPUT-DIRECTORY"


@pytest.mark.parametrize(
    "annotation",
    [
        Annotated[bool, Parameter()],
        Annotated[int, Parameter(count=True)],
    ],
)
def test_metavar_none_for_valueless_keyword_parameters(app, annotation):
    """Parameters that never consume a token have no metavar (and no label)."""

    @app.default
    def main(*, flag: annotation = 0):  # pyright: ignore[reportInvalidTypeForm]
        pass

    (entry,) = _parameter_entries(app)
    assert entry.metavar is None
    assert entry.positional_label is None
    assert entry.display_labels == entry.all_options


def test_metavar_none_for_valueless_positional_parameter(app):
    """A positional parameter that consumes no token has no metavar, but keeps its label.

    The zero-token guard applies to positionals too: their display identifier is the
    positional_label, never a value placeholder.
    """

    @app.default
    def main(verbosity: Annotated[int, Parameter(count=True)], /):
        pass

    (entry,) = _parameter_entries(app)
    assert entry.metavar is None
    assert entry.positional_label == "VERBOSITY"


def test_metavar_ignored_for_valueless_bool(app, console: Console):
    """An explicit metavar on a keyword-only boolean flag is ignored, not leaked into the help."""

    @app.default
    def main(*, flag: Annotated[bool, Parameter(metavar="XYZ")] = False):
        pass

    (entry,) = _parameter_entries(app)
    assert entry.metavar is None

    with console.capture() as capture:
        app.help_print(console=console)

    actual = capture.get()
    expected = dedent(
        """\
        Usage: test_help_metavar [OPTIONS]

        ╭─ Commands ─────────────────────────────────────────────────────────╮
        │ --help (-h)  Display this message and exit.                        │
        │ --version    Display application version.                          │
        ╰────────────────────────────────────────────────────────────────────╯
        ╭─ Parameters ───────────────────────────────────────────────────────╮
        │ --flag --no-flag  [default: False]                                 │
        ╰────────────────────────────────────────────────────────────────────╯
        """
    )
    assert actual == expected


def test_metavar_ignored_for_valueless_count(app, console: Console):
    """An explicit metavar on a count parameter is ignored, not leaked into the help."""

    @app.default
    def main(*, flag: Annotated[int, Parameter(count=True, metavar="XYZ")] = 0):
        pass

    (entry,) = _parameter_entries(app)
    assert entry.metavar is None

    with console.capture() as capture:
        app.help_print(console=console)

    actual = capture.get()
    expected = dedent(
        """\
        Usage: test_help_metavar [OPTIONS]

        ╭─ Commands ─────────────────────────────────────────────────────────╮
        │ --help (-h)  Display this message and exit.                        │
        │ --version    Display application version.                          │
        ╰────────────────────────────────────────────────────────────────────╯
        ╭─ Parameters ───────────────────────────────────────────────────────╮
        │ --flag  [default: 0]                                               │
        ╰────────────────────────────────────────────────────────────────────╯
        """
    )
    assert actual == expected


def test_positional_bool_labeled_by_name(app):
    """A positionally-suppliable bool is labeled by its name and, being a flag, has no metavar."""

    @app.default
    def main(flag: bool = False):
        pass

    (entry,) = _parameter_entries(app)
    assert entry.positional_label == "FLAG"
    assert entry.metavar is None
    assert entry.display_labels == ("FLAG", "--flag", "--no-flag")


def test_metavar_does_not_change_positional_bool_label(app):
    """A metavar on a positionally-suppliable bool is ignored (flags take no value) and never touches the label."""

    @app.default
    def main(flag: Annotated[bool, Parameter(metavar="TOGGLE")] = False):
        pass

    (entry,) = _parameter_entries(app)
    assert entry.positional_label == "FLAG"
    assert entry.metavar is None
    assert entry.display_labels == ("FLAG", "--flag", "--no-flag")


@pytest.mark.parametrize("annotation", [bool | None, Annotated[bool, Parameter(n_tokens=2)]])
def test_metavar_none_for_bool_variants_parser_treats_as_flags(app, annotation, console: Console):
    """Anything the parser accepts as a bare flag (``Optional[bool]``, ``n_tokens`` bools) advertises no value."""

    @app.default
    def main(*, flag: annotation):  # pyright: ignore[reportInvalidTypeForm]
        pass

    (entry,) = _parameter_entries(app)
    assert entry.metavar is None

    with console.capture() as capture:
        app.help_print(console=console)
    assert "Usage: test_help_metavar --flag\n" in capture.get()


def test_metavar_does_not_introspect_fields(app, console: Console):
    """Help must not crash on a type whose field introspection fails (``token_count`` is not consulted)."""

    class Weird:
        def __init__(self, a: "Undefined"):  # noqa: F821  # pyright: ignore[reportUndefinedVariable]
            self.a = a

    @app.default
    def main(*, w: Annotated[Weird | None, Parameter(accepts_keys=False)] = None):
        pass

    (entry,) = _parameter_entries(app)
    assert entry.metavar == "WEIRD"


def test_metavar_strips_nested_annotated(app):
    """``Annotated`` metadata inside a container never leaks into the metavar; its ``metavar`` is honored."""
    from cyclopts import types

    @app.default
    def main(*, ports: list[types.Port] | None = None):
        pass

    (ports,) = _parameter_entries(app)
    assert ports.metavar == "LIST[PORT]"


def test_metavar_choice_for_literal_and_enum(app):
    """``Literal``/``Enum`` derive ``CHOICE`` (Click-style); shown only when the ``[choices]`` list is hidden."""
    from enum import Enum

    class Color(Enum):
        RED = 1

    @app.default
    def main(
        *,
        mode: Annotated[Literal["fast", "Slow"], Parameter(show_choices=False)] = "fast",
        color: Annotated[Color, Parameter(show_choices=False)] = Color.RED,
        either: Annotated[Literal["a"] | int, Parameter(show_choices=False)] = 1,
        pair: tuple[Literal["a", "b"], int] = ("a", 1),
        shown: Literal["x", "y"] = "x",
    ):
        pass

    mode, color, either, pair, shown = _parameter_entries(app)
    assert mode.metavar == "CHOICE"
    assert color.metavar == "CHOICE"
    assert either.metavar == "CHOICE|INT"
    assert pair.metavar == "CHOICE INT"
    assert shown.metavar is None
    assert shown.choices == ("x", "y")


def test_metavar_choice_for_explicit_parameter_choices(app):
    """An explicit ``Parameter.choices`` derives ``CHOICE`` like ``Literal``/``Enum``, not the underlying type name.

    The choice list describes the value, so a plain ``int``/``str`` carrying ``choices``
    shows ``CHOICE`` in usage and is suppressed in the panel (where ``[choices]`` is listed),
    exactly like a ``Literal`` hint. With ``show_choices=False`` the placeholder stays ``CHOICE``.
    """

    @app.default
    def main(
        *,
        num: Annotated[int, Parameter(choices=["1", "2", "3"])] = 1,
        color: Annotated[str, Parameter(choices=["red", "green"])] = "red",
        hidden: Annotated[int, Parameter(choices=["1", "2"], show_choices=False)] = 1,
        plain: int = 0,
    ):
        pass

    num, color, hidden, plain = _parameter_entries(app)
    # Panel rows: the ``[choices]`` list stands in for the placeholder.
    assert num.metavar is None
    assert num.choices == ("1", "2", "3")
    assert color.metavar is None
    assert color.choices == ("red", "green")
    # ``show_choices=False`` hides the list, so the ``CHOICE`` placeholder returns.
    assert hidden.metavar == "CHOICE"
    # A plain type without choices is unaffected.
    assert plain.metavar == "INT"


def test_usage_keeps_choice_metavar_for_explicit_parameter_choices(app, console: Console):
    """The usage line has no ``[choices]`` list, so a ``Parameter.choices`` keyword keeps ``CHOICE`` there."""

    @app.default
    def main(*, num: Annotated[int, Parameter(choices=["1", "2", "3"])]):
        pass

    with console.capture() as capture:
        app.help_print(console=console)
    actual = capture.get()
    assert "Usage: test_help_metavar --num CHOICE" in actual
    assert "[choices: 1, 2, 3]" in actual


def test_usage_wraps_choice_in_container_for_explicit_parameter_choices(app, console: Console):
    """Explicit ``Parameter.choices`` on a container renders like ``list[Literal[...]]`` does."""

    @app.default
    def main(
        *,
        a: Annotated[list[str], Parameter(choices=("x", "y"))],
        b: list[Literal["x", "y"]],
    ):
        pass

    with console.capture() as capture:
        app.help_print(console=console)
    assert "Usage: test_help_metavar --a LIST[CHOICE] --b LIST[CHOICE]" in capture.get()

    a, b = _parameter_entries(app)
    assert a.metavar is None
    assert b.metavar is None


def test_explicit_metavar_shown_alongside_choices(app, console: Console):
    """An explicit metavar is never suppressed by a ``[choices]`` list."""

    @app.default
    def main(*, mode: Annotated[Literal["a", "b"], Parameter(metavar="MODE")]):
        pass

    (entry,) = _parameter_entries(app)
    assert entry.metavar == "MODE"
    assert entry.choices == ("a", "b")

    with console.capture() as capture:
        app.help_print(console=console)
    actual = capture.get()
    assert "Usage: test_help_metavar --mode MODE" in actual
    assert "--mode MODE" in actual
    assert "[choices: a, b]" in actual


def test_metavar_none_for_dict_and_value_type_for_kwargs(app, console: Console):
    """A dict is only populated via ``--name.KEY VALUE`` so it has no metavar; ``**kwargs`` show the value type."""

    @app.default
    def main(*, tastes: dict[str, int] | None = None, **kwargs: int):
        pass

    tastes, kwargs = _parameter_entries(app)
    assert tastes.metavar is None
    assert kwargs.metavar == "INT"

    with console.capture() as capture:
        app.help_print(console=console)
    assert "--[KEYWORD] INT" in capture.get()


def test_positional_dict_is_not_positional(app, console: Console):
    """A dict never receives a positional index; help agrees with the parser and renders it as an option."""

    @app.default
    def main(src: str, d: dict[str, int], /):
        pass

    _, d = _parameter_entries(app)
    assert d.positional_label is None
    assert d.metavar is None

    with console.capture() as capture:
        app.help_print(console=console)
    assert "Usage: test_help_metavar SRC\n" in capture.get()


def test_positional_label_skips_custom_negative(app, console: Console):
    """A custom negative flag is never used as the positional identifier."""

    @app.default
    def main(f: str, g: Annotated[bool, Parameter(name="-g", negative="--quiet")], /):
        pass

    _, g = _parameter_entries(app)
    assert g.positional_label == "G"

    with console.capture() as capture:
        app.help_print(console=console)
    assert "Usage: test_help_metavar F G\n" in capture.get()


def test_usage_keeps_choice_metavar_for_required_choice_parameters(app, console: Console):
    """The usage line has no ``[choices]`` list, so required Literal/Enum keywords keep ``CHOICE`` there."""
    from enum import Enum

    class Color(Enum):
        RED = 1

    @app.default
    def main(*, color: Literal["red", "blue"], mode: Color, n: int):
        pass

    with console.capture() as capture:
        app.help_print(console=console)
    actual = capture.get()
    assert "Usage: test_help_metavar --color CHOICE --mode CHOICE --n INT" in actual
    assert "--color  [choices: red, blue]" in actual


def test_mixed_union_keeps_free_form_metavar_when_choices_shown(app):
    """Only the choice half is dropped in favour of the ``[choices]`` list; ``INT`` still parses and still shows."""

    @app.default
    def main(*, mixed: Literal["auto"] | int = 1):
        pass

    (entry,) = _parameter_entries(app)
    assert entry.choices == ("auto",)
    assert entry.metavar == "INT"


def test_metavar_for_dict_with_accepts_keys_false(app, console: Console):
    """``accepts_keys=False`` makes a dict consume a token, so it gets a metavar and honors an explicit one."""
    import json

    @app.default
    def main(
        *,
        d: Annotated[dict[str, int], Parameter(accepts_keys=False, converter=lambda _, t: json.loads(t[0].value))],
        e: Annotated[dict[str, int], Parameter(accepts_keys=False, metavar="JSON")] = {},  # noqa: B006
    ):
        pass

    d, e = _parameter_entries(app)
    assert d.metavar == "DICT[STR, INT]"
    assert e.metavar == "JSON"

    with console.capture() as capture:
        app.help_print(console=console)
    assert "Usage: test_help_metavar --d DICT[STR, INT]" in capture.get()


def test_show_metavar_false_also_clears_usage_line(console: Console):
    """``show_metavar=False`` restores the placeholder-free usage line too, not just the rows."""
    from cyclopts.help import DefaultFormatter

    app = App(name="app", help_formatter=DefaultFormatter(show_metavar=False))

    @app.default
    def main(*, output: Annotated[Path, Parameter(metavar="DIR")]):
        pass

    with console.capture() as capture:
        app.help_print(console=console)
    actual = capture.get()
    assert "Usage: app --output\n" in actual
    assert "DIR" not in actual


def test_show_metavar_false_on_group_formatter_clears_usage_line(console: Console):
    """The usage line follows the formatter that renders each parameter's row, group formatters included."""
    from cyclopts import Group
    from cyclopts.help import DefaultFormatter

    app = App(name="app")
    quiet = Group("Quiet", help_formatter=DefaultFormatter(show_metavar=False))

    @app.default
    def main(*, output: Annotated[Path, Parameter(group=quiet)], name: str):
        pass

    with console.capture() as capture:
        app.help_print(console=console)
    actual = capture.get()
    assert "Usage: app --output --name STR\n" in actual


def test_docs_usage_keeps_metavar_when_app_formatter_hides_it():
    """Docs formatters always render row metavars, so their usage line does too."""
    from cyclopts.docs import generate_markdown_docs
    from cyclopts.help import DefaultFormatter

    app = App(name="app", help_formatter=DefaultFormatter(show_metavar=False))

    @app.default
    def main(*, name: str):
        pass

    assert "app --name STR" in generate_markdown_docs(app)


def test_metavar_repeats_for_n_tokens(app):
    """``n_tokens`` renders one placeholder per consumed token, matching the tuple rule."""

    @app.default
    def main(
        *,
        x: Annotated[str, Parameter(n_tokens=2, converter=lambda _, tokens: " ".join(t.value for t in tokens))],
        y: Annotated[str, Parameter(n_tokens=-1, converter=lambda _, tokens: " ".join(t.value for t in tokens))],
        z: Annotated[tuple[str, str], Parameter(n_tokens=2)],
        w: Annotated[list[int], Parameter(n_tokens=3)] = [],  # noqa: B006
    ):
        pass

    x, y, z, w = _parameter_entries(app)
    assert x.metavar == "STR STR"
    assert y.metavar == "STR..."
    assert z.metavar == "STR STR"
    assert w.metavar == "INT INT INT"


def test_metavar_strips_none_from_nested_unions(app):
    """``None`` inside a container element is never something the user types, so it is not advertised."""

    @app.default
    def main(*, a: list[int | None] = [], b: list[Literal["x", "y"] | None] = []):  # noqa: B006
        pass

    a, b = _parameter_entries(app)
    assert a.metavar == "LIST[INT]"
    assert b.metavar is None


def test_metavar_honors_element_metavars_in_containers(app):
    """Metavars attached via ``Annotated``/``@Parameter`` survive inside tuples and lists."""
    from cyclopts import types

    @app.default
    def main(*, ports: tuple[types.Port, types.Port], emails: list[types.Email], p: types.Port):
        pass

    ports, emails, p = _parameter_entries(app)
    assert ports.metavar == "PORT PORT"
    assert emails.metavar == "LIST[EMAIL]"
    assert p.metavar == "PORT"


@pytest.mark.parametrize("output_format", ["markdown", "rst", "html", "plain"])
def test_metavar_rendered_by_all_builtin_formatters(app, output_format, console: Console):
    """Every builtin formatter renders the metavar next to the last value-taking name."""

    @app.default
    def main(*, config: Annotated[Path, Parameter(name=["--config", "-c"], metavar="FILE")], flag: bool = False):
        pass

    if output_format == "plain":
        app.help_formatter = "plain"
        with console.capture() as capture:
            app.help_print(console=console)
        docs = capture.get()
    else:
        docs = app.generate_docs(output_format=output_format)  # pyright: ignore[reportArgumentType]
    assert "-c FILE" in docs
    assert "BOOL" not in docs


def test_name_renderer_wraps_long_dotted_names_at_dots():
    """Over-long dotted names break before a ``.`` and never gain an inner space or mid-token break."""
    from cyclopts.help.help import HelpEntry
    from cyclopts.help.specs import NameRenderer

    entry = HelpEntry(
        positive_names=("--config.database-configuration.connection-string-for-primary-db",), metavar="STR"
    )
    rendered = NameRenderer(max_width=28)(entry)
    assert rendered == "--config\n  .database-configuration\n  .connection-string-for-pri\n  mary-db STR"

    short = HelpEntry(positive_names=("--models.{NAME}.inner.value",), metavar="INT")
    assert NameRenderer(max_width=25)(short) == "--models.{NAME}.inner\n  .value INT"


def test_wrap_labels_terminates_when_indent_fills_width():
    """A width no wider than the continuation indent still makes progress instead of looping forever."""
    from cyclopts.help.specs import _wrap_labels

    lines = _wrap_labels("--foo --barbaz", 2)
    assert "".join(line.strip() for line in lines) == "--foo--barbaz"


def test_metavar_not_inherited_by_structured_children(app, console: Console):
    """A metavar on a structured parameter does not propagate to its leaf fields."""
    from dataclasses import dataclass

    @dataclass
    class Config:
        host: str
        port: int = 80

    @app.default
    def main(*, config: Annotated[Config, Parameter(metavar="CFG")]):
        pass

    host, port = _parameter_entries(app)
    assert host.metavar == "STR"
    assert port.metavar == "INT"


def test_metavar_override_wins_over_type(app):
    """An explicit ``metavar`` overrides the type-derived default."""

    @app.default
    def main(*, out: Annotated[Path, Parameter(metavar="FILE")] = Path()):
        pass

    (entry,) = _parameter_entries(app)
    assert entry.metavar == "FILE"


def test_usage_type_derived_metavar_for_required_keyword(app, console: Console):
    """A required keyword parameter's usage placeholder derives from its type."""

    @app.default
    def main(*, out: Path):
        pass

    with console.capture() as capture:
        app.help_print(console=console)

    assert capture.get().startswith("Usage: test_help_metavar --out PATH\n")


def test_parameter_metavar_override(app):
    """``Parameter(metavar=...)`` replaces the type-derived value placeholder."""

    @app.default
    def main(*, cookies: Path | None = None, convert: Annotated[str, Parameter(metavar="EXTENSION")] = "mp4"):
        pass

    entries = {e.names[0]: e for e in _parameter_entries(app)}
    assert entries["--cookies"].metavar == "PATH"  # type-derived default, Optional's None stripped
    assert entries["--convert"].metavar == "EXTENSION"  # explicit override
    assert entries["--convert"].positional_label is None  # keyword-only, no positional label


def test_parameter_metavar_override_empty_string(app):
    """An empty ``metavar`` suppresses the placeholder entirely."""

    @app.default
    def main(*, token: Annotated[str, Parameter(metavar="")]):
        pass

    (entry,) = _parameter_entries(app)
    assert entry.metavar is None


def test_metavar_does_not_change_positional_label(app, console: Console):
    """The override sets the value placeholder but leaves the positional label name-derived."""

    @app.default
    def main(infile: Annotated[Path, Parameter(metavar="FILE")], /):
        pass

    (entry,) = _parameter_entries(app)
    assert entry.positive_names == ()
    assert entry.positional_label == "INFILE"  # from the name, not the metavar
    assert entry.metavar == "FILE"
    assert entry.display_labels == ("INFILE",)

    with console.capture() as capture:
        app.help_print(console=console)

    actual = capture.get()
    expected = dedent(
        """\
        Usage: test_help_metavar INFILE

        ╭─ Commands ─────────────────────────────────────────────────────────╮
        │ --help (-h)  Display this message and exit.                        │
        │ --version    Display application version.                          │
        ╰────────────────────────────────────────────────────────────────────╯
        ╭─ Arguments ────────────────────────────────────────────────────────╮
        │ *  INFILE  [required]                                              │
        ╰────────────────────────────────────────────────────────────────────╯
        """
    )
    assert actual == expected


def test_positional_label_from_name_override(app, console: Console):
    """A positional's label follows ``Parameter.name`` (the identifier), not its metavar."""

    @app.default
    def main(infile: Annotated[Path, Parameter(name="SOURCE")], /):
        pass

    (entry,) = _parameter_entries(app)
    assert entry.positional_label == "SOURCE"
    assert entry.display_labels == ("SOURCE",)

    with console.capture() as capture:
        app.help_print(console=console)

    assert capture.get().startswith("Usage: test_help_metavar SOURCE\n")


def test_parameter_metavar_override_in_usage(app, console: Console):
    """The override is honored in the usage line for required keyword parameters."""

    @app.default
    def main(*, out: Annotated[Path, Parameter(metavar="DIR")]):
        pass

    with console.capture() as capture:
        app.help_print(console=console)

    actual = capture.get()
    expected = dedent(
        """\
        Usage: test_help_metavar --out DIR

        ╭─ Commands ─────────────────────────────────────────────────────────╮
        │ --help (-h)  Display this message and exit.                        │
        │ --version    Display application version.                          │
        ╰────────────────────────────────────────────────────────────────────╯
        ╭─ Parameters ───────────────────────────────────────────────────────╮
        │ *  --out DIR  [required]                                           │
        ╰────────────────────────────────────────────────────────────────────╯
        """
    )
    assert actual == expected


def test_usage_omits_metavar_for_required_flag(app, console: Console):
    """A required boolean flag consumes no token, so the usage line shows no placeholder."""

    @app.default
    def main(*, flag: bool):
        pass

    with console.capture() as capture:
        app.help_print(console=console)

    actual = capture.get()
    expected = dedent(
        """\
        Usage: test_help_metavar --flag

        ╭─ Commands ─────────────────────────────────────────────────────────╮
        │ --help (-h)  Display this message and exit.                        │
        │ --version    Display application version.                          │
        ╰────────────────────────────────────────────────────────────────────╯
        ╭─ Parameters ───────────────────────────────────────────────────────╮
        │ *  --flag --no-flag  [required]                                    │
        ╰────────────────────────────────────────────────────────────────────╯
        """
    )
    assert actual == expected


def test_multiple_positional_only_parameters_not_deduplicated(app, console: Console):
    """Positional-only entries have empty option names, so dedup keys on the source parameter."""

    @app.default
    def main(src: str, dest: str, /):
        pass

    with console.capture() as capture:
        app.help_print(console=console)

    actual = capture.get()
    expected = dedent(
        """\
        Usage: test_help_metavar SRC DEST

        ╭─ Commands ─────────────────────────────────────────────────────────╮
        │ --help (-h)  Display this message and exit.                        │
        │ --version    Display application version.                          │
        ╰────────────────────────────────────────────────────────────────────╯
        ╭─ Arguments ────────────────────────────────────────────────────────╮
        │ *  SRC   [required]                                                │
        │ *  DEST  [required]                                                │
        ╰────────────────────────────────────────────────────────────────────╯
        """
    )
    assert actual == expected


def test_positional_only_metavar_does_not_drive_row(app, console: Console):
    """Positional rows are labeled by name; an explicit metavar does not replace the label."""

    @app.default
    def main(
        a: Annotated[str, Parameter(metavar="FILE")],
        b: Annotated[str, Parameter(metavar="FILE")],
        /,
    ):
        pass

    entries = _parameter_entries(app)
    assert len(entries) == 2
    assert [e.positional_label for e in entries] == ["A", "B"]
    assert all(e.metavar == "FILE" for e in entries)

    with console.capture() as capture:
        app.help_print(console=console)

    actual = capture.get()
    expected = dedent(
        """\
        Usage: test_help_metavar A B

        ╭─ Commands ─────────────────────────────────────────────────────────╮
        │ --help (-h)  Display this message and exit.                        │
        │ --version    Display application version.                          │
        ╰────────────────────────────────────────────────────────────────────╯
        ╭─ Arguments ────────────────────────────────────────────────────────╮
        │ *  A  [required]                                                   │
        │ *  B  [required]                                                   │
        ╰────────────────────────────────────────────────────────────────────╯
        """
    )
    assert actual == expected


def test_empty_metavar_positional_still_labeled_by_name(app, console: Console):
    """An empty metavar suppresses the value placeholder; the positional is still labeled by name."""

    @app.default
    def main(infile: Annotated[Path, Parameter(metavar="")], /):
        pass

    (entry,) = _parameter_entries(app)
    assert entry.metavar is None
    assert entry.positional_label == "INFILE"
    assert entry.display_labels == ("INFILE",)

    with console.capture() as capture:
        app.help_print(console=console)

    actual = capture.get()
    expected = dedent(
        """\
        Usage: test_help_metavar INFILE

        ╭─ Commands ─────────────────────────────────────────────────────────╮
        │ --help (-h)  Display this message and exit.                        │
        │ --version    Display application version.                          │
        ╰────────────────────────────────────────────────────────────────────╯
        ╭─ Arguments ────────────────────────────────────────────────────────╮
        │ *  INFILE  [required]                                              │
        ╰────────────────────────────────────────────────────────────────────╯
        """
    )
    assert actual == expected


def test_remove_duplicates_collapses_identical_rows(app):
    """Rows rendering identically collapse to one, regardless of which Python parameter produced them."""
    from cyclopts.help.help import HelpEntry, HelpPanel

    panel = HelpPanel(
        format="parameter",
        title="Parameters",
        entries=[
            HelpEntry(positive_names=("--verbose",)),
            HelpEntry(positive_names=("--verbose",)),
            HelpEntry(positional_label="A"),
            HelpEntry(positional_label="B"),
        ],
    )
    panel._remove_duplicates()
    assert len(panel.entries) == 3


def test_meta_app_duplicate_option_collapses(console: Console):
    """A meta-app option and the command option it forwards to share one row even under different Python names."""
    app = App(name="app", result_action="return_value")

    @app.meta.default
    def meta(*tokens: str, verbose: bool = False):
        pass

    @app.default
    def cmd(*, v: Annotated[bool, Parameter(name="--verbose")] = False):
        pass

    with console.capture() as capture:
        app.meta.help_print(console=console)
    assert capture.get().count("--verbose --no-verbose") == 1


def test_structured_dict_suffixes_name_not_metavar(app):
    """A cycle-terminated ``dict[str, Model]`` leaf suffixes the ``.{NAME}`` layer onto the
    identifier (name), never the metavar (which describes the value shape).
    """
    from pydantic import BaseModel, Field

    class Node(BaseModel):
        label: str = Field(description="node label")
        children: dict[str, "Node"] = Field(default_factory=dict, description="child nodes")

    Node.model_rebuild()

    class TopConfig(BaseModel):
        root: dict[str, Node] = Field(default_factory=dict)

    @app.default
    def main(cfg: Annotated[TopConfig, Parameter(name="*")] | None = None):
        pass

    entries = {e.names[0]: e for e in _parameter_entries(app)}

    # Leaf field: type-derived metavar, no positional label (dotted keyword parameter).
    label_leaf = entries["--root.{NAME}.label"]
    assert label_leaf.metavar == "STR"
    assert label_leaf.positional_label is None

    # Cycle terminus: the ``.{NAME}`` next-level suffix rides on the name identifier,
    # while the metavar stays the plain type-derived value shape.
    child = entries["--root.{NAME}.children.{NAME}"]
    assert child.names[0].endswith(".{NAME}")
    assert child.metavar is None
    assert child.positional_label is None


def test_metavar_default_panel_rendering_unchanged(app, console: Console):
    """The builtin panel output is unaffected by the metavar/label split."""

    @app.default
    def main(
        url: str,
        /,
        dest: Path = Path(),
        *,
        quality: Literal["144", "720"] = "720",
        flag: bool = False,
    ):
        pass

    with console.capture() as capture:
        app.help_print(console=console)
    actual = capture.get()

    # Assert the label-relevant rendering directly rather than a full-panel snapshot:
    # the ``--quality`` choices/default spacing is width-sensitive and orthogonal to this.
    assert actual.startswith("Usage: test_help_metavar [OPTIONS] URL [ARGS]")
    # Positional-only: label comes from the name, no option name.
    assert "│ *  URL  [required]" in actual
    # Optional positional-or-keyword: name-derived label precedes the option name.
    assert "DEST --dest" in actual
    # Keyword-only with choices: option name only; ``[choices]`` suppresses the metavar.
    assert "│ --quality " in actual
    assert "QUALITY" not in actual
    # Keyword-only boolean flag: negatives shown, never a label.
    assert "--flag --no-flag" in actual
    assert "FLAG" not in actual


def test_metavar_option_rendered_by_custom_formatter(console: Console):
    """A custom column can render ``entry.metavar`` directly (``--config -c FILE``).

    Demonstrates how custom columns opt into the metavar, independent of the default
    :class:`NameRenderer`, per the "Metavars" section of ``docs/source/help_customization.rst``.
    The default metavar is type-derived (``--out STR``); an explicit override wins
    (``--config FILE``).
    """
    from cyclopts import Group
    from cyclopts.help import ColumnSpec, DefaultFormatter

    def names_renderer(entry):
        options = " ".join(entry.all_options)
        return f"{options} {entry.metavar}" if entry.metavar else options

    group = Group(
        "Options",
        help_formatter=DefaultFormatter(
            column_specs=(
                ColumnSpec(renderer=names_renderer),
                ColumnSpec(renderer="description", overflow="fold"),
            )
        ),
    )

    app = App(name="test_help_metavar", result_action="return_value")

    @app.default
    def main(
        *,
        config: Annotated[
            str, Parameter(name=["--config", "-c"], metavar="FILE", group=group, help="Config file.")
        ] = "",
        out: Annotated[str, Parameter(group=group, help="Output path.")] = "",
        verbose: Annotated[bool, Parameter(name=["--verbose", "-v"], group=group, help="Verbose.")] = False,
    ):
        pass

    with console.capture() as capture:
        app.help_print(console=console)

    actual = capture.get()
    expected = dedent(
        """\
        Usage: test_help_metavar [OPTIONS]

        ╭─ Commands ─────────────────────────────────────────────────────────╮
        │ --help (-h)  Display this message and exit.                        │
        │ --version    Display application version.                          │
        ╰────────────────────────────────────────────────────────────────────╯
        ╭─ Options ──────────────────────────────────────────────────────────╮
        │ --config -c FILE           Config file.                            │
        │ --out STR                  Output path.                            │
        │ --verbose -v --no-verbose  Verbose.                                │
        ╰────────────────────────────────────────────────────────────────────╯
        """
    )
    assert actual == expected


@pytest.mark.parametrize("output_format", ["markdown", "restructuredtext", "html"])
def test_positional_label_rendered_by_all_builtin_formatters(app, output_format):
    """Every builtin formatter renders the positional label (name-derived) via ``display_labels``."""

    @app.default
    def main(infile: Annotated[Path, Parameter(name="SOURCE")], /):
        pass

    docs = app.generate_docs(output_format=output_format)  # pyright: ignore[reportArgumentType]
    assert "SOURCE" in docs
    assert "INFILE" not in docs
