import re
from contextlib import nullcontext
from decimal import Decimal
from fractions import Fraction
from typing import Annotated

from pytest import mark, raises

from cyclopts import Parameter
from cyclopts.exceptions import ValidationError
from cyclopts.validators import Number

GT_PAT = re.compile(r" > ")
GTE_PAT = re.compile(r" >= ")
LT_PAT = re.compile(r" < ")
LTE_PAT = re.compile(r" <= ")
MOD_PAT = re.compile(r" multiple of ")


@mark.parametrize(
    "type_,value,expectation", [(int, "this is a string.", raises(TypeError)), (str, "foo", raises(TypeError))]
)
def test_type(type_, value, expectation):
    validator = Number()
    with nullcontext() if expectation is None else expectation:
        validator(type_, value)


@mark.parametrize(
    "type_,value,lt,expectation",
    [
        (int, 0, 5, None),
        (int, 5, 5, raises(ValueError, match=LT_PAT)),
        (int, 6, 5, raises(ValueError, match=LT_PAT)),
        (Fraction, Fraction(0, 1), 1, None),
        (Fraction, Fraction(0, 1), 0, raises(ValueError, match=LT_PAT)),
        (Decimal, Decimal("0"), 1, None),
        (Decimal, Decimal("Infinity"), 0, raises(ValueError, match=LT_PAT)),
        (Decimal, Decimal("NaN"), 0, raises(ValueError, match=LT_PAT)),
        (Decimal, Decimal("-NaN"), 0, raises(ValueError, match=LT_PAT)),
        (Decimal, Decimal("sNaN"), 0, raises(ValueError, match=LT_PAT)),
        (Decimal, Decimal("0.1"), Decimal("0.2"), None),
        (Decimal, Decimal("0.2"), Decimal("0.2"), raises(ValueError, match=LT_PAT)),
        (Decimal, Decimal("0.1"), Fraction(1, 10), raises(ValueError, match=LT_PAT)),
        (Fraction, Fraction(1, 3), Fraction(1, 2), None),
        (Fraction, Fraction(1, 2), Fraction(1, 2), raises(ValueError, match=LT_PAT)),
        (Fraction, Fraction(1, 2), Decimal("0.5"), raises(ValueError, match=LT_PAT)),
        (float, 0.5, Decimal("0.5"), raises(ValueError, match=LT_PAT)),
        (int, (0, 0, 0), 5, None),
        (int, (0, 0, (1, 2)), 5, None),
        (int, (0, 0, 6), 5, raises(ValueError, match=LT_PAT)),
        (int, (0, 0, (1, 6)), 5, raises(ValueError, match=LT_PAT)),
        *(
            (float, value, 0, raises(ValueError, match=LT_PAT))
            for value in [float("nan"), [float("nan")], {"value": [float("nan")]}]
        ),
        (float, float("-inf"), 0, None),
        (set[int], {0, 1, 2}, 5, None),
        (frozenset[int], frozenset({0, 1, 2}), 5, None),
        (set[int], {0, 6}, 5, raises(ValueError, match=LT_PAT)),
        (frozenset[int], frozenset({0, 6}), 5, raises(ValueError, match=LT_PAT)),
        (dict[str, int], {"a": 0, "b": 1}, 5, None),
        (dict[str, int], {"a": 0, "b": 6}, 5, raises(ValueError, match=LT_PAT)),
        (dict[str, list[int]], {"a": [0, 1]}, 5, None),
        (dict[str, list[int]], {"a": [0, 6]}, 5, raises(ValueError, match=LT_PAT)),
        (list[set[int]], [{0}, {6}], 5, raises(ValueError, match=LT_PAT)),
    ],
)
def test_lt(type_, value, lt, expectation):
    validator = Number(lt=lt)
    with nullcontext() if expectation is None else expectation:
        validator(type_, value)


@mark.parametrize(
    "type_,value,lte,expectation",
    [
        (int, 0, 5, None),
        (int, 5, 5, None),
        (int, 6, 5, raises(ValueError, match=LTE_PAT)),
        *(
            (float, value, 0, raises(ValueError, match=LTE_PAT))
            for value in [float("nan"), [float("nan")], {"value": [float("nan")]}]
        ),
        *(
            (Decimal, value, 0, raises(ValueError, match=LTE_PAT))
            for value in [Decimal("NaN"), Decimal("sNaN"), [Decimal("NaN")], {"value": [Decimal("sNaN")]}]
        ),
        (float, float("-inf"), 0, None),
    ],
)
def test_lte(type_, value, lte, expectation):
    validator = Number(lte=lte)
    with nullcontext() if expectation is None else expectation:
        validator(type_, value)


@mark.parametrize(
    "type_,value,gt,expectation",
    [
        (int, 10, 5, None),
        (int, 5, 5, raises(ValueError, match=GT_PAT)),
        (int, 4, 5, raises(ValueError, match=GT_PAT)),
        *(
            (float, value, 0, raises(ValueError, match=GT_PAT))
            for value in [float("nan"), [float("nan")], {"value": [float("nan")]}]
        ),
        *(
            (Decimal, value, 0, raises(ValueError, match=GT_PAT))
            for value in [Decimal("NaN"), Decimal("sNaN"), [Decimal("NaN")], {"value": [Decimal("sNaN")]}]
        ),
        (float, float("inf"), 0, None),
    ],
)
def test_gt(type_, value, gt, expectation):
    validator = Number(gt=gt)
    with nullcontext() if expectation is None else expectation:
        validator(type_, value)


@mark.parametrize(
    "type_,value,gte,expectation",
    [
        (int, 10, 5, None),
        (int, 5, 5, None),
        (int, 4, 5, raises(ValueError, match=GTE_PAT)),
        *(
            (float, value, 0, raises(ValueError, match=GTE_PAT))
            for value in [float("nan"), [float("nan")], {"value": [float("nan")]}]
        ),
        *(
            (Decimal, value, 0, raises(ValueError, match=GTE_PAT))
            for value in [Decimal("NaN"), Decimal("sNaN"), [Decimal("NaN")], {"value": [Decimal("sNaN")]}]
        ),
        (float, float("inf"), 0, None),
    ],
)
def test_gte(type_, value, gte, expectation):
    validator = Number(gte=gte)
    with nullcontext() if expectation is None else expectation:
        validator(type_, value)


@mark.parametrize(
    "type_,value,modulo,expectation",
    [
        (int, 8, 4, None),
        (float, 8.0, 4, None),
        (int, 9, 4, raises(ValueError, match=MOD_PAT)),
        (Fraction, Fraction(8, 1), 4, None),
        (Fraction, Fraction(9, 1), 4, raises(ValueError, match=MOD_PAT)),
        (Decimal, Decimal(8), 4, None),
        (Decimal, Decimal(9), 4, raises(ValueError, match=MOD_PAT)),
        (Decimal, Decimal("0.3"), Decimal("0.1"), None),
        (Decimal, Decimal("0.35"), Decimal("0.1"), raises(ValueError, match=MOD_PAT)),
        (Decimal, Decimal("1.5"), 0.5, None),
        (Decimal, Decimal("1.6"), 0.5, raises(ValueError, match=MOD_PAT)),
        # 0.1 as a float is slightly more than 1/10, so 0.3 is not an exact multiple of it.
        (Decimal, Decimal("0.3"), 0.1, raises(ValueError, match=MOD_PAT)),
        (Decimal, Decimal("1.5"), Fraction(1, 2), None),
        (Decimal, Decimal("1.6"), Fraction(1, 2), raises(ValueError, match=MOD_PAT)),
        (Fraction, Fraction(3, 2), Decimal("0.5"), None),
        (Fraction, Fraction(1, 3), Decimal("0.5"), raises(ValueError, match=MOD_PAT)),
        (float, 1.5, Decimal("0.5"), None),
        (float, 1.6, Decimal("0.5"), raises(ValueError, match=MOD_PAT)),
        (Fraction, Fraction(9, 10), Fraction(3, 10), None),
        (Decimal, Decimal("1E30"), Decimal("0.1"), None),
        (Decimal, Decimal("1000000000000000000000000000000.05"), Decimal("0.1"), raises(ValueError, match=MOD_PAT)),
        *(
            (type(value), value, 4, raises(ValueError, match=MOD_PAT))
            for value in [
                float("nan"),
                float("inf"),
                float("-inf"),
                Decimal("NaN"),
                Decimal("sNaN"),
                Decimal("Infinity"),
                Decimal("-Infinity"),
            ]
        ),
    ],
)
def test_modulo(type_, value, modulo, expectation):
    validator = Number(modulo=modulo)
    with nullcontext() if expectation is None else expectation:
        validator(type_, value)


@mark.parametrize("token", ["-100.00", "0", "nan", "snan", "inf", "-inf", "100.05"])
def test_app_decimal_rejected(app, token):
    @app.default
    def main(cost: Annotated[Decimal, Parameter(validator=Number(gt=0, lt=1000, modulo=Decimal("0.1")))]):
        pass

    with raises(ValidationError):
        app.parse_args([token], exit_on_error=False)


def test_app_decimal_accepted(app, assert_parse_args):
    @app.default
    def main(cost: Annotated[Decimal, Parameter(validator=Number(gt=0, lt=1000, modulo=Decimal("0.1")))]):
        pass

    assert_parse_args(main, "100.10", Decimal("100.10"))


def test_app_optional_omitted(app, assert_parse_args):
    @app.default
    def main(x: Annotated[int | None, Parameter(validator=Number(gte=0))] = None):
        pass

    assert_parse_args(main, "")
