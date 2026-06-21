import inspect
from collections import namedtuple
from dataclasses import dataclass
from typing import Annotated, Dict, Optional, TypedDict, Union  # noqa: UP035

import pytest

from cyclopts.annotations import is_typeddict
from cyclopts.argument import (
    Argument,
    ArgumentCollection,
    _resolve_groups_from_callable,
    resolve_parameter_name,
)
from cyclopts.group import Group
from cyclopts.parameter import Parameter
from cyclopts.token import Token
from cyclopts.utils import UNSET

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


@pytest.mark.parametrize("type_", [dict, Dict])  # noqa: UP006
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
    def foo(a: dict[str, int], b: int):
        pass

    collection = ArgumentCollection._from_callable(foo)

    assert len(collection) == 2

    assert collection[0].field_info.name == "a"
    assert collection[0].hint == dict[str, int]
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


def test_argument_collection_filter_by_has_tree_tokens():
    """``has_tree_tokens`` must be tree-aware, unlike ``has_tokens``.

    A composite whose only tokens live on a child must be matched by
    ``has_tree_tokens=True`` even though it has no immediate tokens of its own.
    """

    class Inner(TypedDict):
        fizz: float
        buzz: int

    def foo(a: Inner):
        pass

    collection = ArgumentCollection._from_callable(foo)

    leaf = collection["--a.fizz"]
    leaf.append(Token(value="1.5", source="test"))

    root = collection["--a"]
    assert not root.tokens  # no immediate tokens
    assert root.has_tokens  # but tree-aware: a child has a token

    has_tree_tokens = collection.filter_by(has_tree_tokens=True)
    assert root in has_tree_tokens
    assert leaf in has_tree_tokens

    # ``has_tokens`` (immediate) must NOT match the root.
    assert root not in collection.filter_by(has_tokens=True)


def _names(collection):
    return [argument.name for argument in collection]


def test_filter_by_missing_simple_leaf():
    def foo(a: int, b: int = 5):
        pass

    collection = ArgumentCollection._from_callable(foo)
    # Nothing supplied: required ``a`` is missing, defaulted ``b`` is not.
    assert _names(collection.filter_by(missing=True)) == ["--a"]

    collection["--a"].append(Token(value="1", source="test"))
    assert _names(collection.filter_by(missing=True)) == []


def test_filter_by_missing_partial_composite():
    """The headline case: a partially-supplied optional composite reports its absent field."""

    @Parameter(name="*")
    @dataclass
    class TimeRange:
        start: int
        end: int

    def cli(data_source: str, /, *, time_range: Optional[TimeRange] = None):
        pass

    collection = ArgumentCollection._from_callable(cli)
    collection["--start"].append(Token(keyword="--start", value="1", source="test"))

    assert _names(collection.filter_by(missing=True)) == ["DATA_SOURCE", "--end"]


def test_filter_by_missing_optional_composite_untouched():
    @Parameter(name="*")
    @dataclass
    class TimeRange:
        start: int
        end: int

    def cli(data_source: str, /, *, time_range: Optional[TimeRange] = None):
        pass

    collection = ArgumentCollection._from_callable(cli)
    # Untouched optional composite contributes nothing.
    assert _names(collection.filter_by(missing=True)) == ["DATA_SOURCE"]


def test_filter_by_missing_required_composite_omitted():
    @Parameter(name="*")
    @dataclass
    class TimeRange:
        start: int
        end: int

    def cli(*, time_range: TimeRange):
        pass

    collection = ArgumentCollection._from_callable(cli)
    # Fully-omitted *required* composite surfaces all of its required leaves.
    assert _names(collection.filter_by(missing=True)) == ["--start", "--end"]


def test_filter_by_missing_defaulted_subfield_excluded():
    @Parameter(name="*")
    @dataclass
    class TimeRange:
        start: int
        end: int = 5

    def cli(*, time_range: Optional[TimeRange] = None):
        pass

    collection = ArgumentCollection._from_callable(cli)
    collection["--start"].append(Token(keyword="--start", value="1", source="test"))
    # ``end`` has a default, so it is not missing.
    assert _names(collection.filter_by(missing=True)) == []


def test_filter_by_missing_nested_composite():
    @dataclass
    class Inner:
        a: int
        b: int

    @dataclass
    class Outer:
        inner: Inner
        name: str

    def cli(o: Outer):
        pass

    collection = ArgumentCollection._from_callable(cli)
    collection["--o.inner.a"].append(Token(value="1", source="test"))
    # Recurses into the activated inner composite to find ``b``.
    assert _names(collection.filter_by(missing=True)) == ["--o.inner.b", "--o.name"]


def test_filter_by_missing_typeddict():
    class Inner(TypedDict):
        x: int
        y: int

    def cli(d: Inner):
        pass

    collection = ArgumentCollection._from_callable(cli)
    collection["--d.x"].append(Token(value="1", source="test"))
    assert _names(collection.filter_by(missing=True)) == ["--d.y"]


def test_filter_by_missing_pydantic():
    import pydantic

    @Parameter(name="*")
    class TimeRange(pydantic.BaseModel):
        start: int
        end: int

    def cli(*, time_range: Optional[TimeRange] = None):
        pass

    collection = ArgumentCollection._from_callable(cli)
    collection["--start"].append(Token(keyword="--start", value="1", source="test"))
    assert _names(collection.filter_by(missing=True)) == ["--end"]


def test_filter_by_missing_attrs():
    import attrs

    @Parameter(name="*")
    @attrs.define
    class TimeRange:
        start: int
        end: int

    def cli(*, time_range: Optional[TimeRange] = None):
        pass

    collection = ArgumentCollection._from_callable(cli)
    collection["--start"].append(Token(keyword="--start", value="1", source="test"))
    assert _names(collection.filter_by(missing=True)) == ["--end"]


def test_filter_by_missing_false_is_complement():
    def foo(a: int, b: int = 5):
        pass

    collection = ArgumentCollection._from_callable(foo)
    missing = collection.filter_by(missing=True)
    not_missing = collection.filter_by(missing=False)
    assert _names(missing) == ["--a"]
    assert _names(not_missing) == ["--b"]


def test_filter_by_missing_composes_with_other_filters():
    @Parameter(name="*")
    @dataclass
    class TimeRange:
        start: int
        end: int

    def cli(data_source: str, /, *, time_range: Optional[TimeRange] = None):
        pass

    collection = ArgumentCollection._from_callable(cli)
    collection["--start"].append(Token(keyword="--start", value="1", source="test"))
    # ``missing`` intersects with the other (AND) filters.
    result = collection.filter_by(missing=True, kind=inspect.Parameter.KEYWORD_ONLY)
    assert _names(result) == ["--end"]


def test_filter_by_missing_end_to_end_prompt():
    """The ``while`` recipe from the docs, driven by an activated-on-CLI composite.

    ``--start`` on the CLI activates the optional composite, so ``--end`` becomes a
    conditionally-required missing field that the static ``Argument.required`` can't see.
    """
    from cyclopts import App

    @Parameter(name="*")
    @dataclass
    class TimeRange:
        start: int
        end: int

    answers = iter(["my_source", "2"])

    def prompt_for_missing(app, commands, arguments):
        prompted = []
        while missing := arguments.filter_by(missing=True):
            argument = missing[0]
            prompted.append(argument.name)
            argument.tokens.append(Token(keyword=argument.name, value=next(answers), source="interactive"))
        assert prompted == ["DATA_SOURCE", "--end"]

    app = App(name="cli", config=prompt_for_missing, result_action="return_value")

    captured = {}

    @app.command
    def run(data_source: str, /, *, time_range: Optional[TimeRange] = None):
        captured["data_source"] = data_source
        captured["time_range"] = time_range

    app(["run", "--start", "1"], exit_on_error=False)
    assert captured == {"data_source": "my_source", "time_range": TimeRange(start=1, end=2)}


def test_filter_by_missing_multi_branch_union_active_branch():
    """Supplying one Union member's field must not mark a sibling member's fields missing."""

    @dataclass
    class TimeRange:
        start: int
        end: int

    @dataclass
    class Live:
        live: bool

    def cli(*, time_period: Union[TimeRange, Live]):
        pass

    # Activate the ``Live`` branch -> nothing missing (it's fully supplied).
    collection = ArgumentCollection._from_callable(cli)
    collection["--time-period.live"].append(Token(value="true", source="test"))
    assert _names(collection.filter_by(missing=True)) == []

    # Activate the ``TimeRange`` branch with only ``start`` -> only ``end`` is missing,
    # *not* the ``Live`` branch's ``live``.
    collection = ArgumentCollection._from_callable(cli)
    collection["--time-period.start"].append(Token(value="1", source="test"))
    assert _names(collection.filter_by(missing=True)) == ["--time-period.end"]


def test_filter_by_missing_multi_branch_union_untouched():
    """A fully-omitted Union composite can't pick a branch, so it reports nothing."""

    @dataclass
    class TimeRange:
        start: int
        end: int

    @dataclass
    class Live:
        live: bool

    def cli(*, time_period: Union[TimeRange, Live]):
        pass

    collection = ArgumentCollection._from_callable(cli)
    assert _names(collection.filter_by(missing=True)) == []


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
    assert resolve_parameter_name(*args) == expected


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
        user: User | None = None,
    ):
        pass

    actual = _resolve_groups_from_callable(build)
    assert actual == [
        Group.create_default_parameters(),
        Group("Flags"),
        Group("Other Flags"),
        Group("Inside Typed Dict"),
    ]


def test_argument_convert():
    argument = Argument(
        hint=list[int],
        tokens=[
            Token(value="42", source="test"),
            Token(value="70", source="test"),
        ],
    )
    assert argument.convert() == [42, 70]


def test_argument_convert_dict():
    def foo(bar: dict[str, int]):
        pass

    collection = ArgumentCollection._from_callable(foo)

    assert len(collection) == 1
    argument = collection[0]

    # Sanity check the match method
    assert argument.match("--bar.buzz") == (("buzz",), UNSET)

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
    assert argument.match("--fizz") == (("fizz",), UNSET)

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
        dict,
        dict[str, int],
    ],
)
def test_is_typed_dict_false(hint):
    assert not is_typeddict(hint)


def test_assemble_argument_collection_no_default_command():
    from cyclopts import App

    app = App()

    @app.command
    def foo(loops: int):
        pass

    with pytest.raises(ValueError, match="Cannot assemble argument collection: no default command is registered"):
        app.assemble_argument_collection()


def test_argument_collection_getitem_by_string():
    def foo(alpha: int, beta: str):
        pass

    collection = ArgumentCollection._from_callable(foo)

    assert collection["--alpha"].field_info.name == "alpha"
    assert collection["--alpha"].hint is int
    assert collection["--beta"].field_info.name == "beta"
    assert collection["--beta"].hint is str


@pytest.mark.parametrize(
    "slice_obj, expected_names",
    [
        (slice(1, 3), ["beta", "gamma"]),
        (slice(5, 10), []),
        (slice(-2, None), ["beta", "gamma"]),
    ],
)
def test_argument_collection_getitem_by_slice(slice_obj, expected_names):
    def foo(alpha: int, beta: str, gamma: float):
        pass

    collection = ArgumentCollection._from_callable(foo)
    subset = collection[slice_obj]
    assert isinstance(subset, list)
    assert [arg.field_info.name for arg in subset] == expected_names


def test_argument_collection_getitem_by_int():
    def foo(alpha: int, beta: str, gamma: float):
        pass

    collection = ArgumentCollection._from_callable(foo)

    assert collection[0].field_info.name == "alpha"
    assert collection[1].field_info.name == "beta"
    assert collection[2].field_info.name == "gamma"


@pytest.mark.parametrize(
    "term, default, expected",
    [
        ("--nonexistent", "my_default", "my_default"),
        (10, "my_default", "my_default"),
    ],
)
def test_argument_collection_get_with_default(term, default, expected):
    def foo(alpha: int, beta: str):
        pass

    collection = ArgumentCollection._from_callable(foo)
    assert collection.get(term, default=default) == expected


@pytest.mark.parametrize(
    "term, exception_type, match_pattern",
    [
        ("--nonexistent", KeyError, "No such Argument: --nonexistent"),
        (10, IndexError, "Argument index 10 out of range"),
    ],
)
def test_argument_collection_get_not_found(term, exception_type, match_pattern):
    def foo(alpha: int, beta: str):
        pass

    collection = ArgumentCollection._from_callable(foo)
    with pytest.raises(exception_type, match=match_pattern):
        collection.get(term)


def test_argument_collection_getitem_not_found():
    def foo(alpha: int, beta: str):
        pass

    collection = ArgumentCollection._from_callable(foo)

    with pytest.raises(KeyError, match="No such Argument: --nonexistent"):
        _ = collection["--nonexistent"]

    with pytest.raises(IndexError):
        _ = collection[10]


def test_argument_collection_contains_with_string():
    """Test that 'in' operator works with string argument names."""

    def foo(alpha: int, beta: str):
        pass

    collection = ArgumentCollection._from_callable(foo)

    # Test with full option names
    assert "--alpha" in collection
    assert "--beta" in collection

    # Test with non-existent option
    assert "--nonexistent" not in collection
    assert "--gamma" not in collection


def test_argument_collection_contains_with_alias():
    """Test that 'in' operator works with argument aliases."""

    def foo(
        alpha: Annotated[int, Parameter(name="--foo", alias="-f")],
        beta: Annotated[str, Parameter(name="--bar", alias=("-b", "--baz"))],
    ):
        pass

    collection = ArgumentCollection._from_callable(foo)

    # Test with primary names
    assert "--foo" in collection
    assert "--bar" in collection

    # Test with aliases
    assert "-f" in collection
    assert "-b" in collection
    assert "--baz" in collection

    # Test that original parameter names don't match
    assert "--alpha" not in collection
    assert "--beta" not in collection


def test_argument_collection_contains_with_object():
    """Test that 'in' operator works with Argument objects (backward compatibility)."""

    def foo(alpha: int, beta: str):
        pass

    collection = ArgumentCollection._from_callable(foo)

    # Test with actual Argument objects from the collection
    assert collection[0] in collection
    assert collection[1] in collection

    # Test with a new Argument object not in the collection
    new_arg = Argument(parameter=Parameter(name="--gamma"), hint=float)
    assert new_arg not in collection


def test_argument_collection_contains_with_filtered():
    """Test that 'in' operator works with filtered collections (common validator pattern)."""
    collection = ArgumentCollection(
        [
            Argument(
                tokens=[Token(keyword="--foo", value="100", source="test")],
                parameter=Parameter(name="--foo"),
                value=100,
            ),
            Argument(
                parameter=Parameter(name="--bar"),
            ),
            Argument(
                tokens=[Token(keyword="--baz", value="text", source="test")],
                parameter=Parameter(name="--baz"),
                value="text",
            ),
        ]
    )

    # All arguments exist in the full collection
    assert "--foo" in collection
    assert "--bar" in collection
    assert "--baz" in collection

    # Only arguments with values exist in the filtered collection
    populated = collection.filter_by(value_set=True)
    assert "--foo" in populated
    assert "--bar" not in populated  # Has no value
    assert "--baz" in populated


def test_argument_collection_contains_with_keys():
    """Test that 'in' operator works with nested argument keys (dataclass fields)."""
    from dataclasses import dataclass

    @dataclass
    class Config:
        host: str
        port: int

    def foo(config: Config):
        pass

    collection = ArgumentCollection._from_callable(foo)

    # Check for nested fields
    assert "--config.host" in collection
    assert "--config.port" in collection

    # Check that parent also exists (for accepting dict/JSON)
    assert "--config" in collection

    # Check non-existent nested fields
    assert "--config.username" not in collection
