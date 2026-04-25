"""Cross-shell behavioral contract tests.

Most tests in this directory assert on the **text of the generated completion
script** (string containment). That is fast and catches regressions in the
generators, but it does not answer the real question: *when the user presses
TAB, does the shell actually offer the right suggestions?*

This file runs the same behavioral scenarios across bash, zsh, and fish via
the non-interactive drivers in ``conftest.py``. Any per-shell divergence
surfaces immediately as a single failing parametrization.

Assertions use subset / exclusion (not exact equality) because shells
legitimately differ in ordering and in whether helper entries like ``--help``
surface at every depth.

Scenarios that depend on shell-specific tokenization (e.g. ``foo=bar``) are
intentionally excluded.
"""

from __future__ import annotations

import pytest

from .apps import (
    app_basic,
    app_disabled_negative,
    app_enum,
    app_multiple_positionals,
    app_negative,
    app_nested,
    app_positional_literal,
    app_positional_path,
)

# Each scenario:
#   id            - human-readable name (used as pytest id)
#   app           - App object
#   prog_name     - program name (matches what the generator was invoked with)
#   partial       - the command-line fragment the user has typed
#   contains      - suggestions that MUST appear (subset check)
#   excludes      - suggestions that MUST NOT appear (exclusion check)
SCENARIOS = [
    # 1. Root-level subcommands listed.
    (
        "root-subcommands",
        app_basic,
        "basic",
        "basic ",
        {"deploy"},
        set(),
    ),
    # 2. Subcommand prefix filters correctly.
    (
        "subcommand-prefix",
        app_basic,
        "basic",
        "basic de",
        {"deploy"},
        set(),
    ),
    # 3. Long-flag prefix.
    (
        "flag-prefix",
        app_basic,
        "basic",
        "basic --v",
        {"--verbose"},
        set(),
    ),
    # 4. All top-level options when user has typed just "-".
    (
        "all-flags",
        app_basic,
        "basic",
        "basic -",
        {"--verbose", "--count"},
        set(),
    ),
    # 5. Negative form of a bool flag.
    (
        "negative-flag",
        app_negative,
        "negapp",
        "negapp --no-",
        {"--no-colors"},
        set(),
    ),
    # 6. Literal choices after an option that takes a value.
    (
        "literal-option-value",
        app_basic,
        "basic",
        "basic deploy --env ",
        {"dev", "staging", "prod"},
        set(),
    ),
    # 7. Literal positional (positional-only).
    (
        "literal-positional",
        app_positional_literal,
        "poslit",
        "poslit command ",
        {"foo", "bar", "baz"},
        set(),
    ),
    # 8. Position-aware multi-positional: second arg has different choices.
    (
        "multi-positional-second",
        app_multiple_positionals,
        "multipos",
        "multipos command-multi red ",
        {"cat", "dog"},
        {"red", "blue"},
    ),
    # 9. Nested subcommand discovery.
    (
        "nested-subcommand",
        app_nested,
        "nested",
        "nested config ",
        {"get", "set"},
        set(),
    ),
    # 10. Path-typed positional triggers file completion (shell-specific).
    #     We can't assert specific filenames, so we only assert the driver
    #     returns *some* non-empty result when a file exists in cwd.
    (
        "path-positional",
        app_positional_path,
        "pathpos",
        "pathpos process ",
        None,  # special-cased in the test body
        set(),
    ),
    # 11. Enum values.
    (
        "enum-value",
        app_enum,
        "enumapp",
        "enumapp --speed ",
        {"fast", "slow"},
        set(),
    ),
    # 12. Disabled-negatives + list-of-literal.
    (
        "list-of-literal",
        app_disabled_negative,
        "disabledneg",
        "disabledneg build --param ",
        {"apple", "banana", "cherry"},
        set(),
    ),
    # 13. --help is always available at the root.
    (
        "help-at-root",
        app_basic,
        "basic",
        "basic --h",
        {"--help"},
        set(),
    ),
]


@pytest.fixture(params=["bash", "zsh", "fish"])
def shell_tester_factory(request):
    """Pick the right tester factory for this shell parametrization.

    Resolves the target shell's fixture lazily via ``getfixturevalue`` so a
    missing shell (e.g. fish absent locally) skips only its own
    parametrizations, not every row in the matrix.
    """
    return request.getfixturevalue(f"{request.param}_tester")


@pytest.mark.parametrize(
    ("scenario_id", "app", "prog_name", "partial", "contains", "excludes"),
    SCENARIOS,
    ids=[s[0] for s in SCENARIOS],
)
def test_behavior(
    scenario_id,
    app,
    prog_name,
    partial,
    contains,
    excludes,
    shell_tester_factory,
):
    tester = shell_tester_factory(app, prog_name)

    # Scenario #10: path completion. Ensure cwd has a file, then just assert
    # the driver returns a non-empty result. Different shells format file
    # completions differently (fish: full path, bash: basename, zsh: a mix),
    # so exact content checks would be brittle.
    if scenario_id == "path-positional":
        import os
        import tempfile
        from pathlib import Path as _Path

        with tempfile.TemporaryDirectory() as tmpdir:
            (_Path(tmpdir) / "sample.txt").write_text("x")
            cwd = _Path.cwd()
            try:
                os.chdir(tmpdir)
                results = tester.get_completions(partial)
            finally:
                os.chdir(cwd)
        assert results, f"expected some file-completion result for {partial!r}, got nothing"
        return

    results = tester.get_completions(partial)

    missing = contains - set(results)
    assert not missing, (
        f"[{scenario_id}] expected completions {missing} missing from shell output. partial={partial!r} got={results!r}"
    )

    leaked = excludes & set(results)
    assert not leaked, (
        f"[{scenario_id}] completions {leaked} should NOT have been offered. partial={partial!r} got={results!r}"
    )
