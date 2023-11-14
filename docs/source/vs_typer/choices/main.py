from enum import Enum, auto
from typing import Literal

import typer

import cyclopts


class Environment(str, Enum):
    DEV = "dev_value"
    STAGING = "staging_value"
    PROD = "prod_value"


typer_app = typer.Typer()


@typer_app.command()
def foo(env: Environment = Environment.DEV):
    env = env.name
    print(f"Using: {env}")


print("Typer (Enum):")
cmd = ["--env", "staging_value"]
print(cmd)
typer_app(cmd, standalone_mode=False)
# Using: STAGING


cyclopts_app = cyclopts.App()


@cyclopts_app.register_default()
def foo(env: Environment = Environment.DEV):
    env = env.name
    print(f"Using: {env}")


print("Cyclopts (Enum):")
cmd = ["--env", "staging"]
print(cmd)
cyclopts_app(cmd)
# Using: STAGING


cyclopts_app = cyclopts.App()


@cyclopts_app.register_default()
def foo(env: Literal["dev", "staging", "prod"] = "staging"):
    print(f"Using: {env}")


print("Cyclopts (Literal):")
cmd = ["--env", "staging"]
print(cmd)
cyclopts_app(cmd)
# Using: staging
