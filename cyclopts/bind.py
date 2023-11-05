import inspect
import typing
from collections import deque
from typing import Any, Callable, Dict, Iterable, List, Tuple, Union

from cyclopts.coercion import lookup as coercion_lookup
from cyclopts.exceptions import (
    MissingArgumentError,
    UnknownKeywordError,
    UnsupportedPositionalError,
)
from cyclopts.parameter import get_coercion, get_hint_parameter


def _cli2parameter_mappings(f: Callable):
    kwargs_parameter = None
    kw_mapping, flag_mapping = {}, {}
    signature = inspect.signature(f)
    for parameter in signature.parameters.values():
        if parameter.kind == parameter.VAR_KEYWORD:
            kwargs_parameter = parameter

        if parameter.kind in (parameter.POSITIONAL_OR_KEYWORD, parameter.KEYWORD_ONLY):
            hint, param = get_hint_parameter(parameter)
            key = param.name if param.name else parameter.name.replace("_", "-")
            if (typing.get_origin(hint) or hint) is bool:  # Boolean Flag
                flag_mapping[key] = (parameter, True)
                flag_mapping["no-" + key] = (parameter, False)
            else:
                kw_mapping[key] = parameter
    return kw_mapping, flag_mapping, kwargs_parameter


def _coerce_parameter(
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
        value = coercion(value)
        out.setdefault(parameter, [])
        out[parameter].append(value)
    else:
        value = coercion(value)
        out[parameter] = value


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

        if not token.startswith("--"):
            # TODO: parse single-hyphen flags here
            remaining_tokens.append(token)
            continue

        token = token[2:]  # remove the leading "--"

        if token in cli2flag:
            parameter, cli_value = cli2flag[token]
        else:
            if "=" in token:
                cli_key, cli_value = token.split("=", 1)
            else:
                cli_key = token
                try:
                    cli_value = tokens[i + 1]
                    skip_next_iterations = 1
                except IndexError as e:
                    raise MissingArgumentError(f"Unknown CLI keyword --{cli_key}") from e

            try:
                parameter = cli2kw[cli_key]
            except KeyError as e:
                if kwargs_parameter:
                    parameter = kwargs_parameter
                    cli_value = {cli_key: cli_value}
                else:
                    raise UnknownKeywordError(cli_key) from e

        _coerce_parameter(mapping, parameter, cli_value)

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
                _coerce_parameter(out, parameter, token)
            tokens.clear()
            break
        else:
            if typing.get_origin(parameter.annotation) is list:
                raise UnsupportedPositionalError("List parameters cannot be populated by positional arguments.")
            _coerce_parameter(out, parameter, tokens.popleft())

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
                raise MissingArgumentError from e
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
    remaining_tokens = _parse_pos(f, remaining_tokens, mapping)
    bound = _bind(f, mapping)
    return bound, remaining_tokens
