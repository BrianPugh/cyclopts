from collections import namedtuple
from typing import NamedTuple


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

    assert_parse_args(
        foo,
        'foo "John Smith" 100',
        Employee(name="John Smith", id=100),
    )


def test_bind_typing_named_tuple_var_positional(app, assert_parse_args):
    class Employee(NamedTuple):
        name: str
        id: int

    @app.command
    def foo(*users: Employee):
        pass

    assert_parse_args(
        foo,
        'foo "John Smith" 100 "Mary Jones" 200',
        Employee(name="John Smith", id=100),
        Employee(name="Mary Jones", id=200),
    )


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
