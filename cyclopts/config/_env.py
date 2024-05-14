import os
from typing import TYPE_CHECKING, Callable, Dict, List, Tuple, Type, Union

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

    def __call__(self, apps: List["App"], commands: Tuple[str, ...], bound: Dict[str, Union[Unset, List[str]]]):
        components = [self.prefix]
        if self.command and commands:
            components.append("_".join(commands))
            components.append("_")
        prefix = "".join(components).upper()

        for key, value in bound.items():
            if not isinstance(value, Unset):
                continue
            env_key = (prefix + key).upper()
            try:
                env_value = os.environ[env_key]
            except KeyError:
                pass
            else:
                bound[key] = self.split(value.type_, env_value)
