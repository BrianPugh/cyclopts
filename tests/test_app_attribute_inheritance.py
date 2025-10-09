import pytest

from cyclopts import App
from cyclopts.exceptions import UnknownOptionError


def test_app_has_extra_attributes_as_attributes():
    """Test that extra attributes are App attributes with defaults None."""
    app = App()

    assert app.print_error is None
    assert app.exit_on_error is None
    assert app.help_on_error is None
    assert app.verbose is None
    assert app.end_of_options_delimiter is None
    assert app.result_action is None


def test_app_attributes_can_be_set():
    """Test that extra attributes can be set as App attributes."""
    app = App(
        print_error=False,
        exit_on_error=False,
        help_on_error=True,
        verbose=True,
        end_of_options_delimiter="--",
    )

    assert app.print_error is False
    assert app.exit_on_error is False
    assert app.help_on_error is True
    assert app.verbose is True
    assert app.end_of_options_delimiter == "--"


def test_call_overrides_app_attributes():
    """Test that parameters in __call__ override the stored values in attributes."""
    app = App(exit_on_error=False)

    @app.default
    def main():
        return "success"

    with pytest.raises(UnknownOptionError):
        app(["--unknown-flag"])

    with pytest.raises(SystemExit):
        app(["--unknown-flag"], exit_on_error=True)


def test_parse_args_overrides_app_attributes():
    """Test that parameters in parse_args override the stored values in attributes."""
    app = App(
        exit_on_error=True,
        verbose=False,
    )

    @app.default
    def main():
        return "success"

    with pytest.raises(UnknownOptionError):
        app.parse_args(["--unknown-flag"], exit_on_error=False)

    with pytest.raises(SystemExit):
        app.parse_args(["--unknown-flag"])


def test_parse_known_args_overrides_app_attributes():
    """Test that parameters in parse_known_args override the stored values in attributes."""
    app = App(end_of_options_delimiter="===")

    @app.default
    def main(arg: str = "default"):
        return arg

    # Override the end_of_options_delimiter
    command, bound, unused_tokens, ignored = app.parse_known_args(
        ["((", "after_delimiter"], end_of_options_delimiter="(("
    )

    # With the override, the standard "--" should work, not "==="
    assert command == main
    assert bound.arguments["arg"] == "after_delimiter"
    assert unused_tokens == []


def test_app_stack_inheritance_simple():
    """Test that child apps inherit extra attributes from parent apps via AppStack."""
    parent_app = App(
        print_error=False,
        exit_on_error=False,
        help_on_error=True,
        verbose=True,
    )

    parent_app.command(child_app := App(name="child"))

    @child_app.default
    def child_command():
        return "child_success"

    # Child should inherit parent's settings
    with pytest.raises(UnknownOptionError):
        # This will raise UnknownOptionError due to unknown flag, but should not exit due to inherited exit_on_error=False
        parent_app("child --unknown-flag", exit_on_error=None)  # None means use inherited


def test_app_stack_inheritance_override():
    """Test that child apps can override parent app extra attributes."""
    parent_app = App(
        print_error=True,
        exit_on_error=True,
        verbose=False,
    )

    child_app = App(
        name="child",
        print_error=False,
        exit_on_error=False,
        verbose=True,
        result_action="return_value",
    )
    parent_app.command(child_app)

    @child_app.default
    def child_command():
        return "child_success"

    # Child's settings should override parent's
    child_app([], exit_on_error=False)


def test_app_stack_resolution_none_values():
    """Test that None values in child apps allow parent values to be used."""
    parent_app = App(
        print_error=False,
        exit_on_error=False,
        help_on_error=True,
        verbose=True,
        end_of_options_delimiter="--parent--",
    )

    # Child has all None values, should inherit from parent
    child_app = App(name="child")
    parent_app.command(child_app)

    @child_app.default
    def child_command():
        return "child_success"

    # Test that child inherits parent's end_of_options_delimiter through AppStack
    command, bound, unused_tokens, ignored = parent_app.parse_known_args(
        ["child", "--parent--", "after_delimiter"],
        end_of_options_delimiter=None,  # Should use app's setting
    )

    # The child should have inherited the parent's delimiter
    assert command == child_command
    assert unused_tokens == ["after_delimiter"]


def test_meta_app_inheritance():
    """Test that meta apps also participate in extra attribute inheritance."""
    parent_app = App(
        print_error=False,
        exit_on_error=False,
        verbose=True,
    )

    # Set up meta app with different settings
    parent_app.meta.print_error = True
    parent_app.meta.verbose = False

    child_app = App(name="child", result_action="return_value")
    parent_app.command(child_app)

    @child_app.default
    def child_command():
        return "child_success"

    # Child should inherit from the closest parent in the stack
    child_app([])


def test_signature_parameter_override_precedence():
    """Test that signature parameters have highest precedence over app attributes."""
    app = App(
        print_error=True,
        exit_on_error=True,
        help_on_error=False,
        verbose=False,
        end_of_options_delimiter="--app--",
    )

    @app.default
    def main(args, /):
        return args

    # All signature parameters should override app attributes
    command, bound, ignored = app.parse_args(
        ["--signature--", "foo"],
        end_of_options_delimiter="--signature--",
    )
    assert command == main
    assert bound.args == ("foo",)
    assert not ignored


def test_true_inheritance_without_fallback_override():
    """Test that parent app attributes are inherited without being overridden by method defaults."""
    parent_app = App(
        exit_on_error=False,
    )

    parent_app.command(child_app := App(name="child"))

    @child_app.default
    def child_command():
        return "child_success"

    with pytest.raises(UnknownOptionError):
        # This should not raise a SystemExit due to the root parent_app exit_on_error=False
        parent_app("child --unknown-flag")

    with pytest.raises(SystemExit):
        # The immediately supplied argument should have highest priority.
        parent_app("child --unknown-flag", exit_on_error=True)
