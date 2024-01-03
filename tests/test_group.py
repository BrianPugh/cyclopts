import sys
from typing import Union

import pytest

from cyclopts import App, Group, Parameter

if sys.version_info < (3, 9):
    from typing_extensions import Annotated
else:
    from typing import Annotated


def test_group_equality():
    """Group equality is SOLELY determined by name."""
    assert Group("foo") == Group("foo")
    assert Group("foo") != Group("bar")
    assert Group("foo") in [Group("foo"), Group("bar")]
