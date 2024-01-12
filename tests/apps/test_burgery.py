import sys
from textwrap import dedent
from typing import Literal

import pytest

from cyclopts import App, Group, Parameter, validators

if sys.version_info < (3, 9):
    from typing_extensions import Annotated
else:
    from typing import Annotated


app = App(name="burgery", help="Welcome to Cyclopts Burgery!")
app.command(create := App(name="create"))


@create.command
def burger(
    variety: Literal["classic", "double"],
    quantity: Annotated[int, Parameter(validator=validators.Number(gt=0))] = 1,
    /,
    *,
    lettuce: Annotated[bool, Parameter(group="Toppings")] = True,
    tomato: Annotated[bool, Parameter(group="Toppings")] = True,
    onion: Annotated[bool, Parameter(group="Toppings")] = True,
    mustard: Annotated[bool, Parameter(group="Condiments")] = True,
    ketchup: Annotated[bool, Parameter(group="Condiments")] = True,
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
    return {
        "variety": variety,
        "quantity": quantity,
        "lettuce": lettuce,
        "tomato": tomato,
        "onion": onion,
        "ketchup": ketchup,
        "mustard": mustard,
    }


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
        │ --mustard,--no-mustard  Add mustard. [default: True]               │
        │ --ketchup,--no-ketchup  Add ketchup. [default: True]               │
        ╰────────────────────────────────────────────────────────────────────╯
        ╭─ Toppings ─────────────────────────────────────────────────────────╮
        │ --lettuce,--no-lettuce  Add lettuce. [default: True]               │
        │ --tomato,--no-tomato    Add tomato. [default: True]                │
        │ --onion,--no-onion      Add onion. [default: True]                 │
        ╰────────────────────────────────────────────────────────────────────╯
        """
    )
    assert actual == expected


def test_create_burger():
    actual = app("create burger classic --lettuce --no-onion --no-ketchup")
    assert actual == {
        "variety": "classic",
        "quantity": 1,
        "lettuce": True,
        "tomato": True,
        "onion": False,
        "ketchup": False,
        "mustard": True,
    }


if __name__ == "__main__":
    test_create_burger()
