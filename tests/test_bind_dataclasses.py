import sys
from dataclasses import dataclass, field

from cyclopts import Parameter

if sys.version_info < (3, 9):
    from typing_extensions import Annotated, TypedDict  # pragma: no cover
else:
    from typing import Annotated  # pragma: no cover


@dataclass
class User:
    id: int
    name: str = "John Doe"
    tastes: dict[str, int] = field(default_factory=dict)


def test_bind_dataclass(app, assert_parse_args):
    @app.command
    def foo(some_number: int, user: User):
        pass

    external_data = {
        "id": 123,
        # "name" is purposely missing.
        "tastes": {
            "wine": 9,
            "cheese": 7,
            "cabbage": 1,
        },
    }
    assert_parse_args(
        foo,
        "foo 100 --user.id=123 --user.tastes.wine=9 --user.tastes.cheese=7 --user.tastes.cabbage=1",
        100,
        User(**external_data),
    )
