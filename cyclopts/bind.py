import inspect
import typing
from collections import deque
from typing import Callable, Dict, Iterable, Tuple

from cyclopts.coercion import default_coercion_lookup
from cyclopts.exceptions import (
    MissingArgumentError,
    MissingTypeError,
    UnknownKeywordError,
    UnreachableError,
    UnsupportedPositionalError,
    UnsupportedTypeHintError,
)
from cyclopts.parameter import get_hint_param


def _cli2parameter_mappings(f: Callable):
    kw_mapping, flag_mapping = {}, {}
    signature = inspect.signature(f)
    for parameter in signature.parameters.values():
        # TODO: add some type validation rules here
        if parameter.kind in (parameter.POSITIONAL_OR_KEYWORD, parameter.KEYWORD_ONLY):
            hint, param = get_hint_param(parameter)
            key = param.name if param.name else parameter.name.replace("_", "-")
            if (typing.get_origin(hint) or hint) is bool:
                # Boolean Flag
                flag_mapping[key] = (parameter, True)
                flag_mapping["no-" + key] = (parameter, False)
            else:
                kw_mapping[key] = parameter
    return kw_mapping, flag_mapping


def _coerce_kw(d, parameter, value: str):
    hint, param = get_hint_param(parameter)
    hint = typing.get_origin(hint) or hint
    # TODO: I don't think this will properly handle List[List[int]]
    coercion = param.coercion if param.coercion else default_coercion_lookup.get(hint, hint)
    value = coercion(value)
    if (typing.get_origin(hint) or hint) in (list, tuple):
        d.setdefault(parameter.name, [])
        d[parameter.name].append(value)
    else:
        d[parameter.name] = value


def _coerce_pos(parameter, value: str):
    hint, param = get_hint_param(parameter)
    hint = typing.get_origin(hint) or hint
    coercion = param.coercion if param.coercion else default_coercion_lookup.get(hint, hint)
    return coercion(value)


def _parse_kw_and_flags(f, tokens):
    cli2kw, cli2flag = _cli2parameter_mappings(f)

    f_kwargs = {}
    remaining_tokens = []

    # Parse All Keyword Arguments & Flags
    skip_next_iteration = False
    for i, token in enumerate(tokens):
        # If the previous argument was a keyword, then this is its value
        if skip_next_iteration:
            skip_next_iteration = False
            continue

        # Check for keyword argument with equal sign
        # Goal: get key and value
        if token.startswith("--"):  # some sort of keyword
            token = token[2:]  # remove the leading "--"
            if "=" in token:
                cli_key, cli_value = token.split("=", 1)
                try:
                    parameter = cli2kw[cli_key]
                except KeyError as e:
                    raise UnknownKeywordError(cli_key) from e
            elif token in cli2flag:
                parameter, cli_value = cli2flag[token]
            elif token in cli2kw:
                cli_key = token
                try:
                    cli_value = tokens[i + 1]
                except IndexError as e:
                    raise MissingArgumentError(f"Unknown CLI keyword --{cli_key}") from e
                parameter = cli2kw[cli_key]
                skip_next_iteration = True
            else:
                raise UnknownKeywordError(f"--{token}")

            _coerce_kw(f_kwargs, parameter, cli_value)
        else:  # positional
            remaining_tokens.append(token)

    return f_kwargs, remaining_tokens


def _parse_pos(f: Callable, tokens: Iterable[str], f_kwargs: Dict) -> Tuple[list, list]:
    tokens = deque(tokens)
    signature = inspect.signature(f)
    parameters = list(signature.parameters.values())

    f_args = []

    def remaining_parameters():
        for parameter in parameters:
            if parameter.name in f_kwargs:
                continue
            yield parameter

    for parameter in remaining_parameters():
        if not tokens:
            break
        if parameter.kind == parameter.VAR_POSITIONAL:  # ``*args``
            f_args.extend(_coerce_pos(parameter, x) for x in tokens)
            break
        elif parameter.kind == parameter.POSITIONAL_ONLY:
            f_args.append(_coerce_pos(parameter, tokens.popleft()))
        elif parameter.kind == parameter.POSITIONAL_OR_KEYWORD:
            if typing.get_origin(parameter.annotation) is list:
                raise UnsupportedPositionalError("List parameters cannot be populated by positional arguments.")
            f_kwargs[parameter.name] = _coerce_pos(parameter, tokens.popleft())
        else:
            raise UnreachableError("Not expected to get here.")

    return f_args, list(tokens)


def create_bound_arguments(f, tokens) -> Tuple[inspect.BoundArguments, Iterable[str]]:
    f_kwargs, remaining_tokens = _parse_kw_and_flags(f, tokens)
    f_pos, remaining_tokens = _parse_pos(f, remaining_tokens, f_kwargs)

    signature = inspect.signature(f)
    try:
        bound = signature.bind(*f_pos, **f_kwargs)
    except TypeError as e:
        raise MissingArgumentError from e

    bound.apply_defaults()

    return bound, remaining_tokens
