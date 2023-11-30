import inspect
from typing import List, Set

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

    iparam = inspect.Parameter(
        name="help",
        kind=inspect.Parameter.KEYWORD_ONLY,
        default=False,
        annotation=Annotated[bool, expected_cparam],
    )
    type_, cparam = get_hint_parameter(iparam.annotation)
    assert type_ is bool
    assert cparam == expected_cparam
