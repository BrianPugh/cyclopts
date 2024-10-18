import inspect
from typing import Annotated, List, Optional, Set

import pytest

from cyclopts import Parameter


def test_parameter_get_negatives_bool_default():
    p = Parameter(name=("--foo", "--bar"))
    assert ("--no-foo", "--no-bar") == p.get_negatives(bool)


@pytest.mark.parametrize("type_", [list, set, List[str], Set[str]])
def test_parameter_get_negatives_iterable_default(type_):
    p = Parameter(name=("--foo", "--bar"))
    assert ("--empty-foo", "--empty-bar") == p.get_negatives(type_)


@pytest.mark.parametrize("type_", [list, set, List[str], Set[str]])
def test_parameter_get_negatives_iterable_custom_prefix(type_):
    p = Parameter(negative_iterable="vacant-", name=("--foo", "--bar"))
    assert ("--vacant-foo", "--vacant-bar") == p.get_negatives(type_)


@pytest.mark.parametrize("type_", [list, set, List[str], Set[str]])
def test_parameter_get_negatives_iterable_custom_prefix_list(type_):
    p = Parameter(negative_iterable=["vacant-", "blank-"], name=("--foo", "--bar"))
    assert {"--vacant-foo", "--vacant-bar", "--blank-foo", "--blank-bar"} == set(p.get_negatives(type_))


def test_parameter_negative_iterable_invalid_name(app, assert_parse_args):
    Parameter(negative_iterable=())  # Valid
    with pytest.raises(ValueError):
        Parameter(negative_iterable="--starts-with-hyphens")


@pytest.mark.parametrize("type_", [bool, list, set])
def test_parameter_get_negatives_custom_single(type_):
    p = Parameter(negative="--foo", name=("this-string-doesnt-matter", "neither-does-this-one"))
    assert ("--foo",) == p.get_negatives(type_)


@pytest.mark.parametrize("type_", [bool, list, set])
def test_parameter_get_negatives_bool_custom_list(type_):
    p = Parameter(negative=["--foo", "--bar"], name="this-string-doesnt-matter")
    assert ("--foo", "--bar") == p.get_negatives(type_)


@pytest.mark.parametrize("type_", [bool, list, set])
def test_parameter_get_negatives_bool_custom_prefix(type_):
    p = Parameter(negative_bool="yesnt-", name=("--foo", "--bar"))
    assert ("--yesnt-foo", "--yesnt-bar") == p.get_negatives(bool)


def test_parameter_negative_bool_invalid_name(app, assert_parse_args):
    Parameter(negative_bool=())  # Valid
    with pytest.raises(ValueError):
        Parameter(negative_bool="--starts-with-hyphens")


@pytest.mark.parametrize("type_", [bool, list, set])
def test_parameter_get_negatives_bool_custom_prefix_list(type_):
    p = Parameter(negative_bool=["yesnt-", "not-"], name=("--foo", "--bar"))
    assert {"--yesnt-foo", "--yesnt-bar", "--not-foo", "--not-bar"} == set(p.get_negatives(bool))


def test_parameter_from_annotation_basic():
    expected_cparam = Parameter(
        name=["--help", "-h"],
        negative="",
        show_default=False,
        help="Display this message and exit.",
    )

    assert Parameter.from_annotation(Annotated[bool, expected_cparam], Parameter()) == expected_cparam


def test_parameter_from_annotation_optional_annotated():
    expected_cparam = Parameter(
        name=["--help", "-h"],
        negative="",
        show_default=False,
        help="Display this message and exit.",
    )

    assert Parameter.from_annotation(Optional[Annotated[bool, expected_cparam]], Parameter()) == expected_cparam


def test_parameter_from_annotation_empty_annotation():
    assert Parameter.from_annotation(inspect.Parameter.empty, Parameter()) == Parameter()


def test_parameter_combine():
    p1 = Parameter(negative="--foo")
    p2 = Parameter(show_default=False)
    p_combined = Parameter.combine(p1, None, p2)

    assert p_combined.negative == ("--foo",)
    assert p_combined.show_default is False


def test_parameter_combine_priority():
    p1 = Parameter(negative="--foo")
    p2 = Parameter(negative="--bar")
    p_combined = Parameter.combine(p1, p2)

    assert p_combined.negative == ("--bar",)


def test_parameter_combine_priority_none():
    p1 = Parameter(negative="--foo")
    p2 = Parameter(negative=None)
    p_combined = Parameter.combine(p1, p2)

    assert p_combined.negative is None


def test_parameter_default():
    p1 = Parameter()
    p2 = Parameter.default()

    # The two parameters should be equivalent.
    assert p1 == p2

    # However, the _provided_args field should differ
    assert p1._provided_args == ()
    # Just testing a few
    assert {"name", "converter", "validator"}.issubset(p2._provided_args)
