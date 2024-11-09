from typing import Any, Optional, Sequence, Union

from attrs import frozen

Numeric = Union[int, float]
NumericSequence = Sequence[Union[Numeric, "NumericSequence"]]


@frozen(kw_only=True)
class Number:
    """Limit input number to a value range.

    Example Usage:

    .. code-block:: python

        from cyclopts import App, Parameter, validators
        from typing import Annotated

        app = App()


        @app.default
        def main(age: Annotated[int, Parameter(validator=validators.Number(gte=0, lte=150))]):
            print(f"You are {age} years old.")


        app()

    .. code-block:: console

        $ my-script 100
        You are 100 years old.

        $ my-script -1
        ╭─ Error ───────────────────────────────────────────────────────╮
        │ Invalid value "-1" for "AGE". Must be >= 0.                   │
        ╰───────────────────────────────────────────────────────────────╯

        $ my-script 200
        ╭─ Error ───────────────────────────────────────────────────────╮
        │ Invalid value "200" for "AGE". Must be <= 150.                │
        ╰───────────────────────────────────────────────────────────────╯
    """

    lt: Optional[Numeric] = None
    """Input value must be **less than** this value."""

    lte: Optional[Numeric] = None
    """Input value must be **less than or equal** this value."""

    gt: Optional[Numeric] = None
    """Input value must be **greater than** this value."""

    gte: Optional[Numeric] = None
    """Input value must be **greater than or equal** this value."""

    modulo: Optional[Numeric] = None
    """Input value must be a multiple of this value."""

    def __call__(self, type_: Any, value: Union[Numeric, NumericSequence]):
        if isinstance(value, Sequence):
            if isinstance(value, str):
                raise TypeError
            for v in value:
                self(type_, v)
        else:
            if self.lt is not None and value >= self.lt:
                raise ValueError(f"Must be < {self.lt}.")

            if self.lte is not None and value > self.lte:
                raise ValueError(f"Must be <= {self.lte}.")

            if self.gt is not None and value <= self.gt:
                raise ValueError(f"Must be > {self.gt}.")

            if self.gte is not None and value < self.gte:
                raise ValueError(f"Must be >= {self.gte}.")

            if self.modulo is not None and value % self.modulo:
                raise ValueError(f"Must be a multiple of {self.modulo}.")
