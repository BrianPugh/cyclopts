from typing import List, Optional

import typer

import cyclopts

typer_app = typer.Typer()


@typer_app.command()
def mv(src, dst):
    print(f"Moving {src} -> {dst}")


print("Typer positional:")
typer_app(["foo", "bar"], standalone_mode=False)
# Moving foo -> bar

print("Typer keyword:")
try:
    typer_app(["--src", "foo", "--dst", "bar"], standalone_mode=False)
except Exception as e:
    print("EXCEPTION: " + str(e))
    # EXCEPTION: No such option: --src


cyclopts_app = cyclopts.App()


@cyclopts_app.default()
def mv(src, dst):
    print(f"Moving {src} -> {dst}")


print("Cyclopts positional:")
cyclopts_app(["foo", "bar"])
# Moving foo -> bar

print("Cyclopts keyword:")
cyclopts_app(["--src", "foo", "--dst", "bar"])
# Moving foo -> bar
