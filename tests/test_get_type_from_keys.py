from typing import Dict, List

import pytest

from cyclopts.bind import _get_type_from_keys
from cyclopts.exceptions import UnknownOptionError


@pytest.mark.parametrize(
    "hint, keys, expected",
    [
        (list, [], list),
        (int, [], int),
        (List[str], [], List[str]),
        (Dict[str, str], ["foo"], str),
        (Dict[str, int], ["foo"], int),
        (dict, ["foo"], str),
    ],
)
def test_get_type_from_keys(hint, keys, expected):
    assert _get_type_from_keys(hint, keys) == expected


@pytest.mark.parametrize(
    "hint, keys, exception",
    [
        (Dict[int, str], [], ValueError),
        (Dict[str, int], ["foo", "bar"], UnknownOptionError),
    ],
)
def test_get_type_from_keys_exceptions(hint, keys, exception):
    with pytest.raises(exception):
        _get_type_from_keys(hint, keys)
