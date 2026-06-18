import pytest

from cyclopts.validators import Slice
from cyclopts.validators._slice import _selects_nothing


@pytest.mark.parametrize(
    "value",
    [
        slice(3, 1),  # start > stop, positive step
        slice(1, 1),  # start == stop
        slice(3, 1, 1),
        slice(-1, -3),  # both negative, positive step
        slice(None, 0),  # ":0"
        slice(1, 3, -1),  # ascending bounds, negative step
        slice(-3, -1, -1),
    ],
)
def test_slice_selects_nothing_true(value):
    assert _selects_nothing(value) is True


@pytest.mark.parametrize(
    "value",
    [
        slice(0, 3),
        slice(None, 10),
        slice(0, 100, 5),
        slice(-10, None),
        slice(None, None),  # ":"
        slice(None, None, -1),  # "::-1"
        slice(5, -5),  # mixed sign, length-dependent
        slice(-5, 5),  # mixed sign, length-dependent
        slice(1, 5, 0),  # invalid step; not our concern
    ],
)
def test_slice_selects_nothing_false(value):
    assert _selects_nothing(value) is False


def test_validator_slice_allow_empty_default():
    validator = Slice()
    validator(slice, slice(3, 1))  # No raise; empty slices allowed by default.


def test_validator_slice_disallow_empty():
    validator = Slice(allow_empty=False)
    validator(slice, slice(0, 3))  # Non-empty; ok.

    with pytest.raises(ValueError):
        validator(slice, slice(3, 1))


def test_validator_slice_disallow_empty_sequence():
    validator = Slice(allow_empty=False)
    validator(slice, [slice(0, 3), slice(1, 5)])

    with pytest.raises(ValueError):
        validator(slice, [slice(0, 3), slice(3, 1)])


def test_validator_slice_sequence_type():
    validator = Slice(allow_empty=False)
    with pytest.raises(TypeError):
        validator(slice, "this is a string.")  # pyright: ignore[reportArgumentType]


def test_validator_slice_ignores_non_slice():
    validator = Slice(allow_empty=False)
    validator(slice, 5)  # Not a slice; silently ignored.
