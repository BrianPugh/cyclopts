"""Load Cyclopts App objects from Python scripts."""

import importlib.util
import sys
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from cyclopts import App


def load_app_from_script(script: str | Path) -> tuple["App", str]:
    """Load a Cyclopts App object from a Python script.

    Parameters
    ----------
    script : str | Path
        Python script path, optionally with ``'::app_object'`` notation to specify
        the :class:`App` object (only supported with str). If not specified, will search
        for :class:`App` objects in the script's global namespace.

    Returns
    -------
    tuple[App, str]
        The loaded :class:`App` object and its name.

    Raises
    ------
    SystemExit
        If the script cannot be loaded, no App objects are found, or multiple
        App objects exist without specification.
    """
    # Avoid circular import
    from cyclopts import App

    # Parse the script path and optional app object
    app_name = None
    if isinstance(script, str) and "::" in script:
        script_path, app_name = script.split("::", 1)
        script_path = Path(script_path)
    elif isinstance(script, Path):
        script_path = script
    else:
        script_path = Path(script)

    script_path = script_path.resolve()

    if not script_path.exists():
        print(f"Error: Script '{script_path}' not found.", file=sys.stderr)
        sys.exit(1)

    if not script_path.suffix == ".py":
        print(f"Error: '{script_path}' is not a Python file.", file=sys.stderr)
        sys.exit(1)

    # Load the module
    spec = importlib.util.spec_from_file_location("__cyclopts_doc_module", script_path)
    if spec is None or spec.loader is None:
        print(f"Error: Could not load module from '{script_path}'.", file=sys.stderr)
        sys.exit(1)

    module = importlib.util.module_from_spec(spec)
    sys.modules["__cyclopts_doc_module"] = module
    spec.loader.exec_module(module)

    # Find the App object
    if app_name:
        # User specified the app object name
        if not hasattr(module, app_name):
            print(f"Error: No object named '{app_name}' found in '{script_path}'.", file=sys.stderr)
            sys.exit(1)
        app_obj = getattr(module, app_name)
        if not isinstance(app_obj, App):
            print(f"Error: '{app_name}' is not a Cyclopts App object.", file=sys.stderr)
            sys.exit(1)
        return app_obj, app_name
    else:
        # Heuristic: find App objects in the module's global namespace
        app_objects = []
        for name in dir(module):
            if not name.startswith("_"):  # Skip private/protected names
                obj = getattr(module, name)
                if isinstance(obj, App):
                    app_objects.append((name, obj))

        if not app_objects:
            print(f"Error: No Cyclopts App objects found in '{script_path}'.", file=sys.stderr)
            sys.exit(1)

        if len(app_objects) > 1:
            # Filter out Apps that are registered as commands to other Apps
            registered_apps = []
            for _, app in app_objects:
                if hasattr(app, "_commands"):
                    registered_apps.extend(app._commands.values())

            # Keep only Apps that are not registered to others
            filtered_apps = [(name, app) for name, app in app_objects if app not in registered_apps]

            if filtered_apps:
                app_objects = filtered_apps

            if len(app_objects) > 1:
                names = ", ".join(name for name, _ in app_objects)
                script_str = str(script) if isinstance(script, Path) else script
                print(
                    f"Error: Multiple App objects found: {names}. Please specify one using '{script_str}::app_name'.",
                    file=sys.stderr,
                )
                sys.exit(1)

        name, app_obj = app_objects[0]
        return app_obj, name
