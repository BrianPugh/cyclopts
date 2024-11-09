from typing import Annotated

import typer

import cyclopts

typer_app = typer.Typer()


@typer_app.command()
def foo(my_flag: bool = False):
    print(f"{my_flag=}")


print("Typer:")
typer_app(["--my-flag"], standalone_mode=False)
typer_app(["--no-my-flag"], standalone_mode=False)
# my_flag=True
# my_flag=False


cyclopts_app = cyclopts.App()


@cyclopts_app.default
def foo(my_flag: bool = False):
    print(f"{my_flag=}")


print("Cyclopts:")
cyclopts_app(["--my-flag"])
cyclopts_app(["--no-my-flag"])
# my_flag=True
# my_flag=False


cyclopts_app = cyclopts.App()


@cyclopts_app.default
def foo(my_flag: Annotated[bool, cyclopts.Parameter(negative="--your-flag")] = False):
    print(f"{my_flag=}")


print("Cyclopts:")
cyclopts_app(["--my-flag"])
cyclopts_app(["--your-flag"])
# my_flag=True
# my_flag=False
