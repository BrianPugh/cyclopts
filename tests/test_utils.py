import pytest

from cyclopts.utils import Sentinel, grouper


def test_grouper():
    assert [(1,), (2,), (3,), (4,)] == list(grouper([1, 2, 3, 4], 1))
    assert [(1, 2), (3, 4)] == list(grouper([1, 2, 3, 4], 2))
    assert [(1, 2, 3, 4)] == list(grouper([1, 2, 3, 4], 4))

    with pytest.raises(ValueError):
        grouper([1, 2, 3, 4], 3)


def test_sentinel():
    class SENTINEL_VALUE(Sentinel):  # noqa: N801
        pass

    assert str(SENTINEL_VALUE) == "<SENTINEL_VALUE>"
    assert bool(SENTINEL_VALUE) is False
