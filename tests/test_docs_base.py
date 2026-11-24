"""Tests for cyclopts.docs.base helpers."""

from cyclopts.docs.base import usage_display_chain


def test_usage_display_chain_none_returns_chain_unchanged():
    chain = ["cli", "files", "cp"]
    assert usage_display_chain(chain, None) is chain


def test_usage_display_chain_empty_chain_returns_single_element_list():
    assert usage_display_chain([], "uv run cli") == ["uv run cli"]


def test_usage_display_chain_replaces_root_only():
    chain = ["cli", "files", "cp"]
    assert usage_display_chain(chain, "uv run cli") == ["uv run cli", "files", "cp"]


def test_usage_display_chain_does_not_mutate_input():
    chain = ["cli", "files"]
    usage_display_chain(chain, "uv run cli")
    assert chain == ["cli", "files"]


def test_usage_display_chain_empty_string_drops_root():
    assert usage_display_chain(["cli", "files"], "") == ["files"]
    assert usage_display_chain(["cli"], "") == []
    assert usage_display_chain([], "") == []
