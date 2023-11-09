from typing import Iterable, List, Tuple

from cyclopts.typing import is_iterable_type_hint


def test_is_iterable_type_hint():
    assert is_iterable_type_hint(List) is True
    assert is_iterable_type_hint(List[int]) is True
    assert is_iterable_type_hint(Tuple) is True
    assert is_iterable_type_hint(Tuple[int, int]) is True
    assert is_iterable_type_hint(int) is False
    assert is_iterable_type_hint(Iterable) is True
    assert is_iterable_type_hint(Iterable[int]) is True
