import inspect

from typing_extensions import Annotated

from cyclopts import Parameter


def test_multiple_names(app):
    def custom_coercion(type_, *args):
        assert args == ("5",)
        return 2 * int(args[0])

    @app.register
    def foo(
        age: Annotated[
            int,
            Parameter(
                coercion=custom_coercion,
            ),
        ]
    ):
        pass

    signature = inspect.signature(foo)
    expected_bind = signature.bind(age=10)

    actual_command, actual_bind = app.parse_args("foo 5")
    assert actual_command == foo
    assert actual_bind == expected_bind
