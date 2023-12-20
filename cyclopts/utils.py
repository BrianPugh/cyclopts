import functools


def record_init_kwargs(target: str):
    """Class decorator that records init argument names as a tuple to ``target``."""

    def decorator(cls):
        original_init = cls.__init__

        @functools.wraps(original_init)
        def new_init(self, **kwargs):
            original_init(self, **kwargs)
            # Circumvent frozen protection.
            object.__setattr__(self, target, tuple(kwargs.keys()))

        cls.__init__ = new_init
        return cls

    return decorator
