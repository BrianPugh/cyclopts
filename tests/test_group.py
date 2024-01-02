from cyclopts.group import Group


def test_group_equality():
    """Group equality is SOLELY determined by name."""
    assert Group("foo") == Group("foo")
    assert Group("foo") != Group("bar")
    assert Group("foo") in [Group("foo"), Group("bar")]
