from typing import Union

import typer

import cyclopts

typer_app = typer.Typer()


@typer_app.command()
def foo(value: Union[int, str] = "default_str"):
    print(f"{type(value)=} {value=}")


print("Typer:")
try:
    typer_app(["123"], standalone_mode=False)
except Exception as e:
    print(e)
# AssertionError: Typer Currently doesn't support Union types

cyclopts_app = cyclopts.App()
# TODO


@cyclopts_app.register_default
def foo(value: Union[int, str] = "default_str"):
    print(f"{type(value)=} {value=}")


print("Cyclopts:")
cyclopts_app(["123"])
# type(value)=<class 'int'> value=123
cyclopts_app(["bar"])
# type(value)=<class 'str'> value='bar'
