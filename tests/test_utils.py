import pytest

from cyclopts.utils import Sentinel, _pascal_to_snake, grouper


def test_grouper():
    assert [(1,), (2,), (3,), (4,)] == list(grouper([1, 2, 3, 4], 1))
    assert [(1, 2), (3, 4)] == list(grouper([1, 2, 3, 4], 2))
    assert [(1, 2, 3, 4)] == list(grouper([1, 2, 3, 4], 4))

    with pytest.raises(ValueError):
        grouper([1, 2, 3, 4], 3)


def test_sentinel():
    class SENTINEL_VALUE(Sentinel):  # noqa: N801
        pass

    assert str(SENTINEL_VALUE) == "<SENTINEL_VALUE>"
    assert bool(SENTINEL_VALUE) is False


@pytest.mark.parametrize(
    "input_str,expected",
    [
        # Basic PascalCase
        ("PascalCase", "pascal_case"),
        ("MyClass", "my_class"),
        # Single word
        ("Class", "class"),
        ("class", "class"),
        # Already snake_case
        ("snake_case", "snake_case"),
        # Multiple consecutive uppercase letters followed by lowercase
        ("HTTPServer", "http_server"),
        ("XMLParser", "xml_parser"),
        ("HTMLElement", "html_element"),
        # Numbers - NO separator between lowercase and digits (avoid cmd1 -> cmd_1 breakage)
        ("cmd1", "cmd1"),
        ("cmd2", "cmd2"),
        ("Test123", "test123"),
        ("version2", "version2"),
        ("Test123ABC", "test123_abc"),
        # All uppercase followed by numbers (no separator added)
        ("ABC123", "abc123"),
        # Uppercase letters followed by numbers, then more uppercase
        ("ABC123DEF", "abc123_def"),
        # Digits followed by uppercase (separator added)
        ("test2Class", "test2_class"),
        ("version2Config", "version2_config"),
        # Mixed cases
        ("getUserID", "get_user_id"),
        ("getHTTPResponseCode", "get_http_response_code"),
        # Edge cases
        ("", ""),
        ("A", "a"),
        ("AB", "ab"),
        ("ABC", "abc"),
        ("AbC", "ab_c"),
        # Common identifiers that should NOT be split
        ("username", "username"),
        ("filepath", "filepath"),
        ("ageinyears", "ageinyears"),
    ],
)
def test_pascal_to_snake(input_str, expected):
    """Test PascalCase to snake_case conversion.

    Converts PascalCase identifiers to snake_case format by inserting underscores
    and converting to lowercase:
    - Between consecutive uppercase letters and an uppercase+lowercase sequence (HTTPServer -> http_server)
    - Between a lowercase letter and an uppercase letter (myClass -> my_class)
    - Between a digit and an uppercase letter (test2Class -> test2_class)
    - Does NOT insert underscore between lowercase letter and digit (cmd1 stays cmd1)
    - Converts all characters to lowercase
    """
    assert _pascal_to_snake(input_str) == expected
