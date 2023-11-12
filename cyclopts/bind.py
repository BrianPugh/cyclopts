import inspect
import shlex
import sys
import typing
from collections import deque
from typing import Any, Callable, Dict, Iterable, List, NewType, Tuple, Union

from cyclopts.coercion import coerce, token_count
from cyclopts.exceptions import (
    CoercionError,
    MissingArgumentError,
    UnsupportedPositionalError,
)
from cyclopts.parameter import get_hint_parameter, get_names

UnknownTokens = NewType("UnknownTokens", List[str])


def normalize_tokens(tokens: Union[None, str, Iterable[str]]) -> List[str]:
    if tokens is None:
        tokens = sys.argv[1:]  # Remove the executable
    elif isinstance(tokens, str):
        tokens = shlex.split(tokens)
    else:
        tokens = list(tokens)
    return tokens


def _cli2parameter_mappings(f: Callable):
    kwargs_parameter = None
    kw_mapping, flag_mapping = {}, {}
    signature = inspect.signature(f)
    for parameter in signature.parameters.values():
        if parameter.kind == parameter.VAR_KEYWORD:
            kwargs_parameter = parameter

        if parameter.kind in (parameter.POSITIONAL_OR_KEYWORD, parameter.KEYWORD_ONLY):
            hint, param = get_hint_parameter(parameter)
            keys = get_names(parameter)
            if (typing.get_origin(hint) or hint) is bool:  # Boolean Flag
                for key in keys:
                    flag_mapping[key] = (parameter, True)
                # flag_mapping["no-" + key] = (parameter, False)  # TODO
            else:
                for key in keys:
                    kw_mapping[key] = parameter
    return kw_mapping, flag_mapping, kwargs_parameter


def _coerce_parameter(
    f: Callable,
    out: Dict[inspect.Parameter, Any],
    parameter: inspect.Parameter,
    value: Union[str, Dict[str, str]],
):
    """Coerce an input string value according to Cyclopts rules.

    Updates dictionary inplace.

    Parameters
    ----------
    value: Union[str, Dict[str, str]]
        If a dictionary, the parameter must be VAR_KEYWORD
    """
    coercion, is_iterable = get_coercion(parameter)

    def _safe_coerce(value):
        try:
            return coercion(value)
        except Exception as e:
            raise CoercionError(
                f'Error trying to coerce value "{value}" via "{coercion}" '
                f'for parameter "{parameter.name}" of function "{f}"'
            ) from e

    if parameter.kind is parameter.VAR_KEYWORD:  # ``**kwargs``
        assert isinstance(value, dict)

        key = list(value)[0]
        value = {key: coercion(value[key])}

        out.setdefault(parameter, {})

        if is_iterable:
            out[parameter].setdefault(key, [])
            out[parameter][key].append(value[key])
        else:
            out[parameter].update(value)
    elif is_iterable or parameter.kind is parameter.VAR_POSITIONAL:  # ``*args``
        value = _safe_coerce(value)
        out.setdefault(parameter, [])
        out[parameter].append(value)
    else:
        value = _safe_coerce(value)
        out[parameter] = value


def _cli_kw_to_f_kw(cli_key: str):
    """Only used for converting unknown CLI key/value keys for ``**kwargs``."""
    cli_key = cli_key[2:]  # strip off leading "--"
    cli_key = cli_key.replace("-", "_")
    return cli_key


def _parse_kw_and_flags(f, tokens, mapping):
    cli2kw, cli2flag, kwargs_parameter = _cli2parameter_mappings(f)

    remaining_tokens = []

    # Parse All Keyword Arguments & Flags
    skip_next_iterations = 0
    for i, token in enumerate(tokens):
        # If the previous argument was a keyword, then this is its value
        if skip_next_iterations:
            skip_next_iterations -= 1
            continue

        if not token.startswith("-"):
            remaining_tokens.append(token)
            continue

        if token in cli2flag:
            parameter, cli_value = cli2flag[token]
        elif "=" in token:
            cli_key, cli_value = token.split("=", 1)
            try:
                parameter = cli2kw[cli_key]
            except KeyError:
                if kwargs_parameter:
                    parameter = kwargs_parameter
                    cli_value = {_cli_kw_to_f_kw(cli_key): cli_value}
                else:
                    remaining_tokens.append(token)
                    continue
        else:
            cli_key = token
            try:
                cli_value = tokens[i + 1]
                skip_next_iterations = 1
            except IndexError:
                # This could be a flag downstream
                remaining_tokens.append(token)
                continue

            try:
                parameter = cli2kw[cli_key]
            except KeyError:
                if kwargs_parameter:
                    parameter = kwargs_parameter
                    cli_value = {_cli_kw_to_f_kw(cli_key): cli_value}
                else:
                    remaining_tokens.append(cli_key)
                    remaining_tokens.append(cli_value)
                    continue

        _coerce_parameter(f, mapping, parameter, cli_value)

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
                _coerce_parameter(f, out, parameter, token)
            tokens.clear()
            break
        else:
            if typing.get_origin(parameter.annotation) is list:
                raise UnsupportedPositionalError("List parameters cannot be populated by positional arguments.")
            _coerce_parameter(f, out, parameter, tokens.popleft())

    return list(tokens)


def _is_required(parameter: inspect.Parameter) -> bool:
    return parameter.default is parameter.empty


def _bind(f: Callable, mapping):
    signature = inspect.signature(f)

    f_pos, f_kwargs = [], {}
    use_pos = True

    def f_pos_append(p):
        nonlocal use_pos
        assert use_pos
        try:
            f_pos.append(mapping[p])
        except KeyError as e:
            if _is_required(p):
                raise MissingArgumentError(f'Missing argument "{p.name}"') from e
            use_pos = False

    """
    Unintuitive notes:
    * Parameters before a ``*args`` may have type ``POSITIONAL_OR_KEYWORD``.
        * Only args before a ``/`` are ``POSITIONAL_ONLY``.
    """
    for p in signature.parameters.values():
        if use_pos and p.kind in (p.POSITIONAL_ONLY, p.POSITIONAL_OR_KEYWORD):
            f_pos_append(p)
        elif use_pos and p.kind is p.VAR_POSITIONAL:  # ``*args``
            f_pos.extend(mapping.get(p, []))
            use_pos = False
        elif p.kind is p.VAR_KEYWORD:
            f_kwargs.update(mapping.get(p, {}))
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

    for parameter in inspect.signature(f).parameters.values():
        hint = typing.get_origin(parameter.annotation) or parameter.annotation
        if hint is UnknownTokens:
            mapping[parameter] = remaining_tokens
            remaining_tokens = []
            break

    remaining_tokens = _parse_pos(f, remaining_tokens, mapping)

    bound = _bind(f, mapping)
    return bound, remaining_tokens
