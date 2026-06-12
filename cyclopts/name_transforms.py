"""Reusable :data:`~cyclopts.NameTransform` callables for :attr:`.Parameter.name_transform`.

Each callable maps a python identifier to one or more CLI names (index 0 is the
canonical name). Assign one directly, or compose several in a list::

    from cyclopts import App, Parameter, name_transforms

    # Keep the default long name AND add a single-letter short flag (--verbose / -v):
    app = App(default_parameter=Parameter(name_transform=[name_transforms.default, name_transforms.short]))
"""

from cyclopts.utils import NameTransform, _pascal_to_snake

__all__ = ["NameTransform", "default", "short"]


def default(s: str) -> str:
    """Converts a python identifier into a CLI token.

    Performs the following operations (in order):

    1. Convert PascalCase to snake_case.
    2. Convert the string to all lowercase.
    3. Replace ``_`` with ``-``.
    4. Strip any leading/trailing ``-`` (also stripping ``_``, due to point 3).

    Intended to be used with :attr:`App.name_transform` and :attr:`Parameter.name_transform`.
    Also available as :func:`cyclopts.default_name_transform`.

    Parameters
    ----------
    s: str
        Input python identifier string.

    Returns
    -------
    str
        Transformed name.
    """
    return _pascal_to_snake(s).lower().replace("_", "-").strip("-")


def short(s: str) -> str:
    """Generate a single-letter short flag (e.g. ``verbose`` -> ``-v``).

    This returns **only** the short flag; pair it with :func:`default` in a list to
    keep the long name as well::

        Parameter(name_transform=[name_transforms.default, name_transforms.short])

    The short flag's letter is taken from the :func:`default`-transformed name, so it
    stays consistent for ``PascalCase``/leading-underscore identifiers (e.g.
    ``HelloWorld`` -> ``-h``, ``_foo`` -> ``-f``).

    If multiple parameters would generate the same short flag, the later parameter's
    colliding short flag is silently dropped (first-wins); use :attr:`.Parameter.alias`
    or :attr:`.Parameter.name` for explicit control in that case.
    """
    return "-" + default(s)[0]
