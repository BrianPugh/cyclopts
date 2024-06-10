import os
from typing import TYPE_CHECKING, Callable, Dict, List, Tuple, Union

from attrs import define, field

from cyclopts._env_var import env_var_split
from cyclopts.config import Unset

if TYPE_CHECKING:
    from cyclopts.core import App


@define
class Env:
    prefix: str = ""
    command: bool = field(default=True, kw_only=True)
    split: Callable = field(default=env_var_split, kw_only=True)

    def __call__(self, apps: List["App"], commands: Tuple[str, ...], mapping: Dict[str, Union[Unset, List[str]]]):
        prefix = self.prefix
        if self.command and commands:
            prefix += "_".join(commands) + "_"
        for key, value in mapping.items():
            if not isinstance(value, Unset) or value.related_set(mapping):
                continue
            env_key = (prefix + key).upper().replace("-", "_")
            try:
                env_value = os.environ[env_key]
            except KeyError:
                continue
            mapping[key] = self.split(value.iparam.annotation, env_value)
