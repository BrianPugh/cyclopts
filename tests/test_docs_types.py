"""Tests for cyclopts.docs.types module."""

from typing import get_args

import pytest

from cyclopts.docs.types import (
    FORMAT_ALIASES,
    CanonicalDocFormat,
    DocFormat,
    normalize_format,
)


def test_format_aliases_sync_with_docformat():
    """Test that all FORMAT_ALIASES keys are in DocFormat type."""
    # Get all literal values from DocFormat type
    doc_format_values = set(get_args(DocFormat))

    # Get all keys from FORMAT_ALIASES
    format_alias_keys = set(FORMAT_ALIASES.keys())

    # Ensure all FORMAT_ALIASES keys are in DocFormat
    assert (
        format_alias_keys == doc_format_values
    ), f"FORMAT_ALIASES keys {format_alias_keys} must match DocFormat values {doc_format_values}"


def test_format_aliases_values_are_canonical():
    """Test that all FORMAT_ALIASES values are valid canonical formats."""
    canonical_values = set(get_args(CanonicalDocFormat))

    for alias, canonical in FORMAT_ALIASES.items():
        assert (
            canonical in canonical_values
        ), f"FORMAT_ALIASES['{alias}'] = '{canonical}' is not a valid CanonicalDocFormat"


def test_common_suffixes_have_format_aliases():
    """Test that common file suffixes have corresponding format aliases."""
    # Common suffixes that should work
    common_suffixes = ["md", "markdown", "html", "htm", "rst", "rest"]

    for suffix in common_suffixes:
        assert suffix in FORMAT_ALIASES, f"Common suffix '{suffix}' should have a format alias"


def test_canonical_formats_have_identity_mapping():
    """Test that canonical formats map to themselves in FORMAT_ALIASES."""
    canonical_values = get_args(CanonicalDocFormat)

    for canonical in canonical_values:
        assert canonical in FORMAT_ALIASES, f"Canonical format '{canonical}' should be in FORMAT_ALIASES"
        assert FORMAT_ALIASES[canonical] == canonical, f"Canonical format '{canonical}' should map to itself"


def test_file_suffix_handling():
    """Test that file suffixes work correctly with period stripping and format inference."""
    # Test cases for common file extensions
    test_cases = [
        (".md", "md", "markdown"),
        (".markdown", "markdown", "markdown"),
        (".html", "html", "html"),
        (".htm", "htm", "html"),
        (".rst", "rst", "rst"),
        (".rest", "rest", "rst"),
    ]

    for suffix_with_period, suffix_key, expected_canonical in test_cases:
        # Test period stripping mechanism
        key = suffix_with_period.lstrip(".")
        assert key == suffix_key, f"Period stripping failed for '{suffix_with_period}'"

        # Test that the key exists in FORMAT_ALIASES
        assert key in FORMAT_ALIASES, f"Key '{key}' should be in FORMAT_ALIASES"

        # Test that it maps to the correct canonical format
        assert (
            FORMAT_ALIASES[key] == expected_canonical
        ), f"FORMAT_ALIASES['{key}'] should be '{expected_canonical}', got '{FORMAT_ALIASES[key]}'"

        # Test that this is consistent with file suffix inference
        # (simulating how the system would infer format from a file extension)
        inferred_format = FORMAT_ALIASES.get(key)
        assert (
            inferred_format == expected_canonical
        ), f"Suffix '{suffix_with_period}' should infer format '{expected_canonical}', got '{inferred_format}'"


def test_normalize_format_with_all_aliases():
    """Test normalize_format works with all defined aliases."""
    for alias, expected_canonical in FORMAT_ALIASES.items():
        # Test lowercase
        assert normalize_format(alias) == expected_canonical

        # Test uppercase
        assert normalize_format(alias.upper()) == expected_canonical

        # Test mixed case
        if len(alias) > 1:
            mixed_case = alias[0].upper() + alias[1:].lower()
            assert normalize_format(mixed_case) == expected_canonical


def test_normalize_format_invalid():
    """Test normalize_format raises ValueError for invalid formats."""
    with pytest.raises(ValueError, match='Unsupported format "invalid"'):
        normalize_format("invalid")

    with pytest.raises(ValueError, match='Unsupported format "pdf"'):
        normalize_format("pdf")


def test_all_doc_format_values_have_normalization():
    """Test that all DocFormat literal values can be normalized."""
    doc_format_values = get_args(DocFormat)

    for format_value in doc_format_values:
        # Should not raise an exception
        result = normalize_format(format_value)
        # Result should be a canonical format
        assert result in get_args(
            CanonicalDocFormat
        ), f"normalize_format('{format_value}') = '{result}' is not a CanonicalDocFormat"
