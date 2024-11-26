from typing import NewType


def test_new_type_str(app, assert_parse_args):
    CustomStr = NewType("CustomStr", str)

    @app.default
    def main(a: CustomStr):
        pass

    assert_parse_args(main, "foo", CustomStr("foo"))
