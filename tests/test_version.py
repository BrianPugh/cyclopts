def test_version_print_console_from_init(app, console):
    app.console = console

    with console.capture() as capture:
        app.version_print()

    assert "0.0.0\n" == capture.get()


def test_version_print_console_from_method(app, console):
    with console.capture() as capture:
        app.version_print(console)

    assert "0.0.0\n" == capture.get()


def test_version_print_console_none(app, console):
    app.version = None
    with console.capture() as capture:
        app.version_print(console)

    assert "0.0.0\n" == capture.get()


def test_version_print_custom_string(app, console):
    """The asterisks also test to make sure the proper help_format is being used."""
    app.version = "**foo**"

    with console.capture() as capture:
        app.version_print(console)

    assert "foo\n" == capture.get()


def test_version_print_custom_callable(app, console):
    def my_version():
        return "**foo**"

    app.version = my_version

    with console.capture() as capture:
        app.version_print(console)

    assert "foo\n" == capture.get()


def test_version_print_help_format_fallback(app, console):
    """If no explicit version_format is provided, we should fallback to help_format."""
    app.help_format = "rich"
    app.version = "[red]foo[/red]"

    with console.capture() as capture:
        app.version_print(console)

    assert "foo\n" == capture.get()


def test_version_print_help_format_override(app, console):
    """If version_format is provided, help_format should not be used for version."""
    app.help_format = "plain"
    app.version_format = "rich"
    app.version = "[red]foo[/red]"

    with console.capture() as capture:
        app.version_print(console)

    assert "foo\n" == capture.get()
