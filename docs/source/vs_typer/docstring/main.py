import typer

import cyclopts

typer_app = typer.Typer()


@typer_app.callback()
def dummy():
    # So that ``foo`` is considered a command.
    pass


@typer_app.command()
def foo(bar):
    """Foo Docstring.

    Parameters
    ----------
    bar: str
        Bar parameter docstring.
    """
    pass


print("Typer:")

# Typer correctly parses the docstring short description.
typer_app(["--help"], standalone_mode=False)
# ╭─ Commands ─────────────────────────────────────────────────────╮
# │ foo                 Foo Docstring.                             │
# ╰────────────────────────────────────────────────────────────────╯


# However, it fails at parsing the rest of the docstring.
typer_app(["foo", "--help"], standalone_mode=False)
# Foo Docstring.
#  Parameters ---------- bar: str     Bar parameter docstring.
#
# ╭─ Arguments ────────────────────────────────────────────────────╮
# │ *    bar      TEXT  [default: None] [required]                 │
# ╰────────────────────────────────────────────────────────────────╯

cyclopts_app = cyclopts.App()


@cyclopts_app.command()
def foo(bar):
    """Foo Docstring.

    Parameters
    ----------
    bar: str
        Bar parameter docstring.
    """
    pass


print("Cyclopts:")

# Cyclopts also properly parses the short description.
cyclopts_app(["--help"])
# ╭─ Commands ─────────────────────────────────────────────────────╮
# │ foo  Foo Docstring.                                            │
# ╰────────────────────────────────────────────────────────────────╯
cyclopts_app(["foo", "--help"])
# Foo Docstring.
#
# ╭─ Parameters ───────────────────────────────────────────────────╮
# │ *  BAR,--bar  Bar parameter docstring. [required]              │
# ╰────────────────────────────────────────────────────────────────╯
