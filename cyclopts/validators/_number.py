from typing import Optional, Type, Union, get_args, get_origin

from attrs import frozen

Numeric = Union[int, float, complex]


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

    def __call__(self, type_: Type, value: Numeric):
        origin = get_origin(type_) or type_
        if origin not in get_args(Numeric):
            raise TypeError
        if not isinstance(value, get_args(Numeric)):
            raise TypeError

        if self.lt is not None and value >= self.lt:  # pyright: ignore[reportGeneralTypeIssues]
            raise ValueError(f"Must be < {self.lt}")

        if self.lte is not None and value > self.lte:  # pyright: ignore[reportGeneralTypeIssues]
            raise ValueError(f"Must be <= {self.lte}")

        if self.gt is not None and value <= self.gt:  # pyright: ignore[reportGeneralTypeIssues]
            raise ValueError(f"Must be > {self.gt}")

        if self.gte is not None and value < self.gte:  # pyright: ignore[reportGeneralTypeIssues]
            raise ValueError(f"Must be >= {self.gte}")
