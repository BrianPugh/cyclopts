import pytest

from cyclopts.validators import Number


def test_validator_number_type():
    validator = Number()
    with pytest.raises(TypeError):
        validator(int, "this is a string.")  # pyright: ignore[reportArgumentType]


def test_validator_number_lt():
    validator = Number(lt=5)
    validator(int, 0)

    with pytest.raises(ValueError):
        validator(int, 5)

    with pytest.raises(ValueError):
        validator(int, 6)


def test_validator_number_lt_sequence():
    validator = Number(lt=5)
    validator(int, (0, 0, 0))
    validator(int, (0, 0, (1, 2)))

    with pytest.raises(ValueError):
        validator(int, 5)

    with pytest.raises(ValueError):
        validator(int, 6)

    with pytest.raises(ValueError):
        validator(int, (0, 0, 6))

    with pytest.raises(ValueError):
        validator(int, (0, 0, (1, 6)))


def test_validator_number_lte():
    validator = Number(lte=5)
    validator(int, 0)
    validator(int, 5)

    with pytest.raises(ValueError):
        validator(int, 6)


def test_validator_number_gt():
    validator = Number(gt=5)
    validator(int, 10)

    with pytest.raises(ValueError):
        validator(int, 5)

    with pytest.raises(ValueError):
        validator(int, 4)


def test_validator_number_gte():
    validator = Number(gte=5)
    validator(int, 10)
    validator(int, 5)

    with pytest.raises(ValueError):
        validator(int, 4)


def test_validator_number_modulo():
    validator = Number(modulo=4)
    validator(int, 8)
    validator(float, 8.0)
    with pytest.raises(ValueError):
        validator(int, 9)


def test_validator_number_typeerror():
    validator = Number(gte=5)
    with pytest.raises(TypeError):
        validator(str, "foo")  # pyright: ignore[reportArgumentType]


def test_validator_number_set():
    """Sets are validated element-wise, just like sequences."""
    validator = Number(lt=5)
    validator(set[int], {0, 1, 2})
    validator(frozenset[int], frozenset({0, 1, 2}))

    with pytest.raises(ValueError):
        validator(set[int], {0, 6})

    with pytest.raises(ValueError):
        validator(frozenset[int], frozenset({0, 6}))


def test_validator_number_mapping():
    """Mapping **values** are validated element-wise."""
    validator = Number(lt=5)
    validator(dict[str, int], {"a": 0, "b": 1})

    with pytest.raises(ValueError):
        validator(dict[str, int], {"a": 0, "b": 6})


def test_validator_number_nested_containers():
    validator = Number(lt=5)
    validator(dict[str, list[int]], {"a": [0, 1]})

    with pytest.raises(ValueError):
        validator(dict[str, list[int]], {"a": [0, 6]})

    with pytest.raises(ValueError):
        validator(list[set[int]], [{0}, {6}])
