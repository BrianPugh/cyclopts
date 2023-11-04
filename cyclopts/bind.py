import inspect
import typing
from collections import deque
from typing import Any, Callable, Dict, Iterable, List, Tuple

from cyclopts.coercion import default_coercion_lookup
from cyclopts.exceptions import (
    MissingArgumentError,
    UnknownKeywordError,
    UnsupportedPositionalError,
)
from cyclopts.parameter import get_hint_parameter


def _cli2parameter_mappings(f: Callable):
    kw_mapping, flag_mapping = {}, {}
    signature = inspect.signature(f)
    for parameter in signature.parameters.values():
        # TODO: add some type validation rules here
        if parameter.kind in (parameter.POSITIONAL_OR_KEYWORD, parameter.KEYWORD_ONLY):
            hint, param = get_hint_parameter(parameter)
            key = param.name if param.name else parameter.name.replace("_", "-")
            if (typing.get_origin(hint) or hint) is bool:
                # Boolean Flag
                flag_mapping[key] = (parameter, True)
                flag_mapping["no-" + key] = (parameter, False)
            else:
                kw_mapping[key] = parameter
    return kw_mapping, flag_mapping


def _coerce_kw(out, parameter, value: str):
    """Coerce an input string value according to Cyclopts rules.

    Updates dictionary inplace.
    """
    hint, param = get_hint_parameter(parameter)
    hint = typing.get_origin(hint) or hint
    coercion = param.coercion if param.coercion else default_coercion_lookup.get(hint, hint)
    value = coercion(value)
    if hint in (list, tuple, Iterable):
        out.setdefault(parameter, [])
        out[parameter].append(value)
    elif parameter.kind == parameter.VAR_POSITIONAL:  # ``*args``
        out.setdefault(parameter, [])
        out[parameter].append(value)
    else:
        out[parameter] = value


def _coerce_pos(parameter, value: str):
    hint, param = get_hint_parameter(parameter)
    hint = typing.get_origin(hint) or hint
    coercion = param.coercion if param.coercion else default_coercion_lookup.get(hint, hint)
    return coercion(value)


def _parse_kw_and_flags(f, tokens, mapping):
    cli2kw, cli2flag = _cli2parameter_mappings(f)

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

            _coerce_kw(mapping, parameter, cli_value)
        else:  # positional
            remaining_tokens.append(token)

    return remaining_tokens


def _parse_pos(f: Callable, tokens: Iterable[str], out: Dict) -> List[str]:
    tokens = deque(tokens)
    signature = inspect.signature(f)
    parameters = list(signature.parameters.values())

    def remaining_parameters():
        for parameter in parameters:
            if parameter in out:
                continue
            yield parameter

    for parameter in remaining_parameters():
        if not tokens:
            break
        if parameter.kind == parameter.VAR_POSITIONAL:  # ``*args``
            for token in tokens:
                _coerce_kw(out, parameter, token)
            tokens.clear()
            break
        else:
            if typing.get_origin(parameter.annotation) is list:
                raise UnsupportedPositionalError("List parameters cannot be populated by positional arguments.")
            _coerce_kw(out, parameter, tokens.popleft())

    return list(tokens)


def _is_required(parameter: inspect.Parameter) -> bool:
    return parameter.default is parameter.empty


def _bind(f: Callable, mapping):
    signature = inspect.signature(f)

    f_pos, f_kwargs = [], {}
    for p in signature.parameters.values():
        if p.kind in (p.POSITIONAL_ONLY, p.POSITIONAL_OR_KEYWORD):
            try:
                f_pos.append(mapping[p])
            except KeyError as e:
                if _is_required(p):
                    raise MissingArgumentError from e
        elif p.kind is p.VAR_POSITIONAL:  # ``*args``
            f_pos.extend(mapping.get(p, []))
        else:
            try:
                f_kwargs[p.name] = mapping[p]
            except KeyError as e:
                if _is_required(p):
                    raise MissingArgumentError from e

    return signature.bind(*f_pos, **f_kwargs)


def create_bound_arguments(f, tokens) -> Tuple[inspect.BoundArguments, Iterable[str]]:
    # Note: mapping is updated inplace
    mapping: Dict[inspect.Parameter, Any] = {}
    remaining_tokens = _parse_kw_and_flags(f, tokens, mapping)
    remaining_tokens = _parse_pos(f, remaining_tokens, mapping)
    bound = _bind(f, mapping)
    return bound, remaining_tokens
