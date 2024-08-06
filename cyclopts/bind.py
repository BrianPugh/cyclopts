import inspect
import itertools
import os
import shlex
import sys
from contextlib import suppress
from typing import (
    Callable,
    Dict,
    Iterable,
    List,
    Tuple,
    Type,
    Union,
    get_args,
    get_origin,
)

import cyclopts.utils
from cyclopts._convert import _bool, _DictHint, accepts_keys, resolve, token_count
from cyclopts.argument import ArgumentCollection, Token
from cyclopts.config import Unset
from cyclopts.exceptions import (
    CoercionError,
    CycloptsError,
    MissingArgumentError,
    MixedArgumentError,
    RepeatArgumentError,
    UnknownOptionError,
    ValidationError,
)
from cyclopts.parameter import get_hint_parameter, validate_command
from cyclopts.resolve import ResolvedCommand
from cyclopts.utils import ParameterDict


def normalize_tokens(tokens: Union[None, str, Iterable[str]]) -> List[str]:
    if tokens is None:
        tokens = sys.argv[1:]  # Remove the executable
    elif isinstance(tokens, str):
        tokens = shlex.split(tokens)
    else:
        tokens = list(tokens)
    return tokens


def _cli_kws_to_f_kws(cli_keys: List[str]) -> List[str]:
    """Only used for converting unknown CLI key/value keys for ``**kwargs``."""
    out = []
    for cli_key in cli_keys:
        assert cli_key.startswith("--")
        cli_key = cli_key[2:]  # strip off leading "--"
        cli_key = cli_key.replace("-", "_")
        out.append(cli_key)
    return out


def _check_repeat_arg(
    mapping: Dict,
    iparam: inspect.Parameter,
    keys: List[str],
) -> bool:
    """Checks if iparam/keys agrees with previously supplied CLI arguments.

    Returns
    -------
    bool
        True if this specific iparam/key combo has been supplied before.
    """
    if iparam.kind is iparam.VAR_KEYWORD:
        assert keys
        d = mapping.get(iparam, {})
    else:
        if not keys:
            return iparam in mapping
        d = mapping.get(iparam, {} if keys else [])

    for key in keys[:-1]:
        if isinstance(d, list):
            raise MixedArgumentError(parameter=iparam)
        d = d.get(key, {})

    return keys[-1] in d


def _get_mapping_values(
    mapping: Dict,
    iparam: inspect.Parameter,
    keys: List[str],
) -> List:
    if iparam.kind is iparam.VAR_KEYWORD:
        assert keys
        d = mapping.setdefault(iparam, {})
    else:
        d = mapping.setdefault(iparam, {} if keys else [])

    for i, key in enumerate(keys):
        if isinstance(d, list):
            raise MixedArgumentError(parameter=iparam)
        is_last = i == len(keys) - 1

        d = d.setdefault(key, [] if is_last else {})
    if not isinstance(d, list):
        raise MixedArgumentError(parameter=iparam)
    return d


def _parse_kw_and_flags_3(argument_collection: ArgumentCollection, tokens):
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
                # TODO: fix exceptions to have the Argument
                raise MissingArgumentError(tokens_so_far=cli_values)

            for index, cli_value in enumerate(cli_values):
                argument.append(Token(cli_option, cli_value, source="cli", index=index, keys=leftover_keys))

    return unused_tokens


def _parse_kw_and_flags(command: ResolvedCommand, tokens, mapping):
    kwargs_iparam = next((x for x in command.iparams if x.kind == x.VAR_KEYWORD), None)

    if kwargs_iparam:
        mapping[kwargs_iparam] = {}

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

        cli_values = []
        consume_count = 0

        if "=" in token:
            cli_option, cli_value = token.split("=", 1)
            cli_values.append(cli_value)
            consume_count -= 1
        else:
            cli_option = token

        cli_keys = cli_option.split(".")

        # Determine the iparam
        try:
            iparam, implicit_value = command.cli2parameter[cli_keys[0]]
            cli_keys = cli_keys[1:]
        except KeyError:
            if kwargs_iparam:
                iparam = kwargs_iparam
                cli_keys = _cli_kws_to_f_kws(cli_keys)
                implicit_value = None
            else:
                unused_tokens.append(token)
                continue
        # Generally, keys in dictionary/objects aren't allowed to have dashes.
        cli_keys = [cli_key.replace("-", "_") for cli_key in cli_keys]

        cparam = command.iparam_to_cparam[iparam]

        is_repeated = _check_repeat_arg(mapping, iparam, cli_keys)

        if implicit_value is not None:
            # A flag was parsed
            if cli_values:
                # A value was parsed from "--key=value", and the ``value`` is in ``cli_values``.
                # Immediately convert to actual boolean datatype.
                if _bool(cli_values[-1]):
                    # --negative-flag=true or --empty-flag=true
                    cli_values[-1] = implicit_value
                else:
                    # --negative-flag=false or --empty-flag=false
                    if implicit_value in (True, False):  # This is a boolean "--no-" flag.
                        cli_values[-1] = not implicit_value
                    else:  # This is an iterable "--empty-"
                        # Just skip it, it doesn't mean anything.
                        continue
            else:
                cli_values.append(implicit_value)
            tokens_per_element, consume_all = 0, False
        else:
            type_ = iparam.annotation
            try:
                for cli_key in cli_keys[1:] if iparam is kwargs_iparam else cli_keys:
                    type_ = _DictHint(type_)[cli_key]
            except KeyError:
                raise UnknownOptionError(token=token) from None

            tokens_per_element, consume_all = token_count(type_)

            if is_repeated and not consume_all:
                raise RepeatArgumentError(parameter=iparam)

            with suppress(IndexError):
                if consume_all:
                    for j in itertools.count():
                        token = tokens[i + 1 + j]
                        if not cparam.allow_leading_hyphen and _is_option_like(token):
                            break
                        cli_values.append(token)
                        skip_next_iterations += 1
                else:
                    consume_count += tokens_per_element
                    for j in range(consume_count):
                        token = tokens[i + 1 + j]
                        if not cparam.allow_leading_hyphen:
                            _validate_is_not_option_like(token)
                        cli_values.append(token)
                        skip_next_iterations += 1

            if not cli_values or len(cli_values) % tokens_per_element:
                raise MissingArgumentError(parameter=iparam, tokens_so_far=cli_values)

        # Update mapping
        existing_cli_values = _get_mapping_values(mapping, iparam, cli_keys)

        existing_cli_values.extend(cli_values)
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


def _parse_pos_3(
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
                raise MissingArgumentError(parameter=argument.iparam, tokens_so_far=tokens)

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


def _parse_pos(
    command: ResolvedCommand,
    tokens: Iterable[str],
    mapping: ParameterDict,
) -> List[str]:
    tokens = list(tokens)

    def remaining_parameters():
        for iparam, cparam in command.iparam_to_cparam.items():
            _, consume_all = token_count(iparam)
            if iparam in mapping and not consume_all:
                continue
            if iparam.kind is iparam.KEYWORD_ONLY:  # pragma: no cover
                # the kwargs parameter should always be in mapping.
                break
            yield iparam, cparam

    for iparam, cparam in remaining_parameters():
        if not tokens:
            break

        if iparam.kind is iparam.VAR_POSITIONAL:  # ``*args``
            mapping.setdefault(iparam, [])
            for token in tokens:
                if not cparam.allow_leading_hyphen:
                    _validate_is_not_option_like(token)

                mapping[iparam].append(token)
            tokens = []
            break

        tokens_per_element, consume_all = token_count(iparam)

        if consume_all:
            # Prepend the positional values to the keyword values.
            mapping.setdefault(iparam, [])
            pos_tokens = []

            for token in tokens:
                if not cparam.allow_leading_hyphen:
                    _validate_is_not_option_like(token)
                pos_tokens.append(token)
            mapping[iparam] = pos_tokens + mapping[iparam]
            tokens = []
            break

        tokens_per_element = max(1, tokens_per_element)

        if len(tokens) < tokens_per_element:
            raise MissingArgumentError(parameter=iparam, tokens_so_far=tokens)

        mapping.setdefault(iparam, [])
        for token in tokens[:tokens_per_element]:
            if not cparam.allow_leading_hyphen:
                _validate_is_not_option_like(token)

            mapping[iparam].append(token)

        tokens = tokens[tokens_per_element:]

    return tokens


def _parse_env_3(argument_collection):
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


def _parse_env(command: ResolvedCommand, mapping: ParameterDict):
    """Populate argument defaults from environment variables.

    In cyclopts, arguments are parsed with the following priority:

    1. CLI-provided values
    2. Values parsed from ``Parameter.env_var``.
    3. Default values from the function signature.
    """
    for iparam, cparam in command.iparam_to_cparam.items():
        if iparam in mapping:
            # Don't check environment variables for already-parsed parameters.
            continue

        for env_var_name in cparam.env_var:
            try:
                env_var_value = os.environ[env_var_name]
            except KeyError:
                pass
            else:
                mapping[iparam] = cparam.env_var_split(iparam.annotation, env_var_value)
                break


def _is_required(iparam: inspect.Parameter) -> bool:
    """A token must be provided for the given :class:``inspect.Parameter``."""
    return iparam.default is iparam.empty and iparam.kind not in (
        iparam.VAR_KEYWORD,
        iparam.VAR_POSITIONAL,
    )


def _bind(
    command: ResolvedCommand,
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

    for iparam in command.iparams:
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

    bound = command.bind(*f_pos, **f_kwargs)
    return bound


def _bind_3(
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


def _convert(command: ResolvedCommand, mapping: ParameterDict) -> ParameterDict:
    coerced = ParameterDict()
    for iparam, parameter_tokens in mapping.items():
        cparam = command.iparam_to_cparam[iparam]
        type_ = get_hint_parameter(iparam)[0]

        # Checking if parameter_token is a string is a little jank,
        # but works for all current use-cases.
        for parameter_token in parameter_tokens:
            if not isinstance(parameter_token, str):
                # A token would be non-string if it's the implied-value (from a flag).
                coerced[iparam] = parameter_token
                break
        else:
            try:
                if iparam.kind == iparam.VAR_KEYWORD:
                    coerced[iparam] = {}
                    for key, values in parameter_tokens.items():
                        val = cparam.converter(type_, values)
                        for validator in cparam.validator:
                            validator(type_, val)
                        coerced[iparam][key] = val
                elif iparam.kind == iparam.VAR_POSITIONAL:
                    val = cparam.converter(List[type_], parameter_tokens)
                    for validator in cparam.validator:
                        for v in val:
                            validator(type_, v)
                    coerced[iparam] = val
                else:
                    val = cparam.converter(type_, parameter_tokens)
                    for validator in cparam.validator:
                        validator(type_, val)
                    coerced[iparam] = val
            except (CoercionError, MissingArgumentError) as e:
                e.parameter = iparam
                raise
            except (AssertionError, ValueError, TypeError):
                raise ValueError  # TODO: this whole function is getting deleted.
                # raise ValidationError(value=e.args[0] if e.args else "", parameter=iparam) from e
    return coerced


def _walk_name_iparam_implicit_value(command: ResolvedCommand):
    for name, (iparam, implicit_value) in command.cli2parameter.items():
        if not name.startswith("--"):
            continue
        name = name[2:]  # Strip off the leading "--"
        yield name, iparam, implicit_value


def _parse_configs_3(argument_collection: ArgumentCollection, configs):
    for config in configs:
        # Each ``config`` is a partial that already has apps and commands provided.
        config(argument_collection)
        # TODO: validate argument_collection after every config?


def _parse_configs(command: ResolvedCommand, mapping: ParameterDict, configs):
    """Iteratively apply each ``config`` callable to the token mapping."""
    # Remap `mapping` back to CLI values for config parsing.
    cli_kwargs: Dict[str, Union[Unset, list]] = {}
    for cli_name, iparam, implicit_value in _walk_name_iparam_implicit_value(command):
        # Assign existing tokens to the "positive" flag/keyword if it exists.
        # Otherwise, assign it to the "negative" flag/keyword.
        cparam = command.iparam_to_cparam[iparam]
        if implicit_value is None or cparam.name == ("",) or implicit_value:
            with suppress(KeyError):
                cli_kwargs[cli_name] = mapping[iparam]

    def repopulate_unset():
        # Repopulate deleted keys with ``Unset``
        for name, iparam, _ in _walk_name_iparam_implicit_value(command):
            if name not in cli_kwargs or not cli_kwargs[name]:
                cli_kwargs[name] = Unset(iparam, {x[2:] for x in command.parameter2cli[iparam] if x.startswith("--")})

    repopulate_unset()

    for config in configs:
        config(cli_kwargs)
        repopulate_unset()

        # Validate that ``config`` produced reasonable modifications.
        # If there is an error at this stage, it is a developer-error of the config object
        for cli_name, values in cli_kwargs.items():
            if not isinstance(cli_name, str):
                raise TypeError(f"{config.func!r} produced non-str key {cli_name!r}.")
            if isinstance(values, Unset):
                continue
            if not isinstance(values, list):
                raise TypeError(f"{config.func!r} produced non-list value for key {cli_name!r}.")
            if "--" + cli_name not in command.cli2parameter:
                raise ValueError(f"{config.func!r} produced unknown key {cli_name!r}.")
            if len(values) > 1:
                # They all must be strings, or reinterpret as a list-of-list
                for value in values:
                    if not isinstance(value, str):
                        raise TypeError(f"{config.func!r} produced non-str element value for key {cli_name!r}.")

    # Rebind updated values to ``mapping``
    set_iparams = set()
    for cli_name, value in cli_kwargs.items():
        iparam, _ = command.cli2parameter["--" + cli_name]
        if isinstance(value, Unset):
            if not value.related_set(cli_kwargs):
                # No other "aliases" have provided values, safe to delete.
                # This can occur if a config Unsets/deletes a value.
                mapping.pop(iparam, None)
        elif id(iparam) in set_iparams and value != mapping[iparam]:
            # Intended to detect if a config sets different
            # values to different aliases of the same parameter.
            raise RepeatArgumentError(parameter=iparam)
        else:
            mapping[iparam] = value
            set_iparams.add(id(iparam))


def create_bound_arguments_3(
    func: Callable,
    argument_collection: ArgumentCollection,
    tokens: List[str],
    configs: Iterable[Callable],
) -> Tuple[inspect.BoundArguments, List[str]]:
    unused_tokens = []

    validate_command(func)  # TODO: is this the appropriate location?

    try:
        # Build up a mapping of inspect.Parameter->List[str]
        unused_tokens = _parse_kw_and_flags_3(argument_collection, tokens)
        unused_tokens = _parse_pos_3(argument_collection, unused_tokens)
        _parse_env_3(argument_collection)
        _parse_configs_3(argument_collection, configs)

        # TODO: apply group converters
        # TODO: apply group validators

        iparam_to_value = argument_collection.convert()
        bound = _bind_3(func, iparam_to_value)

        for iparam in argument_collection.iparams:
            if _is_required(iparam) and iparam.name not in bound.arguments:
                raise MissingArgumentError(parameter=iparam)

    except CycloptsError as e:
        e.root_input_tokens = tokens
        # e.cli2parameter = command.cli2parameter
        # e.parameter2cli = command.parameter2cli
        e.unused_tokens = unused_tokens
        raise

    return bound, unused_tokens


def create_bound_arguments(
    command: ResolvedCommand,
    tokens: List[str],
    configs: Iterable[Callable],
) -> Tuple[inspect.BoundArguments, List[str]]:
    """Parse and coerce CLI tokens to match a function's signature.

    Parameters
    ----------
    command: ResolvedCommand
    tokens: List[str]
        CLI tokens to parse and coerce to match ``f``'s signature.

    Returns
    -------
    bound: inspect.BoundArguments
        The converted and bound positional and keyword arguments for ``f``.

    unused_tokens: List[str]
        Remaining tokens that couldn't be matched to ``f``'s signature.
    """
    # ``mapping`` maps inspect.Parameter to list of tokens/values.
    #    * Each token is USUALLY a string and needs further casting/interpretation.
    #    * However, if it's NOT a string, the value should be used as-is.
    #        * This is used for implicit-value keyword tokens like "--flag" and "--empty-iterable"
    # ``mapping`` is updated inplace throughout this function.
    mapping = ParameterDict()
    unused_tokens = []

    validate_command(command.command)

    try:
        # Build up a mapping of inspect.Parameter->List[str]
        unused_tokens = _parse_kw_and_flags(command, tokens, mapping)
        unused_tokens = _parse_pos(command, unused_tokens, mapping)
        _parse_env(command, mapping)
        # _parse_configs(command, mapping, configs)

        # For each parameter, convert the list of string tokens.
        coerced = _convert(command, mapping)
        bound = _bind(command, coerced)

        # Apply group converters
        for group, iparams in command.groups_iparams:
            if not group.converter:
                continue
            names = tuple(x.name for x in iparams)
            converted = group.converter(**{k: bound.arguments[k] for k in names if k in bound.arguments})
            for name in names:  # Merge back in the result
                try:
                    bound.arguments[name] = converted[name]
                except KeyError:
                    bound.arguments.pop(name, None)

        # Apply group validators
        try:
            for group, iparams in command.groups_iparams:
                names = tuple(x.name for x in iparams)
                for validator in group.validator:  # pyright: ignore
                    validator(**{k: bound.arguments[k] for k in names if k in bound.arguments})
        except (AssertionError, ValueError, TypeError) as e:
            # group will always be set from the above for loop if an exception occurs.
            raise ValidationError(
                value=e.args[0] if e.args else "",
                group=group,  # pyright: ignore[reportPossiblyUnboundVariable]
            ) from e

        for iparam in command.iparams:
            if _is_required(iparam) and iparam.name not in bound.arguments:
                raise MissingArgumentError(parameter=iparam)

    except CycloptsError as e:
        e.target = command.command
        e.root_input_tokens = tokens
        e.cli2parameter = command.cli2parameter
        e.parameter2cli = command.parameter2cli
        e.unused_tokens = unused_tokens
        raise

    return bound, unused_tokens
