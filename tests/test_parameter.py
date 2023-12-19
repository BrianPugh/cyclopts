from typing import List, Optional, Set

import pytest
from typing_extensions import Annotated

from cyclopts import Parameter
from cyclopts.parameter import get_hint_parameter


def test_parameter_get_negatives_bool_default():
    p = Parameter()
    assert ("--no-foo", "--no-bar") == p.get_negatives(bool, "--foo", "--bar")


@pytest.mark.parametrize("type_", [list, set, List[str], Set[str]])
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


def test_get_hint_parameter_basic():
    expected_cparam = Parameter(
        name=["--help", "-h"],
        negative="",
        show_default=False,
        help="Display this message and exit.",
    )

    type_, cparam = get_hint_parameter(Annotated[bool, expected_cparam])
    assert type_ is bool
    assert cparam == expected_cparam


def test_get_hint_parameter_optional_annotated():
    expected_cparam = Parameter(
        name=["--help", "-h"],
        negative="",
        show_default=False,
        help="Display this message and exit.",
    )

    type_, cparam = get_hint_parameter(Optional[Annotated[bool, expected_cparam]])
    assert type_ is bool
    assert cparam == expected_cparam


def test_parameter_combine():
    p1 = Parameter(negative="--foo")
    p2 = Parameter(show_default=False)
    p_combined = Parameter.combine(p1, p2)

    assert p_combined.negative == ("--foo",)
    assert p_combined.show_default is False


def test_parameter_combine_priority():
    p1 = Parameter(negative="--foo")
    p2 = Parameter(negative="--bar")
    p_combined = Parameter.combine(p1, p2)

    assert p_combined.negative == ("--foo",)
