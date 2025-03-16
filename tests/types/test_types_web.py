import pytest

from cyclopts import ValidationError
from cyclopts.types import Email


def test_types_web_email(convert):
    convert(Email, "foo@bar.com")


def test_types_web_email_invalid(convert):
    with pytest.raises(ValidationError):
        convert(Email, "foo")
