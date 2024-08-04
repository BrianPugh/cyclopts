import inspect
import sys
from typing import Dict, List, Optional, Tuple, TypedDict

import pytest

from cyclopts.argument import (
    Argument,
    ArgumentCollection,
    Token,
    _resolve_groups_3,
    _resolve_parameter_name,
)
from cyclopts.group import Group
from cyclopts.parameter import Parameter

if sys.version_info < (3, 9):
    from typing_extensions import Annotated  # pragma: no cover
else:
    from typing import Annotated  # pragma: no cover


def test_argument_collection_no_annotation_no_default():
    def foo(a, b):
        pass

    iparams = inspect.signature(foo).parameters
    collection = ArgumentCollection.from_callable(foo)

    assert len(collection) == 2

    assert collection[0].iparam == iparams["a"]
    assert collection[0].hint is str
    assert collection[0].keys == ()
    assert collection[0].accepts_keywords is False

    assert collection[1].iparam == iparams["b"]
    assert collection[1].hint is str
    assert collection[1].keys == ()
    assert collection[1].accepts_keywords is False


def test_argument_collection_no_annotation_default():
    def foo(a="foo", b=100):
        pass

    iparams = inspect.signature(foo).parameters
    collection = ArgumentCollection.from_callable(foo)

    assert len(collection) == 2

    assert collection[0].iparam == iparams["a"]
    assert collection[0].hint is str
    assert collection[0].keys == ()
    assert collection[0].accepts_keywords is False

    assert collection[1].iparam == iparams["b"]
    assert collection[1].hint is int
    assert collection[1].keys == ()
    assert collection[1].accepts_keywords is False


def test_argument_collection_basic_annotation():
    def foo(a: str, b: int):
        pass

    iparams = inspect.signature(foo).parameters
    collection = ArgumentCollection.from_callable(foo)

    assert len(collection) == 2

    assert collection[0].iparam == iparams["a"]
    assert collection[0].hint is str
    assert collection[0].keys == ()
    assert collection[0].accepts_keywords is False

    assert collection[1].iparam == iparams["b"]
    assert collection[1].hint is int
    assert collection[1].keys == ()
    assert collection[1].accepts_keywords is False


@pytest.mark.parametrize("type_", [dict, Dict])
def test_argument_collection_bare_dict(type_):
    def foo(a: type_, b: int):
        pass

    iparams = inspect.signature(foo).parameters
    collection = ArgumentCollection.from_callable(foo)

    assert len(collection) == 2

    assert collection[0].iparam == iparams["a"]
    assert collection[0].cparam.name == ("--a",)
    assert collection[0].hint is type_
    assert collection[0].keys == ()
    assert collection[0].accepts_keywords is True
    assert collection[0].accepts_arbitrary_keywords is True

    assert collection[1].iparam == iparams["b"]
    assert collection[1].cparam.name == ("--b",)
    assert collection[1].hint is int
    assert collection[1].keys == ()
    assert collection[1].accepts_keywords is False


def test_argument_collection_typing_dict():
    def foo(a: Dict[str, int], b: int):
        pass

    iparams = inspect.signature(foo).parameters
    collection = ArgumentCollection.from_callable(foo)

    assert len(collection) == 2

    assert collection[0].iparam == iparams["a"]
    assert collection[0].hint == Dict[str, int]
    assert collection[0].keys == ()
    assert collection[0].accepts_keywords is True
    assert collection[0].accepts_arbitrary_keywords is True

    assert collection[1].iparam == iparams["b"]
    assert collection[1].hint is int
    assert collection[1].keys == ()
    assert collection[1].accepts_keywords is False


def test_argument_collection_typeddict():
    class ExampleTypedDict(TypedDict):
        foo: str
        bar: int

    def foo(a: ExampleTypedDict, b: int):
        pass

    iparams = inspect.signature(foo).parameters
    collection = ArgumentCollection.from_callable(foo)

    assert len(collection) == 3

    assert collection[0].iparam == iparams["a"]
    assert collection[0].cparam.name == ("--a.foo",)
    assert collection[0].hint is str
    assert collection[0].keys == ("foo",)
    assert collection[0].accepts_keywords is False

    assert collection[1].iparam == iparams["a"]
    assert collection[1].cparam.name == ("--a.bar",)
    assert collection[1].hint is int
    assert collection[1].keys == ("bar",)
    assert collection[1].accepts_keywords is False

    assert collection[2].iparam == iparams["b"]
    assert collection[2].cparam.name == ("--b",)
    assert collection[2].hint is int
    assert collection[2].keys == ()
    assert collection[2].accepts_keywords is False


def test_argument_collection_typeddict_nested():
    class Inner(TypedDict):
        fizz: float
        buzz: Annotated[complex, Parameter(name="bazz")]

    class ExampleTypedDict(TypedDict):
        foo: Inner
        bar: int

    def foo(a: ExampleTypedDict, b: int):
        pass

    iparams = inspect.signature(foo).parameters
    collection = ArgumentCollection.from_callable(foo)

    assert len(collection) == 4

    assert collection[0].iparam == iparams["a"]
    assert collection[0].cparam.name == ("--a.foo.fizz",)
    assert collection[0].hint is float
    assert collection[0].keys == ("foo", "fizz")
    assert collection[0].accepts_keywords is False

    assert collection[1].iparam == iparams["a"]
    assert collection[1].cparam.name == ("--a.foo.bazz",)
    assert collection[1].hint is complex
    assert collection[1].keys == ("foo", "buzz")
    assert collection[1].accepts_keywords is False

    assert collection[2].iparam == iparams["a"]
    assert collection[2].cparam.name == ("--a.bar",)
    assert collection[2].hint is int
    assert collection[2].keys == ("bar",)
    assert collection[2].accepts_keywords is False

    assert collection[3].iparam == iparams["b"]
    assert collection[3].cparam.name == ("--b",)
    assert collection[3].hint is int
    assert collection[3].keys == ()
    assert collection[3].accepts_keywords is False


def test_argument_collection_typeddict_annotated_keys_name_change():
    class ExampleTypedDict(TypedDict):
        foo: Annotated[str, Parameter(name="fizz")]
        bar: Annotated[int, Parameter(name="buzz")]

    def foo(a: ExampleTypedDict, b: int):
        pass

    iparams = inspect.signature(foo).parameters
    collection = ArgumentCollection.from_callable(foo)

    assert len(collection) == 3

    assert collection[0].iparam == iparams["a"]
    assert collection[0].cparam.name == ("--a.fizz",)
    assert collection[0].hint is str
    assert collection[0].keys == ("foo",)
    assert collection[0].accepts_keywords is False

    assert collection[1].iparam == iparams["a"]
    assert collection[1].cparam.name == ("--a.buzz",)
    assert collection[1].hint is int
    assert collection[1].keys == ("bar",)
    assert collection[1].accepts_keywords is False

    assert collection[2].iparam == iparams["b"]
    assert collection[2].cparam.name == ("--b",)
    assert collection[2].hint is int
    assert collection[2].keys == ()
    assert collection[2].accepts_keywords is False


def test_argument_collection_typeddict_annotated_keys_name_override():
    class ExampleTypedDict(TypedDict):
        foo: Annotated[str, Parameter(name="--fizz")]
        bar: Annotated[int, Parameter(name="--buzz")]

    def foo(a: ExampleTypedDict, b: int):
        pass

    iparams = inspect.signature(foo).parameters
    collection = ArgumentCollection.from_callable(foo)

    assert len(collection) == 3

    assert collection[0].iparam == iparams["a"]
    assert collection[0].cparam.name == ("--fizz",)
    assert collection[0].hint is str
    assert collection[0].keys == ("foo",)
    assert collection[0].accepts_keywords is False

    assert collection[1].iparam == iparams["a"]
    assert collection[1].cparam.name == ("--buzz",)
    assert collection[1].hint is int
    assert collection[1].keys == ("bar",)
    assert collection[1].accepts_keywords is False

    assert collection[2].iparam == iparams["b"]
    assert collection[2].cparam.name == ("--b",)
    assert collection[2].hint is int
    assert collection[2].keys == ()
    assert collection[2].accepts_keywords is False


def test_argument_collection_typeddict_flatten_root():
    class ExampleTypedDict(TypedDict):
        foo: str
        bar: int

    def foo(a: Annotated[ExampleTypedDict, Parameter(name="*")], b: int):
        pass

    iparams = inspect.signature(foo).parameters
    collection = ArgumentCollection.from_callable(foo)

    assert len(collection) == 3

    assert collection[0].iparam == iparams["a"]
    assert collection[0].cparam.name == ("--foo",)
    assert collection[0].hint is str
    assert collection[0].keys == ("foo",)
    assert collection[0].accepts_keywords is False

    assert collection[1].iparam == iparams["a"]
    assert collection[1].cparam.name == ("--bar",)
    assert collection[1].hint is int
    assert collection[1].keys == ("bar",)
    assert collection[1].accepts_keywords is False

    assert collection[2].iparam == iparams["b"]
    assert collection[2].cparam.name == ("--b",)
    assert collection[2].hint is int
    assert collection[2].keys == ()
    assert collection[2].accepts_keywords is False


def test_argument_collection_var_positional():
    def foo(a: int, *b: float):
        pass

    iparams = inspect.signature(foo).parameters
    collection = ArgumentCollection.from_callable(foo)

    assert len(collection) == 2

    assert collection[0].iparam == iparams["a"]
    assert collection[0].cparam.name == ("--a",)
    assert collection[0].hint is int
    assert collection[0].keys == ()
    assert collection[0].accepts_keywords is False

    assert collection[1].iparam == iparams["b"]
    assert collection[1].cparam.name == ("B",)
    assert collection[1].hint is Tuple[float, ...]
    assert collection[1].keys == ()
    assert collection[1].accepts_keywords is False


def test_argument_collection_var_keyword():
    def foo(a: int, **b: float):
        pass

    iparams = inspect.signature(foo).parameters
    collection = ArgumentCollection.from_callable(foo)

    assert len(collection) == 2

    assert collection[0].iparam == iparams["a"]
    assert collection[0].cparam.name == ("--a",)
    assert collection[0].hint is int
    assert collection[0].keys == ()
    assert collection[0].accepts_keywords is False

    assert collection[1].iparam == iparams["b"]
    assert collection[1].cparam.name == ("--[KEYWORD]",)
    assert collection[1].hint is Dict[str, float]
    assert collection[1].keys == ()
    assert collection[1].accepts_keywords is True


def test_argument_collection_var_keyword_match():
    def foo(a: int, **b: float):
        pass

    iparams = inspect.signature(foo).parameters
    collection = ArgumentCollection.from_callable(foo)

    argument, keys, _ = collection.match("--fizz")
    assert keys == ("fizz",)
    assert argument.iparam == iparams["b"]


@pytest.mark.parametrize(
    "args, expected",
    [
        ((("--foo",),), ("--foo",)),
        ((("--foo", "--bar"),), ("--foo", "--bar")),
        ((("--foo",), ("--bar",)), ("--bar",)),
        ((("--foo",), ("baz",)), ("--foo.baz",)),
        ((("--foo",), ("--bar", "baz")), ("--bar", "--foo.baz")),
        ((("--foo", "--bar"), ("baz",)), ("--foo.baz", "--bar.baz")),
        ((("*",), ("bar",)), ("--bar",)),
        ((("--foo", "*"), ("bar",)), ("--foo.bar", "--bar")),
        ((("--foo",), ("*",), ("bar",)), ("--foo.bar",)),
    ],
)
def test_resolve_parameter_name(args, expected):
    assert _resolve_parameter_name(*args) == expected


def test_resolve_groups_3():
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

    actual = _resolve_groups_3(build)
    assert actual == [Group("Flags"), Group("Other Flags"), Group("Inside Typed Dict")]


def test_argument_convert():
    argument = Argument(
        hint=List[int],
        tokens=[
            Token("doesn't matter", "42", source="test"),
            Token("doesn't matter", "70", source="test"),
        ],
    )
    assert argument.convert() == [42, 70]


def test_argument_convert_dict():
    def foo(bar: Dict[str, int]):
        pass

    collection = ArgumentCollection.from_callable(foo)

    assert len(collection) == 1
    argument = collection[0]

    # Sanity check the match method
    assert argument.match("--bar.buzz") == (("buzz",), None)

    argument.append(Token("--bar.fizz", "7", source="test", keys=("fizz",)))
    argument.append(Token("--bar.buzz", "12", source="test", keys=("buzz",)))

    assert argument.convert() == {"fizz": 7, "buzz": 12}


def test_argument_convert_var_keyword():
    def foo(**kwargs: int):
        pass

    collection = ArgumentCollection.from_callable(foo)

    assert len(collection) == 1
    argument = collection[0]

    # Sanity check the match method
    assert argument.match("--fizz") == (("fizz",), None)

    argument.append(Token("--fizz", "7", source="test", keys=("fizz",)))
    argument.append(Token("--buzz", "12", source="test", keys=("buzz",)))

    assert argument.convert() == {"fizz": 7, "buzz": 12}


def test_argument_convert_cparam_provided():
    def my_converter(type_, tokens):
        return f"my_converter_{tokens[0]}"

    argument = Argument(
        hint=str,
        tokens=[
            Token("doesn't matter", "my_value", source="test"),
        ],
        cparam=Parameter(
            converter=my_converter,
        ),
    )
    assert argument.convert() == "my_converter_my_value"
