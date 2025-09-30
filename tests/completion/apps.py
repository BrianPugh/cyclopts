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
