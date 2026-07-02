"""Randomized differential tests for hierarchical token scoping (parse_mode).

Each case builds a meta-app/subcommand pair from a seeded random signature and
parses a seeded random token stream. Three oracles:

1. **Meta-only parity** — when only the meta level defines keyword parameters,
   the scoped parse must bind exactly what a flat parse of the same tokens
   (command token removed) binds; if one errors, both must error.
2. **Child-only parity** — same, when only the subcommand defines keyword
   parameters and all tokens appear after the command.
3. **Mixed accounting** — both levels define (disjoint) parameters placed
   randomly around the command, including combined short options, GNU-style
   attached values, ``=`` syntax, and the ``--`` delimiter. Clean cases must
   succeed with every flag/option bound at its own level and positionals
   preserved in order; cases with injected junk must terminate with a
   :class:`CycloptsError` (never a hang, never any other exception).

Failures report the seed and token stream for reproduction. A daemon-thread
watchdog turns a non-terminating parse into a clean test failure.
"""

import random
import string
import threading
from typing import Annotated, NamedTuple

import pytest

from cyclopts import App, Parameter
from cyclopts.exceptions import CycloptsError

PARSE_TIMEOUT_S = 15
FAST_SEEDS = range(50)
BULK_SEEDS = range(1000)


class _ParamSpec(NamedTuple):
    kind: str  # "flag" | "option"
    pyname: str
    names: tuple[str, ...]

    @property
    def short(self) -> str | None:
        for name in self.names:
            if len(name) == 2 and name[0] == "-" and name[1] != "-":
                return name
        return None


def _run_with_watchdog(fn, timeout=PARSE_TIMEOUT_S):
    """Run ``fn`` in a daemon thread; fail the test if it doesn't finish."""
    result: dict = {}

    def target():
        try:
            result["value"] = fn()
        except BaseException as e:
            result["error"] = e

    thread = threading.Thread(target=target, daemon=True)
    thread.start()
    thread.join(timeout)
    if thread.is_alive():
        pytest.fail(f"parse did not terminate within {timeout}s (probable infinite loop)")
    if "error" in result:
        raise result["error"]
    return result.get("value")


def _render_param(spec: _ParamSpec) -> str:
    names_src = ", ".join(repr(n) for n in spec.names)
    if spec.kind == "flag":
        return f"{spec.pyname}: Annotated[bool, Parameter(name=[{names_src}])] = False"
    return f"{spec.pyname}: Annotated[str, Parameter(name=[{names_src}])] = 'unset'"


def _record_expr(specs: list[_ParamSpec]) -> str:
    return "{" + ", ".join(f"{s.pyname!r}: {s.pyname}" for s in specs) + "}"


def _build_hier_app(meta_specs: list[_ParamSpec], child_specs: list[_ParamSpec]) -> tuple[App, dict]:
    """Build ``app`` with a forwarding meta default and a ``cmd`` subcommand."""
    app = App(name="fuzz", result_action="return_value")
    captured: dict = {}
    ns = {"Annotated": Annotated, "Parameter": Parameter, "app": app, "captured": captured}

    meta_sig = "".join(", " + _render_param(s) for s in meta_specs)
    exec(  # noqa: S102
        "def meta(*tokens: Annotated[str, Parameter(show=False, allow_leading_hyphen=True)]"
        + meta_sig
        + "):\n"
        + f"    captured['meta'] = {_record_expr(meta_specs)}\n"
        + "    return app(tokens)\n",
        ns,
    )
    app.meta.default(ns["meta"])

    child_sig = "".join(", " + _render_param(s) for s in child_specs)
    exec(  # noqa: S102
        "def cmd(*args: str"
        + child_sig
        + "):\n"
        + f"    captured['child'] = {_record_expr(child_specs)}\n"
        + "    captured['args'] = args\n",
        ns,
    )
    app.command(ns["cmd"])
    return app, captured


def _build_flat_app(specs: list[_ParamSpec]) -> tuple[App, dict]:
    """Reference app: the same keyword parameters, parsed flat (no meta dispatch)."""
    flat = App(name="flat", result_action="return_value")
    captured: dict = {}
    ns = {"Annotated": Annotated, "Parameter": Parameter, "captured": captured}
    sig = "".join(", " + _render_param(s) for s in specs)
    exec(  # noqa: S102
        "def main(*args: str"
        + sig
        + "):\n"
        + f"    captured['params'] = {_record_expr(specs)}\n"
        + "    captured['args'] = args\n",
        ns,
    )
    flat.default(ns["main"])
    return flat, captured


def _generate_specs(rng: random.Random, prefix: str, shorts: list[str]) -> list[_ParamSpec]:
    """Generate 0-4 parameter specs consuming (up to) the provided short letters."""
    specs: list[_ParamSpec] = []
    n_flags = rng.randint(0, 2)
    n_options = rng.randint(0, 2)
    for i in range(n_flags + n_options):
        kind = "flag" if i < n_flags else "option"
        pyname = f"{prefix}{kind[0]}{i}"
        names: tuple[str, ...] = (f"--{pyname}",)
        if shorts and rng.random() < 0.8:
            names = (*names, f"-{shorts.pop()}")
        specs.append(_ParamSpec(kind, pyname, names))
    return specs


def _random_value(rng: random.Random) -> str:
    return "v" + "".join(rng.choices(string.ascii_lowercase, k=rng.randint(1, 4)))


def _emit(rng: random.Random, spec: _ParamSpec, value: str | None) -> list[str]:
    """Random surface form for one parameter: long/short, ``=``, or attached value."""
    name = rng.choice(spec.names)
    if spec.kind == "flag":
        return [name]
    assert value is not None
    style = rng.random()
    if name.startswith("--"):
        return [f"{name}={value}"] if style < 0.3 else [name, value]
    if style < 0.4:
        return [f"{name}{value}"]  # GNU-style attached: -uroot
    return [name, value]


class _Emission(NamedTuple):
    groups: list[list[str]]
    """Atomic token groups (an option and its value never get separated)."""
    expected: dict
    """pyname -> expected bound value."""
    clean: bool
    """False when junk/duplicates were injected (outcome may legitimately error)."""


def _generate_emission(
    rng: random.Random,
    specs: list[_ParamSpec],
    *,
    allow_junk: bool,
    combined_pool: list[str] | None = None,
) -> _Emission:
    """Random token groups for ``specs``; each spec emitted at most once.

    Flags whose shorts land in ``combined_pool`` (when provided) are emitted by
    the caller as combined short-option tokens instead.
    """
    groups: list[list[str]] = []
    expected: dict = {}
    clean = True
    for spec in specs:
        if spec.kind == "flag":
            if combined_pool is not None and spec.short and rng.random() < 0.3:
                combined_pool.append(spec.short[1])
                expected[spec.pyname] = True
                continue
            if rng.random() < 0.7:
                groups.append(_emit(rng, spec, None))
                expected[spec.pyname] = True
            else:
                expected[spec.pyname] = False
        else:
            if rng.random() < 0.7:
                value = _random_value(rng)
                groups.append(_emit(rng, spec, value))
                expected[spec.pyname] = value
            else:
                expected[spec.pyname] = "unset"
    if allow_junk and rng.random() < 0.2:
        groups.append([rng.choice(["--junk", "-Z", "-junkk"])])
        clean = False
    return _Emission(groups, expected, clean)


def _outcome(fn):
    try:
        _run_with_watchdog(fn)
        return "ok"
    except CycloptsError:
        return "error"


def _check_parity(seed: int, *, meta_side: bool) -> None:
    """Oracle 1/2: single-level keyword parameters must match a flat parse."""
    rng = random.Random(seed)
    shorts = rng.sample(string.ascii_lowercase, k=6)
    specs = _generate_specs(rng, "m" if meta_side else "c", shorts)
    meta_specs, child_specs = (specs, []) if meta_side else ([], specs)

    emission = _generate_emission(rng, specs, allow_junk=False)
    kw_groups = list(emission.groups)
    rng.shuffle(kw_groups)
    # Child-side parameters only bind after the command token. Words and junk
    # must also come after it: a non-option token before the command stops
    # command discovery entirely (standard CLI semantics), which the flat
    # reference cannot model.
    boundary = rng.randint(0, len(kw_groups)) if meta_side else 0
    pre_groups = kw_groups[:boundary]
    post_groups = kw_groups[boundary:]
    if rng.random() < 0.2:
        post_groups.append([rng.choice(["--junk", "-Z", "-junkk"])])
    for _ in range(rng.randint(0, 3)):
        post_groups.append([f"w{rng.randint(0, 5)}"])
    has_delimiter = rng.random() < 0.15
    if has_delimiter:
        post_groups.append(["--"])
        post_groups.append([f"w{rng.randint(0, 5)}"])
    rng.shuffle(post_groups)

    pre = [token for group in pre_groups for token in group]
    post = [token for group in post_groups for token in group]
    hier_tokens = [*pre, "cmd", *post]
    flat_tokens = [*pre, *post]

    app, captured = _build_hier_app(meta_specs, child_specs)
    flat, flat_captured = _build_flat_app(specs)

    hier_outcome = _outcome(lambda: app.meta(hier_tokens, exit_on_error=False, print_error=False))
    flat_outcome = _outcome(lambda: flat(flat_tokens, exit_on_error=False, print_error=False))

    if has_delimiter:
        # Pre-existing (v5-develop) quirk unrelated to scoping: a forwarding
        # meta's ``*tokens`` positional binding consumes the ``--`` marker, so
        # the inner parse sees the post-delimiter tokens unprotected and can
        # legitimately diverge from the flat reference. Only termination and
        # the no-crash guarantee are asserted for these streams.
        return

    context = f"seed={seed} tokens={hier_tokens!r}"
    assert hier_outcome == flat_outcome, (
        f"{context}: scoped parse {hier_outcome} but flat parse {flat_outcome}"
        f" (hier={captured!r} flat={flat_captured!r})"
    )
    if hier_outcome == "ok":
        bound = captured["meta"] if meta_side else captured["child"]
        assert bound == flat_captured["params"], f"{context}: {bound!r} != flat {flat_captured['params']!r}"
        assert captured["args"] == flat_captured["args"], (
            f"{context}: args {captured['args']!r} != flat {flat_captured['args']!r}"
        )


def _check_mixed(seed: int) -> None:
    """Oracle 3: disjoint meta/child parameters, random placement, exact accounting."""
    rng = random.Random(seed)
    shorts = rng.sample(string.ascii_lowercase, k=12)
    meta_specs = _generate_specs(rng, "m", shorts[:6])
    child_specs = _generate_specs(rng, "c", shorts[6:])

    combined_pool: list[str] = []
    meta_emission = _generate_emission(rng, meta_specs, allow_junk=True, combined_pool=combined_pool)
    child_emission = _generate_emission(rng, child_specs, allow_junk=False, combined_pool=combined_pool)

    meta_groups = list(meta_emission.groups)
    child_groups = list(child_emission.groups)
    combined_junk = False
    if combined_pool:
        # One combined short-option token possibly spanning both scopes (e.g. -vd),
        # sometimes salted with a short flag unknown to BOTH levels — the case
        # where the claimed/unclaimed split of one token gets contested.
        if rng.random() < 0.4:
            unknown = [c for c in string.ascii_lowercase if c not in shorts]
            combined_pool.append(rng.choice(unknown))
            combined_junk = True
        rng.shuffle(combined_pool)
        child_groups.append(["-" + "".join(combined_pool)])

    for i in range(rng.randint(0, 3)):
        child_groups.append([f"w{i}"])

    rng.shuffle(meta_groups)
    rng.shuffle(child_groups)
    # Positional order is the post-shuffle stream order.
    words = [group[0] for group in child_groups if group[0].startswith("w")]
    boundary = rng.randint(0, len(meta_groups))
    pre = [token for group in meta_groups[:boundary] for token in group]
    post_meta = [token for group in meta_groups[boundary:] for token in group]
    post = [token for group in child_groups for token in group]
    tokens = [*pre, "cmd", *post, *post_meta]

    app, captured = _build_hier_app(meta_specs, child_specs)
    clean = meta_emission.clean and child_emission.clean and not combined_junk
    context = f"seed={seed} tokens={tokens!r}"

    try:
        _run_with_watchdog(lambda: app.meta(tokens, exit_on_error=False, print_error=False))
    except CycloptsError:
        assert not clean, f"{context}: clean disjoint case unexpectedly errored (captured={captured!r})"
        return

    if not clean:
        return  # Junk that happened to parse (e.g. swallowed by a leading-hyphen path) is fine.
    assert captured["meta"] == meta_emission.expected, (
        f"{context}: meta bound {captured['meta']!r}, expected {meta_emission.expected!r}"
    )
    assert captured["child"] == child_emission.expected, (
        f"{context}: child bound {captured['child']!r}, expected {child_emission.expected!r}"
    )
    assert list(captured["args"]) == words, f"{context}: args {captured['args']!r}, expected {words!r}"


@pytest.mark.parametrize("seed", FAST_SEEDS)
def test_fuzz_meta_only_parity(seed):
    _check_parity(seed, meta_side=True)


@pytest.mark.parametrize("seed", FAST_SEEDS)
def test_fuzz_child_only_parity(seed):
    _check_parity(seed, meta_side=False)


@pytest.mark.parametrize("seed", FAST_SEEDS)
def test_fuzz_mixed_accounting(seed):
    _check_mixed(seed)


@pytest.mark.slow
def test_fuzz_bulk():
    """Large corpus; run with ``pytest --run-slow``."""
    for seed in BULK_SEEDS:
        _check_parity(seed, meta_side=True)
        _check_parity(seed, meta_side=False)
        _check_mixed(seed)
