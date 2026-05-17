"""Rich-formatted output tests for cyclopts exceptions."""

import re
from io import StringIO
from typing import Literal
from unittest.mock import Mock

import pytest

import cyclopts
from cyclopts import (
    Argument,
    ArgumentOrderError,
    CoercionError,
    MissingArgumentError,
    MixedArgumentError,
    Parameter,
    RepeatArgumentError,
    RequiresEqualsError,
    Token,
    UnknownCommandError,
    UnknownOptionError,
    ValidationError,
)
from cyclopts._convert import convert
from cyclopts.panel import CycloptsPanel
from cyclopts.utils import default_name_transform

_ANSI_RE = re.compile(r"\x1b\[[0-9;]*m")


def _strip_ansi(s: str) -> str:
    return _ANSI_RE.sub("", s)


def _provoke_coercion_error(*args, **kwargs) -> CoercionError:
    """Provoke a CoercionError the way the production code path would, then
    attach a mocked argument so the exception is fully populated.
    """
    mock_argument = Mock()
    mock_argument.name = "mocked_argument_name"
    mock_argument.parameter.name_transform = default_name_transform
    kwargs.setdefault("name_transform", default_name_transform)
    try:
        convert(*args, **kwargs)
    except CoercionError as e:
        e.argument = mock_argument
        e.verbose = False  # strip the multi-line debug prefix so tests stay focused
        return e
    raise AssertionError("convert() did not raise CoercionError")


def _spans(text) -> list[tuple[str, str | None]]:
    """Extract (text, style) pairs from a rich.text.Text object.

    rich's Text stores styles as Spans that index into a flat plain string;
    we slice the plain string by each span. Gaps between spans are emitted
    as (text, None) entries so callers can see un-styled regions in order.
    """
    plain = text.plain
    out: list[tuple[str, str | None]] = []
    cursor = 0
    for span in text.spans:
        if span.start > cursor:
            out.append((plain[cursor : span.start], None))
        out.append((plain[span.start : span.end], str(span.style)))
        cursor = span.end
    if cursor < len(plain):
        out.append((plain[cursor:], None))
    return out


# ---------------------------------------------------------------------------
# __str__ unchanged: parity assertions on a few representative cases.
# ---------------------------------------------------------------------------


def test_str_parity_literal_with_suggestion():
    e = _provoke_coercion_error(Literal["pishock", "openshock"], ["pisock"])
    assert str(e) == (
        'Invalid value "pisock" for MOCKED_ARGUMENT_NAME. Choose from: "pishock", "openshock". Did you mean "pishock"?'
    )


def test_str_parity_literal_keyword_non_cli_source():
    e = _provoke_coercion_error(
        Literal["foo", "bar", 3],
        [Token(keyword="--MY-KEYWORD", value="invalid-choice", source="TEST")],
    )
    assert str(e) == 'Invalid value "invalid-choice" for --MY-KEYWORD from TEST. Choose from: "foo", "bar", 3.'


def test_str_parity_fallback_int_conversion():
    e = _provoke_coercion_error(int, ["abc"])
    assert str(e) == 'Invalid value for MOCKED_ARGUMENT_NAME: unable to convert "abc" into int.'


def test_str_parity_msg_override_no_keyword():
    e = CoercionError(msg="custom error")
    assert str(e) == "custom error"


def test_str_parity_msg_override_with_keyword():
    e = CoercionError(msg="custom error", token=Token(keyword="--flag", value="x"))
    assert str(e) == "Invalid value for --flag: custom error"


# ---------------------------------------------------------------------------
# __rich__ spans: per-branch verification.
# ---------------------------------------------------------------------------


def test_rich_literal_branch_styles_value_name_choices_suggestion():
    e = _provoke_coercion_error(Literal["pishock", "openshock"], ["pisock"])
    spans = _spans(e.__rich__())

    # Value, name, each choice, and the suggestion are styled.
    assert ("pisock", "bold red") in spans
    assert ("MOCKED_ARGUMENT_NAME", "bold") in spans
    assert ('"pishock"', "cyan") in spans
    assert ('"openshock"', "cyan") in spans
    assert ("pishock", "bold green") in spans


def test_rich_literal_branch_no_suggestion_omits_did_you_mean():
    e = _provoke_coercion_error(Literal["pishock", "openshock"], ["auth"])
    rich_text = e.__rich__()
    assert "Did you mean" not in rich_text.plain
    styles = [str(s.style) for s in rich_text.spans]
    assert "bold green" not in styles


def test_rich_literal_branch_dims_non_cli_source():
    e = _provoke_coercion_error(
        Literal["foo", "bar"],
        [Token(value="bad", source="CONFIG")],
    )
    spans = _spans(e.__rich__())
    assert (" from CONFIG", "dim") in spans


def test_rich_literal_branch_uses_keyword_as_name_when_present():
    e = _provoke_coercion_error(
        Literal["foo", "bar"],
        [Token(keyword="--my-flag", value="bad")],
    )
    spans = _spans(e.__rich__())
    assert ("--my-flag", "bold") in spans
    # MOCKED_ARGUMENT_NAME should NOT appear when keyword is present.
    plain = e.__rich__().plain
    assert "MOCKED_ARGUMENT_NAME" not in plain


def test_rich_fallback_branch_styles_value_and_name():
    e = _provoke_coercion_error(int, ["abc"])
    spans = _spans(e.__rich__())
    assert ("MOCKED_ARGUMENT_NAME", "bold") in spans
    assert ("abc", "bold red") in spans


def test_rich_fallback_branch_dims_non_cli_source():
    e = _provoke_coercion_error(int, [Token(value="abc", source="ENV")])
    spans = _spans(e.__rich__())
    assert (" from ENV", "dim") in spans
    assert ("abc", "bold red") in spans


def test_rich_msg_override_yields_unstyled():
    e = CoercionError(msg="custom error", token=Token(keyword="--flag", value="x"))
    rich_text = e.__rich__()
    assert rich_text.plain == "Invalid value for --flag: custom error"
    # No styled spans -- override stays plain.
    assert all(s.style is None or str(s.style) == "" for s in rich_text.spans)


# ---------------------------------------------------------------------------
# ANSI smoke test: end-to-end render through CycloptsPanel.
# ---------------------------------------------------------------------------


def test_panel_renders_rich_styles_when_color_enabled(rich_console):
    """End-to-end: CycloptsPanel + truecolor console emits ANSI for styled spans."""
    e = _provoke_coercion_error(Literal["pishock", "openshock"], ["pisock"])
    buf = StringIO()
    rich_console.file = buf
    rich_console.print(CycloptsPanel(e))
    output = buf.getvalue()

    # ANSI escapes are present -- the panel didn't flatten styling away.
    assert "\x1b[" in output
    # Plain text (with ANSI stripped) is intact end-to-end.
    plain = _strip_ansi(output)
    assert 'Invalid value "pisock"' in plain
    assert 'Did you mean "pishock"?' in plain


def test_panel_renders_plain_when_color_disabled(console):
    """Existing snapshot-style test: color_system=None strips styles cleanly."""
    e = _provoke_coercion_error(Literal["pishock", "openshock"], ["pisock"])
    buf = StringIO()
    console.file = buf
    console.print(CycloptsPanel(e))
    output = buf.getvalue()

    assert "\x1b[" not in output
    assert 'Invalid value "pisock" for MOCKED_ARGUMENT_NAME' in output
    assert 'Did you mean "pishock"?' in output


# ---------------------------------------------------------------------------
# UnknownCommandError
# ---------------------------------------------------------------------------


def _provoke_unknown_command(commands: list[str], typed: str) -> UnknownCommandError:
    """Build an app, register `commands`, then run with `typed` to provoke the error."""
    app = cyclopts.App(result_action="return_value")
    for name in commands:
        app.command(name=name)(lambda: None)
    with pytest.raises(UnknownCommandError) as ei:
        app.parse_args(typed, exit_on_error=False)
    e = ei.value
    e.verbose = False
    return e


def test_unknown_command_str_parity_with_suggestion_and_list():
    e = _provoke_unknown_command(["mad-command"], "bad-command")
    assert str(e) == 'Unknown command "bad-command". Did you mean "mad-command"? Available commands: mad-command.'


def test_unknown_command_str_parity_ellipsis():
    e = _provoke_unknown_command([f"cmd{i}" for i in range(1, 10)], "cmd")
    assert str(e) == (
        'Unknown command "cmd". Did you mean "cmd9"? '
        "Available commands: cmd1, cmd2, cmd3, cmd4, cmd5, cmd6, cmd7, cmd8, ..."
    )


def test_unknown_command_str_parity_no_suggestion():
    e = _provoke_unknown_command(["foo"], "zzz")
    assert str(e) == 'Unknown command "zzz". Available commands: foo.'


def test_unknown_command_rich_styles_token_suggestion_and_commands():
    e = _provoke_unknown_command(["mad-command", "other-command"], "bad-command")
    spans = _spans(e.__rich__())
    assert ("bad-command", "bold red") in spans
    assert ("mad-command", "bold green") in spans
    # Both commands are listed and styled.
    assert ("mad-command", "cyan") in spans
    assert ("other-command", "cyan") in spans


def test_unknown_command_rich_no_suggestion_omits_did_you_mean():
    e = _provoke_unknown_command(["foo"], "zzz")
    rich_text = e.__rich__()
    assert "Did you mean" not in rich_text.plain
    styles = [str(s.style) for s in rich_text.spans]
    assert "bold green" not in styles


def test_unknown_command_rich_ellipsis_truncates_styled_list():
    e = _provoke_unknown_command([f"cmd{i}" for i in range(1, 10)], "cmd")
    spans = _spans(e.__rich__())
    # First 8 commands appear as cyan-styled spans; cmd9 does NOT (truncated).
    cyan_texts = [text for text, style in spans if style == "cyan"]
    assert "cmd1" in cyan_texts
    assert "cmd8" in cyan_texts
    assert "cmd9" not in cyan_texts
    # Ellipsis tail is plain.
    plain = e.__rich__().plain
    assert plain.endswith(", ...")


# ---------------------------------------------------------------------------
# Phase 4: UnknownOptionError
# ---------------------------------------------------------------------------


def _provoke_app_exception(exc_cls, app: cyclopts.App, argv: str):
    """Run app and capture an exception of type `exc_cls`."""
    with pytest.raises(exc_cls) as ei:
        app.parse_args(argv, exit_on_error=False)
    e = ei.value
    e.verbose = False
    return e


def _make_unknown_option_app() -> cyclopts.App:
    """An app where `--no-my-flag` is unknown but `--my-flag` is a close match."""
    app = cyclopts.App(result_action="return_value", default_parameter=Parameter(negative=""))

    @app.default
    def main(my_flag: bool = True):
        pass

    return app


def test_unknown_option_str_parity_cli_with_suggestion():
    e = _provoke_app_exception(UnknownOptionError, _make_unknown_option_app(), "--no-my-flag")
    assert str(e) == "Unknown option: --no-my-flag. Did you mean --my-flag?"


def test_unknown_option_rich_styles_token_and_suggestion():
    e = _provoke_app_exception(UnknownOptionError, _make_unknown_option_app(), "--no-my-flag")
    spans = _spans(e.__rich__())
    assert ("--no-my-flag", "bold red") in spans
    assert ("--my-flag", "bold green") in spans


def test_unknown_option_rich_dims_non_cli_source():
    e = UnknownOptionError(
        token=Token(keyword="--bogus", value="x", source="ENV"),
        argument_collection=Mock(__iter__=lambda self: iter([])),
    )
    e.verbose = False
    spans = _spans(e.__rich__())
    assert ("--bogus", "bold red") in spans
    assert (" from ENV", "dim") in spans


# ---------------------------------------------------------------------------
# Phase 5: MissingArgumentError + ConsumeMultipleError
# ---------------------------------------------------------------------------


def test_missing_argument_str_parity_with_command_chain():
    app = cyclopts.App(result_action="return_value")

    @app.command
    def foo(bar: int):
        pass

    e = _provoke_app_exception(MissingArgumentError, app, "foo")
    assert str(e) == 'Command "foo" parameter --bar requires an argument.'


def test_missing_argument_rich_styles_command_and_param():
    app = cyclopts.App(result_action="return_value")

    @app.command
    def foo(bar: int):
        pass

    e = _provoke_app_exception(MissingArgumentError, app, "foo")
    spans = _spans(e.__rich__())
    assert ("foo", "bold") in spans
    assert ("--bar", "bold") in spans


def test_missing_argument_rich_styles_did_you_mean_suggestion_and_typo():
    """`Did you mean --foo instead of --boo?` -- correct is suggestion, typo is value."""
    app = cyclopts.App(result_action="return_value")

    @app.command
    def some_command(*, foo: int):
        pass

    e = _provoke_app_exception(MissingArgumentError, app, "some-command --boo 123")
    spans = _spans(e.__rich__())
    # Correct option (suggestion) is bold green; user's typo is bold red.
    assert ("--foo", "bold green") in spans
    assert ("--boo", "bold red") in spans


# ---------------------------------------------------------------------------
# Phase 6: ValidationError
# ---------------------------------------------------------------------------


def test_validation_error_str_parity_with_argument_and_source():
    """Mirrors test_exceptions_validation_error_non_cli_single_keyword."""

    def positive_validator(type_, value):
        if value <= 0:
            raise ValueError("Value must be positive.")

    argument = Argument(
        hint=int,
        parameter=Parameter(name=("--bar",), validator=positive_validator),
        tokens=[Token(value="-2", source="test")],
    )
    with pytest.raises(ValidationError) as ei:
        argument.convert_and_validate()
    e = ei.value
    e.verbose = False

    assert str(e) == 'Invalid value "-2" for BAR provided by test. Value must be positive.'


def test_validation_error_rich_styles_value_name_source_and_appended_message():
    def positive_validator(type_, value):
        if value <= 0:
            raise ValueError("Value must be positive.")

    argument = Argument(
        hint=int,
        parameter=Parameter(name=("--bar",), validator=positive_validator),
        tokens=[Token(value="-2", source="test")],
    )
    with pytest.raises(ValidationError) as ei:
        argument.convert_and_validate()
    e = ei.value
    e.verbose = False
    spans = _spans(e.__rich__())

    assert ("-2", "bold red") in spans
    assert ("BAR", "bold") in spans
    assert (" provided by test", "dim") in spans
    # Appended exception_message stays plain.
    assert "Value must be positive." in e.__rich__().plain


# ---------------------------------------------------------------------------
# Phase 7: small one-line classes
# ---------------------------------------------------------------------------


def test_repeat_argument_error_rich_styles_keyword():
    app = cyclopts.App(result_action="return_value")

    @app.default
    def main(a):
        pass

    e = _provoke_app_exception(RepeatArgumentError, app, "--a=1 --a=2")
    assert str(e) == "Parameter --a specified multiple times."
    spans = _spans(e.__rich__())
    assert ("--a", "bold") in spans


def test_requires_equals_error_rich_styles_keyword_twice():
    e = RequiresEqualsError(
        keyword="--name",
        argument=Mock(name="--name"),
    )
    e.verbose = False
    assert str(e) == "Parameter --name requires a value assigned with `=`. Use --name=VALUE."
    spans = _spans(e.__rich__())
    # The keyword appears twice in the message, both styled bold.
    bold_names = [text for text, style in spans if style == "bold"]
    assert bold_names == ["--name", "--name"]


def test_mixed_argument_error_rich_styles_display_name():
    app = cyclopts.App(result_action="return_value")

    @app.default
    def foo(bar: int | dict):
        pass

    e = _provoke_app_exception(MixedArgumentError, app, "--bar 5 --bar.baz fizz")
    assert str(e) == "Cannot supply keyword & non-keyword arguments to --bar."
    spans = _spans(e.__rich__())
    assert ("--bar", "bold") in spans


def test_argument_order_error_singular_str_parity_and_styling():
    app = cyclopts.App(result_action="return_value")

    @app.command
    def foo(a, b, c):
        pass

    e = _provoke_app_exception(ArgumentOrderError, app, "foo --b=5 1 2")
    assert str(e) == (
        'Cannot specify token "2" positionally for parameter c due to '
        "previously specified keyword --b. --b must either be passed positionally, "
        'or "2" must be passed as a keyword to --c.'
    )
    spans = _spans(e.__rich__())
    # Token appears twice (bold red), display_name once (bold), prior keyword twice (bold),
    # argument.name once (bold).
    red_tokens = [text for text, style in spans if style == "bold red"]
    assert red_tokens == ["2", "2"]
    bold_names = [text for text, style in spans if style == "bold"]
    # display_name "c", prior "--b" twice, argument.name "--c"
    assert bold_names == ["c", "--b", "--b", "--c"]


def test_argument_order_error_plural_styles_list_literal():
    app = cyclopts.App(result_action="return_value")

    @app.command
    def foo(a, b, c):
        pass

    e = _provoke_app_exception(ArgumentOrderError, app, "foo --a=1 --b=5 3")
    spans = _spans(e.__rich__())
    # The list literal "['--a', '--b']" appears twice, styled as a single bold span each time.
    bold_strs = [text for text, style in spans if style == "bold"]
    assert bold_strs.count("['--a', '--b']") == 2
