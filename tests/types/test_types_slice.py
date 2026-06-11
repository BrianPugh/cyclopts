import pytest

from cyclopts.exceptions import ValidationError
from cyclopts.types import NonEmptySlice


def test_non_empty_slice_valid(app, assert_parse_args):
    @app.default
    def default(time: NonEmptySlice):
        pass

    assert_parse_args(default, "0:3", slice(0, 3))
    assert_parse_args(default, "--time :10", slice(None, 10))


def test_non_empty_slice_empty_raises(app):
    @app.default
    def default(time: NonEmptySlice):
        pass

    with pytest.raises(ValidationError) as e:
        app.parse_args("3:1", exit_on_error=False)
    assert str(e.value) == 'Invalid value "3:1" for TIME. Slice must select a non-empty range.'
