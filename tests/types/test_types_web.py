import pytest

from cyclopts import ValidationError
from cyclopts.types import URL, Email


def test_types_web_email(convert):
    convert(Email, "foo@bar.com")


def test_types_web_email_invalid(convert):
    with pytest.raises(ValidationError):
        convert(Email, "foo")


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
    ],
)
def test_types_url_invalid(convert, url):
    with pytest.raises(ValidationError):
        convert(URL, url)
