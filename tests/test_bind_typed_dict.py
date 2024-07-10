"""TypedDict.

TODO/Notes:
    * total=False/True (>=3.8)
        * MyDict.__total__
    * MyDict.__required_keys__ frozenset  (>= 3.9)
    * MyDict.__optional_keys__ frozenset  (>= 3.9)
    * Required/NotRequired (>= 3.11)
"""

import sys
from typing import List, TypedDict

import pytest


class MyDict(TypedDict):
    my_int: int
    my_str: str
    my_list: list
    my_list_int: List[int]


def test_bind_typed_dict(app, assert_parse_args):
    @app.command
    def foo(d: MyDict):
        pass

    assert_parse_args(
        foo,
        "foo --d.my_int=5 --d.my_str=bar --d.my-list=a --d.my-list=b --d.my-list-int=1 --d.my-list-int=2",
        d={
            "my_int": 5,
            "my_str": "bar",
            "my_list": ["a", "b"],
            "my_list_int": [1, 2],
        },
    )


@pytest.mark.skipif(sys.version_info < (3, 11) or True, reason="Not Implemented")
def test_bind_typed_dict_not_required():
    raise NotImplementedError


@pytest.mark.skipif(sys.version_info < (3, 11) or True, reason="Not Implemented")
def test_bind_typed_dict_required():
    raise NotImplementedError
