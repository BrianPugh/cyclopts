from textwrap import dedent

from cyclopts.config._json import Json


def test_config_json(tmp_path):
    fn = tmp_path / "test.yaml"
    fn.write_text(
        dedent(
            """\
            {
                "foo": {
                    "key1": "foo1",
                    "key2": "foo2",
                    "function1": {
                        "key1": "bar1",
                        "key2": "bar2"
                    }
                }
            }
            """
        )
    )
    config = Json(fn)
    assert config.config == {
        "foo": {
            "key1": "foo1",
            "key2": "foo2",
            "function1": {
                "key1": "bar1",
                "key2": "bar2",
            },
        }
    }
