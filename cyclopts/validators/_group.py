from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
    from cyclopts.argument import ArgumentCollection


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

    def __call__(self, argument_collection: "ArgumentCollection"):
        argument_collection = argument_collection.filter_by(value_set=True)
        n_arguments = len(argument_collection)

        if self.min <= n_arguments <= self.max:
            return  # Happy path

        offenders = "{" + ", ".join(a.name for a in argument_collection) + "}"
        if self.min == 0 and self.max == 1:
            raise ValueError(f"Mutually exclusive arguments: {offenders}")
        else:
            raise ValueError(
                f"Received {n_arguments} arguments: {offenders}. Only [{self.min}, {self.max}] choices may be specified."
            )


class MutuallyExclusive(LimitedChoice):
    def __init__(self):
        """Alias for :class:`LimitedChoice` to make intentions more obvious.

        Only 1 argument in the group can be supplied a value.
        """
        super().__init__()
