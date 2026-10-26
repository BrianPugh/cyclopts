"""Tests for the 'cyclopts skill' command."""

import pytest

from cyclopts.cli import app as cyclopts_cli
from cyclopts.cli.skill import SKILL_PATH


def test_skill_install_project(tmp_path, capsys):
    """--project writes the bundled SKILL.md into ./.claude/skills/cyclopts/."""
    with pytest.raises(SystemExit):
        cyclopts_cli(["skill", "install", "--project"])
    installed = tmp_path / ".claude" / "skills" / "cyclopts" / "SKILL.md"
    assert installed.read_text() == SKILL_PATH.read_text()
    assert str(installed) in capsys.readouterr().out


def test_skill_install_dest(tmp_path):
    dest = tmp_path / "custom"
    with pytest.raises(SystemExit):
        cyclopts_cli(["skill", "install", "--dest", str(dest)])
    assert (dest / "SKILL.md").exists()


def test_skill_show(capsys):
    with pytest.raises(SystemExit):
        cyclopts_cli(["skill", "show"])
    assert capsys.readouterr().out == SKILL_PATH.read_text()
