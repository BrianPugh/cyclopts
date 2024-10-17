import os
from typing import TYPE_CHECKING, Callable

from attrs import define, field

from cyclopts._env_var import env_var_split
from cyclopts.argument import ArgumentCollection, Token

if TYPE_CHECKING:
    from cyclopts.core import App


@define
class Env:
    prefix: str = ""
    command: bool = field(default=True, kw_only=True)
    split: Callable = field(default=env_var_split, kw_only=True)

    def __call__(self, apps: list["App"], commands: tuple[str, ...], arguments: "ArgumentCollection"):
        prefix = self.prefix
        if self.command and commands:
            prefix += "_".join(x.upper() for x in commands) + "_"

        candidate_env_keys = [x for x in os.environ if x.startswith(prefix)]
        candidate_env_keys.sort()
        for candidate_env_key in candidate_env_keys:
            try:
                argument, remaining_keys, _ = arguments.match(
                    candidate_env_key[len(prefix) :],
                    transform=lambda s: s.upper().replace("-", "_").replace(".", "_").lstrip("_"),
                    delimiter="_",
                )
            except ValueError:
                continue
            if any(x.source != "env" for x in argument.tokens):
                continue
            remaining_keys = tuple(x.lower() for x in remaining_keys)
            for i, value in enumerate(argument.env_var_split(os.environ[candidate_env_key])):
                argument.append(
                    Token(keyword=candidate_env_key, value=value, source="env", index=i, keys=remaining_keys)
                )
