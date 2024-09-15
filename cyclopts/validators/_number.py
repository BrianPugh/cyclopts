from typing import Optional, Sequence, Union

from attrs import frozen

Numeric = Union[int, float]
NumericSequence = Sequence[Union[Numeric, "NumericSequence"]]


@frozen(kw_only=True)
class Number:
    """Limit input number to a value range."""

    lt: Optional[Numeric] = None
    """Input value must be **less than** this value."""

    lte: Optional[Numeric] = None
    """Input value must be **less than or equal** this value."""

    gt: Optional[Numeric] = None
    """Input value must be **greater than** this value."""

    gte: Optional[Numeric] = None
    """Input value must be **greater than or equal** this value."""

    def __call__(self, type_: type, value: Union[Numeric, NumericSequence]):
        if isinstance(value, Sequence):
            if isinstance(value, str):
                raise TypeError
            for v in value:
                self(type_, v)
        else:
            if self.lt is not None and value >= self.lt:
                raise ValueError(f"Must be < {self.lt}")

            if self.lte is not None and value > self.lte:
                raise ValueError(f"Must be <= {self.lte}")

            if self.gt is not None and value <= self.gt:
                raise ValueError(f"Must be > {self.gt}")

            if self.gte is not None and value < self.gte:
                raise ValueError(f"Must be >= {self.gte}")
