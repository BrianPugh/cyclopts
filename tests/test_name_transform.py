import pytest

from cyclopts import default_name_transform


@pytest.mark.parametrize(
    "before,after",
    [
        ("FOO", "foo"),
        ("_FOO", "foo"),
        ("_FOO_", "foo"),
        ("_F_O_O_", "f-o-o"),
    ],
)
def test_default_name_transform(before, after):
    assert default_name_transform(before) == after


@pytest.mark.skip(reason="TODO")
def test_app_name_transform_default(app):
    pass


@pytest.mark.skip(reason="TODO")
def test_app_name_transform_custom(app):
    pass


@pytest.mark.skip(reason="TODO")
def test_subapp_name_transform_override(app):
    pass


@pytest.mark.skip(reason="TODO")
def test_subapp_name_transform_custom(app):
    pass


@pytest.mark.skip(reason="TODO")
def test_parameter_name_transform_default(app):
    pass


@pytest.mark.skip(reason="TODO")
def test_parameter_name_transform_custom(app):
    pass
