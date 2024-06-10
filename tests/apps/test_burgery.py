import sys
from pathlib import Path
from textwrap import dedent
from typing import List, Literal, Optional

import pytest

import cyclopts
from cyclopts import App, Group, Parameter, validators

if sys.version_info < (3, 9):
    from typing_extensions import Annotated
else:
    from typing import Annotated

config_file = Path(__file__).parent / "config.toml"

app = App(
    name="burgery",
    help="Welcome to Cyclopts Burgery!",
    config=cyclopts.config.Toml(config_file),
)
app.command(create := App(name="create"))


@create.command
def burger(
    variety: Literal["classic", "double"],
    quantity: Annotated[int, Parameter(validator=validators.Number(gt=0))] = 1,
    /,
    *,
    lettuce: Annotated[bool, Parameter(name="--iceberg", group="Toppings")] = True,
    tomato: Annotated[bool, Parameter(group="Toppings")] = True,
    onion: Annotated[bool, Parameter(group="Toppings")] = True,
    mustard: Annotated[bool, Parameter(group="Condiments")] = True,
    ketchup: Annotated[bool, Parameter(group="Condiments")] = True,
    mayo: Annotated[bool, Parameter(group="Condiments")] = True,
    custom: Annotated[Optional[List[str]], Parameter(group="Condiments")] = None,
):
    """Create a burger.

    Parameters
    ----------
    variety: Literal["classic", "double"]
        Type of burger to create
    quantity: int
    lettuce: bool
        Add lettuce.
    tomato: bool
        Add tomato.
    onion: bool
        Add onion.
    mustard: bool
        Add mustard.
    ketchup: bool
        Add ketchup.
    """
    return locals()


def test_create_burger_help(console):
    with console.capture() as capture:
        app("create burger --help", console=console)
    actual = capture.get()
    expected = dedent(
        """\
        Usage: burgery create burger [ARGS] [OPTIONS]

        Create a burger.

        ╭─ Arguments ────────────────────────────────────────────────────────╮
        │ *  VARIETY   Type of burger to create [choices: classic,double]    │
        │              [required]                                            │
        │    QUANTITY  [default: 1]                                          │
        ╰────────────────────────────────────────────────────────────────────╯
        ╭─ Condiments ───────────────────────────────────────────────────────╮
        │ --mustard,--no-mustard   Add mustard. [default: True]              │
        │ --ketchup,--no-ketchup   Add ketchup. [default: True]              │
        │ --mayo,--no-mayo         [default: True]                           │
        │ --custom,--empty-custom                                            │
        ╰────────────────────────────────────────────────────────────────────╯
        ╭─ Toppings ─────────────────────────────────────────────────────────╮
        │ --iceberg,--no-iceberg  Add lettuce. [default: True]               │
        │ --tomato,--no-tomato    Add tomato. [default: True]                │
        │ --onion,--no-onion      Add onion. [default: True]                 │
        ╰────────────────────────────────────────────────────────────────────╯
        """
    )
    assert actual == expected


def test_create_burger_1():
    """Tests generic functionality.

    Detailed:
        * that config-file overrides (mayo, custom) work.
        * typical boolean flags work.
    """
    actual = app("create burger classic --iceberg --no-onion --no-ketchup --custom sriracha --custom egg")
    assert actual == {
        "variety": "classic",
        "quantity": 1,
        "lettuce": True,
        "tomato": True,
        "onion": False,
        "ketchup": False,
        "mustard": True,
        "mayo": False,  # Set from config file.
        "custom": ["sriracha", "egg"],
    }


def test_create_burger_2():
    """Tests that the list from the toml file correctly populates."""
    actual = app("create burger classic")
    assert actual == {
        "variety": "classic",
        "quantity": 1,
        "lettuce": True,
        "tomato": True,
        "onion": True,
        "ketchup": True,
        "mustard": True,
        "mayo": False,  # Set from config file.
        "custom": ["sweet-chili", "house-sauce"],  # Set from config file.
    }


def test_create_burger_3():
    """Tests the --empty- config override."""
    actual = app("create burger classic --empty-custom")
    assert actual == {
        "variety": "classic",
        "quantity": 1,
        "lettuce": True,
        "tomato": True,
        "onion": True,
        "ketchup": True,
        "mustard": True,
        "mayo": False,  # Set from config file.
        "custom": [],
    }


if __name__ == "__main__":
    test_create_burger_1()
