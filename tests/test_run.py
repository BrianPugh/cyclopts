from pytest import MonkeyPatch

from cyclopts import App, run


def test_run(monkeypatch: MonkeyPatch):
    def main(input: int) -> int:
        return input * 2

    class TestApp(App):
        def __call__(self, tokens=None, **kwargs):
            return super().__call__("2", **kwargs)

    monkeypatch.setitem(run.__globals__, "App", TestApp)

    assert run(main) == 4
