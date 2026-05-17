import textwrap
from io import StringIO

from rich.console import Console
from rich.text import Text

from cyclopts.panel import CycloptsPanel


def _render(panel) -> str:
    buf = StringIO()
    console = Console(file=buf, width=70, force_terminal=True, highlight=False, color_system=None, legacy_windows=False)
    console.print(panel)
    return buf.getvalue()


def test_cyclopts_panel_stringifies_plain_message():
    """A plain object without rich-protocol attrs is rendered via str()."""
    output = _render(CycloptsPanel("hello world"))
    expected = textwrap.dedent(
        """\
        ╭─ Error ────────────────────────────────────────────────────────────╮
        │ hello world                                                        │
        ╰────────────────────────────────────────────────────────────────────╯
        """
    )
    assert output == expected


def test_cyclopts_panel_passes_through_rich_renderable():
    """A message implementing __rich__ is passed through unwrapped."""

    class HasRich:
        def __str__(self) -> str:
            return "string fallback"

        def __rich__(self) -> Text:
            return Text("rich body")

    output = _render(CycloptsPanel(HasRich()))
    assert "rich body" in output
    assert "string fallback" not in output


def test_cyclopts_panel_passes_through_rich_console_renderable():
    """A message implementing __rich_console__ is also passed through."""

    class HasRichConsole:
        def __str__(self) -> str:
            return "string fallback"

        def __rich_console__(self, console, options):
            yield Text("console body")

    output = _render(CycloptsPanel(HasRichConsole()))
    assert "console body" in output
    assert "string fallback" not in output
