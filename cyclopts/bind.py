import inspect
import shlex
import sys
from typing import Any, Callable, Dict, Iterable, List, NewType, Tuple, Union, get_origin

from cyclopts.coercion import coerce, resolve_annotated, resolve_union, token_count
from cyclopts.exceptions import (
    MissingArgumentError,
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


def cli2parameter_mappings(f: Callable) -> Dict[str, Tuple[inspect.Parameter, Any]]:
    mapping: Dict[str, Tuple[inspect.Parameter, Any]] = {}
    signature = inspect.signature(f)
    for parameter in signature.parameters.values():
        annotation = str if parameter.annotation is parameter.empty else parameter.annotation
        _, user_param = get_hint_parameter(annotation)

        if parameter.kind in (parameter.POSITIONAL_OR_KEYWORD, parameter.KEYWORD_ONLY):
            hint = resolve_union(resolve_annotated(annotation))
            keys = get_names(parameter)

            for key in keys:
                mapping[key] = (parameter, True if hint is bool else None)

            for key in user_param.get_negatives(hint, *keys):
                mapping[key] = (parameter, (get_origin(hint) or hint)())

    return mapping


def _cli_kw_to_f_kw(cli_key: str):
    """Only used for converting unknown CLI key/value keys for ``**kwargs``."""
    assert cli_key.startswith("--")
    cli_key = cli_key[2:]  # strip off leading "--"
    cli_key = cli_key.replace("-", "_")
    return cli_key


def _parse_kw_and_flags(f, tokens, mapping):
    cli2kw = cli2parameter_mappings(f)
    kwargs_parameter = next((p for p in inspect.signature(f).parameters.values() if p.kind == p.VAR_KEYWORD), None)

    if kwargs_parameter:
        mapping[kwargs_parameter] = {}

    remaining_tokens = []

    # Parse All Keyword Arguments & Flags
    skip_next_iterations = 0
    for i, token in enumerate(tokens):
        # If the previous argument was a keyword, then this is its value
        if skip_next_iterations > 0:
            skip_next_iterations -= 1
            continue

        if not token.startswith("-"):
            remaining_tokens.append(token)
            continue

        cli_values = []

        if "=" in token:
            cli_key, cli_value = token.split("=", 1)
            cli_values.append(cli_value)

            try:
                parameter, _ = cli2kw[cli_key]
            except KeyError:
                if kwargs_parameter:
                    consume_count = max(1, token_count(kwargs_parameter.annotation))

                    try:
                        for j in range(consume_count - 1):
                            cli_values.append(tokens[i + 1 + j])
                    except IndexError:
                        # This could be a flag downstream
                        remaining_tokens.append(token)
                        continue

                    key = _cli_kw_to_f_kw(cli_key)
                    mapping[kwargs_parameter].setdefault(key, [])
                    mapping[kwargs_parameter][key].extend(cli_values)
                    skip_next_iterations = consume_count - 1
                else:
                    remaining_tokens.append(token)
                continue

            consume_count = max(1, token_count(parameter.annotation))

            try:
                for j in range(consume_count - 1):
                    cli_values.append(tokens[i + 1 + j])
            except IndexError:
                # This could be a flag downstream
                remaining_tokens.append(token)
                continue
            skip_next_iterations = consume_count - 1
        else:
            cli_key = token

            try:
                parameter, implicit_value = cli2kw[cli_key]
            except KeyError:
                if kwargs_parameter:
                    consume_count = max(1, token_count(kwargs_parameter.annotation))

                    try:
                        for j in range(consume_count):
                            cli_values.append(tokens[i + 1 + j])
                        skip_next_iterations = consume_count
                    except IndexError:
                        # This could be a flag downstream
                        remaining_tokens.append(token)
                        continue

                    key = _cli_kw_to_f_kw(cli_key)
                    mapping[kwargs_parameter].setdefault(key, [])
                    mapping[kwargs_parameter][key].extend(cli_values)
                    continue
                else:
                    remaining_tokens.append(cli_key)
                    continue
            else:
                if implicit_value is not None:
                    cli_values.append(implicit_value)
                else:
                    consume_count = max(1, token_count(parameter.annotation))

                    try:
                        for j in range(consume_count):
                            cli_values.append(tokens[i + 1 + j])
                        skip_next_iterations = consume_count
                    except IndexError:
                        # This could be a flag downstream
                        remaining_tokens.append(token)
                        continue

        mapping.setdefault(parameter, [])
        mapping[parameter].extend(cli_values)

    return remaining_tokens


def _parse_pos(f: Callable, tokens: Iterable[str], mapping: Dict) -> List[str]:
    tokens = list(tokens)
    signature = inspect.signature(f)

    def remaining_parameters():
        for parameter in signature.parameters.values():
            if parameter in mapping:
                continue
            if parameter.kind is parameter.KEYWORD_ONLY:
                break
            yield parameter

    for parameter in remaining_parameters():
        if not tokens:
            break

        if parameter.kind == parameter.VAR_POSITIONAL:  # ``*args``
            mapping[parameter] = tokens
            tokens = []
            break

        consume_count = token_count(parameter.annotation)
        if consume_count < 0:  # Consume all remaining tokens
            mapping[parameter] = tokens
            tokens = []
            break

        consume_count = max(1, consume_count)

        if len(tokens) < consume_count:
            raise MissingArgumentError(f"Not enough arguments for {parameter}")
        mapping[parameter] = tokens[:consume_count]
        tokens = tokens[consume_count:]

    return tokens


def _is_required(parameter: inspect.Parameter) -> bool:
    return parameter.default is parameter.empty


def _bind(f: Callable, mapping: Dict[inspect.Parameter, Any]):
    """Bind the mapping to the function signature.

    Better than directly using ``signature.bind`` because this can handle
    intermingled keywords.
    """
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

    # Unintuitive notes:
    # * Parameters before a ``*args`` may have type ``POSITIONAL_OR_KEYWORD``.
    #     * Only args before a ``/`` are ``POSITIONAL_ONLY``.
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
    mapping: Dict[inspect.Parameter, List[str]] = {}
    remaining_tokens = _parse_kw_and_flags(f, tokens, mapping)

    for parameter in inspect.signature(f).parameters.values():
        if parameter.annotation is UnknownTokens:
            mapping[parameter] = remaining_tokens
            remaining_tokens = []
            break

    # TODO: should this be before checking for UnknownTokens?
    remaining_tokens = _parse_pos(f, remaining_tokens, mapping)

    coerced = {}
    for parameter, parameter_tokens in mapping.items():
        _, p = get_hint_parameter(parameter.annotation)

        # This is a little jank, but works for all current use-cases
        for parameter_token in parameter_tokens:
            if not isinstance(parameter_token, str):
                coerced[parameter] = parameter_tokens[0]
                break
        else:
            action = p.coercion if p.coercion else coerce

            if parameter.kind == parameter.VAR_KEYWORD:
                coerced[parameter] = {}
                for key, values in parameter_tokens.items():  # pyright: ignore[reportGeneralTypeIssues]
                    coerced[parameter][key] = action(parameter.annotation, *values)
            else:
                coerced[parameter] = action(parameter.annotation, *parameter_tokens)

    bound = _bind(f, coerced)
    return bound, remaining_tokens
