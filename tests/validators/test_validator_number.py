import decimal
import re
from contextlib import nullcontext
from decimal import Decimal
from fractions import Fraction

from pytest import mark, raises

from cyclopts.validators import Number

LT_PAT = re.compile(r" < ")
MOD_PAT = re.compile(r" multiple of ")


def test_validator_number_type():
    validator = Number()
    with raises(TypeError):
        validator(int, "this is a string.")  # pyright: ignore[reportArgumentType]


def test_validator_number_lt():
    validator = Number(lt=5)
    validator(int, 0)

    with raises(ValueError):
        validator(int, 5)

    with raises(ValueError):
        validator(int, 6)


@mark.parametrize(
    "type_,value,lt,expectation",
    [
        (Fraction, Fraction(0, 1), 1, None),
        (Fraction, Fraction(0, 1), 0, raises(ValueError, match=LT_PAT)),
        (Decimal, Decimal("0"), 1, None),
        (Decimal, Decimal("Infinity"), 0, raises(ValueError, match=LT_PAT)),
        (Decimal, Decimal("NaN"), 0, raises(ValueError, match=LT_PAT)),
    ],
)
def test_validator_lt_fraction_decimal(type_, value, lt, expectation):
    validator = Number(lt=lt)
    with decimal.localcontext(decimal.ExtendedContext), nullcontext() if expectation is None else expectation:
        validator(type_, value)


def test_validator_number_lt_sequence():
    validator = Number(lt=5)
    validator(int, (0, 0, 0))
    validator(int, (0, 0, (1, 2)))

    with raises(ValueError):
        validator(int, 5)

    with raises(ValueError):
        validator(int, 6)

    with raises(ValueError):
        validator(int, (0, 0, 6))

    with raises(ValueError):
        validator(int, (0, 0, (1, 6)))


def test_validator_number_lte():
    validator = Number(lte=5)
    validator(int, 0)
    validator(int, 5)

    with raises(ValueError):
        validator(int, 6)


def test_validator_number_gt():
    validator = Number(gt=5)
    validator(int, 10)

    with raises(ValueError):
        validator(int, 5)

    with raises(ValueError):
        validator(int, 4)


def test_validator_number_gte():
    validator = Number(gte=5)
    validator(int, 10)
    validator(int, 5)

    with raises(ValueError):
        validator(int, 4)


@mark.parametrize(
    "validator, message",
    [
        (Number(lt=0), "Must be < 0."),
        (Number(lte=0), "Must be <= 0."),
        (Number(gt=0), "Must be > 0."),
        (Number(gte=0), "Must be >= 0."),
    ],
)
@mark.parametrize(
    "value",
    [float("nan"), [float("nan")], {"value": [float("nan")]}],
    ids=["scalar", "list", "nested_mapping"],
)
def test_validator_number_nan(validator, message, value):
    with raises(ValueError) as exc_info:
        validator(float, value)
    assert str(exc_info.value) == message


@mark.parametrize(
    "validator, value",
    [
        (Number(lt=0), float("-inf")),
        (Number(lte=0), float("-inf")),
        (Number(gt=0), float("inf")),
        (Number(gte=0), float("inf")),
    ],
)
def test_validator_number_infinity(validator, value):
    validator(float, value)


def test_validator_number_modulo():
    validator = Number(modulo=4)
    validator(int, 8)
    validator(float, 8.0)
    with raises(ValueError):
        validator(int, 9)


@mark.parametrize(
    "type_,value,modulo,expectation",
    [
        (Fraction, Fraction(8, 1), 4, None),
        (Fraction, Fraction(9, 1), 4, raises(ValueError, match=MOD_PAT)),
        (Decimal, Decimal(8), 4, None),
        (Decimal, Decimal(9), 4, raises(ValueError, match=MOD_PAT)),
    ],
)
def test_validator_modulo_fraction_decimal(type_, value, modulo, expectation):
    validator = Number(modulo=modulo)
    with decimal.localcontext(decimal.ExtendedContext), nullcontext() if expectation is None else expectation:
        validator(type_, value)


def test_validator_number_typeerror():
    validator = Number(gte=5)
    with raises(TypeError):
        validator(str, "foo")  # pyright: ignore[reportArgumentType]


def test_validator_number_set():
    """Sets are validated element-wise, just like sequences."""
    validator = Number(lt=5)
    validator(set[int], {0, 1, 2})
    validator(frozenset[int], frozenset({0, 1, 2}))

    with raises(ValueError):
        validator(set[int], {0, 6})

    with raises(ValueError):
        validator(frozenset[int], frozenset({0, 6}))


def test_validator_number_mapping():
    """Mapping **values** are validated element-wise."""
    validator = Number(lt=5)
    validator(dict[str, int], {"a": 0, "b": 1})

    with raises(ValueError):
        validator(dict[str, int], {"a": 0, "b": 6})


def test_validator_number_nested_containers():
    validator = Number(lt=5)
    validator(dict[str, list[int]], {"a": [0, 1]})

    with raises(ValueError):
        validator(dict[str, list[int]], {"a": [0, 6]})

    with raises(ValueError):
        validator(list[set[int]], [{0}, {6}])
