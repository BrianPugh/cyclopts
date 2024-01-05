import inspect
import os
import shlex
import sys
from typing import Any, Callable, Dict, Iterable, List, Optional, Tuple, Union, get_origin

from cyclopts.coercion import resolve, token_count
from cyclopts.exceptions import (
    CoercionError,
    CycloptsError,
    MissingArgumentError,
    RepeatArgumentError,
    ValidationError,
)
from cyclopts.group import Group
from cyclopts.group_extractors import groups_from_function, iparam_to_groups
from cyclopts.parameter import Parameter, get_hint_parameter, get_names, validate_command
from cyclopts.utils import ParameterDict


def normalize_tokens(tokens: Union[None, str, Iterable[str]]) -> List[str]:
    if tokens is None:
        tokens = sys.argv[1:]  # Remove the executable
    elif isinstance(tokens, str):
        tokens = shlex.split(tokens)
    else:
        tokens = list(tokens)
    return tokens


def cli2parameter(
    f: Callable,
    default_parameter: Parameter,
    group_arguments: Group,
    group_parameters: Group,
) -> Dict[str, Tuple[inspect.Parameter, Any]]:
    """Creates a dictionary mapping CLI keywords to python keywords.

    Typically the mapping is something like::

        {"--foo": (<Parameter "foo">, None)}

    Each value is a tuple containing:

    1. The corresponding ``inspect.Parameter``.
    2. A predefined value. If this value is ``None``, the value should be
       inferred from subsequent tokens.
    """
    mapping: Dict[str, Tuple[inspect.Parameter, Any]] = {}
    signature = inspect.signature(f)
    for iparam in signature.parameters.values():
        groups = iparam_to_groups(iparam, default_parameter, group_arguments, group_parameters)
        _, cparam = get_hint_parameter(iparam.annotation, default_parameter, *(x.default_parameter for x in groups))

        if not cparam.parse:
            continue

        if iparam.kind in (iparam.POSITIONAL_OR_KEYWORD, iparam.KEYWORD_ONLY):
            hint = resolve(iparam.annotation)
            keys = get_names(iparam, default_parameter, *(x.default_parameter for x in groups))

            for key in keys:
                mapping[key] = (iparam, True if hint is bool else None)

            for key in cparam.get_negatives(hint, *keys):
                mapping[key] = (iparam, (get_origin(hint) or hint)())

    return mapping


def parameter2cli(
    f: Callable,
    default_parameter: Parameter,
    group_arguments: Group,
    group_parameters: Group,
) -> ParameterDict:
    c2p = cli2parameter(f, default_parameter, group_arguments, group_parameters)
    p2c = ParameterDict()

    for cli, tup in c2p.items():
        iparam = tup[0]
        p2c.setdefault(iparam, [])
        p2c[iparam].append(cli)

    signature = inspect.signature(f)
    for iparam in signature.parameters.values():
        groups = iparam_to_groups(iparam, default_parameter, group_arguments, group_parameters)
        _, cparam = get_hint_parameter(iparam.annotation, default_parameter, *(x.default_parameter for x in groups))

        if not cparam.parse:
            continue

        # POSITIONAL_OR_KEYWORD and KEYWORD_ONLY already handled in cli2parameter
        if iparam.kind in (iparam.POSITIONAL_ONLY, iparam.VAR_KEYWORD, iparam.VAR_POSITIONAL):
            p2c[iparam] = get_names(iparam, default_parameter, *(x.default_parameter for x in groups))

    return p2c


def _cli_kw_to_f_kw(cli_key: str):
    """Only used for converting unknown CLI key/value keys for ``**kwargs``."""
    assert cli_key.startswith("--")
    cli_key = cli_key[2:]  # strip off leading "--"
    cli_key = cli_key.replace("-", "_")
    return cli_key


def _parse_kw_and_flags(
    f,
    tokens,
    mapping,
    default_parameter: Parameter,
    group_arguments: Group,
    group_parameters: Group,
):
    cli2kw = cli2parameter(f, default_parameter, group_arguments, group_parameters)
    kwargs_iparam = next((p for p in inspect.signature(f).parameters.values() if p.kind == p.VAR_KEYWORD), None)

    if kwargs_iparam:
        mapping[kwargs_iparam] = {}

    unused_tokens = []

    skip_next_iterations = 0
    for i, token in enumerate(tokens):
        # If the previous argument was a keyword, then this is its value
        if skip_next_iterations > 0:
            skip_next_iterations -= 1
            continue

        if not token.startswith("-"):
            unused_tokens.append(token)
            continue

        cli_values = []
        kwargs_key = None
        consume_count = 0

        if "=" in token:
            cli_key, cli_value = token.split("=", 1)
            cli_values.append(cli_value)
            consume_count -= 1
        else:
            cli_key = token

        try:
            iparam, implicit_value = cli2kw[cli_key]
        except KeyError:
            if kwargs_iparam:
                iparam = kwargs_iparam
                kwargs_key = _cli_kw_to_f_kw(cli_key)
                implicit_value = None
            else:
                unused_tokens.append(token)
                continue

        groups = iparam_to_groups(iparam, default_parameter, group_arguments, group_parameters)

        if implicit_value is not None:
            cli_values.append(implicit_value)
        else:
            consume_count += max(
                1, token_count(iparam.annotation, default_parameter, *(x.default_parameter for x in groups))[0]
            )

            try:
                for j in range(consume_count):
                    cli_values.append(tokens[i + 1 + j])
            except IndexError:
                raise MissingArgumentError(parameter=iparam, tokens_so_far=cli_values) from None

        skip_next_iterations = consume_count

        _, repeatable = token_count(iparam.annotation, default_parameter, *(x.default_parameter for x in groups))
        if iparam is kwargs_iparam:
            assert kwargs_key is not None
            if kwargs_key in mapping[iparam] and not repeatable:
                raise RepeatArgumentError(parameter=iparam)
            mapping[iparam].setdefault(kwargs_key, [])
            mapping[iparam][kwargs_key].extend(cli_values)
        else:
            if iparam in mapping and not repeatable:
                raise RepeatArgumentError(parameter=iparam)

            mapping.setdefault(iparam, [])
            mapping[iparam].extend(cli_values)

    return unused_tokens


def _parse_pos(
    f: Callable,
    tokens: Iterable[str],
    mapping: ParameterDict,
    default_parameter: Parameter,
    group_arguments: Group,
    group_parameters: Group,
) -> List[str]:
    tokens = list(tokens)
    signature = inspect.signature(f)

    def remaining_parameters():
        for iparam in signature.parameters.values():
            groups = iparam_to_groups(iparam, default_parameter, group_arguments, group_parameters)
            _, cparam = get_hint_parameter(iparam.annotation, default_parameter, *(x.default_parameter for x in groups))
            if not cparam.parse:
                continue
            _, consume_all = token_count(iparam.annotation, default_parameter, *(x.default_parameter for x in groups))
            if iparam in mapping and not consume_all:
                continue
            if iparam.kind is iparam.KEYWORD_ONLY:  # pragma: no cover
                # the kwargs parameter should always be in mapping.
                break
            yield iparam

    for iparam in remaining_parameters():
        if not tokens:
            break

        if iparam.kind == iparam.VAR_POSITIONAL:  # ``*args``
            mapping[iparam] = tokens
            tokens = []
            break

        groups = iparam_to_groups(iparam, default_parameter, group_arguments, group_parameters)
        consume_count, consume_all = token_count(
            iparam.annotation, default_parameter, *(x.default_parameter for x in groups)
        )
        if consume_all:
            mapping.setdefault(iparam, [])
            mapping[iparam] = tokens + mapping[iparam]
            tokens = []
            break

        consume_count = max(1, consume_count)

        if len(tokens) < consume_count:
            raise MissingArgumentError(parameter=iparam, tokens_so_far=tokens)

        mapping[iparam] = tokens[:consume_count]
        tokens = tokens[consume_count:]

    return tokens


def _parse_env(
    f,
    mapping,
    default_parameter: Parameter,
    group_arguments: Group,
    group_parameters: Group,
):
    """Populate argument defaults from environment variables.

    In cyclopts, arguments are parsed with the following priority:

    1. CLI-provided values
    2. Values parsed from ``Parameter.env_var``.
    3. Default values from the function signature.
    """
    for iparam in inspect.signature(f).parameters.values():
        if iparam in mapping:
            # Don't check environment variables for already-parsed parameters.
            continue

        groups = iparam_to_groups(iparam, default_parameter, group_arguments, group_parameters)
        _, cparam = get_hint_parameter(iparam.annotation, default_parameter, *(x.default_parameter for x in groups))
        for env_var_name in cparam.env_var:
            try:
                env_var_value = os.environ[env_var_name]
            except KeyError:
                pass
            else:
                mapping.setdefault(iparam, [])
                mapping[iparam].append(env_var_value)
                break


def _is_required(parameter: inspect.Parameter) -> bool:
    return parameter.default is parameter.empty


def _bind(
    f: Callable,
    mapping: ParameterDict,
    default_parameter: Parameter,
    group_arguments: Group,
    group_parameters: Group,
):
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
        except KeyError:
            if _is_required(p):
                raise MissingArgumentError(parameter=p, tokens_so_far=[]) from None
            use_pos = False

    has_unparsed_parameters = False

    for iparam in signature.parameters.values():
        groups = iparam_to_groups(iparam, default_parameter, group_arguments, group_parameters)
        _, cparam = get_hint_parameter(iparam.annotation, default_parameter, *(x.default_parameter for x in groups))
        if not cparam.parse:
            has_unparsed_parameters |= _is_required(iparam)
            continue

        if use_pos and iparam.kind in (iparam.POSITIONAL_ONLY, iparam.POSITIONAL_OR_KEYWORD):
            f_pos_append(iparam)
        elif use_pos and iparam.kind is iparam.VAR_POSITIONAL:  # ``*args``
            f_pos.extend(mapping.get(iparam, []))
            use_pos = False
        elif iparam.kind is iparam.VAR_KEYWORD:
            f_kwargs.update(mapping.get(iparam, {}))
        else:
            try:
                f_kwargs[iparam.name] = mapping[iparam]
            except KeyError:
                if _is_required(iparam):
                    raise MissingArgumentError(parameter=iparam, tokens_so_far=[]) from None

    binder = signature.bind_partial if has_unparsed_parameters else signature.bind
    bound = binder(*f_pos, **f_kwargs)
    return bound


def _convert(
    mapping: ParameterDict,
    default_parameter: Parameter,
    group_arguments: Group,
    group_parameters: Group,
) -> ParameterDict:
    coerced = ParameterDict()
    for iparam, parameter_tokens in mapping.items():
        groups = iparam_to_groups(iparam, default_parameter, group_arguments, group_parameters)
        combined_parameter = Parameter.combine(default_parameter, *(x.default_parameter for x in groups))
        type_, cparam = get_hint_parameter(iparam.annotation, combined_parameter)

        if not cparam.parse:
            continue

        # Checking if parameter_token is a string is a little jank,
        # but works for all current use-cases
        for parameter_token in parameter_tokens:
            if not isinstance(parameter_token, str):
                coerced[iparam] = parameter_tokens[0]
                break
        else:
            try:
                if iparam.kind == iparam.VAR_KEYWORD:
                    coerced[iparam] = {}
                    for key, values in parameter_tokens.items():
                        val = cparam.converter(type_, *values)
                        for validator in cparam.validator:
                            validator(type_, val)
                        coerced[iparam][key] = val
                elif iparam.kind == iparam.VAR_POSITIONAL:
                    val = cparam.converter(List[type_], *parameter_tokens)
                    for validator in cparam.validator:
                        validator(type_, val)
                    coerced[iparam] = val
                else:
                    val = cparam.converter(type_, *parameter_tokens)
                    for validator in cparam.validator:
                        validator(type_, val)
                    coerced[iparam] = val
            except CoercionError as e:
                e.parameter = iparam
                raise
            except (AssertionError, ValueError, TypeError) as e:
                new_exception = ValidationError(value=e.args[0], parameter=iparam)
                raise new_exception from e
    return coerced


def create_bound_arguments(
    f: Callable,
    tokens: List[str],
    default_parameter: Optional[Parameter] = None,
    group_arguments: Optional[Group] = None,
    group_parameters: Optional[Group] = None,
) -> Tuple[inspect.BoundArguments, List[str]]:
    """Parse and coerce CLI tokens to match a function's signature.

    Parameters
    ----------
    f: Callable
        A function with (possibly) annotated parameters.
    tokens: List[str]
        CLI tokens to parse and coerce to match ``f``'s signature.
    default_parameter: Optional[Parameter]
        Default Parameter configuration.

    Returns
    -------
    bound: inspect.BoundArguments
        The converted and bound positional and keyword arguments for ``f``.

    unused_tokens: List[str]
        Remaining tokens that couldn't be matched to ``f``'s signature.
    """
    # Note: mapping is updated inplace
    mapping = ParameterDict()
    c2p, p2c = None, None
    unused_tokens = []

    default_parameter = default_parameter or Parameter()
    group_arguments = group_arguments or Group.create_default_arguments()
    group_parameters = group_parameters or Group.create_default_parameters()

    validate_command(f, default_parameter, group_arguments, group_parameters)

    try:
        c2p = cli2parameter(f, default_parameter, group_arguments, group_parameters)
        p2c = parameter2cli(f, default_parameter, group_arguments, group_parameters)
        unused_tokens = _parse_kw_and_flags(f, tokens, mapping, default_parameter, group_arguments, group_parameters)
        unused_tokens = _parse_pos(f, unused_tokens, mapping, default_parameter, group_arguments, group_parameters)
        _parse_env(f, mapping, default_parameter, group_arguments, group_parameters)
        coerced = _convert(mapping, default_parameter, group_arguments, group_parameters)
        bound = _bind(f, coerced, default_parameter, group_arguments, group_parameters)

        for group, iparams in groups_from_function(f, default_parameter, group_arguments, group_parameters):
            names = tuple(x.name for x in iparams)
            for validator in group.validator:
                validator(**{k: bound.arguments[k] for k in names if k in bound.arguments})
    except CycloptsError as e:
        e.target = f
        e.root_input_tokens = tokens
        e.cli2parameter = c2p
        e.parameter2cli = p2c
        e.unused_tokens = unused_tokens
        raise

    return bound, unused_tokens
