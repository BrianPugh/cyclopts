from typing import Optional, Union

from attrs import frozen

Numeric = Union[int, float, complex]


@frozen
class Number:
    lt: Optional[Numeric] = None
    lte: Optional[Numeric] = None
    gt: Optional[Numeric] = None
    gte: Optional[Numeric] = None

    def __call__(self, type_: type, value: Numeric):
        if not isinstance(value, Numeric):
            raise TypeError

        if self.lt is not None and value < self.lt:  # pyright: ignore[reportGeneralTypeIssues]
            raise ValueError(f"must be < {self.lt}")

        if self.lte is not None and value <= self.lte:  # pyright: ignore[reportGeneralTypeIssues]
            raise ValueError(f"must be >= {self.lte}")

        if self.gt is not None and value > self.gt:  # pyright: ignore[reportGeneralTypeIssues]
            raise ValueError(f"must be > {self.gt}")

        if self.gte is not None and value >= self.gte:  # pyright: ignore[reportGeneralTypeIssues]
            raise ValueError(f"must be >= {self.gte}")
