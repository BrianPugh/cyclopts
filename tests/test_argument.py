import inspect
from typing import Dict, TypedDict

import pytest

from cyclopts.argument import Argument, ArgumentCollection
from cyclopts.parameter import Parameter


def test_argument_collection_no_annotation_no_default():
    def foo(a, b):
        pass

    iparams = inspect.signature(foo).parameters
    collection = ArgumentCollection.from_callable(foo)

    assert len(collection) == 2

    assert collection[0].iparam == iparams["a"]
    assert collection[0].hint == str
    assert collection[0].keys == ()
    assert collection[0].accepts_keywords == False

    assert collection[1].iparam == iparams["b"]
    assert collection[1].hint == str
    assert collection[1].keys == ()
    assert collection[1].accepts_keywords == False


def test_argument_collection_no_annotation_default():
    def foo(a="foo", b=100):
        pass

    iparams = inspect.signature(foo).parameters
    collection = ArgumentCollection.from_callable(foo)

    assert len(collection) == 2

    assert collection[0].iparam == iparams["a"]
    assert collection[0].hint == str
    assert collection[0].keys == ()
    assert collection[0].accepts_keywords == False

    assert collection[1].iparam == iparams["b"]
    assert collection[1].hint == int
    assert collection[1].keys == ()
    assert collection[1].accepts_keywords == False


def test_argument_collection_basic_annotation():
    def foo(a: str, b: int):
        pass

    iparams = inspect.signature(foo).parameters
    collection = ArgumentCollection.from_callable(foo)

    assert len(collection) == 2

    assert collection[0].iparam == iparams["a"]
    assert collection[0].hint == str
    assert collection[0].keys == ()
    assert collection[0].accepts_keywords == False

    assert collection[1].iparam == iparams["b"]
    assert collection[1].hint == int
    assert collection[1].keys == ()
    assert collection[1].accepts_keywords == False


@pytest.mark.parametrize("type_", [dict, Dict])
def test_argument_collection_bare_dict(type_):
    def foo(a: type_, b: int):
        pass

    iparams = inspect.signature(foo).parameters
    collection = ArgumentCollection.from_callable(foo)

    assert len(collection) == 2

    assert collection[0].iparam == iparams["a"]
    assert collection[0].hint == type_
    assert collection[0].keys == ()
    assert collection[0].accepts_keywords == True
    assert collection[0].accepts_arbitrary_keywords == True

    assert collection[1].iparam == iparams["b"]
    assert collection[1].hint == int
    assert collection[1].keys == ()
    assert collection[1].accepts_keywords == False


def test_argument_collection_typing_dict():
    def foo(a: Dict[str, int], b: int):
        pass

    iparams = inspect.signature(foo).parameters
    collection = ArgumentCollection.from_callable(foo)

    assert len(collection) == 2

    assert collection[0].iparam == iparams["a"]
    assert collection[0].hint == Dict[str, int]
    assert collection[0].keys == ()
    assert collection[0].accepts_keywords == True
    assert collection[0].accepts_arbitrary_keywords == True

    assert collection[1].iparam == iparams["b"]
    assert collection[1].hint == int
    assert collection[1].keys == ()
    assert collection[1].accepts_keywords == False


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
    assert collection[0].hint == str
    assert collection[0].keys == ("foo",)
    assert collection[0].accepts_keywords == False

    assert collection[1].iparam == iparams["a"]
    assert collection[1].hint == int
    assert collection[1].keys == ("bar",)
    assert collection[1].accepts_keywords == False

    assert collection[2].iparam == iparams["b"]
    assert collection[2].hint == int
    assert collection[2].keys == ()
    assert collection[2].accepts_keywords == False
