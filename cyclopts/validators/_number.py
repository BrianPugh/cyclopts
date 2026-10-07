import math
import numbers
import sys
from typing import TYPE_CHECKING, Any

from cyclopts.utils import frozen
from cyclopts.validators._utils import iter_container_elements

if TYPE_CHECKING:
    from decimal import Decimal
    from fractions import Fraction


@frozen(kw_only=True)
class Number:
    """Limit input number to a value range.

    If the annotated parameter is a container (``list``, ``tuple``, ``set``,
    ``frozenset``, or ``dict``), each element is validated individually.
    For a ``dict``, the **values** are validated; keys are not.

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

    lt: "int | float | Decimal | Fraction | None" = None
    """Input value must be **less than** this value."""

    lte: "int | float | Decimal | Fraction | None" = None
    """Input value must be **less than or equal** this value."""

    gt: "int | float | Decimal | Fraction | None" = None
    """Input value must be **greater than** this value."""

    gte: "int | float | Decimal | Fraction | None" = None
    """Input value must be **greater than or equal** this value."""

    modulo: "int | float | Decimal | Fraction | None" = None
    """Input value must be a multiple of this value."""

    def __call__(self, type_: Any, value: Any):
        elements = iter_container_elements(value)
        if elements is not None:
            for v in elements:
                self(type_, v)
        else:
            if not _is_number(value):
                return

            # Ordering comparisons against a Decimal NaN raise decimal.InvalidOperation,
            # so detect NaN quietly up front and treat it as out of bounds.
            is_nan = _is_nan(value)
            if self.lt is not None and (is_nan or not value < self.lt):
                raise ValueError(f"Must be < {self.lt}.")

            if self.lte is not None and (is_nan or not value <= self.lte):
                raise ValueError(f"Must be <= {self.lte}.")

            if self.gt is not None and (is_nan or not value > self.gt):
                raise ValueError(f"Must be > {self.gt}.")

            if self.gte is not None and (is_nan or not value >= self.gte):
                raise ValueError(f"Must be >= {self.gte}.")

            if self.modulo is not None and (is_nan or not _is_finite(value) or _remainder(value, self.modulo)):
                raise ValueError(f"Must be a multiple of {self.modulo}.")


def _is_number(value: Any) -> bool:
    return isinstance(value, numbers.Real) or _is_decimal(value)


def _is_decimal(value: Any) -> bool:
    # A Decimal can only exist once its module is imported, so checking sys.modules
    # avoids importing decimal for apps that never use it.
    decimal = sys.modules.get("decimal")
    return decimal is not None and isinstance(value, decimal.Decimal)


def _is_nan(value: Any) -> bool:
    if isinstance(value, float):
        return math.isnan(value)
    if _is_decimal(value):
        return value.is_nan()
    return value != value


def _is_finite(value: Any) -> bool:
    if isinstance(value, float):
        return math.isfinite(value)
    if _is_decimal(value):
        return value.is_finite()
    return True


def _remainder(value: Any, divisor: "int | float | Decimal | Fraction") -> Any:
    # Decimal refuses % with float and Fraction, and Decimal % Decimal raises InvalidOperation
    # once the quotient exceeds the context precision; Fraction is exact in every case.
    if _is_decimal(value) or _is_decimal(divisor):
        from fractions import Fraction

        return Fraction(value) % Fraction(divisor)
    return value % divisor
