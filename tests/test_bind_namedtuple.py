import sys
from collections import namedtuple
from typing import NamedTuple

import pytest


def test_bind_typing_named_tuple(app, assert_parse_args):
    class Employee(NamedTuple):
        name: str
        id: int = 3

    @app.command
    def foo(user: Employee):
        pass

    assert_parse_args(
        foo,
        'foo --user.name="John Smith" --user.id=100',
        Employee(name="John Smith", id=100),
    )


@pytest.mark.skipif(sys.version_info < (3, 10), reason="<3.10 does not have __annotations__ field.")
def test_bind_collections_named_tuple(app, assert_parse_args):
    # All fields will be strings since cyclopts doesn't know the types.
    Employee = namedtuple("Employee", ["name", "id"])

    @app.command
    def foo(user: Employee):
        pass

    assert_parse_args(
        foo,
        'foo --user.name="John Smith" --user.id=100',
        Employee(name="John Smith", id="100"),
    )


@pytest.mark.skipif(sys.version_info > (3, 9), reason="namedtuple fully supported.")
def test_bind_collections_named_tuple_unsupported(app, assert_parse_args):
    # All fields will be strings since cyclopts doesn't know the types.
    Employee = namedtuple("Employee", ["name", "id"])

    @app.command
    def foo(user: Employee):
        pass

    with pytest.raises(ValueError):
        assert_parse_args(
            foo,
            'foo --user.name="John Smith" --user.id=100',
        )
