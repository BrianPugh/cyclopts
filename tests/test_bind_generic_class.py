from typing import Annotated, Dict, Optional

from cyclopts import Parameter


class Outfit:
    def __init__(self, body: str, head: str):
        self.body = body
        self.head = head

    def __eq__(self, other):
        if not isinstance(other, type(self)):
            return False
        return self.body == other.body and self.head == other.head


class User:
    def __init__(
        self,
        id: int,
        name: str = "John Doe",
        tastes: Optional[Dict[str, int]] = None,
        outfit: Optional[Annotated[Outfit, Parameter(accepts_keys=True)]] = None,
    ):
        self.id = id
        self.name = name
        self.tastes = tastes if tastes is not None else {}
        self.outfit = outfit

    def __eq__(self, other):
        if not isinstance(other, type(self)):
            return False
        return (
            self.id == other.id
            and self.name == other.name
            and self.tastes == other.tastes
            and self.outfit == other.outfit
        )


def test_bind_attrs(app, assert_parse_args):
    @app.command
    def foo(user: Annotated[User, Parameter(accepts_keys=True)]):
        pass

    assert_parse_args(
        foo,
        "foo --user.id=123 --user.tastes.wine=9 --user.tastes.cheese=7 --user.tastes.cabbage=1 --user.outfit.body=t-shirt --user.outfit.head=baseball-cap",
        User(id=123, tastes={"wine": 9, "cheese": 7, "cabbage": 1}, outfit=Outfit(body="t-shirt", head="baseball-cap")),
    )
