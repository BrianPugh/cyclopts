import pytest
from typing import Iterable, List, Tuple, Literal

from cyclopts.typing import is_iterable_type_hint


@pytest.mark.parametrize(
    "t",
    [
        List,
        List[int],
        Tuple,
        Tuple[int, int],
        Iterable,
        Iterable[int],
    ],
)
def test_is_iterable_type_hint_true(t):
    assert is_iterable_type_hint(t) is True


@pytest.mark.parametrize(
    "t",
    [
        int,
        Literal[1, 2, 3],
    ],
)
def test_is_iterable_type_hint_false(t):
    assert is_iterable_type_hint(t) is False
