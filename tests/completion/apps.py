from enum import Enum
from pathlib import Path
from typing import Annotated, Literal

from cyclopts import App, Parameter

app_basic = App(name="basic")


@app_basic.default
def main(
    verbose: Annotated[bool, Parameter(help="Enable verbose output")] = False,
    count: Annotated[int, Parameter(help="Number of items")] = 1,
):
    """Basic app for testing."""
    pass


@app_basic.command
def deploy(
    env: Annotated[Literal["dev", "staging", "prod"], Parameter(help="Environment")],
    force: bool = False,
):
    """Deploy to environment."""
    pass


class Speed(Enum):
    FAST = "fast"
    SLOW = "slow"


app_enum = App(name="enumapp")


@app_enum.default
def enum_main(speed: Speed = Speed.FAST):
    """App with enum parameter."""
    pass


app_nested = App(name="nested")
config_app = App(name="config")


@config_app.command
def get(key: str):
    """Get config value."""
    pass


@config_app.command
def set(key: str, value: str):
    """Set config value."""
    pass


app_nested.command(config_app)


app_path = App(name="pathapp")


@app_path.default
def path_main(
    input_file: Annotated[Path, Parameter(help="Input file")],
    output: Annotated[Path | None, Parameter(help="Output file")] = None,
):
    """App with path parameters."""
    pass


app_negative = App(name="negapp")


@app_negative.default
def negative_main(
    verbose: Annotated[bool, Parameter(help="Enable verbose")] = False,
    colors: Annotated[bool, Parameter(negative="no-colors")] = True,
):
    """App with negative flags."""
    pass


app_markup = App(name="markupapp")


@app_markup.default
def markup_main(
    verbose: Annotated[bool, Parameter(help="Enable **verbose** output with `extra` details")] = False,
    mode: Annotated[
        Literal["fast", "slow"],
        Parameter(help="Choose *execution* mode: **fast** or **slow**"),
    ] = "fast",
):
    """App with **markdown** markup in help text.

    This tests that markup is properly stripped in completions.
    """
    pass


@app_markup.command
def deploy_markup(
    env: Annotated[str, Parameter(help="Target `environment` like **dev** or **prod**")],
):
    """Deploy to `environment`."""
    pass


app_rst = App(name="rstapp", help_format="rst")


@app_rst.default
def rst_main(
    verbose: Annotated[bool, Parameter(help="Enable **verbose** output with ``code`` samples")] = False,
    mode: Annotated[
        Literal["fast", "slow"],
        Parameter(help="Choose *execution* mode: **fast** or **slow**"),
    ] = "fast",
):
    """App with **RST** markup in help text.

    This tests that RST markup is properly stripped in completions.
    """
    pass


app_positional_literal = App(name="poslit")


@app_positional_literal.command
def command(param: Literal["foo", "bar", "baz"], /):
    """Simple command with positional literal.

    Parameters
    ----------
    param : Literal["foo", "bar", "baz"]
        Literal param.
    """
    pass


app_multiple_positionals = App(name="multipos")


@app_multiple_positionals.command
def command_multi(
    first: Literal["red", "blue"],
    second: Literal["cat", "dog"],
    /,
):
    """Command with multiple positionals with distinct choices.

    Parameters
    ----------
    first : Literal["red", "blue"]
        Color choice.
    second : Literal["cat", "dog"]
        Animal choice.
    """
    pass


app_deploy = App(name="deploy")


@app_deploy.command
def deploy_project(
    project: Literal["web", "api", "worker"],
    /,
    *,
    environment: Literal["dev", "staging", "prod"],
    branch: str = "main",
):
    """Deploy a project to an environment.

    Parameters
    ----------
    project : Literal["web", "api", "worker"]
        Project to deploy.
    environment : Literal["dev", "staging", "prod"]
        Target environment.
    branch : str
        Git branch.
    """
    pass
