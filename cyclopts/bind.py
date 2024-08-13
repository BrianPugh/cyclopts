import inspect
import itertools
import os
import shlex
import sys
from contextlib import suppress
from typing import TYPE_CHECKING, Callable, Iterable, List, Tuple, Union

import cyclopts.utils
from cyclopts._convert import _bool
from cyclopts.argument import Argument, ArgumentCollection, Token
from cyclopts.exceptions import (
    CycloptsError,
    MissingArgumentError,
    UnknownOptionError,
    ValidationError,
)
from cyclopts.parameter import validate_command
from cyclopts.utils import ParameterDict

if TYPE_CHECKING:
    from cyclopts.group import Group


def normalize_tokens(tokens: Union[None, str, Iterable[str]]) -> List[str]:
    if tokens is None:
        tokens = sys.argv[1:]  # Remove the executable
    elif isinstance(tokens, str):
        tokens = shlex.split(tokens)
    else:
        tokens = list(tokens)
    return tokens


def _common_root_keys(argument_collection) -> Tuple[str, ...]:
    if not argument_collection:
        return ()
    common = argument_collection[0].keys
    for argument in argument_collection[1:]:
        if not argument.keys:
            return ()
        for i, (common_key, argument_key) in enumerate(zip(common, argument.keys)):
            if common_key != argument_key:
                if i == 0:
                    return ()

                common = argument.keys[:i]
                break
        common = common[: len(argument.keys)]
    return common


def _parse_kw_and_flags(argument_collection: ArgumentCollection, tokens):
    unused_tokens = []
    skip_next_iterations = 0
    for i, token in enumerate(tokens):
        # If the previous argument was a keyword, then this is its value
        if skip_next_iterations > 0:
            skip_next_iterations -= 1
            continue

        if not _is_option_like(token):
            unused_tokens.append(token)
            continue

        cli_values: List[str] = []
        consume_count = 0

        if "=" in token:
            cli_option, cli_value = token.split("=", 1)
            cli_values.append(cli_value)
            consume_count -= 1
        else:
            cli_option = token

        try:
            argument, leftover_keys, implicit_value = argument_collection.match(cli_option)
        except ValueError:
            unused_tokens.append(token)
            continue

        if implicit_value is not None:
            # A flag was parsed
            if cli_values:
                if _bool(cli_values[-1]):  # --positive-flag=true or --negative-flag=true or --empty-flag=true
                    argument.append(Token(cli_option, "", source="cli", implicit_value=implicit_value))
                else:  # --positive-flag=false or --negative-flag=false or --empty-flag=false
                    if isinstance(implicit_value, bool):
                        argument.append(Token(cli_option, "", source="cli", implicit_value=not implicit_value))
                    else:
                        continue
            else:
                argument.append(Token(cli_option, "", source="cli", implicit_value=implicit_value))
        else:
            tokens_per_element, consume_all = argument.token_count(leftover_keys)

            with suppress(IndexError):
                if consume_all:
                    for j in itertools.count():
                        token = tokens[i + 1 + j]
                        if not argument.cparam.allow_leading_hyphen and _is_option_like(token):
                            break
                        cli_values.append(token)
                        skip_next_iterations += 1
                else:
                    consume_count += tokens_per_element
                    for j in range(consume_count):
                        token = tokens[i + 1 + j]
                        if not argument.cparam.allow_leading_hyphen:
                            _validate_is_not_option_like(token)
                        cli_values.append(token)
                        skip_next_iterations += 1

            if not cli_values or len(cli_values) % tokens_per_element:
                raise MissingArgumentError(argument=argument, tokens_so_far=cli_values)

            for index, cli_value in enumerate(cli_values):
                argument.append(Token(cli_option, cli_value, source="cli", index=index, keys=leftover_keys))

    return unused_tokens


def _is_option_like(token: str) -> bool:
    """Checks if a token looks like an option.

    Namely, negative numbers are not options, but a token like ``--foo`` is.
    """
    with suppress(ValueError):
        complex(token)
        return False
    return token.startswith("-")


def _validate_is_not_option_like(token):
    if _is_option_like(token):
        raise UnknownOptionError(token=token)


def _parse_pos(
    argument_collection: ArgumentCollection,
    tokens: List[str],
) -> List[str]:
    for i in itertools.count():
        try:
            argument, _, _ = argument_collection.match(i)
        except ValueError:
            break
        tokens_per_element, consume_all = argument.token_count()

        if not consume_all and argument.tokens:
            continue

        tokens_per_element = max(1, tokens_per_element)
        new_tokens = []
        while tokens:
            if len(tokens) < tokens_per_element:
                raise MissingArgumentError(argument=argument, tokens_so_far=tokens)

            for index, token in enumerate(tokens[:tokens_per_element]):
                if not argument.cparam.allow_leading_hyphen:
                    _validate_is_not_option_like(token)
                new_tokens.append(Token(None, token, "cli", index=index))
            tokens = tokens[tokens_per_element:]
            if not consume_all:
                break
        argument.tokens[:0] = new_tokens  # Prepend the new tokens to the argument.
        if not tokens:
            break

    return tokens


def _parse_env(argument_collection):
    for argument in argument_collection:
        if argument.tokens:
            # Don't check environment variables for parameters that already have values from CLI.
            continue
        for env_var_name in argument.cparam.env_var:
            try:
                env_var_value = os.environ[env_var_name]
            except KeyError:
                pass
            else:
                argument.tokens.append(Token(env_var_name, env_var_value, source="env"))
                break


def _is_required(iparam: inspect.Parameter) -> bool:
    """A token must be provided for the given :class:``inspect.Parameter``."""
    return iparam.default is iparam.empty and iparam.kind not in (
        iparam.VAR_KEYWORD,
        iparam.VAR_POSITIONAL,
    )


def _bind(
    func: Callable,
    mapping: ParameterDict,
):
    """Bind the mapping to the function signature.

    Better than directly using ``signature.bind`` because this can handle
    intermingled positional and keyword arguments.
    """
    f_pos, f_kwargs = [], {}
    use_pos = True

    def f_pos_append(p):
        nonlocal use_pos
        assert use_pos
        try:
            f_pos.append(mapping[p])
        except KeyError:
            use_pos = False

    signature = cyclopts.utils.signature(func)
    for iparam in signature.parameters.values():
        if use_pos and iparam.kind in (iparam.POSITIONAL_ONLY, iparam.POSITIONAL_OR_KEYWORD):
            f_pos_append(iparam)
        elif use_pos and iparam.kind is iparam.VAR_POSITIONAL:  # ``*args``
            f_pos.extend(mapping.get(iparam, []))
            use_pos = False
        elif iparam.kind is iparam.VAR_KEYWORD:
            f_kwargs.update(mapping.get(iparam, {}))
        else:
            with suppress(KeyError):
                f_kwargs[iparam.name] = mapping[iparam]

    bound = signature.bind_partial(*f_pos, **f_kwargs)
    return bound


def _parse_configs(argument_collection: ArgumentCollection, configs):
    for config in configs:
        # Each ``config`` is a partial that already has apps and commands provided.
        config(argument_collection)
        # TODO: validate argument_collection after every config?


def _sort_group_converters(argument_collection) -> List[Tuple["Group", List[Argument]]]:
    """Sort groups into "deepest common-root-keys first" order.

    This is imperfect, but probably works sufficiently well for practical use-cases.
    """
    out = {}
    # Sort alphabetically by group-name to enfroce some determinism.
    for i, group in enumerate(sorted(argument_collection.groups, key=lambda x: x.name)):
        if group.converter is None:
            continue
        group_arguments = [x for x in argument_collection if group in x.cparam.group and x._n_branch_tokens]
        if not group_arguments:
            continue
        common_root_keys = _common_root_keys(group_arguments)
        # Add i to key so that we don't get collisions.
        out[(common_root_keys, i)] = (
            group,
            [x for x in group_arguments if x.keys[: len(common_root_keys)] == common_root_keys],
        )
    return [ga for _, ga in sorted(out.items(), reverse=True)]


def create_bound_arguments(
    func: Callable,
    argument_collection: ArgumentCollection,
    tokens: List[str],
    configs: Iterable[Callable],
) -> Tuple[inspect.BoundArguments, List[str]]:
    """Parse and coerce CLI tokens to match a function's signature.

    Parameters
    ----------
    func: Callable
        Function.
    argument_collection: ArgumentCollection,
    tokens: List[str]
        CLI tokens to parse and coerce to match ``f``'s signature.
    configs: Iterable[Callable],

    Returns
    -------
    bound: inspect.BoundArguments
        The converted and bound positional and keyword arguments for ``f``.

    unused_tokens: List[str]
        Remaining tokens that couldn't be matched to ``f``'s signature.
    """
    unused_tokens = []

    validate_command(func)  # TODO: is this the appropriate location?

    try:
        # Build up a mapping of inspect.Parameter->List[str]
        unused_tokens = _parse_kw_and_flags(argument_collection, tokens)
        unused_tokens = _parse_pos(argument_collection, unused_tokens)
        _parse_env(argument_collection)
        _parse_configs(argument_collection, configs)

        argument_collection.convert()
        groups_with_arguments = _sort_group_converters(argument_collection)
        for group, group_arguments in groups_with_arguments:
            group.converter(group_arguments)  # pyright: ignore[reportOptionalCall]
            # A downstream Argument may have been overrode, so we have to reconvert the tree.
            argument_collection.convert()
        try:
            for group, group_arguments in groups_with_arguments:
                for validator in group.validator:  # pyright: ignore
                    validator(group_arguments)  # pyright: ignore[reportOptionalCall]
        except (AssertionError, ValueError, TypeError) as e:
            raise ValidationError(value=e.args[0] if e.args else "", group=group) from e  # pyright: ignore

        bound = _bind(func, argument_collection.iparam_to_value())

        for argument in argument_collection:
            if not _is_required(argument.iparam) or argument.keys:
                continue
            if not bool(argument._n_branch_tokens):
                raise MissingArgumentError(argument=argument)

    except CycloptsError as e:
        e.root_input_tokens = tokens
        e.unused_tokens = unused_tokens
        raise

    return bound, unused_tokens
