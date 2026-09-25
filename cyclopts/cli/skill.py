"""Install the bundled Cyclopts agent skill for LLM coding assistants."""

import shutil
from pathlib import Path
from typing import Annotated

from cyclopts.cli import app
from cyclopts.core import App
from cyclopts.parameter import Parameter

SKILL_PATH = Path(__file__).parent.parent / "skills" / "cyclopts" / "SKILL.md"

skill = App(name="skill")
app.command(skill)


@skill.command
def install(
    *,
    project: Annotated[bool, Parameter(alias="-p", negative="")] = False,
    dest: Path | None = None,
):
    """Install the bundled Cyclopts skill for AI coding assistants.

    The skill teaches assistants idiomatic Cyclopts (docstrings for help, ``alias`` for short flags, etc.).
    Writes ``SKILL.md`` to Claude Code's user-wide directory ``~/.claude/skills/cyclopts/`` by default.
    To install into every detected agent at once, use ``npx skills add BrianPugh/cyclopts`` instead.

    Parameters
    ----------
    project : bool
        Install into the current project's ``.claude/skills/`` instead of the user-wide directory.
    dest : Path | None
        Directory to write ``SKILL.md`` into, for agents other than Claude Code; overrides ``--project``.
    """
    if dest is None:
        dest = (Path.cwd() if project else Path.home()) / ".claude" / "skills" / "cyclopts"
    dest.mkdir(parents=True, exist_ok=True)
    target = dest / "SKILL.md"
    shutil.copyfile(SKILL_PATH, target)
    print(f"Installed Cyclopts skill to {target}")


@skill.command
def show():
    """Print the Cyclopts skill to stdout, for redirecting into AGENTS.md or another tool's rules file."""
    print(SKILL_PATH.read_text(), end="")
