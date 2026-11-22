import pytest

from cyclopts import ValidationError
from cyclopts.types import URL, Email


def test_types_web_email(convert):
    convert(Email, "foo@bar.com")


@pytest.mark.parametrize(
    "tokens",
    [
        "foo",
        ["foo@bar.com\n"],  # a list keeps the trailing newline (a string is split by shlex)
    ],
)
def test_types_web_email_invalid(convert, tokens):
    with pytest.raises(ValidationError):
        convert(Email, tokens)


@pytest.mark.parametrize(
    "url",
    [
        "google.com",
        "www.google.com",
        "http://www.google.com",
        "https://www.google.com",
        "https://www.google.com:443",
        "https://www.google.com/foo/bar",
    ],
)
def test_types_url(convert, url):
    convert(URL, url)


@pytest.mark.parametrize(
    "url",
    [
        "foo",
        "bar.",
        "foo bar.com",
        ["https://example.com\n"],  # a list keeps the trailing newline (a string is split by shlex)
        ["https://example.com/path\n"],
    ],
)
def test_types_url_invalid(convert, url):
    with pytest.raises(ValidationError):
        convert(URL, url)
