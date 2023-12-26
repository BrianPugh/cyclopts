import pytest

from cyclopts.validators import LimitedChoice


def test_limited_choice_default():
    """Mutually-exclusive functionality."""
    validator = LimitedChoice()

    validator()
    validator(foo=100)
    with pytest.raises(ValueError):
        validator(foo=100, bar=200)


def test_limited_choice_default_single():
    validator = LimitedChoice(1)
    with pytest.raises(ValueError):
        validator()
    validator(foo=100)
    with pytest.raises(ValueError):
        validator(foo=100, bar=200)


def test_limited_choice_default_min_max():
    validator = LimitedChoice(1, 2)
    with pytest.raises(ValueError):
        validator()
    validator(foo=100)
    validator(foo=100, bar=200)
    with pytest.raises(ValueError):
        validator(foo=100, bar=200, baz=300)
