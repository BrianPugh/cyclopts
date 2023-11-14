from typing import Union

import typer

import cyclopts

typer_app = typer.Typer()


@typer_app.command()
def foo(value: Union[int, str] = "default_str"):
    print(f"{type(value)=} {value=}")


typer_app(["foo"], standalone_mode=False)
# AssertionError: Typer Currently doesn't support Union types

cyclopts_app = cyclopts.App()
# TODO
