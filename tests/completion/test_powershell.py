"""PowerShell completion: the full-mode ``__complete`` protocol and the generated script.

The script tests drive real PowerShell through ``TabExpansion2`` (see ``conftest.py``).
They run under ``pwsh``, plus Windows PowerShell 5.1 (``powershell.exe``) on Windows.
"""

import os
import sys
from pathlib import Path
from typing import Annotated, Literal

import pytest

from cyclopts import App, Parameter
from cyclopts.completion._engine import COMPLETE_WORDS_ENV_VAR

from .conftest import PowerShellCompletionTester, _check_windows_powershell_available


def _full_complete(app, words, monkeypatch, capsys) -> list[str]:
    monkeypatch.setenv(COMPLETE_WORDS_ENV_VAR, "".join(word + "\x1f" for word in words))
    app(["__complete"], exit_on_error=False)
    lines = capsys.readouterr().out.splitlines()
    return lines[lines.index("\x1fbegin") + 1 :]


@pytest.fixture
def app():
    app = App(name="myapp", result_action="return_value")

    def complete_user(ctx):
        return [("alice", "Admin"), "bob", "anna"]

    @app.command
    def deploy(
        env: Literal["dev", "prod"],
        *,
        user: Annotated[str, Parameter(completer=complete_user)] = "",
        config: Path | None = None,
        verbose: bool = False,
    ):
        """Deploy the **service**.

        Parameters
        ----------
        user: str
            Who *deploys*.
        """

    @app.command
    def destroy():
        """Tear it all down."""

    return app


def test_full_mode_commands_with_descriptions(app, monkeypatch, capsys):
    assert _full_complete(app, [""], monkeypatch, capsys) == [
        "deploy\tDeploy the service.",
        "destroy\tTear it all down.",
    ]


def test_full_mode_filters_by_prefix(app, monkeypatch, capsys):
    assert _full_complete(app, ["dep"], monkeypatch, capsys) == ["deploy\tDeploy the service."]


def test_full_mode_prefix_is_case_insensitive(app, monkeypatch, capsys):
    assert _full_complete(app, ["DeP"], monkeypatch, capsys) == ["deploy\tDeploy the service."]
    assert _full_complete(app, ["deploy", "--U"], monkeypatch, capsys) == ["--user\tWho deploys."]
    assert _full_complete(app, ["deploy", "--user", "A"], monkeypatch, capsys) == ["alice\tAdmin", "anna"]


def test_full_mode_option_names_with_docstring_descriptions(app, monkeypatch, capsys):
    assert _full_complete(app, ["deploy", "--u"], monkeypatch, capsys) == ["--user\tWho deploys."]


def test_full_mode_uses_command_help_version_flags(monkeypatch, capsys):
    app = App(name="myapp", version="1.0", result_action="return_value")

    @app.command(help_flags=["--aide"], version_flags=[])
    def deploy(): ...

    assert _full_complete(app, ["-"], monkeypatch, capsys) == [
        "--help\tDisplay this message and exit.",
        "-h\tDisplay this message and exit.",
        "--version\tDisplay application version.",
    ]
    assert _full_complete(app, ["deploy", "-"], monkeypatch, capsys) == ["--aide"]


def test_full_mode_static_choices(app, monkeypatch, capsys):
    assert _full_complete(app, ["deploy", ""], monkeypatch, capsys) == ["dev", "prod"]


def test_full_mode_filters_completer_values(app, monkeypatch, capsys):
    """Unlike legacy mode, full mode prefix-filters completer output too."""
    assert _full_complete(app, ["deploy", "--user", "a"], monkeypatch, capsys) == ["alice\tAdmin", "anna"]


def test_full_mode_eq_form_emits_prefix_directive(app, monkeypatch, capsys):
    assert _full_complete(app, ["deploy", "--user=a"], monkeypatch, capsys) == [
        "\x1fprefix\t--user=",
        "alice\tAdmin",
        "anna",
    ]


def test_full_mode_path_emits_files_directive(app, monkeypatch, capsys):
    assert _full_complete(app, ["deploy", "--config", ""], monkeypatch, capsys) == ["\x1ffiles"]


def test_full_mode_unresolvable_line_is_empty(app, monkeypatch, capsys):
    assert _full_complete(app, ["deploy", "--bogus", "x", ""], monkeypatch, capsys) == []


def test_full_mode_env_var_hidden_from_completer(monkeypatch, capsys):
    seen = []
    app = App(name="myapp", result_action="return_value")

    def spy(ctx):
        import os

        seen.append(os.environ.get(COMPLETE_WORDS_ENV_VAR))
        return ["x"]

    @app.default
    def main(*, thing: Annotated[str, Parameter(completer=spy)] = ""):
        pass

    assert _full_complete(app, ["--thing", ""], monkeypatch, capsys) == ["x"]
    assert seen == [None]


def test_full_mode_words_env_overrides_arguments(app, monkeypatch, capsys):
    monkeypatch.setenv(COMPLETE_WORDS_ENV_VAR, "dep\x1f")
    app(["__complete", "ignored", ""], exit_on_error=False)
    out = capsys.readouterr().out.splitlines()
    assert out[out.index("\x1fbegin") + 1 :] == ["deploy\tDeploy the service."]


def test_legacy_mode_has_no_static_candidates(app, capsys):
    """bash/zsh/fish already know the static candidates; ``__complete`` must not repeat them."""
    app(["__complete", "deploy", ""], exit_on_error=False)
    out = capsys.readouterr().out.splitlines()
    assert out[out.index("\x1fbegin") + 1 :] == []


# --- Generated script -----------------------------------------------------------


def test_script_is_ascii():
    """Windows PowerShell 5.1 reads a BOM-less script as ANSI."""
    App(name="myapp").generate_completion(shell="powershell").encode("ascii")


def test_script_registers_exe_name():
    script = App(name="myapp").generate_completion(shell="powershell")
    assert "-CommandName 'myapp', 'myapp.exe'" in script


def test_script_quotes_prog_name():
    script = App(name="it's").generate_completion(shell="powershell")
    assert "-CommandName 'it''s', 'it''s.exe'" in script
    assert "$programName = 'it''s'" in script


def test_script_non_ascii_prog_name_is_ascii():
    script = App(name="d\u00e9ploy\U0001f600").generate_completion(shell="powershell")
    script.encode("ascii")
    assert "$programName = (-join [char[]](0x64,0xe9,0x70,0x6c,0x6f,0x79,0xd83d,0xde00))" in script


def test_script_comment_strips_line_breaks():
    script = App(name="a\rb\nc").generate_completion(shell="powershell")
    assert script.startswith("# PowerShell completion for a b c (generated by cyclopts).\n")


def test_script_syntax(pwsh_available):
    if not pwsh_available:
        pytest.skip("pwsh not available")
    script = App(name="it's").generate_completion(shell="powershell")
    assert PowerShellCompletionTester(script, "its").validate_script_syntax()


# --- End to end ------------------------------------------------------------------

E2E_SOURCE = '''
from pathlib import Path
from typing import Annotated, Literal

from cyclopts import App, Parameter

app = App(name="deployer")


def complete_target(ctx):
    return [
        ("my target", "Has a space"),
        ("cost$5", "Has a dollar"),
        ("it's", "Has a quote"),
        ("café", "Non-ASCII"),
        ("rel*", "Has a glob"),
        ("br[ab]", "Has a glob"),
        ("O\u2019Brien", "Has a smart single quote"),
        ("dq\u201cz", "Has a smart double quote"),
    ]


@app.command
def deploy(
    env: Literal["dev", "prod"],
    *,
    target: Annotated[str, Parameter(completer=complete_target)] = "",
    config: Path | None = None,
    verbose: bool = False,
):
    """Deploy the service."""


if __name__ == "__main__":
    app()
'''


@pytest.fixture(params=["pwsh", "powershell"])
def tester(request, dynamic_completion_tester) -> PowerShellCompletionTester:
    if request.param == "powershell" and not _check_windows_powershell_available():
        pytest.skip("Windows PowerShell 5.1 not available")
    tester = dynamic_completion_tester(E2E_SOURCE, prog_name="deployer", shell="powershell")
    tester.executable = request.param
    return tester


def _texts(tester, line, cursor=None):
    return [text for text, *_ in tester.get_results(line, cursor)]


def test_e2e_result_types_and_tooltips(tester):
    results = tester.get_results("deployer deploy --c")
    assert results == [("--config", "--config", "--config", "ParameterName")]
    results = tester.get_results("deployer d")
    assert results == [("deploy", "deploy", "Deploy the service.", "ParameterValue")]


@pytest.mark.parametrize(
    ("line", "expected"),
    [
        ("deployer deploy --target my", ["'my target'"]),
        ("deployer deploy --target co", ["'cost$5'"]),
        ("deployer deploy --target it", ["'it''s'"]),
        ("deployer deploy --target 'my", ["'my target'"]),
        ("deployer deploy --target 'co", ["'cost$5'"]),
        ('deployer deploy --target "co', ['"cost`$5"']),
        ("deployer deploy --target=my", ["'--target=my target'"]),
        ("deployer deploy --target re", ["'rel*'"]),
        ("deployer deploy --target br", ["'br[ab]'"]),
        ("deployer deploy --target O", ["'O\u2019\u2019Brien'"]),
        ("deployer deploy --target 'O", ["'O\u2019\u2019Brien'"]),
        ("deployer deploy --target dq", ["'dq\u201cz'"]),
        ('deployer deploy --target "dq', ['"dq`\u201cz"']),
    ],
)
def test_e2e_quoting(tester, line, expected):
    assert _texts(tester, line) == expected


def test_e2e_case_insensitive(tester):
    assert _texts(tester, "deployer DEP") == ["deploy"]


def test_e2e_non_ascii(tester):
    assert tester.get_results("deployer deploy --target ca") == [("café", "café", "Non-ASCII", "ParameterValue")]


def test_e2e_eq_form_menu_shows_bare_value(tester):
    assert tester.get_results("deployer deploy --env=p") == [("--env=prod", "prod", "prod", "ParameterValue")]


def test_e2e_cursor_mid_line(tester):
    """Words after the cursor are ignored; the word under the cursor is cut at the cursor."""
    line = "deployer deploy --env=pxyz --verbose"
    assert _texts(tester, line, cursor=len("deployer deploy --env=p")) == ["--env=prod"]


def test_e2e_command_later_in_line(tester):
    assert _texts(tester, "$x = 1; deployer deploy p") == ["prod"]


def test_e2e_paths(tester, tmp_path, monkeypatch):
    (tmp_path / "work").mkdir()
    (tmp_path / "work" / "my file.txt").write_text("")
    (tmp_path / "work" / "conf.toml").write_text("")
    monkeypatch.chdir(tmp_path / "work")
    sep = "\\" if sys.platform == "win32" else "/"
    assert sorted(_texts(tester, "deployer deploy --config ")) == [f"'.{sep}my file.txt'", f".{sep}conf.toml"]
    assert _texts(tester, "deployer deploy --config=co") == [f"--config=.{sep}conf.toml"]


def test_e2e_paths_are_literal(tester, tmp_path, monkeypatch):
    """CompleteFilename's cmdlet escaping is undone; the program receives the literal file name."""
    (tmp_path / "work").mkdir()
    names = ["br[1].txt", "tick`y.txt", "it's.txt"] + ([] if sys.platform == "win32" else ["a*b.txt"])
    for name in names:
        (tmp_path / "work" / name).write_text("")
    monkeypatch.chdir(tmp_path / "work")
    sep = "\\" if sys.platform == "win32" else "/"
    expected = [f"'.{sep}br[1].txt'", f"'.{sep}tick`y.txt'", f"'.{sep}it''s.txt'"]
    if sys.platform != "win32":
        expected.append(f"'.{sep}a*b.txt'")
    assert sorted(_texts(tester, "deployer deploy --config ")) == sorted(expected)
    assert _texts(tester, "deployer deploy --config=br") == [f"'--config=.{sep}br[1].txt'"]


def test_e2e_environment_restored(tester):
    """The script's temporary environment variables don't leak into the session."""
    driver = (
        "param([string]$Script)\n"
        ". $Script\n"
        "$env:PYTHONIOENCODING = 'sentinel'\n"
        "$null = TabExpansion2 -inputScript 'deployer deploy ' -cursorColumn 16\n"
        '[Console]::Out.Write("$env:PYTHONIOENCODING|$([bool](Test-Path env:CYCLOPTS_COMPLETE_WORDS))")\n'
    )
    result = tester._run(driver)
    assert result.stdout.decode() == "sentinel|False"


GAPS_SOURCE = """
from typing import Annotated

from cyclopts import App, Parameter

app = App(name="deployer")


def complete_point(ctx):
    return ["10", "11"] if ctx.index == 0 else ["20", "21"]


@app.default
def main(
    name: Annotated[str, Parameter(completer=lambda ctx: ["alpha", "beta"])] = "",
    *,
    point: Annotated[tuple[int, int], Parameter(completer=complete_point)] = (0, 0),
):
    pass


if __name__ == "__main__":
    app()
"""


def test_e2e_multi_token_option_later_values(dynamic_completion_tester):
    """The bash/zsh/fish scripts miss ``--point 1 <TAB>``; PowerShell asks the engine for every slot."""
    tester = dynamic_completion_tester(GAPS_SOURCE, prog_name="deployer", shell="powershell")
    assert tester.get_completions("deployer --point ") == ["10", "11"]
    assert tester.get_completions("deployer --point 10 ") == ["20", "21"]


def test_e2e_root_positional_completer(dynamic_completion_tester):
    """Fish doesn't wire a root-command positional completer; PowerShell does."""
    tester = dynamic_completion_tester(GAPS_SOURCE, prog_name="deployer", shell="powershell")
    assert tester.get_completions("deployer ") == ["alpha", "beta"]


def test_e2e_invoked_by_path_off_path(dynamic_completion_tester, tmp_path, monkeypatch):
    """The program the user typed is asked, even when its name isn't on PATH."""
    tester = dynamic_completion_tester(GAPS_SOURCE, prog_name="deployer", shell="powershell")
    bindir = tmp_path / "bin"
    monkeypatch.setenv("PATH", os.environ["PATH"].replace(f"{bindir}{os.pathsep}", "", 1))
    assert tester.get_completions(f"& '{bindir / 'deployer'}' ") == ["alpha", "beta"]


def test_e2e_non_ascii_prog_name(dynamic_completion_tester):
    tester = dynamic_completion_tester(
        GAPS_SOURCE.replace('"deployer"', '"déployer"'), prog_name="déployer", shell="powershell"
    )
    assert tester.get_completions("déployer ") == ["alpha", "beta"]


# --- Static script: completes without running the program ---------------------------------


def _static_app():
    app = App(name="ghost", version="1.0")

    @app.command(alias="dep")
    def deploy(
        env: Literal["dev", "prod"],
        *,
        point: tuple[int, int] = (0, 0),
        tags: Annotated[list[str], Parameter(consume_multiple=True)] = [],  # noqa: B006
        verbose: bool = False,
        out: Annotated[Path, Parameter(name="--out")] = Path(),
    ):
        """Deploy the service."""

    sub = App(name="sub", help_flags=["--aide"], version_flags=[])
    app.command(sub)

    @sub.default
    def run(level: Literal["low", "high"] = "low"): ...

    return app


@pytest.fixture(params=["pwsh", "powershell"])
def static_tester(request, pwsh_available) -> PowerShellCompletionTester:
    """Tester whose program ``ghost`` is not on PATH, so only the script's own data can answer."""
    if request.param == "pwsh" and not pwsh_available:
        pytest.skip("pwsh not available")
    if request.param == "powershell" and not _check_windows_powershell_available():
        pytest.skip("Windows PowerShell 5.1 not available")
    script = _static_app().generate_completion(shell="powershell")
    return PowerShellCompletionTester(script, "ghost", executable=request.param)


@pytest.mark.parametrize(
    ("line", "expected"),
    [
        ("ghost ", ["deploy", "dep", "sub"]),
        ("ghost d", ["deploy", "dep"]),
        ("ghost DE", ["deploy", "dep"]),
        ("ghost --", ["--help", "--version"]),
        ("ghost -", ["--help", "-h", "--version"]),
        ("ghost deploy ", ["dev", "prod"]),
        ("ghost dep p", ["prod"]),
        ("ghost deploy --env ", ["dev", "prod"]),
        ("ghost deploy --env=d", ["dev"]),
        ("ghost deploy --v", ["--verbose", "--version"]),
        ("ghost deploy --no", ["--no-verbose"]),
        ("ghost deploy --point 1 --v", ["--verbose", "--version"]),
        ("ghost deploy --tags a b --verb", ["--verbose"]),
        ("ghost deploy dev ", []),
        ("ghost sub -", ["--level", "--aide"]),
        ("ghost sub ", ["low", "high"]),
    ],
)
def test_static_completions(static_tester, line, expected):
    if static_tester.executable == "powershell" and line.split(" ")[-1] in ("-", "--"):
        pytest.skip("Windows PowerShell 5.1 never calls a native completer for a bare - or --")
    assert static_tester.get_completions(line) == expected


def test_static_after_end_of_options(static_tester):
    """Words after ``--`` are positional values, never option names."""
    assert static_tester.get_completions("ghost deploy -- -") == []
    assert static_tester.get_completions("ghost deploy -- p") == ["prod"]


def test_static_skips_option_values(static_tester):
    """A value that looks like a command or choice is consumed by its option, not counted as a positional."""
    assert static_tester.get_completions("ghost deploy --point 1 2 ") == ["dev", "prod"]


def test_static_eq_form_inserts_prefix(static_tester):
    assert _texts(static_tester, "ghost deploy --env=d") == ["--env=dev"]


def test_static_path_option(static_tester, tmp_path, monkeypatch):
    (tmp_path / "work").mkdir()
    (tmp_path / "work" / "folder").mkdir()
    (tmp_path / "work" / "file.txt").write_text("")
    monkeypatch.chdir(tmp_path / "work")
    sep = "\\" if sys.platform == "win32" else "/"
    assert sorted(_texts(static_tester, "ghost deploy --out ")) == [f".{sep}file.txt", f".{sep}folder"]


def test_static_negative_number_is_a_value(static_tester):
    assert static_tester.get_completions("ghost deploy --point -1 ") == []
    assert static_tester.get_completions("ghost deploy --point -1 -2 --verb") == ["--verbose"]
