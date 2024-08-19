from datetime import datetime
from textwrap import dedent
from typing import Dict, Optional, Union

import pytest
from pydantic import BaseModel, PositiveInt, validate_call
from pydantic import ValidationError as PydanticValidationError


def test_pydantic_error_msg(app, console):
    @app.command
    @validate_call
    def foo(value: PositiveInt):
        print(value)

    assert app["foo"].default_command == foo

    foo(1)
    with pytest.raises(PydanticValidationError):
        foo(-1)

    with console.capture() as capture, pytest.raises(PydanticValidationError):
        app(["foo", "-1"], console=console, exit_on_error=False, print_error=True)

    actual = capture.get()

    expected_prefix = dedent(
        """\
        ╭─ Error ────────────────────────────────────────────────────────────╮
        │ 1 validation error for foo                                         │
        │ 0                                                                  │
        │   Input should be greater than 0 [type=greater_than,               │
        │ input_value=-1, input_type=int]                                    │
        │     For further information visit                                  │
        """
    )

    assert actual.startswith(expected_prefix)


# Modified from https://docs.pydantic.dev/latest/#pydantic-examples
class Outfit(BaseModel):
    body: str
    head: str


class User(BaseModel):
    id: int
    name: str = "John Doe"
    signup_ts: Union[datetime, None]
    tastes: Dict[str, PositiveInt]
    outfit: Optional[Outfit] = None


def test_bind_pydantic_basemodel(app, assert_parse_args):
    @app.command
    def foo(user: User):
        pass

    external_data = {
        "id": 123,
        "signup_ts": "2019-06-01 12:22",
        "tastes": {
            "wine": 9,
            b"cheese": 7,
            "cabbage": "1",
        },
        "outfit": {
            "body": "t-shirt",
            "head": "baseball-cap",
        },
    }
    assert_parse_args(
        foo,
        'foo --user.id=123 --user.signup-ts="2019-06-01 12:22" --user.tastes.wine=9 --user.tastes.cheese=7 --user.tastes.cabbage=1 --user.outfit.body=t-shirt --user.outfit.head=baseball-cap',
        User(**external_data),
    )
