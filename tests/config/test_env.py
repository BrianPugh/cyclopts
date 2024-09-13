import pytest

from cyclopts.argument import ArgumentCollection
from cyclopts.config import Env


@pytest.fixture
def apps():
    """App is only used as a dictionary in these tests."""
    return [{"function1": None}]


def test_config_env_default(apps, monkeypatch):
    def foo(bar: int):
        pass

    argument_collection = ArgumentCollection.from_callable(foo)

    monkeypatch.setenv("CYCLOPTS_TEST_APP_BAR", "100")
    monkeypatch.setenv("CYCLOPTS_TEST_APP_SOMETHING_ELSE", "100")
    Env("CYCLOPTS_TEST_APP_", command=False)(apps, (), argument_collection)

    assert len(argument_collection[0].tokens) == 1
    assert argument_collection[0].tokens[0].keyword == "CYCLOPTS_TEST_APP_BAR"
    assert argument_collection[0].tokens[0].value == "100"
    assert argument_collection[0].tokens[0].source == "env"
    assert argument_collection[0].tokens[0].index == 0
    assert argument_collection[0].tokens[0].keys == ()


def test_config_env_dict(apps, monkeypatch):
    def foo(bar_bar: dict):
        pass

    argument_collection = ArgumentCollection.from_callable(foo)

    monkeypatch.setenv("CYCLOPTS_TEST_APP_BAR_BAR_BUZZ", "100")
    monkeypatch.setenv("CYCLOPTS_TEST_APP_BAR_BAR_FIZZ", "200")

    Env("CYCLOPTS_TEST_APP_", command=False)(apps, (), argument_collection)

    assert len(argument_collection[0].tokens) == 2

    assert argument_collection[0].tokens[0].keyword == "CYCLOPTS_TEST_APP_BAR_BAR_BUZZ"
    assert argument_collection[0].tokens[0].value == "100"
    assert argument_collection[0].tokens[0].source == "env"
    assert argument_collection[0].tokens[0].index == 0
    assert argument_collection[0].tokens[0].keys == ("buzz",)

    assert argument_collection[0].tokens[1].keyword == "CYCLOPTS_TEST_APP_BAR_BAR_FIZZ"
    assert argument_collection[0].tokens[1].value == "200"
    assert argument_collection[0].tokens[1].source == "env"
    assert argument_collection[0].tokens[1].index == 0
    assert argument_collection[0].tokens[1].keys == ("fizz",)
