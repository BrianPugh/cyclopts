from collections.abc import Sequence
from typing import Any

from cyclopts.utils import frozen


def _selects_nothing(s: slice) -> bool:
    """Return :obj:`True` if the slice provably selects zero elements for *any* sequence.

    Only slices that are empty regardless of the sequence they're applied to are
    reported; length-dependent slices (e.g. ``5:-5``) are conservatively allowed.
    """
    step = 1 if s.step is None else s.step
    if step == 0:
        # An invalid slice (applying it raises ``ValueError``); not our concern here.
        return False

    start, stop = s.start, s.stop
    if step > 0:
        if start is None:
            start = 0
        if stop is None:
            # Extends to the end of the sequence; non-empty for any non-empty sequence.
            return False
    else:  # step < 0
        if start is None or stop is None:
            # Unbounded ends depend on the sequence length; cannot prove emptiness.
            return False

    # Both bounds are concrete integers, but they're only comparable without a
    # sequence length when they share a sign frame (both non-negative or both negative).
    if (start < 0) != (stop < 0):
        return False

    return start >= stop if step > 0 else start <= stop


@frozen(kw_only=True)
class Slice:
    """Assertions on properties of a :class:`slice`.

    Example Usage:

    .. code-block:: python

        from cyclopts import App, Parameter, validators
        from typing import Annotated

        app = App()


        @app.default
        def main(time: Annotated[slice, Parameter(validator=validators.Slice(allow_empty=False))]):
            print(f"Selecting {time}.")


        app()

    .. code-block:: console

        $ my-script 0:3
        Selecting slice(0, 3, None).

        $ my-script 3:1
        ╭─ Error ───────────────────────────────────────────────────────╮
        │ Invalid value "3:1" for "TIME". Slice must select a non-empty │
        │ range.                                                         │
        ╰───────────────────────────────────────────────────────────────╯
    """

    allow_empty: bool = True
    """If :obj:`False`, the slice **must** select a non-empty range. Defaults to :obj:`True`."""

    def __call__(self, type_: Any, value: Any):
        if isinstance(value, Sequence):
            if isinstance(value, str):
                raise TypeError
            for v in value:
                self(type_, v)
        else:
            if not isinstance(value, slice):
                return

            if not self.allow_empty and _selects_nothing(value):
                raise ValueError("Slice must select a non-empty range.")
