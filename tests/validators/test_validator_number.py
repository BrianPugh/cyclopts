import decimal
import re
from contextlib import nullcontext
from decimal import Decimal
from fractions import Fraction

from pytest import mark, param, raises

from cyclopts.validators import Number

LT_PAT = re.compile(r" < ")
MOD_PAT = re.compile(r" multiple of ")


@mark.parametrize(
    "type_,value,expectation", [(int, "this is a string.", raises(TypeError)), (str, "foo", raises(TypeError))]
)
def test_validator_number_type(type_, value, expectation):
    validator = Number()
    with nullcontext() if expectation is None else expectation:
        validator(type_, value)


@mark.parametrize(
    "type_,value,lt,expectation",
    [
        (int, 0, 5, None),
        (int, 5, 5, raises(ValueError)),
        (int, 6, 5, raises(ValueError)),
        (Fraction, Fraction(0, 1), 1, None),
        (Fraction, Fraction(0, 1), 0, raises(ValueError, match=LT_PAT)),
        (Decimal, Decimal("0"), 1, None),
        (Decimal, Decimal("Infinity"), 0, raises(ValueError, match=LT_PAT)),
        (Decimal, Decimal("NaN"), 0, raises(ValueError, match=LT_PAT)),
        (int, (0, 0, 0), 5, None),
        (int, (0, 0, (1, 2)), 5, None),
        (int, (0, 0, 6), 5, raises(ValueError)),
        (int, (0, 0, (1, 6)), 5, raises(ValueError)),
        *(
            param(float, value, 0, raises(ValueError, match=r"Must be < 0."), id=id)
            for value, id in [
                (float("nan"), "scalar"),
                ([float("nan")], "list"),
                ({"value": [float("nan")]}, "nested_mapping"),
            ]
        ),
        (float, float("-inf"), 0, None),
        (set[int], {0, 1, 2}, 5, None),
        (frozenset[int], frozenset({0, 1, 2}), 5, None),
        (set[int], {0, 6}, 5, raises(ValueError)),
        (frozenset[int], frozenset({0, 6}), 5, raises(ValueError)),
        (dict[str, int], {"a": 0, "b": 1}, 5, None),
        (dict[str, int], {"a": 0, "b": 6}, 5, raises(ValueError)),
        (dict[str, list[int]], {"a": [0, 1]}, 5, None),
        (dict[str, list[int]], {"a": [0, 6]}, 5, raises(ValueError)),
        (list[set[int]], [{0}, {6}], 5, raises(ValueError)),
    ],
)
def test_validator_number_lt(type_, value, lt, expectation):
    validator = Number(lt=lt)
    with decimal.localcontext(decimal.ExtendedContext), nullcontext() if expectation is None else expectation:
        validator(type_, value)


@mark.parametrize(
    "type_,value,lte,expectation",
    [
        (int, 0, 5, None),
        (int, 5, 5, None),
        (int, 6, 5, raises(ValueError)),
        *(
            param(float, value, 0, raises(ValueError, match=r"Must be <= 0."), id=id)
            for value, id in [
                (float("nan"), "scalar"),
                ([float("nan")], "list"),
                ({"value": [float("nan")]}, "nested_mapping"),
            ]
        ),
        (float, float("-inf"), 0, None),
    ],
)
def test_validator_number_lte(type_, value, lte, expectation):
    validator = Number(lte=lte)
    with nullcontext() if expectation is None else expectation:
        validator(type_, value)


@mark.parametrize(
    "type_,value,gt,expectation",
    [
        (int, 10, 5, None),
        (int, 5, 5, raises(ValueError)),
        (int, 4, 5, raises(ValueError)),
        *(
            param(float, value, 0, raises(ValueError, match=r"Must be > 0."), id=id)
            for value, id in [
                (float("nan"), "scalar"),
                ([float("nan")], "list"),
                ({"value": [float("nan")]}, "nested_mapping"),
            ]
        ),
        (float, float("inf"), 0, None),
    ],
)
def test_validator_number_gt(type_, value, gt, expectation):
    validator = Number(gt=gt)
    with nullcontext() if expectation is None else expectation:
        validator(type_, value)


@mark.parametrize(
    "type_,value,gte,expectation",
    [
        (int, 10, 5, None),
        (int, 5, 5, None),
        (int, 4, 5, raises(ValueError)),
        *(
            param(float, value, 0, raises(ValueError, match=r"Must be >= 0."), id=id)
            for value, id in [
                (float("nan"), "scalar"),
                ([float("nan")], "list"),
                ({"value": [float("nan")]}, "nested_mapping"),
            ]
        ),
        (float, float("inf"), 0, None),
    ],
)
def test_validator_number_gte(type_, value, gte, expectation):
    validator = Number(gte=gte)
    with nullcontext() if expectation is None else expectation:
        validator(type_, value)


@mark.parametrize(
    "type_,value,modulo,expectation",
    [
        (int, 8, 4, None),
        (float, 8.0, 4, None),
        (int, 9, 4, raises(ValueError)),
        (Fraction, Fraction(8, 1), 4, None),
        (Fraction, Fraction(9, 1), 4, raises(ValueError, match=MOD_PAT)),
        (Decimal, Decimal(8), 4, None),
        (Decimal, Decimal(9), 4, raises(ValueError, match=MOD_PAT)),
    ],
)
def test_validator_number_modulo(type_, value, modulo, expectation):
    validator = Number(modulo=modulo)
    with decimal.localcontext(decimal.ExtendedContext), nullcontext() if expectation is None else expectation:
        validator(type_, value)
