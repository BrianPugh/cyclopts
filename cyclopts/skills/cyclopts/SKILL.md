---
name: cyclopts
description: Idiomatic usage of the Cyclopts Python CLI library. Use when writing, reviewing, or converting (from Typer, Click, argparse) a command-line interface built with `cyclopts`.
---

# Cyclopts idioms

Cyclopts derives the CLI from the function **signature**, **type hints**, and **docstring**.
Reach for `Parameter(...)` only to change one specific behavior. Most Typer/Click habits are unnecessary.

## Skeleton

```python
from cyclopts import App

app = App()  # name, version, and help are inferred from the package/docstring

@app.command
def deploy(env: str, *, replicas: int = 1, dry_run: bool = False):
    """Deploy the service.

    Parameters
    ----------
    env: str
        Target environment.
    replicas: int
        Number of workers to start.
    dry_run: bool
        Print the plan without applying it.
    """

@app.default  # runs when no command is given
def main():
    ...

if __name__ == "__main__":
    app()
```

* Help text comes from the docstring (NumPy, Google, or Sphinx style). The first line is the command's short description.
* Parameters before `/` are positional-only, after `*` are keyword-only, otherwise usable both ways.
* A parameter with no default is required. `None` defaults are not shown in `--help`.
* Python `snake_case` becomes `--kebab-case`. Command functions likewise (`def list_items` -> `list-items`).
* Sub-apps: `sub = App(name="db"); app.command(sub); @sub.command def migrate(): ...`

## `Parameter` cheat sheet

Attach with `Annotated[T, Parameter(...)]`.

| Want | Use | Not |
|---|---|---|
| Help text | docstring | `Parameter(help=...)` (override only, e.g. third-party dataclass fields) |
| Add a short flag `-v` | `Parameter(alias="-v")` | `Parameter(name=["--verbose", "-v"])` |
| Replace the CLI name entirely | `Parameter(name="--out")` | |
| Short flags for every option | `App(default_parameter=Parameter(short_alias=True))` | |
| Choices | `Literal["a", "b"]` or an `Enum` | `choices=` |
| Env var fallback | `Parameter(env_var="MYAPP_TOKEN")` | |
| Hide from help | `Parameter(show=False)` | |
| Help panel/grouping | `Parameter(group="Tuning")` or `Group("Tuning")` | |
| Numeric bounds | `Parameter(validator=validators.Number(gte=0, lte=10))` | |
| Path checks | `Parameter(validator=validators.Path(exists=True, dir_okay=False))` | |
| Custom parse | `Parameter(converter=fn)` where `fn(type_, tokens) -> value` | |
| Custom check | `Parameter(validator=fn)` where `fn(type_, value) -> None` raises on failure | |
| Counting flag `-vvv` | `Parameter(count=True)` on an `int` | |
| Disable `--no-flag` | `Parameter(negative="")` | |
| Rename negative flag | `Parameter(negative="--quiet")` | |
| `--items 1 2 3` in one go | `Parameter(consume_multiple=True)` on a `list[int]` | default is `--items 1 --items 2` |
| Skip CLI parsing for a param | `Parameter(parse=False)` | |
| Flatten a dataclass param into root options | `Parameter(name="*")` | |

`from cyclopts import validators` for the built-in validators.

## Types

* `bool` -> `--flag` / `--no-flag`. `bool | None` -> negative sets `None`.
* `list[T]` / `set[T]` / `tuple[T, ...]` -> repeatable keyword, or consumes all remaining positionals.
* `T | None` (Optional) -> same parsing as `T`; `None` when omitted.
* Unions try each member in order.
* `Path`, `datetime`, `int`, `float`, `Decimal`, `UUID`, `Enum`, `Literal`, `Flag` all work with no configuration.
* dataclass / attrs / pydantic / `TypedDict` / `NamedTuple` parameters become nested options: `--user.name`, `--user.age`. A JSON string is also accepted for the whole object.
* `cyclopts.types` has ready-made annotated types: `PositiveInt`, `ExistingFile`, `ResolvedDirectory`, etc.

## App-level

* `App(help_format="markdown" | "rst" | "rich" | "plaintext")` for docstring markup (default: rst).
* `App(config=cyclopts.config.Toml("pyproject.toml", root_keys=["tool", "myapp"]))` reads defaults from files; `cyclopts.config.Env("MYAPP_")` for env-var prefixes. Also `Json`, `Yaml`.
* `App(version="1.2.3")` or a callable; `--version` is built in. `--help`/`-h` is built in.
* Return an `int` from a command to set the exit code. Other return values are printed. No `typer.Exit` needed.
* `app.meta` wraps every command for cross-cutting options (verbosity, config path); see the "Meta App" docs.
* `App(result_action="return_value")` makes `app(["cmd", "--x", "1"])` return the command's return value, useful in tests. `app.parse_args(tokens)` returns `(command, bound_args, ignored)` without executing.
* `app.register_install_completion_command()` adds `--install-completion` for bash/zsh/fish.

## Tooling

```console
cyclopts run script.py -- --arg value  # run an App from a script without a __main__ block
cyclopts tree script.py                # print the command tree
cyclopts docs script.py -o CLI.md      # generate markdown/rst/html docs
```

## Anti-patterns

```python
# Bad: Typer habits carried over
def deploy(
    env: Annotated[str, Parameter(help="Target environment.")],
    verbose: Annotated[bool, Parameter(name=["--verbose", "-v"], help="Chatty output.")] = False,
):
    ...

# Good
def deploy(env: str, verbose: Annotated[bool, Parameter(alias="-v")] = False):
    """Deploy the service.

    Parameters
    ----------
    env: str
        Target environment.
    verbose: bool
        Chatty output.
    """
```

* Do not write a `--version` callback; it is built in.
* Do not use `Enum` just for choices; `Literal` is shorter.
* Do not `raise SystemExit` for help/usage errors; Cyclopts raises `CycloptsError` subclasses with formatted output.
* Do not put `if __name__ == "__main__": app()` boilerplate in library modules that are only run via an entry point; `[project.scripts] myapp = "mypkg.cli:app"` works directly.
