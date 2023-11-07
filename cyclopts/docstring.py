from functools import cached_property


class DocString:
    def __init__(self, fn):
        self.docstring = fn.__doc__ or ""

    @cached_property
    def short_description(self):
        return self.docstring.split("\n")[0]
