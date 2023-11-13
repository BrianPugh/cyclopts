import pytest

from cyclopts import Parameter


def test_parameter_get_negatives_bool_default():
    p = Parameter()
    assert ("--no-foo", "--no-bar") == p.get_negatives(bool, "--foo", "--bar")


@pytest.mark.parametrize("type_", [list, set])
def test_parameter_get_negatives_iterable_default(type_):
    p = Parameter()
    assert ("--empty-foo", "--empty-bar") == p.get_negatives(type_, "--foo", "--bar")


@pytest.mark.parametrize("type_", [bool, list, set])
def test_parameter_get_negatives_custom_single(type_):
    p = Parameter(negative="--foo")
    assert ("--foo",) == p.get_negatives(type_, "this-string-doesnt-matter", "neither-does-this-one")


@pytest.mark.parametrize("type_", [bool, list, set])
def test_parameter_get_negatives_bool_custom_list(type_):
    p = Parameter(negative=["--foo", "--bar"])
    assert ("--foo", "--bar") == p.get_negatives(type_, "this-string-doesnt-matter")
