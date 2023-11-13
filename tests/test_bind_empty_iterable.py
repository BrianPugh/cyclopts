import inspect
from typing import List, Optional

import pytest
from typing_extensions import Annotated

from cyclopts import Parameter


@pytest.mark.parametrize(
    "cmd_str,expected",
    [
        ("", None),
        ("--empty-my-list", []),
    ],
)
def test_optional_list_empty_flag_default(app, cmd_str, expected):
    @app.register_default
    def foo(my_list: Optional[List[int]] = None):
        pass

    signature = inspect.signature(foo)

    if expected is None:
        expected_bind = signature.bind()
    else:
        expected_bind = signature.bind(expected)

    actual_command, actual_bind = app.parse_args(cmd_str)
    assert actual_command == foo
    assert actual_bind == expected_bind
