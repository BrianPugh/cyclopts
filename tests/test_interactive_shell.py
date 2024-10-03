def test_interactive_shell(app, mocker, console):
    mocker.patch(
        "cyclopts.core.input",
        side_effect=[
            "foo 1 2 3",
            "bad-command 123",
            "",
            "bar bloop",
            "quit",
        ],
    )

    foo_called, bar_called = 0, 0

    @app.command
    def foo(a: int, b: int, c: int):
        nonlocal foo_called
        foo_called += 1

    @app.command
    def bar(token):
        nonlocal bar_called
        bar_called += 1

    with console.capture() as capture:
        app.interactive_shell(console=console)

    actual = capture.get()

    assert foo_called == 1
    assert bar_called == 1

    assert actual == (
        "╭─ Error ────────────────────────────────────────────────────────────╮\n"
        '│ Unknown command "bad-command".                                     │\n'
        "╰────────────────────────────────────────────────────────────────────╯\n"
    )
