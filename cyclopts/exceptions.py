class CycloptsError(Exception):
    """Root exception."""


class UnreachableError(CycloptsError):
    """Code-block should be unreachable."""


class MissingTypeError(CycloptsError):
    """Function parameter is missing a type annotation."""

    def __init__(self, value, message="Parameter missing type: "):
        self.value = value
        self.message = message + str(value)
        super().__init__(self.message)


class UnsupportedTypeHintError(CycloptsError):
    pass


class UnsupportedPositionalError(CycloptsError):
    pass


class CommandCollisionError(CycloptsError):
    pass


class UnusedCliTokensError(CycloptsError):
    def __init__(self, value, message="Unused parameters: "):
        self.value = value
        self.message = message + str(value)
        super().__init__(self.message)


class UnknownKeywordError(CycloptsError):
    def __init__(self, value, message="Unknown keyword or flag: "):
        self.value = value
        self.message = message + str(value)
        super().__init__(self.message)


class MissingArgumentError(CycloptsError):
    pass


class RepeatKeywordError(CycloptsError):
    def __init__(self, message="Cannot specify keyword multiple times."):
        super().__init__(message)


class MultipleParameterAnnotationError(CycloptsError):
    pass
