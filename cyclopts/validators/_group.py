from typing import Optional


class LimitedChoice:
    def __init__(self, min: int = 0, max: Optional[int] = None):
        """Group validator that limits the number of selections per group.

        Commonly used for enforcing mutually-exclusive parameters (default behavior).

        Parameters
        ----------
        min: int
            The minimum (inclusive) number of CLI parameters allowed.
        max: Optional[int]
            The maximum (inclusive) number of CLI parameters allowed.
            Defaults to ``1`` if ``min==0``, ``min`` otherwise.
        """
        self.min = min
        self.max = (self.min or 1) if max is None else max
        if self.max < self.min:
            raise ValueError("max must be >=min.")

    def __call__(self, **kwargs):
        if not (self.min <= len(kwargs) <= self.max):
            offenders = "{" + ", ".join(f"--{k}" for k in kwargs.keys()) + "}"
            if self.min == 0 and self.max == 1:
                raise ValueError(f"Mutually exclusive arguments: {offenders}")
            else:
                raise ValueError(
                    f"Received {len(kwargs)} arguments: {offenders}. Only [{self.min}, {self.max}] choices may be specified."
                )
