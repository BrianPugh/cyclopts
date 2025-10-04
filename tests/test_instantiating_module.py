"""Test that _instantiating_module correctly captures the module that created the App.

This feature was introduced in PR #495 to improve automatic version detection.
The instantiating module is used to detect the version when --version is called.
"""

import subprocess
import sys


def test_instantiating_module_is_captured(tmp_path):
    """Test that App._instantiating_module captures the module that created it.

    This is critical for automatic version detection from the app's package.
    """
    # Create a test script
    test_script = tmp_path / "test_app.py"
    test_script.write_text("""
import cyclopts

app = cyclopts.App()

# Verify the module was captured
if app._instantiating_module is not None:
    print(f"SUCCESS: {app._instantiating_module.__name__}")
else:
    print("FAIL: Module was not captured")
    exit(1)
""")

    result = subprocess.run(
        [sys.executable, str(test_script)],
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, f"Module capture failed:\n{result.stdout}\n{result.stderr}"
    assert "SUCCESS" in result.stdout
    # When run as a script, it should be __main__
    assert "__main__" in result.stdout


def test_instantiating_module_lazy_property():
    """Test that _instantiating_module behaves as a lazy property."""
    import cyclopts

    app = cyclopts.App()

    # The module name should be captured at init - this is the KEY test
    # If this fails, the optimization broke the feature
    assert (
        app._instantiating_module_name is not None
    ), "Module name was not captured during App initialization. This breaks version detection!"
    assert (
        app._instantiating_module_name == __name__
    ), f"Expected module name '{__name__}', got '{app._instantiating_module_name}'"

    # The module object should be lazy (uses UNSET sentinel before first access)
    from cyclopts.utils import UNSET

    assert app._instantiating_module_cache is UNSET

    # First access should resolve it
    module = app._instantiating_module
    assert module is not None
    assert app._instantiating_module_cache is not UNSET

    # Subsequent accesses should return cached value
    module2 = app._instantiating_module
    assert module is module2


def test_instantiating_module_used_for_version():
    """Test that _instantiating_module is correctly used for version detection."""
    import cyclopts

    app = cyclopts.App()

    # The app should have captured the test module
    assert app._instantiating_module is not None

    # When we call _get_fallback_version_string, it should try to use the instantiating module
    # (though it may fall back to other methods if the module doesn't have version metadata)
    version = app._get_fallback_version_string()
    assert isinstance(version, str)
    # Should return something (either actual version or default "0.0.0")
    assert version != ""
