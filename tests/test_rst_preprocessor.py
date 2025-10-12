"""Tests for RST preprocessor functionality."""

from textwrap import dedent

from cyclopts.help.rst_preprocessor import (
    _gather_indented_block,
    _skip_indented_block,
    process_sphinx_directives,
)


def test_process_sphinx_directives_empty_content():
    """Test that empty/None content is handled gracefully."""
    assert process_sphinx_directives(None) == ""
    assert process_sphinx_directives("") == ""
    assert process_sphinx_directives("   ") == ""


def test_process_sphinx_directives_malformed_directive():
    """Test that malformed directives are handled gracefully."""
    text = dedent("""\
        Some text

        .. not-a-proper-directive
            Content here

        More text
    """)
    result = process_sphinx_directives(text)
    assert "Some text" in result
    assert "More text" in result


def test_process_sphinx_directives_unknown_directive():
    """Test that unknown directives are skipped."""
    text = dedent("""\
        Some text

        .. unknown_directive:: arg
            This content should be skipped

        More text
    """)
    result = process_sphinx_directives(text)
    assert "Some text" in result
    assert "More text" in result
    assert "unknown_directive" not in result
    assert "This content should be skipped" not in result


def test_skip_indented_block():
    """Test _skip_indented_block helper function."""
    lines = [
        "base line",
        "    indented line 1",
        "    indented line 2",
        "        more indented",
        "",
        "    indented line 3",
        "next base line",
    ]
    result_index = _skip_indented_block(lines, 1, 0)
    assert result_index == 6
    assert lines[result_index] == "next base line"


def test_skip_indented_block_end_of_file():
    """Test _skip_indented_block when reaching end of file."""
    lines = [
        "base line",
        "    indented line 1",
        "    indented line 2",
    ]
    result_index = _skip_indented_block(lines, 1, 0)
    assert result_index == 3


def test_gather_indented_block():
    """Test _gather_indented_block helper function preserves paragraph structure."""
    lines = [
        "base line",
        "    indented line 1",
        "    indented line 2",
        "        more indented",
        "",
        "    indented line 3",
        "next base line",
    ]
    content, result_index = _gather_indented_block(lines, 1, 0)
    assert content == [
        "indented line 1 indented line 2",
        "    more indented",
        "indented line 3",
    ]
    assert result_index == 6


def test_gather_indented_block_empty():
    """Test _gather_indented_block with no indented content."""
    lines = [
        "base line",
        "next base line",
    ]
    content, result_index = _gather_indented_block(lines, 1, 0)
    assert content == []
    assert result_index == 1


def test_gather_indented_block_end_of_file():
    """Test _gather_indented_block when reaching end of file."""
    lines = [
        "base line",
        "    indented line 1",
        "    indented line 2",
    ]
    content, result_index = _gather_indented_block(lines, 1, 0)
    assert content == ["indented line 1 indented line 2"]
    assert result_index == 3


def test_process_sphinx_directives_with_options():
    """Test that directive options are ignored (not processed)."""
    text = dedent("""\
        Some text

        .. versionadded:: 1.0
           :platform: Unix
           :synopsis: Added Unix support

        More text
    """)
    result = process_sphinx_directives(text)
    assert "Some text" in result
    assert "More text" in result
    assert "[Added in v1.0]" in result


def test_process_sphinx_directives_with_list_content(normalize_trailing_whitespace):
    """Test directives containing list structures."""
    text = dedent("""\
        Some text

        .. note::
            This note contains a list:

            - Item 1
            - Item 2
            - Item 3

        More text
    """)
    result = process_sphinx_directives(text)
    expected = dedent("""\
        Some text

        Note: This note contains a list:

        - Item 1
        - Item 2
        - Item 3
        More text""")
    assert normalize_trailing_whitespace(result) == normalize_trailing_whitespace(expected)


def test_process_sphinx_directives_non_ascii_content(normalize_trailing_whitespace):
    """Test directives with non-ASCII characters."""
    text = dedent("""\
        Some text

        .. versionadded:: 2.0β

        .. note:: 这是中文内容 / Contenu français / Содержание

        .. deprecated:: 3.0α
            Use alternative 日本語

        More text
    """)
    result = process_sphinx_directives(text)
    expected = dedent("""\
        Some text


        Note: 这是中文内容 / Contenu français / Содержание
        More text [Added in v2.0β] [⚠ Deprecated in v3.0α] Use alternative 日本語""")
    assert normalize_trailing_whitespace(result) == normalize_trailing_whitespace(expected)


def test_process_sphinx_directives_nested_directives(normalize_trailing_whitespace):
    """Test directives that contain other directives (should handle gracefully)."""
    text = dedent("""\
        Some text

        .. note::
            This is a note.

            .. warning::
                Nested warning inside note.

        More text
    """)
    result = process_sphinx_directives(text)
    expected = dedent("""\
        Some text

        Note: This is a note.

        .. warning::

            Nested warning inside note.
        More text""")
    assert normalize_trailing_whitespace(result) == normalize_trailing_whitespace(expected)


def test_gather_indented_block_with_multiple_paragraphs():
    """Test _gather_indented_block with multiple paragraphs separated by blank lines."""
    lines = [
        "base line",
        "    First paragraph line 1",
        "    First paragraph line 2",
        "",
        "    Second paragraph line 1",
        "    Second paragraph line 2",
        "",
        "    Third paragraph",
        "next base line",
    ]
    content, result_index = _gather_indented_block(lines, 1, 0)
    assert content == [
        "First paragraph line 1 First paragraph line 2",
        "Second paragraph line 1 Second paragraph line 2",
        "Third paragraph",
    ]
    assert result_index == 8


def test_process_sphinx_directives_code_block_in_directive(normalize_trailing_whitespace):
    """Test directives containing code block-like content."""
    text = dedent("""\
        Some text

        .. note::
            Use this function like:

                result = my_function(arg)
                print(result)

            Remember to check the output.

        More text
    """)
    result = process_sphinx_directives(text)
    expected = dedent("""\
        Some text

        Note: Use this function like:

            result = my_function(arg)
            print(result)

        Remember to check the output.
        More text""")
    assert normalize_trailing_whitespace(result) == normalize_trailing_whitespace(expected)


def test_process_sphinx_directives_version_with_punctuation(normalize_trailing_whitespace):
    """Test version numbers with various punctuation."""
    text = dedent("""\
        .. versionadded:: 1.2.3

        .. versionchanged:: 2.0.0-rc1

        .. deprecated:: 3.0.0a1
    """)
    result = process_sphinx_directives(text)
    expected = "[Added in v1.2.3] [Changed in v2.0.0-rc1] [⚠ Deprecated in v3.0.0a1]"
    assert normalize_trailing_whitespace(result) == normalize_trailing_whitespace(expected)
