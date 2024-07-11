from dataclasses import dataclass, field


@dataclass
class User:
    id: int
    name: str = "John Doe"
    tastes: dict[str, int] = field(default_factory=dict)


def test_bind_dataclass(app, assert_parse_args):
    @app.command
    def foo(user: User):
        pass

    external_data = {
        "id": 123,
        "tastes": {
            "wine": 9,
            "cheese": 7,
            "cabbage": 1,
        },
    }
    assert_parse_args(
        foo,
        "foo --user.id=123 --user.tastes.wine=9 --user.tastes.cheese=7 --user.tastes.cabbage=1",
        User(**external_data),
    )
