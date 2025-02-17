import json
from dataclasses import dataclass, field
from typing import Annotated, Dict, Optional

import pytest

from cyclopts import Parameter


@dataclass
class User:
    id: int
    name: str = "John Doe"
    tastes: Dict[str, int] = field(default_factory=dict)


def test_bind_dataclass_from_env_json(app, assert_parse_args, monkeypatch):
    @app.command
    def foo(some_number: int, user: Annotated[User, Parameter(env_var="USER")]):
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
    monkeypatch.setenv("USER", json.dumps(external_data))
    assert_parse_args(
        foo,
        "foo 100",
        100,
        User(**external_data),
    )


@pytest.mark.parametrize(
    "cmd_str",
    [
        """--origin='{"x": 1, "y": 2}'""",
        """--origin '{"x": 1, "y": 2}'""",
        """--origin='{"x": 1, "y": 2, "label": null}'""",
    ],
)
def test_bind_dataclass_from_cli_json(app, assert_parse_args, cmd_str):
    @dataclass
    class Coordinate:
        x: int
        y: int
        label: Optional[str] = None

    @app.default
    def main(origin: Coordinate):
        pass

    assert_parse_args(main, cmd_str, Coordinate(1, 2))
