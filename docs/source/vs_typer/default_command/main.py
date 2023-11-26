import typer

import cyclopts

typer_app = typer.Typer()


@typer_app.command()
def foo():
    print("FOO")


typer_app([], standalone_mode=False)
# FOO
try:
    typer_app(["foo"], standalone_mode=False)
except Exception as e:
    print(f"EXCEPTION: {e}")
# EXCEPTION: Got unexpected extra argument (foo)


@typer_app.command()
def bar():
    print("BAR")


typer_app(["foo"], standalone_mode=False)
# FOO
typer_app(["bar"], standalone_mode=False)
# BAR


cyclopts_app = cyclopts.App()


@cyclopts_app.command
def foo():
    print("FOO")


cyclopts_app(["foo"])
# FOO


@cyclopts_app.command
def bar():
    print("BAR")


cyclopts_app(["bar"])
# BAR
