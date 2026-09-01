"""Tests for dynamic (Python-invoked) shell completion.

These exercise the shell-agnostic engine (``compute_completions``) and the
reserved ``__complete`` command routing, without spawning a real shell.
"""

from pathlib import Path
from typing import Annotated

import pytest

from cyclopts import App, Parameter
from cyclopts.completion._engine import Completion, CompletionContext, compute_completions, normalize_completions
from cyclopts.utils import UNSET


@pytest.fixture
def users():
    return ["alice", "bob", "carol"]


@pytest.fixture
def app(users):
    app = App(name="myapp", result_action="return_value")

    def complete_user(ctx):
        return [u for u in users if u.startswith(ctx.incomplete)]

    def complete_env(ctx):
        return [("dev", "Development"), ("prod", "Production")]

    @app.command
    def deploy(
        service: Annotated[str, Parameter(completer=complete_env)],
        *,
        user: Annotated[str, Parameter(completer=complete_user)] = "",
        verbose: bool = False,
    ):
        pass

    return app


def _values(completions):
    return [c.value for c in completions]


def test_option_value_completion_empty(app, users):
    """``deploy --user <TAB>`` offers every candidate."""
    result = compute_completions(app, ["deploy", "--user", ""])
    assert _values(result) == users


def test_option_value_completion_prefix(app):
    """``ctx.incomplete`` is available so the callback can filter."""
    result = compute_completions(app, ["deploy", "--user", "a"])
    assert _values(result) == ["alice"]


def test_positional_value_completion_with_descriptions(app):
    """First positional slot uses its completer, preserving descriptions."""
    result = compute_completions(app, ["deploy", ""])
    assert result == [Completion("dev", "Development"), Completion("prod", "Production")]


def test_positional_completion_after_flag(app):
    """A boolean flag consumes no value, so the positional slot is unshifted."""
    result = compute_completions(app, ["deploy", "--verbose", ""])
    assert _values(result) == ["dev", "prod"]


def test_option_value_completion_after_positional(app):
    """An option value is completed even after a positional has been supplied."""
    result = compute_completions(app, ["deploy", "web", "--user", "b"])
    assert _values(result) == ["bob"]


def test_flag_option_does_not_trigger_value_completion(app):
    """The token following a flag is NOT that flag's value."""
    # ``--verbose`` is a flag; the next slot is the positional ``service``.
    result = compute_completions(app, ["deploy", "--verbose", "d"])
    assert _values(result) == ["dev", "prod"]


def test_unknown_command_returns_empty(app):
    result = compute_completions(app, ["does-not-exist", ""])
    assert result == []


def test_option_name_completion_is_not_dynamic(app):
    """Completing an option *name* (``--u``) is the static script's job, not ours."""
    result = compute_completions(app, ["deploy", "--u"])
    assert result == []


def test_argument_with_no_completer_returns_empty():
    app = App(name="myapp")

    @app.command
    def greet(name: str):
        pass

    assert compute_completions(app, ["greet", ""]) == []


def test_root_default_command_completion(users):
    app = App(name="myapp")

    def complete_user(ctx):
        return [u for u in users if u.startswith(ctx.incomplete)]

    @app.default
    def main(*, user: Annotated[str, Parameter(completer=complete_user)] = ""):
        pass

    result = compute_completions(app, ["--user", "c"])
    assert _values(result) == ["carol"]


def test_complete_command_prints_tab_separated(app, capsys):
    """The reserved ``__complete`` command prints ``value<TAB>description``."""
    app(["__complete", "deploy", ""], exit_on_error=False)
    out = capsys.readouterr().out.strip().splitlines()
    assert out == ["dev\tDevelopment", "prod\tProduction"]


def test_complete_command_bare_values_have_no_tab(app, capsys):
    app(["__complete", "deploy", "--user", ""], exit_on_error=False)
    out = capsys.readouterr().out.strip().splitlines()
    assert out == ["alice", "bob", "carol"]
    assert all("\t" not in line for line in out)


def test_complete_command_via_parse_args(app, capsys):
    """``__complete`` is intercepted inside the shared parse pipeline, so entry points that skip ``__call__`` (e.g. custom scripts using ``parse_args``) still handle it."""
    command, bound, _ = app.parse_args(["__complete", "deploy", "--user", ""])
    command(*bound.args, **bound.kwargs)
    assert capsys.readouterr().out.strip().splitlines() == ["alice", "bob", "carol"]


def test_complete_command_via_parse_known_args(app, capsys):
    command, bound, unused, _ = app.parse_known_args(["__complete", "deploy", ""])
    assert unused == []
    command(*bound.args, **bound.kwargs)
    assert capsys.readouterr().out.strip().splitlines() == ["dev\tDevelopment", "prod\tProduction"]


def test_broken_completer_is_swallowed(capsys):
    """A completer that raises must not surface a traceback into the shell."""
    app = App(name="myapp", result_action="return_value")

    def boom(ctx):
        raise RuntimeError("kaboom")

    @app.command
    def deploy(service: Annotated[str, Parameter(completer=boom)]):
        pass

    app(["__complete", "deploy", ""], exit_on_error=False)
    assert capsys.readouterr().out.strip() == ""


# --- active-slot resolution (real-parser backbone) ----------------------------


def test_sibling_positional_visible_when_completing_option_value():
    """A typed positional sibling is visible to an option value's completer."""
    app = App(name="myapp")
    seen = {}

    def complete_cluster(ctx):
        seen["provided"] = ctx["service"].provided
        seen["value"] = ctx["service"].value
        return ["c1"]

    @app.command
    def deploy(service: str, *, cluster: Annotated[str, Parameter(completer=complete_cluster)] = ""):
        pass

    result = compute_completions(app, ["deploy", "web", "--cluster", ""])
    assert _values(result) == ["c1"]
    assert seen == {"provided": True, "value": "web"}


def test_multi_token_option_does_not_shift_positional_slot():
    """An option consuming multiple tokens (``tuple[int, int]``) owns both value slots."""
    app = App(name="myapp")

    @app.command
    def cmd(
        target: Annotated[str, Parameter(completer=lambda ctx: ["t1"])] = "",
        *,
        point: tuple[int, int] = (0, 0),
    ):
        pass

    assert compute_completions(app, ["cmd", "--point", "1", ""]) == []  # still --point's 2nd value
    assert _values(compute_completions(app, ["cmd", "--point", "1", "2", ""])) == ["t1"]


def test_multi_token_option_completer_fires_for_each_element():
    app = App(name="myapp")

    @app.command
    def cmd(*, point: Annotated[tuple[int, int], Parameter(completer=lambda ctx: ["0"])] = (0, 0)):
        pass

    assert _values(compute_completions(app, ["cmd", "--point", ""])) == ["0"]
    assert _values(compute_completions(app, ["cmd", "--point", "1", ""])) == ["0"]
    assert compute_completions(app, ["cmd", "--point", "1", "2", ""]) == []


def test_var_positional_completer_fires_for_every_slot():
    app = App(name="myapp")

    @app.command
    def add(*files: Annotated[str, Parameter(completer=lambda ctx: ["f"])]):
        pass

    assert _values(compute_completions(app, ["add", ""])) == ["f"]
    assert _values(compute_completions(app, ["add", "one", ""])) == ["f"]
    assert _values(compute_completions(app, ["add", "one", "two", ""])) == ["f"]


def test_hidden_positional_occupies_a_slot():
    """A ``show=False`` positional still consumes a real slot."""
    app = App(name="myapp")

    @app.command
    def hid(
        secret: Annotated[str, Parameter(show=False)],
        service: Annotated[str, Parameter(completer=lambda ctx: ["svc"])],
    ):
        pass

    assert compute_completions(app, ["hid", ""]) == []  # the hidden secret's slot
    assert _values(compute_completions(app, ["hid", "tok", ""])) == ["svc"]


def test_end_of_options_delimiter_forces_positional():
    app = App(name="myapp")

    @app.command
    def cmd(name: Annotated[str, Parameter(completer=lambda ctx: ["n"])]):
        pass

    assert _values(compute_completions(app, ["cmd", "--", ""])) == ["n"]
    # ``--user`` after ``--`` is positional data that already filled ``name``.
    assert compute_completions(app, ["cmd", "--", "--user", ""]) == []


def test_negative_number_fills_positional_slot():
    app = App(name="myapp")

    @app.command
    def neg(delta: int, target: Annotated[str, Parameter(completer=lambda ctx: ["t"])]):
        pass

    assert _values(compute_completions(app, ["neg", "-5", ""])) == ["t"]
    assert _values(compute_completions(app, ["neg", "5", ""])) == ["t"]


def test_eq_form_option_value(app):
    """``--user=al`` (zsh/fish joined form) completes ``--user``'s value."""
    assert _values(compute_completions(app, ["deploy", "--user=a"])) == ["alice"]
    assert _values(compute_completions(app, ["deploy", "--user="])) == ["alice", "bob", "carol"]


def test_eq_form_bash_wordbreak_split(app):
    """Bash forwards ``--user=al`` as ``['--user', '=', 'al']``; the engine rejoins it."""
    assert _values(compute_completions(app, ["deploy", "--user", "=", "a"])) == ["alice"]
    assert _values(compute_completions(app, ["deploy", "--user", "="])) == ["alice", "bob", "carol"]


def test_keyword_supplied_positional_or_keyword_closes_slot(app):
    """``--service x`` fills the positional slot; the free word has no argument."""
    result = compute_completions(app, ["deploy", "--service", "x", ""])
    assert result == []


def test_default_parameter_completer_applies():
    """A completer supplied via ``App(default_parameter=...)`` is honored at runtime."""
    app = App(name="myapp", default_parameter=Parameter(completer=lambda ctx: ["dp"]))

    @app.command
    def cmd(service: str):
        pass

    assert _values(compute_completions(app, ["cmd", ""])) == ["dp"]


def test_meta_launcher_option_completer():
    """A meta launcher's option completer resolves at the root and after a subcommand."""
    app = App(name="myapp")

    @app.command
    def deploy(service: Annotated[str, Parameter(completer=lambda ctx: ["svc"])]):
        pass

    @app.meta.default
    def launcher(*tokens: str, env: Annotated[str, Parameter(completer=lambda ctx: ["dev", "prod"])] = ""):
        app(tokens)

    assert _values(compute_completions(app.meta, ["--env", ""])) == ["dev", "prod"]
    assert _values(compute_completions(app.meta, ["deploy", "--env", ""])) == ["dev", "prod"]
    # The command's own positional slot is unaffected by launcher parameters.
    assert _values(compute_completions(app.meta, ["deploy", ""])) == ["svc"]


def test_bare_name_lookup_with_kwargs_catch_all():
    """A bare-name lookup resolves the named sibling, not the ``**kwargs`` catch-all."""
    app = App(name="myapp")
    clusters = {"us-west": ["wa-1"]}

    def complete_cluster(ctx):
        return clusters.get(ctx["region"].value, [])

    @app.command
    def d(
        *,
        region: str = "",
        cluster: Annotated[str, Parameter(completer=complete_cluster)] = "",
        **kwargs: str,
    ):
        pass

    assert _values(compute_completions(app, ["d", "--region", "us-west", "--cluster", ""])) == ["wa-1"]


def test_sibling_value_from_env_var(monkeypatch):
    app = App(name="myapp")
    seen = {}

    def complete_cluster(ctx):
        seen["provided"] = ctx["region"].provided
        seen["value"] = ctx["region"].value
        return ["c"]

    @app.command
    def d(
        *,
        region: Annotated[str, Parameter(env_var="MYAPP_REGION")] = "",
        cluster: Annotated[str, Parameter(completer=complete_cluster)] = "",
    ):
        pass

    monkeypatch.setenv("MYAPP_REGION", "us-west")
    compute_completions(app, ["d", "--cluster", ""])
    assert seen == {"provided": True, "value": "us-west"}


def test_sibling_value_falls_back_to_default():
    """An untyped sibling's ``.value`` is its parameter default (the docs' Dependent Completions example)."""
    app = App(name="myapp")
    seen = {}

    def complete_cluster(ctx):
        seen["provided"] = ctx["region"].provided
        seen["value"] = ctx["region"].value
        return ["c"]

    @app.command
    def d(*, region: str = "us-east", cluster: Annotated[str, Parameter(completer=complete_cluster)] = ""):
        pass

    compute_completions(app, ["d", "--cluster", ""])
    assert seen == {"provided": False, "value": "us-east"}


def test_sibling_value_unset_without_default():
    app = App(name="myapp")
    seen = {}

    def complete_note(ctx):
        seen["value"] = ctx["req"].value
        return ["t"]

    @app.command
    def d(*, req: str, note: Annotated[str, Parameter(completer=complete_note)] = ""):
        pass

    compute_completions(app, ["d", "--note", ""])
    assert seen == {"value": UNSET}


# --- CYCLOPTS_COMPLETION_DEBUG diagnostic ------------------------------------


def test_debug_off_by_default_is_silent_on_stderr(app, capsys):
    app(["__complete", "deploy", "--user", ""], exit_on_error=False)
    captured = capsys.readouterr()
    assert captured.out.strip().splitlines() == ["alice", "bob", "carol"]  # candidates on stdout
    assert "[cyclopts:completion]" not in captured.err  # nothing on stderr


def test_debug_reports_resolution_on_stderr(app, capsys, monkeypatch):
    monkeypatch.setenv("CYCLOPTS_COMPLETION_DEBUG", "1")
    app(["__complete", "deploy", "--user", ""], exit_on_error=False)
    err = capsys.readouterr().err
    assert "[cyclopts:completion]" in err
    assert "active argument='--user'" in err
    assert "completer='complete_user'" in err
    assert "returned 3 candidate(s)" in err


def test_debug_surfaces_broken_completer_traceback(capsys, monkeypatch):
    monkeypatch.setenv("CYCLOPTS_COMPLETION_DEBUG", "1")
    app = App(name="myapp", result_action="return_value")

    def boom(ctx):
        raise RuntimeError("kaboom")

    @app.command
    def deploy(service: Annotated[str, Parameter(completer=boom)]):
        pass

    app(["__complete", "deploy", ""], exit_on_error=False)
    captured = capsys.readouterr()
    assert captured.out.strip() == ""  # still no candidates on stdout
    assert "RuntimeError: kaboom" in captured.err  # traceback surfaced on stderr


# --- normalize_completions (return-shape handling) ---------------------------


def test_normalize_bare_strings():
    assert normalize_completions(["a", "b"]) == [("a", ""), ("b", "")]


def test_normalize_single_string_is_one_candidate():
    """A bare ``str`` is one candidate, not one-per-character."""
    assert normalize_completions("alice") == [("alice", "")]


def test_normalize_top_level_tuple_is_one_described_candidate():
    """A bare ``(value, description)`` tuple is one candidate, not two values."""
    assert normalize_completions(("us-west", "Oregon")) == [("us-west", "Oregon")]


def test_normalize_mixed_iterable():
    assert normalize_completions(["a", ("b", "desc")]) == [("a", ""), ("b", "desc")]


def test_normalize_none_is_empty():
    assert normalize_completions(None) == []


def test_get_completions_none_without_completer():
    app = App(name="myapp")

    @app.command
    def deploy(service: str):
        pass

    arguments = app["deploy"].assemble_argument_collection()
    argument = next(a for a in arguments if a.field_info.name == "service")
    assert argument.get_completions(None) is None


def test_completer_participates_in_combine():
    fn = lambda ctx: ["x"]  # noqa: E731
    combined = Parameter.combine(Parameter(), Parameter(completer=fn))
    assert combined.completer is fn


# --- CompletionContext -------------------------------------------------------


def test_context_dependent_completion():
    """A completer can gate its candidates on a sibling argument's value."""
    clusters = {"us-west": ["wa-1", "wa-2"], "us-east": ["va-1"]}
    app = App(name="myapp")

    def complete_cluster(ctx):
        return clusters.get(ctx["--region"].value, [])

    @app.command
    def deploy(*, region: str = "", cluster: Annotated[str, Parameter(completer=complete_cluster)] = ""):
        pass

    assert _values(compute_completions(app, ["deploy", "--region", "us-west", "--cluster", ""])) == ["wa-1", "wa-2"]
    assert _values(compute_completions(app, ["deploy", "--region", "us-east", "--cluster", ""])) == ["va-1"]
    # No region supplied yet -> the sibling lookup yields "" -> no clusters.
    assert compute_completions(app, ["deploy", "--cluster", ""]) == []


def test_context_raw_and_coerced_value():
    """``.raw`` is the typed string; ``.value`` is best-effort coerced."""
    captured = {}
    app = App(name="myapp")

    def complete(ctx):
        sibling = ctx["replicas"]
        captured["raw"] = sibling.raw
        captured["value"] = sibling.value
        captured["provided"] = sibling.provided
        captured["parameter_is"] = ctx.parameter is ctx.argument.parameter
        return ["ok"]

    @app.command
    def scale(*, replicas: int = 1, note: Annotated[str, Parameter(completer=complete)] = ""):
        pass

    compute_completions(app, ["scale", "--replicas", "5", "--note", ""])
    assert captured["raw"] == "5"  # raw string
    assert captured["value"] == 5  # coerced to int
    assert captured["provided"] is True
    assert captured["parameter_is"] is True


def test_context_unprovided_sibling():
    """An untyped sibling reports not-provided, raw None, and its default as value."""
    captured = {}
    app = App(name="myapp")

    def complete(ctx):
        sibling = ctx["replicas"]
        captured["raw"] = sibling.raw
        captured["value"] = sibling.value
        captured["provided"] = sibling.provided
        return ["ok"]

    @app.command
    def scale(*, replicas: int = 1, note: Annotated[str, Parameter(completer=complete)] = ""):
        pass

    compute_completions(app, ["scale", "--note", ""])
    assert captured["raw"] is None
    assert captured["value"] == 1
    assert captured["provided"] is False


def test_context_get_unknown_name_returns_default():
    app = App(name="myapp")

    def complete(ctx):
        return [str(ctx.get("does-not-exist", "fallback"))]

    @app.command
    def deploy(service: Annotated[str, Parameter(completer=complete)]):
        pass

    assert _values(compute_completions(app, ["deploy", ""])) == ["fallback"]


def test_context_getitem_unknown_name_raises_keyerror():
    app = App(name="myapp")

    @app.command
    def deploy(service: str):
        pass

    ctx = CompletionContext(incomplete="", argument=None, arguments=app["deploy"].assemble_argument_collection())  # type: ignore[arg-type]
    with pytest.raises(KeyError):
        ctx["totally-unknown"]


# --- generated shell scripts delegate to __complete --------------------------


@pytest.fixture
def completer_app():
    app = App(name="deployer")

    @app.command
    def deploy(*, user: Annotated[str, Parameter(completer=lambda ctx: ["alice"])] = ""):
        pass

    return app


@pytest.mark.parametrize("shell", ["bash", "zsh", "fish"])
def test_generated_script_delegates_to_complete(completer_app, shell):
    """A completer-backed option makes each shell call back into ``__complete``."""
    script = completer_app.generate_completion(prog_name="deployer", shell=shell)
    assert "__complete" in script


def test_fish_positional_completer_guarded_against_option_tokens():
    """Positional completer entries must not spawn ``__complete`` while an option name is being typed."""
    app = App(name="deployer")

    @app.command
    def deploy(service: Annotated[str, Parameter(completer=lambda ctx: ["web"])]):
        pass

    script = app.generate_completion(prog_name="deployer", shell="fish")
    positional_entries = [line for line in script.splitlines() if "__complete" in line and "positional_index" in line]
    assert positional_entries
    assert all('not string match -q -- "-*" (commandline -ct)' in line for line in positional_entries)


def test_zsh_helper_only_emitted_when_completer_present():
    """Completer-free apps generate no runtime helper (keeps the autoload structure)."""
    app = App(name="plain")

    @app.command
    def deploy(*, name: str = ""):
        pass

    script = app.generate_completion(prog_name="plain", shell="zsh")
    assert "_cyclopts_plain_complete" not in script
    assert "__complete" not in script


# --- real-shell end-to-end (bash/zsh/fish drive the actual __complete call) ---

# A self-contained app module for the ``dynamic_completion_tester`` fixture: it
# must define ``app`` and dispatch on ``__main__`` so the installed shim can
# answer ``deployer __complete ...``.
E2E_APP_SOURCE = """
from typing import Annotated

from cyclopts import App, Parameter

app = App(name="deployer")

USERS = ["alice", "bob", "carol"]
CLUSTERS = {"us-east": ["va-1"], "us-west": ["wa-1", "wa-2"]}


def complete_user(ctx):
    return [u for u in USERS if u.startswith(ctx.incomplete)]


def complete_cluster(ctx):
    return CLUSTERS.get(ctx["--region"].value, [])


def complete_env(ctx):
    return [("dev", "Development"), ("prod", "Production")]


@app.command
def deploy(
    *,
    region: str = "",
    cluster: Annotated[str, Parameter(completer=complete_cluster)] = "",
    user: Annotated[str, Parameter(completer=complete_user)] = "",
    env: Annotated[str, Parameter(completer=complete_env)] = "",
):
    pass


if __name__ == "__main__":
    app()
"""


# zsh renders described completions as ``value -- description``; fish/bash return
# the bare value. Normalize to the value so assertions are cross-shell uniform.
def _lead(completion: str) -> str:
    return completion.split("\t", 1)[0].split(" -- ", 1)[0].strip()


@pytest.fixture(params=["bash", "zsh", "fish"])
def shell(request):
    return request.param


def test_e2e_option_value(dynamic_completion_tester, shell):
    tester = dynamic_completion_tester(E2E_APP_SOURCE, prog_name="deployer", shell=shell)
    result = [_lead(c) for c in tester.get_completions("deployer deploy --user ")]
    assert sorted(result) == ["alice", "bob", "carol"]


def test_e2e_option_value_prefix(dynamic_completion_tester, shell):
    tester = dynamic_completion_tester(E2E_APP_SOURCE, prog_name="deployer", shell=shell)
    result = [_lead(c) for c in tester.get_completions("deployer deploy --user a")]
    assert result == ["alice"]


def test_e2e_descriptions(dynamic_completion_tester, shell):
    tester = dynamic_completion_tester(E2E_APP_SOURCE, prog_name="deployer", shell=shell)
    result = sorted(_lead(c) for c in tester.get_completions("deployer deploy --env "))
    assert result == ["dev", "prod"]


E2E_SUBCOMMAND_NAMED_ENV_SOURCE = """
from typing import Annotated

from cyclopts import App, Parameter

app = App(name="deployer")


def complete_user(ctx):
    return ["alice", "bob", "carol"]


@app.command
def env(*, user: Annotated[str, Parameter(completer=complete_user)] = ""):
    pass


if __name__ == "__main__":
    app()
"""


def test_e2e_subcommand_named_like_path_executable(dynamic_completion_tester, shell):
    """A subcommand named after a PATH executable (``env``) must still complete.

    Regression test for the zsh helper reading live ``$words[1]`` inside a
    subcommand frame, where ``_arguments`` rebases ``$words`` so ``words[1]`` is
    the subcommand name -- ``/usr/bin/env __complete ...`` was exec'd instead of
    the program.
    """
    tester = dynamic_completion_tester(E2E_SUBCOMMAND_NAMED_ENV_SOURCE, prog_name="deployer", shell=shell)
    result = [_lead(c) for c in tester.get_completions("deployer env --user ")]
    assert sorted(result) == ["alice", "bob", "carol"]


E2E_INJECTION_APP_SOURCE = """
from typing import Annotated

from cyclopts import App, Parameter

app = App(name="deployer")


def complete_place(ctx):
    return ["New York", "$(touch pwned)"]


@app.command
def deploy(*, place: Annotated[str, Parameter(completer=complete_place)] = ""):
    pass


if __name__ == "__main__":
    app()
"""


def test_e2e_bash_candidates_not_shell_expanded(dynamic_completion_tester):
    """Completer output must reach COMPREPLY verbatim: no word-splitting, no expansion.

    Regression test for the ``compgen -W "$(...)"`` path, where a candidate
    containing ``$(...)`` executed on TAB and whitespace split values.
    """
    tester = dynamic_completion_tester(E2E_INJECTION_APP_SOURCE, prog_name="deployer", shell="bash")
    result = tester.get_completions("deployer deploy --place ")
    assert sorted(result) == ["$(touch pwned)", "New York"]
    assert not Path("pwned").exists()


def test_e2e_eq_form_option_value(dynamic_completion_tester, shell):
    """``--user=al<TAB>`` completes the same candidates as ``--user al<TAB>``."""
    tester = dynamic_completion_tester(E2E_APP_SOURCE, prog_name="deployer", shell=shell)
    result = [_lead(c) for c in tester.get_completions("deployer deploy --user=a")]
    assert result == ["alice"]
    result = [_lead(c) for c in tester.get_completions("deployer deploy --user=")]
    assert sorted(result) == ["alice", "bob", "carol"]


def test_e2e_dependent_completion(dynamic_completion_tester, shell):
    """The headline feature: --cluster candidates gated on the typed --region."""
    tester = dynamic_completion_tester(E2E_APP_SOURCE, prog_name="deployer", shell=shell)
    west = [_lead(c) for c in tester.get_completions("deployer deploy --region us-west --cluster ")]
    assert sorted(west) == ["wa-1", "wa-2"]
    east = [_lead(c) for c in tester.get_completions("deployer deploy --region us-east --cluster ")]
    assert east == ["va-1"]
