from __future__ import annotations


def test_future_annotations_basic(app, assert_parse_args):
    @app.default
    def default(value: str):
        pass

    assert_parse_args(default, "foo", "foo")


def test_future_annotations_dataclass(app, assert_parse_args):
    """
    https://github.com/BrianPugh/cyclopts/issues/352
    """
    pass
