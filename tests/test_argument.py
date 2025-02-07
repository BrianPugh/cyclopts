from collections import namedtuple
from typing import Annotated, Dict, List, Optional, TypedDict, Union

import pytest

from cyclopts.argument import (
    Argument,
    ArgumentCollection,
    _resolve_groups_from_callable,
    _resolve_parameter_name,
    is_typeddict,
)
from cyclopts.group import Group
from cyclopts.parameter import Parameter
from cyclopts.token import Token

Case = namedtuple("TestCase", ["args", "expected"])


def test_argument_collection_no_annotation_no_default():
    def foo(a, b):
        pass

    collection = ArgumentCollection._from_callable(foo)

    assert len(collection) == 2

    assert collection[0].field_info.name == "a"
    assert collection[0].hint is str
    assert collection[0].keys == ()
    assert collection[0]._accepts_keywords is False

    assert collection[1].field_info.name == "b"
    assert collection[1].hint is str
    assert collection[1].keys == ()
    assert collection[1]._accepts_keywords is False


def test_argument_collection_no_annotation_default():
    def foo(a="foo", b=100):
        pass

    collection = ArgumentCollection._from_callable(foo)

    assert len(collection) == 2

    assert collection[0].field_info.name == "a"
    assert collection[0].hint is str
    assert collection[0].keys == ()
    assert collection[0]._accepts_keywords is False

    assert collection[1].field_info.name == "b"
    assert collection[1].hint is int
    assert collection[1].keys == ()
    assert collection[1]._accepts_keywords is False


def test_argument_collection_basic_annotation():
    def foo(a: str, b: int):
        pass

    collection = ArgumentCollection._from_callable(foo)

    assert len(collection) == 2

    assert collection[0].field_info.name == "a"
    assert collection[0].hint is str
    assert collection[0].keys == ()
    assert collection[0]._accepts_keywords is False

    assert collection[1].field_info.name == "b"
    assert collection[1].hint is int
    assert collection[1].keys == ()
    assert collection[1]._accepts_keywords is False


@pytest.mark.parametrize("type_", [dict, Dict])
def test_argument_collection_bare_dict(type_):
    def foo(a: type_, b: int):  # pyright: ignore
        pass

    collection = ArgumentCollection._from_callable(foo)

    assert len(collection) == 2

    assert collection[0].field_info.name == "a"
    assert collection[0].parameter.name == ("--a",)
    assert collection[0].hint is type_
    assert collection[0].keys == ()
    assert collection[0]._accepts_keywords is True
    assert collection[0]._accepts_arbitrary_keywords is True

    assert collection[1].field_info.name == "b"
    assert collection[1].parameter.name == ("--b",)
    assert collection[1].hint is int
    assert collection[1].keys == ()
    assert collection[1]._accepts_keywords is False


def test_argument_collection_typing_dict():
    def foo(a: Dict[str, int], b: int):
        pass

    collection = ArgumentCollection._from_callable(foo)

    assert len(collection) == 2

    assert collection[0].field_info.name == "a"
    assert collection[0].hint == Dict[str, int]
    assert collection[0].keys == ()
    assert collection[0]._accepts_keywords is True
    assert collection[0]._accepts_arbitrary_keywords is True

    assert collection[1].field_info.name == "b"
    assert collection[1].hint is int
    assert collection[1].keys == ()
    assert collection[1]._accepts_keywords is False


def test_argument_collection_typeddict():
    class ExampleTypedDict(TypedDict):
        foo: str
        bar: int

    def foo(a: ExampleTypedDict, b: int):
        pass

    collection = ArgumentCollection._from_callable(foo)

    assert len(collection) == 4

    assert collection[0].field_info.name == "a"
    assert collection[0].parameter.name == ("--a",)
    assert collection[0].hint is ExampleTypedDict
    assert collection[0].keys == ()
    assert collection[0]._accepts_keywords is True
    assert collection[0].children

    assert collection[1].field_info.name == "foo"
    assert collection[1].parameter.name == ("--a.foo",)
    assert collection[1].hint is str
    assert collection[1].keys == ("foo",)
    assert collection[1]._accepts_keywords is False
    assert not collection[1].children

    assert collection[2].field_info.name == "bar"
    assert collection[2].parameter.name == ("--a.bar",)
    assert collection[2].hint is int
    assert collection[2].keys == ("bar",)
    assert collection[2]._accepts_keywords is False
    assert not collection[2].children

    assert collection[3].field_info.name == "b"
    assert collection[3].parameter.name == ("--b",)
    assert collection[3].hint is int
    assert collection[3].keys == ()
    assert collection[3]._accepts_keywords is False
    assert not collection[3].children


def test_argument_collection_typeddict_nested():
    class Inner(TypedDict):
        fizz: float
        buzz: Annotated[complex, Parameter(name="bazz")]

    class ExampleTypedDict(TypedDict):
        foo: Inner
        bar: int

    def foo(a: ExampleTypedDict, b: int):
        pass

    collection = ArgumentCollection._from_callable(foo)

    assert len(collection) == 6

    assert collection[0].field_info.name == "a"
    assert collection[0].parameter.name == ("--a",)
    assert collection[0].hint is ExampleTypedDict
    assert collection[0].keys == ()
    assert collection[0]._accepts_keywords is True
    assert collection[0].children

    assert collection[1].field_info.name == "foo"
    assert collection[1].parameter.name == ("--a.foo",)
    assert collection[1].hint is Inner
    assert collection[1].keys == ("foo",)
    assert collection[1]._accepts_keywords is True
    assert collection[1].children

    assert collection[2].field_info.name == "fizz"
    assert collection[2].parameter.name == ("--a.foo.fizz",)
    assert collection[2].hint is float
    assert collection[2].keys == ("foo", "fizz")
    assert collection[2]._accepts_keywords is False
    assert not collection[2].children

    assert collection[3].field_info.name == "buzz"
    assert collection[3].parameter.name == ("--a.foo.bazz",)
    assert collection[3].hint is complex
    assert collection[3].keys == ("foo", "buzz")
    assert collection[3]._accepts_keywords is False
    assert not collection[3].children

    assert collection[4].field_info.name == "bar"
    assert collection[4].parameter.name == ("--a.bar",)
    assert collection[4].hint is int
    assert collection[4].keys == ("bar",)
    assert collection[4]._accepts_keywords is False
    assert not collection[4].children

    assert collection[5].field_info.name == "b"
    assert collection[5].parameter.name == ("--b",)
    assert collection[5].hint is int
    assert collection[5].keys == ()
    assert collection[5]._accepts_keywords is False
    assert not collection[5].children


def test_argument_collection_typeddict_annotated_keys_name_change():
    class ExampleTypedDict(TypedDict):
        foo: Annotated[str, Parameter(name="fizz")]
        bar: Annotated[int, Parameter(name="buzz")]

    def foo(a: ExampleTypedDict, b: int):
        pass

    collection = ArgumentCollection._from_callable(foo)

    assert len(collection) == 4

    assert collection[0].field_info.name == "a"
    assert collection[0].parameter.name == ("--a",)
    assert collection[0].hint is ExampleTypedDict
    assert collection[0].keys == ()
    assert collection[0]._accepts_keywords is True
    assert collection[0].children

    assert collection[1].field_info.name == "foo"
    assert collection[1].parameter.name == ("--a.fizz",)
    assert collection[1].hint is str
    assert collection[1].keys == ("foo",)
    assert collection[1]._accepts_keywords is False
    assert not collection[1].children

    assert collection[2].field_info.name == "bar"
    assert collection[2].parameter.name == ("--a.buzz",)
    assert collection[2].hint is int
    assert collection[2].keys == ("bar",)
    assert collection[2]._accepts_keywords is False
    assert not collection[2].children

    assert collection[3].field_info.name == "b"
    assert collection[3].parameter.name == ("--b",)
    assert collection[3].hint is int
    assert collection[3].keys == ()
    assert collection[3]._accepts_keywords is False
    assert not collection[3].children


def test_argument_collection_typeddict_annotated_keys_name_override():
    class ExampleTypedDict(TypedDict):
        foo: Annotated[str, Parameter(name="--fizz")]
        bar: Annotated[int, Parameter(name="--buzz")]

    def foo(a: ExampleTypedDict, b: int):
        pass

    collection = ArgumentCollection._from_callable(foo)

    assert len(collection) == 4

    assert collection[0].field_info.name == "a"
    assert collection[0].parameter.name == ("--a",)
    assert collection[0].hint is ExampleTypedDict
    assert collection[0].keys == ()
    assert collection[0]._accepts_keywords is True
    assert collection[0].children

    assert collection[1].field_info.name == "foo"
    assert collection[1].parameter.name == ("--fizz",)
    assert collection[1].hint is str
    assert collection[1].keys == ("foo",)
    assert collection[1]._accepts_keywords is False
    assert not collection[1].children

    assert collection[2].field_info.name == "bar"
    assert collection[2].parameter.name == ("--buzz",)
    assert collection[2].hint is int
    assert collection[2].keys == ("bar",)
    assert collection[2]._accepts_keywords is False
    assert not collection[2].children

    assert collection[3].field_info.name == "b"
    assert collection[3].parameter.name == ("--b",)
    assert collection[3].hint is int
    assert collection[3].keys == ()
    assert collection[3]._accepts_keywords is False
    assert not collection[3].children


def test_argument_collection_typeddict_flatten_root():
    class ExampleTypedDict(TypedDict):
        foo: str
        bar: int

    def foo(a: Annotated[ExampleTypedDict, Parameter(name="*")], b: int):
        pass

    collection = ArgumentCollection._from_callable(foo)

    assert collection[0].field_info.name == "a"
    assert collection[0].parameter.name == ("*",)
    assert collection[0].hint is ExampleTypedDict
    assert collection[0].keys == ()
    assert collection[0]._accepts_keywords is True
    assert collection[0].children

    assert collection[1].field_info.name == "foo"
    assert collection[1].parameter.name == ("--foo",)
    assert collection[1].hint is str
    assert collection[1].keys == ("foo",)
    assert collection[1]._accepts_keywords is False
    assert not collection[1].children

    assert collection[2].field_info.name == "bar"
    assert collection[2].parameter.name == ("--bar",)
    assert collection[2].hint is int
    assert collection[2].keys == ("bar",)
    assert collection[2]._accepts_keywords is False
    assert not collection[2].children

    assert collection[3].field_info.name == "b"
    assert collection[3].parameter.name == ("--b",)
    assert collection[3].hint is int
    assert collection[3].keys == ()
    assert collection[3]._accepts_keywords is False
    assert not collection[3].children


def test_argument_collection_var_positional():
    def foo(a: int, *b: float):
        pass

    collection = ArgumentCollection._from_callable(foo)

    assert len(collection) == 2

    assert collection[0].parameter.name == ("--a",)
    assert collection[0].hint is int
    assert collection[0].keys == ()
    assert collection[0]._accepts_keywords is False

    assert collection[1].field_info.name == "b"
    assert collection[1].parameter.name == ("B",)
    assert collection[1].hint == tuple[float, ...]
    assert collection[1].keys == ()
    assert collection[1]._accepts_keywords is False


def test_argument_collection_var_keyword():
    def foo(a: int, **b: float):
        pass

    collection = ArgumentCollection._from_callable(foo)

    assert len(collection) == 2

    assert collection[0].field_info.name == "a"
    assert collection[0].parameter.name == ("--a",)
    assert collection[0].hint is int
    assert collection[0].keys == ()
    assert collection[0]._accepts_keywords is False

    assert collection[1].field_info.name == "b"
    assert collection[1].parameter.name == ("--[KEYWORD]",)
    assert collection[1].hint == dict[str, float]
    assert collection[1].keys == ()
    assert collection[1]._accepts_keywords is True


def test_argument_collection_var_keyword_named():
    def foo(a: int, **b: Annotated[float, Parameter(name=("--foo", "--bar"))]):
        pass

    collection = ArgumentCollection._from_callable(foo)

    assert len(collection) == 2

    assert collection[0].field_info.name == "a"
    assert collection[0].parameter.name == ("--a",)
    assert collection[0].hint is int
    assert collection[0].keys == ()
    assert collection[0]._accepts_keywords is False

    assert collection[1].field_info.name == "b"
    assert collection[1].parameter.name == ("--foo", "--bar")
    assert collection[1].hint == dict[str, float]
    assert collection[1].keys == ()
    assert collection[1]._accepts_keywords is True


def test_argument_collection_var_keyword_match():
    def foo(a: int, **b: float):
        pass

    collection = ArgumentCollection._from_callable(foo)

    argument, keys, _ = collection.match("--fizz")
    assert keys == ("fizz",)
    assert argument.field_info.name == "b"


@pytest.mark.parametrize(
    "args, expected",
    [
        Case(args=(), expected=()),
        Case(args=(("foo",),), expected=("--foo",)),
        Case(args=(("--foo",),), expected=("--foo",)),
        Case(args=(("--foo", "--bar"),), expected=("--foo", "--bar")),
        Case(args=(("--foo",), ("--bar",)), expected=("--bar",)),
        Case(args=(("--foo",), ("baz",)), expected=("--foo.baz",)),
        Case(args=(("--foo",), ("--bar", "baz")), expected=("--bar", "--foo.baz")),
        Case(args=(("--foo", "--bar"), ("baz",)), expected=("--foo.baz", "--bar.baz")),
        Case(args=(("*",), ("bar",)), expected=("--bar",)),
        Case(args=(("--foo", "*"), ("bar",)), expected=("--foo.bar", "--bar")),
        Case(args=(("--foo",), ("*",), ("bar",)), expected=("--foo.bar",)),
        Case(args=(("foo",), ("--bar",)), expected=("--bar",)),
        Case(args=(("foo",), ("bar",)), expected=("--foo.bar",)),
    ],
)
def test_resolve_parameter_name(args, expected):
    assert _resolve_parameter_name(*args) == expected


def test_resolve_groups_from_callable():
    class User(TypedDict):
        name: Annotated[str, Parameter(group="Inside Typed Dict")]
        age: Annotated[int, Parameter(group="Inside Typed Dict")]
        height: float

    def build(
        config1: str,
        config2: Annotated[str, Parameter()],
        flag1: Annotated[bool, Parameter(group="Flags")] = False,
        flag2: Annotated[bool, Parameter(group=("Flags", "Other Flags"))] = False,
        user: Optional[User] = None,
    ):
        pass

    actual = _resolve_groups_from_callable(build)
    assert actual == [Group("Parameters"), Group("Flags"), Group("Other Flags"), Group("Inside Typed Dict")]


def test_argument_convert():
    argument = Argument(
        hint=List[int],
        tokens=[
            Token(value="42", source="test"),
            Token(value="70", source="test"),
        ],
    )
    assert argument.convert() == [42, 70]


def test_argument_convert_dict():
    def foo(bar: Dict[str, int]):
        pass

    collection = ArgumentCollection._from_callable(foo)

    assert len(collection) == 1
    argument = collection[0]

    # Sanity check the match method
    assert argument.match("--bar.buzz") == (("buzz",), None)

    argument.append(Token(value="7", source="test", keys=("fizz",)))
    argument.append(Token(value="12", source="test", keys=("buzz",)))

    assert argument.convert() == {"fizz": 7, "buzz": 12}


def test_argument_convert_var_keyword():
    def foo(**kwargs: int):
        pass

    collection = ArgumentCollection._from_callable(foo)

    assert len(collection) == 1
    argument = collection[0]

    # Sanity check the match method
    assert argument.match("--fizz") == (("fizz",), None)

    argument.append(Token(value="7", source="test", keys=("fizz",)))
    argument.append(Token(value="12", source="test", keys=("buzz",)))

    assert argument.convert() == {"fizz": 7, "buzz": 12}


def test_argument_convert_cparam_provided():
    def my_converter(type_, tokens):
        return f"my_converter_{tokens[0].value}"

    argument = Argument(
        hint=str,
        tokens=[Token(value="my_value", source="test")],
        parameter=Parameter(
            converter=my_converter,
        ),
    )
    assert argument.convert() == "my_converter_my_value"


class ExampleTypedDict(TypedDict):
    foo: str
    bar: int


@pytest.mark.parametrize(
    "hint",
    [
        ExampleTypedDict,
        Optional[ExampleTypedDict],
        Annotated[ExampleTypedDict, "foo"],
        # A union including a Typed Dict is allowed.
        Union[ExampleTypedDict, str, int],
    ],
)
def test_is_typed_dict_true(hint):
    assert is_typeddict(hint)


@pytest.mark.parametrize(
    "hint",
    [
        list,
        dict,
        Dict,
        Dict[str, int],
    ],
)
def test_is_typed_dict_false(hint):
    assert not is_typeddict(hint)
