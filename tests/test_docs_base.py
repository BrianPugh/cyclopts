"""Tests for cyclopts.docs.base helpers."""

from cyclopts.docs.base import apply_usage_name


def test_apply_usage_name_none_returns_chain_unchanged():
    chain = ["cli", "files", "cp"]
    assert apply_usage_name(chain, None) is chain


def test_apply_usage_name_empty_chain_returns_single_element_list():
    assert apply_usage_name([], "uv run cli") == ["uv run cli"]


def test_apply_usage_name_replaces_root_only():
    chain = ["cli", "files", "cp"]
    assert apply_usage_name(chain, "uv run cli") == ["uv run cli", "files", "cp"]


def test_apply_usage_name_does_not_mutate_input():
    chain = ["cli", "files"]
    apply_usage_name(chain, "uv run cli")
    assert chain == ["cli", "files"]


def test_apply_usage_name_empty_string_drops_root():
    assert apply_usage_name(["cli", "files"], "") == ["files"]
    assert apply_usage_name(["cli"], "") == []
    assert apply_usage_name([], "") == []
