import inspect
import itertools
import os
import shlex
import sys
from collections.abc import Callable, Iterable, Sequence
from contextlib import suppress
from functools import partial
from typing import TYPE_CHECKING, get_origin

from cyclopts._convert import _bool
from cyclopts.annotations import resolve_optional
from cyclopts.argument import ArgumentCollection
from cyclopts.exceptions import (
    ArgumentOrderError,
    CoercionError,
    CombinedShortOptionError,
    CycloptsError,
    MissingArgumentError,
    UnknownOptionError,
    ValidationError,
)
from cyclopts.field_info import POSITIONAL_ONLY, POSITIONAL_OR_KEYWORD
from cyclopts.token import Token
from cyclopts.utils import UNSET, is_option_like

if sys.version_info < (3, 11):  # pragma: no cover
    pass
else:  # pragma: no cover
    pass


if TYPE_CHECKING:
    from cyclopts.group import Group

CliToken = partial(Token, source="cli")


def normalize_tokens(tokens: None | str | Iterable[str]) -> list[str]:
    if tokens is None:
        tokens = sys.argv[1:]  # Remove the executable
    elif isinstance(tokens, str):
        tokens = shlex.split(tokens)
    else:
        tokens = list(tokens)
    return tokens


def _common_root_keys(argument_collection) -> tuple[str, ...]:
    if not argument_collection:
        return ()
    common = argument_collection[0].keys
    for argument in argument_collection[1:]:
        if not argument.keys:
            return ()
        for i, (common_key, argument_key) in enumerate(zip(common, argument.keys, strict=False)):
            if common_key != argument_key:
                if i == 0:
                    return ()

                common = argument.keys[:i]
                break
        common = common[: len(argument.keys)]
    return common


def _parse_kw_and_flags(
    argument_collection: ArgumentCollection,
    tokens: Sequence[str],
    *,
    end_of_options_delimiter: str = "--",
    stop_at_first_unknown: bool = False,
):
    unused_tokens, positional_only_tokens = [], []
    skip_next_iterations = 0
    if end_of_options_delimiter:
        try:
            delimiter_index = tokens.index(end_of_options_delimiter)
        except ValueError:
            pass  # end_of_options_delimiter not in token stream
        else:
            positional_only_tokens = tokens[delimiter_index:]
            tokens = tokens[:delimiter_index]
    for i, token in enumerate(tokens):
        # If the previous argument was a keyword, then this is its value
        if skip_next_iterations > 0:
            skip_next_iterations -= 1
            continue

        if not is_option_like(token, allow_numbers=True):
            if stop_at_first_unknown:
                # Stop parsing and return all remaining tokens as unused
                unused_tokens.extend(tokens[i:])
                break
            unused_tokens.append(token)
            continue

        cli_values: list[str] = []
        consume_count = 0

        # startswith("-") is redundant, but it's cheap safety.
        allow_combined_flags = token.startswith("-") and not token.startswith("--")

        if "=" in token:
            cli_option, cli_value = token.split("=", 1)
            cli_values.append(cli_value)
            consume_count -= 1

            # Cannot have combined flags when an "=" is parsed.
            allow_combined_flags = False
        else:
            cli_option = token

        matches = []
        try:
            matches.append(argument_collection.match(cli_option))
        except ValueError:
            # Length has to be greater than 2 (hyphen + character) to be exploded.
            if allow_combined_flags and len(token) > 2:
                # since no direct match was found, try to see if this was a combination of short flags.
                flags = [f"-{x}" for x in cli_option.lstrip("-")]
                for flag in flags:
                    try:
                        matches.append(argument_collection.match(flag))
                    except ValueError:
                        if stop_at_first_unknown:
                            # Can't parse this flag combination, stop here
                            unused_tokens.extend(tokens[i:])
                            return unused_tokens
                        unused_tokens.append(flag)
            else:
                if stop_at_first_unknown:
                    # Unknown option, stop parsing and return all remaining tokens
                    unused_tokens.extend(tokens[i:])
                    return unused_tokens
                unused_tokens.append(token)
                continue
        for argument, leftover_keys, implicit_value in matches:
            if implicit_value is not UNSET:
                # A flag was parsed
                if cli_values:
                    try:
                        coerced_value = _bool(cli_values[-1])
                    except CoercionError as e:
                        if e.token is None:
                            e.token = CliToken(keyword=cli_option)
                        if e.argument is None:
                            e.argument = argument
                        raise
                    if coerced_value:  # --positive-flag=true or --negative-flag=true or --empty-flag=true
                        argument.append(CliToken(keyword=cli_option, implicit_value=implicit_value))
                    else:  # --positive-flag=false or --negative-flag=false or --empty-flag=false
                        if isinstance(implicit_value, bool):
                            argument.append(CliToken(keyword=cli_option, implicit_value=not implicit_value))
                        else:
                            # A negative for a non-bool field doesn't really make sense;
                            # e.g. --empty-list=False
                            # So we'll just silently skip it, as it may make bash scripting easier.
                            pass
                else:
                    argument.append(CliToken(keyword=cli_option, implicit_value=implicit_value))
            elif len(matches) != 1:
                raise CombinedShortOptionError(msg=f"Cannot combine flags and short-options in token {cli_option}")
            else:
                tokens_per_element, consume_all = argument.token_count(leftover_keys)

                # Consume the appropriate number of tokens
                with suppress(IndexError):
                    if consume_all and argument.parameter.consume_multiple:
                        for j in itertools.count():
                            token = tokens[i + 1 + j]
                            if not argument.parameter.allow_leading_hyphen and is_option_like(token):
                                break
                            cli_values.append(token)
                            skip_next_iterations += 1
                    else:
                        consume_count += tokens_per_element
                        for j in range(consume_count):
                            if len(cli_values) == 1 and (
                                argument._should_attempt_json_dict(cli_values)
                                or argument._should_attempt_json_list(cli_values, leftover_keys)
                            ):
                                tokens_per_element = 1
                                # Assume that the contents are json and that we shouldn't
                                # consume any additional tokens.
                                break

                            token = tokens[i + 1 + j]
                            if not argument.parameter.allow_leading_hyphen and is_option_like(token):
                                raise MissingArgumentError(
                                    argument=argument,
                                    tokens_so_far=cli_values,
                                )
                            cli_values.append(token)
                            skip_next_iterations += 1

                if not cli_values:
                    # No values were consumed after the keyword
                    if consume_all and argument.parameter.consume_multiple:
                        # Allow empty iterables (e.g., --urls with no values behaves like --empty-urls)
                        hint = resolve_optional(argument.hint)
                        empty_container = (get_origin(hint) or hint)()
                        argument.append(
                            CliToken(keyword=cli_option, implicit_value=empty_container, keys=leftover_keys)
                        )
                    else:
                        # Non-iterables or consume_multiple=False require at least one value
                        raise MissingArgumentError(argument=argument, tokens_so_far=cli_values)
                elif len(cli_values) % tokens_per_element:
                    # For multi-token elements (e.g., tuples), ensure we have complete sets
                    raise MissingArgumentError(argument=argument, tokens_so_far=cli_values)
                else:
                    # Normal case: append the consumed values
                    for index, cli_value in enumerate(cli_values):
                        argument.append(CliToken(keyword=cli_option, value=cli_value, index=index, keys=leftover_keys))

    unused_tokens.extend(positional_only_tokens)
    return unused_tokens


def _future_positional_only_token_count(argument_collection: ArgumentCollection, starting_index: int) -> int:
    n_tokens_to_leave = 0
    for i in itertools.count():
        try:
            argument, _, _ = argument_collection.match(starting_index + i)
        except ValueError:
            break
        if argument.field_info.kind is not POSITIONAL_ONLY:
            break
        future_tokens_per_element, future_consume_all = argument.token_count()
        if future_consume_all:
            raise ValueError("Cannot have 2 all-consuming positional arguments.")
        n_tokens_to_leave += future_tokens_per_element
    return n_tokens_to_leave


def _preprocess_positional_tokens(tokens: Sequence[str], end_of_options_delimiter: str) -> list[tuple[str, bool]]:
    try:
        delimiter_index = tokens.index(end_of_options_delimiter)
        return [(t, False) for t in tokens[:delimiter_index]] + [(t, True) for t in tokens[delimiter_index + 1 :]]
    except ValueError:  # delimiter not found
        return [(t, False) for t in tokens]


def _parse_pos(
    argument_collection: ArgumentCollection,
    tokens: list[str],
    *,
    end_of_options_delimiter: str = "--",
) -> list[str]:
    prior_positional_or_keyword_supplied_as_keyword_arguments = []

    if not tokens:
        return []

    tokens_and_force_positional = _preprocess_positional_tokens(tokens, end_of_options_delimiter)

    for i in itertools.count():
        try:
            argument, _, _ = argument_collection.match(i)
        except ValueError:
            break
        if argument.field_info.kind is POSITIONAL_OR_KEYWORD:
            if argument.tokens and argument.tokens[0].keyword is not None:
                prior_positional_or_keyword_supplied_as_keyword_arguments.append(argument)
                # Continue in case we hit a VAR_POSITIONAL argument.
                continue
            if prior_positional_or_keyword_supplied_as_keyword_arguments:
                token = tokens[0]
                if not argument.parameter.allow_leading_hyphen and is_option_like(token):
                    # It's more meaningful to interpret the token as an intended option,
                    # rather than an intended positional value for ``argument``.
                    raise UnknownOptionError(token=CliToken(value=token), argument_collection=argument_collection)
                else:
                    raise ArgumentOrderError(
                        argument=argument,
                        prior_positional_or_keyword_supplied_as_keyword_arguments=prior_positional_or_keyword_supplied_as_keyword_arguments,
                        token=tokens_and_force_positional[0][0],
                    )

        tokens_per_element, consume_all = argument.token_count()
        tokens_per_element = max(1, tokens_per_element)

        if consume_all and argument.field_info.kind is POSITIONAL_ONLY:
            # POSITIONAL_ONLY parameters can come after a POSITIONAL_ONLY list/iterable.
            # This makes it easier to create programs that do something like:
            #    $ python my-program.py input_folder/*.csv output.csv

            # Need to see how many tokens we need to leave for subsequent POSITIONAL_ONLY parameters.
            n_tokens_to_leave = _future_positional_only_token_count(argument_collection, i + 1)
        else:
            n_tokens_to_leave = 0

        new_tokens = []
        while (len(tokens_and_force_positional) - n_tokens_to_leave) > 0:
            if (len(tokens_and_force_positional) - n_tokens_to_leave) < tokens_per_element:
                raise MissingArgumentError(
                    argument=argument,
                    tokens_so_far=[x[0] for x in tokens_and_force_positional],
                )

            for index, (token, force_positional) in enumerate(tokens_and_force_positional[:tokens_per_element]):
                if not force_positional and not argument.parameter.allow_leading_hyphen and is_option_like(token):
                    raise UnknownOptionError(token=CliToken(value=token), argument_collection=argument_collection)
                new_tokens.append(CliToken(value=token, index=index))
            tokens_and_force_positional = tokens_and_force_positional[tokens_per_element:]
            if not consume_all:
                break
        argument.tokens[:0] = new_tokens  # Prepend the new tokens to the argument.
        if not tokens_and_force_positional:
            break

    return [x[0] for x in tokens_and_force_positional]


def _parse_env(argument_collection: ArgumentCollection):
    for argument in argument_collection:
        if argument.tokens:
            # Don't check environment variables for parameters that already have values from CLI.
            continue
        assert argument.parameter.env_var is not None
        for env_var_name in argument.parameter.env_var:
            try:
                env_var_value = os.environ[env_var_name]
            except KeyError:
                pass
            else:
                argument.tokens.append(Token(keyword=env_var_name, value=env_var_value, source="env"))
                break


def _bind(
    argument_collection: ArgumentCollection,
    func: Callable,
):
    """Bind the mapping to the function signature."""
    bound = inspect.signature(func).bind_partial()
    for argument in argument_collection._root_arguments:
        if argument.value is not UNSET:
            bound.arguments[argument.field_info.name] = argument.value
    return bound


def _parse_configs(argument_collection: ArgumentCollection, configs):
    for config in configs:
        # Each ``config`` is a partial that already has apps and commands provided.
        config(argument_collection)


def _sort_group(argument_collection) -> list[tuple["Group", ArgumentCollection]]:
    """Sort groups into "deepest common-root-keys first" order.

    This is imperfect, but probably works sufficiently well for practical use-cases.
    """
    out = {}
    # Sort alphabetically by group-name to enfroce some determinism.
    for i, group in enumerate(sorted(argument_collection.groups, key=lambda x: x.name)):
        group_arguments = argument_collection.filter_by(group=group)
        common_root_keys = _common_root_keys(group_arguments)
        # Add i to key so that we don't get collisions.
        out[(common_root_keys, i)] = (group, group_arguments.filter_by(keys_prefix=common_root_keys))
    return [ga for _, ga in sorted(out.items(), reverse=True)]


def create_bound_arguments(
    func: Callable,
    argument_collection: ArgumentCollection,
    tokens: list[str],
    configs: Iterable[Callable],
    *,
    end_of_options_delimiter: str = "--",
) -> tuple[inspect.BoundArguments, list[str]]:
    """Parse and coerce CLI tokens to match a function's signature.

    Parameters
    ----------
    func: Callable
        Function.
    argument_collection: ArgumentCollection
    tokens: list[str]
        CLI tokens to parse and coerce to match ``f``'s signature.
    configs: Iterable[Callable]
    end_of_options_delimiter: str
        Everything after this special token is forced to be supplied as a positional argument.

    Returns
    -------
    bound: inspect.BoundArguments
        The converted and bound positional and keyword arguments for ``f``.

    unused_tokens: list[str]
        Remaining tokens that couldn't be matched to ``f``'s signature.
    """
    unused_tokens = tokens

    try:
        unused_tokens = _parse_kw_and_flags(
            argument_collection, unused_tokens, end_of_options_delimiter=end_of_options_delimiter
        )
        unused_tokens = _parse_pos(
            argument_collection, unused_tokens, end_of_options_delimiter=end_of_options_delimiter
        )

        _parse_env(argument_collection)
        _parse_configs(argument_collection, configs)

        argument_collection._convert()
        groups_with_arguments = _sort_group(argument_collection)
        try:
            for group, group_arguments in groups_with_arguments:
                for validator in group.validator:  # pyright: ignore
                    validator(group_arguments)  # pyright: ignore[reportOptionalCall]
        except (AssertionError, ValueError, TypeError) as e:
            raise ValidationError(exception_message=e.args[0] if e.args else "", group=group) from e  # pyright: ignore

        for argument in argument_collection:
            # if a dict-like argument is missing, raise a MissingArgumentError on the first
            # required child (as opposed generically to the root dict-like object).
            if not argument.parameter.parse or not argument.field_info.required or argument.keys:
                continue
            if not argument.has_tokens:
                raise MissingArgumentError(argument=argument)

        bound = _bind(argument_collection, func)
    except CycloptsError as e:
        e.root_input_tokens = tokens
        e.unused_tokens = unused_tokens
        raise

    return bound, unused_tokens
