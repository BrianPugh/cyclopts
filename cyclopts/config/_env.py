import os
from typing import TYPE_CHECKING

from attrs import define, field

from cyclopts.argument import Argument, ArgumentCollection, Token
from cyclopts.argument._collection import earlier_source_filter

if TYPE_CHECKING:
    from cyclopts.core import App


def _transform(s: str) -> str:
    return s.upper().replace("-", "_").replace(".", "_").lstrip("_")


@define
class Env:
    prefix: str = ""
    source: str = field(default="env", kw_only=True)
    command: bool = field(default=True, kw_only=True)
    show: bool = field(default=True, kw_only=True)

    def _prefix(self, commands: tuple[str, ...]) -> str:
        prefix = self.prefix
        if self.command and commands:
            prefix += "_".join(x.upper() for x in commands) + "_"

        return prefix

    def _convert_argument(self, commands: tuple[str, ...], argument: Argument) -> str:
        """For generating environment variable names for the help-page.

        Internal Cyclopts use only.
        """
        return self._prefix(commands) + _transform(argument.name)

    def __call__(self, app: "App", commands: tuple[str, ...], arguments: ArgumentCollection):
        rejects = earlier_source_filter(arguments)

        prefix = self._prefix(commands)

        candidate_env_keys = [x for x in os.environ if x.startswith(prefix)]
        candidate_env_keys.sort()
        delimiter = "_"
        for candidate_env_key in candidate_env_keys:
            try:
                argument, remaining_keys, _ = arguments.match(
                    candidate_env_key[len(prefix) :],
                    transform=_transform,
                    delimiter=delimiter,
                )
            except ValueError:
                continue
            env_value = os.environ[candidate_env_key]
            if rejects(argument, remaining_keys, env_value):
                continue

            # There's inherently an ambiguity because we use "_" as the key-delimiter.
            # However, we can somewhat resolve this ambiguity by checking if the argument
            # accepts subkeys. If there are no children arguments, then just re-combine the
            # remaining_keys.
            if not argument.children and remaining_keys:
                remaining_keys = (delimiter.join(remaining_keys),)

            remaining_keys = tuple(x.lower() for x in remaining_keys)
            for i, value in enumerate(argument._split_env_value(env_value, remaining_keys)):
                token = Token(keyword=candidate_env_key, value=value, source=self.source, index=i, keys=remaining_keys)
                argument.append(token)
