from functools import cached_property


class DocString:
    def __init__(self, docstring):
        self.docstring = docstring

    @cached_property
    def short_description(self):
        return self.docstring.split("\n")[0]
