import pytest

from cyclopts import App, Group, Parameter
from cyclopts.group_extractors import groups_from_app


def test_groups_annotated_invalid_recursive_definition():
    """A default_parameter isn't allowed to have a group set, as it would introduce a paradox."""
    default_parameter = Parameter(group="Drink")  # pyright: ignore[reportGeneralTypeIssues]
    with pytest.raises(ValueError):
        Group("Food", default_parameter=default_parameter)


def test_groups_from_app_implicit():
    def validator(**kwargs):
        pass

    app = App(help_flags=[], version_flags=[])

    @app.command(group="Food")
    def food1():
        pass

    @app.command(group=Group("Food", validator=validator))
    def food2():
        pass

    @app.command(group="Drink")
    def drink1():
        pass

    actual_groups = groups_from_app(app)
    assert actual_groups == [
        (Group("Drink"), [app["drink1"]]),
        (Group("Food", validator=validator), [app["food1"], app["food2"]]),
    ]
