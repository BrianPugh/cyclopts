from dataclasses import KW_ONLY, dataclass  # pyright: ignore[reportAttributeAccessIssue]
from pathlib import Path
from typing import Annotated, Literal, NamedTuple

import cyclopts
from cyclopts import App, Parameter
from cyclopts.types import UInt8

toml_path = Path("draw.toml")
toml_data = """\
[tool.draw]
units = "meters"
no_exit_on_error = false

[tool.draw.line]
units = "feet"
"""
toml_path.write_text(toml_data)

app = App(
    help="Demo drawing app.",
    config=(
        cyclopts.config.Toml(toml_path, root_keys=("tool", "draw")),
        cyclopts.config.Toml(toml_path, root_keys=("tool", "draw"), use_commands_as_keys=False, allow_unknown=True),
    ),
)


class Coordinate(NamedTuple):
    x: float
    "X coordinate."

    y: float
    "Y coordinate."


@dataclass
class _Config:
    _: KW_ONLY
    units: Literal["meters", "feet"] = "meters"
    "Drawing units."

    color: tuple[UInt8, UInt8, UInt8] = (0x00, 0x00, 0x00)
    "RGB uint8 triple."


Config = Annotated[_Config, Parameter(name="*")]


@app.command
def line(
    start: Coordinate,
    end: Coordinate,
    *,
    config: Config,
):
    """Draw a line.

    Parameters
    ----------
    start: Coordinate
        Start of line.
    end: Coordinate
        End of line.
    """
    print(f"Drawing a line with from {start} to {end} {config.units} in {config.color=}.")


@app.command
def circle(
    center: Coordinate,
    radius: float,
    *,
    config: Config,
):
    """Draw a circle.

    Parameters
    ----------
    center.x: float
        Circle center's X position.
    center.y: float
        Circle center's Y position.
    radius: float
        Radius of the circle.
    """
    print(f"Drawing a circle with {radius=} {config.units} at {center=}")


@app.meta.default
def meta(
    *tokens: Annotated[str, Parameter(show=False, allow_leading_hyphen=True)],
    no_exit_on_error: Annotated[bool, Parameter(negative=())] = False,
):
    """
    Parameters
    ----------
    exit_on_error: bool
        Exit on error.
    """
    app(tokens, exit_on_error=not no_exit_on_error, print_error=not no_exit_on_error)
    toml_path.unlink()


if __name__ == "__main__":
    app.meta(print_error=False, exit_on_error=False)
