"""Test for issue #643: version_flags and help_flags setter bug.

When changing version_flags or help_flags, the _delete_commands() call
happens AFTER setting the new value, so it tries to delete commands matching
the NEW flags instead of the OLD flags. This leaves orphaned commands from
the old flags in the app.
"""

from cyclopts import App


def test_version_flags_change_deletes_old_commands(console):
    """Test that changing version_flags properly deletes old version commands.

    Bug: Currently fails because old commands remain in app.
    """
    app = App(name="test", version="1.0.0", result_action="return_value")

    # Initial state: default version flags are ["--version"]
    assert "--version" in app

    # Change version_flags to a different set
    app.version_flags = ["--ver", "-V"]

    # The OLD commands should be deleted
    assert "--version" not in app, "Old version flag should be deleted"

    # The NEW commands should exist
    assert "--ver" in app, "New version flag should be created"
    assert "-V" in app, "New version flag should be created"


def test_help_flags_change_deletes_old_commands(console):
    """Test that changing help_flags properly deletes old help commands.

    Bug: Currently fails because old commands remain in app.
    """
    app = App(name="test", result_action="return_value")

    # Initial state: default help flags are ["--help", "-h"]
    assert "--help" in app
    assert "-h" in app

    # Change help_flags to a different set
    app.help_flags = ["--ayuda"]  # Spanish for "help"

    # The OLD commands should be deleted
    assert "--help" not in app, "Old help flag should be deleted"
    assert "-h" not in app, "Old help flag should be deleted"

    # The NEW commands should exist
    assert "--ayuda" in app, "New help flag should be created"


def test_version_flags_change_overlapping_flags(console):
    """Test changing version_flags when there's overlap between old and new."""
    app = App(name="test", version="1.0.0", result_action="return_value")

    # Set initial custom version flags
    app.version_flags = ["--version", "-v", "--ver"]

    assert "--version" in app
    assert "-v" in app
    assert "--ver" in app

    # Change to a set that overlaps with one old flag
    app.version_flags = ["--version", "-V"]  # Keep --version, change -v to -V, remove --ver

    # Should keep the overlapping flag
    assert "--version" in app, "Overlapping flag should remain"

    # Should add new flag
    assert "-V" in app, "New flag should be created"

    # Should remove old flags that aren't in new set
    assert "-v" not in app, "Old flag not in new set should be deleted"
    assert "--ver" not in app, "Old flag not in new set should be deleted"


def test_help_flags_change_overlapping_flags(console):
    """Test changing help_flags when there's overlap between old and new."""
    app = App(name="test", result_action="return_value")

    # Set initial custom help flags
    app.help_flags = ["--help", "-h", "--ayuda"]

    assert "--help" in app
    assert "-h" in app
    assert "--ayuda" in app

    # Change to a set that overlaps with one old flag
    app.help_flags = ["--help", "-?"]  # Keep --help, change -h to -?, remove --ayuda

    # Should keep the overlapping flag
    assert "--help" in app, "Overlapping flag should remain"

    # Should add new flag
    assert "-?" in app, "New flag should be created"

    # Should remove old flags that aren't in new set
    assert "-h" not in app, "Old flag not in new set should be deleted"
    assert "--ayuda" not in app, "Old flag not in new set should be deleted"


def test_version_flags_empty_to_nonempty(console):
    """Test changing from empty version_flags to non-empty."""
    app = App(name="test", version="1.0.0", version_flags=[], result_action="return_value")

    # Initially no version flags
    assert "--version" not in app

    # Set version flags
    app.version_flags = ["--version"]

    # Should now have version flag
    assert "--version" in app


def test_version_flags_nonempty_to_empty(console):
    """Test changing from non-empty version_flags to empty."""
    app = App(name="test", version="1.0.0", result_action="return_value")

    # Initially has default version flags
    assert "--version" in app

    # Remove all version flags
    app.version_flags = []

    # Should no longer have version flag
    assert "--version" not in app


def test_help_flags_empty_to_nonempty(console):
    """Test changing from empty help_flags to non-empty."""
    app = App(name="test", help_flags=[], result_action="return_value")

    # Initially no help flags
    assert "--help" not in app

    # Set help flags
    app.help_flags = ["--help"]

    # Should now have help flag
    assert "--help" in app


def test_help_flags_nonempty_to_empty(console):
    """Test changing from non-empty help_flags to empty."""
    app = App(name="test", result_action="return_value")

    # Initially has default help flags
    assert "--help" in app
    assert "-h" in app

    # Remove all help flags
    app.help_flags = []

    # Should no longer have help flags
    assert "--help" not in app
    assert "-h" not in app


def test_version_flags_functional_after_change(tmp_path, console):
    """Test that version command works correctly after changing flags."""
    app = App(name="test", version="1.0.0", result_action="return_value")

    # Change version flags
    app.version_flags = ["--ver"]

    # Test that new flag works
    with console.capture() as capture:
        app(["--ver"], console=console)

    assert "1.0.0" in capture.get()


def test_help_flags_functional_after_change(tmp_path, console):
    """Test that help command works correctly after changing flags."""
    app = App(name="test", help="Test app", result_action="return_value")

    # Change help flags
    app.help_flags = ["--ayuda"]

    # Test that new flag works
    with console.capture() as capture:
        app(["--ayuda"], console=console)

    assert "Test app" in capture.get()


def test_multiple_flag_changes(console):
    """Test changing flags multiple times in sequence."""
    app = App(name="test", version="1.0.0", result_action="return_value")

    # First change
    app.version_flags = ["--ver1"]
    assert "--ver1" in app
    assert "--version" not in app

    # Second change
    app.version_flags = ["--ver2"]
    assert "--ver2" in app
    assert "--ver1" not in app
    assert "--version" not in app

    # Third change
    app.version_flags = ["--ver3"]
    assert "--ver3" in app
    assert "--ver2" not in app
    assert "--ver1" not in app
    assert "--version" not in app
