import inspect
import itertools
import os
import shlex
import sys
from collections.abc import Callable, Iterable, Iterator, Sequence
from contextlib import suppress
from functools import partial
from typing import TYPE_CHECKING, Any, NamedTuple, get_origin

from cyclopts._convert import _bool
from cyclopts.argument import Argument, ArgumentCollection
from cyclopts.exceptions import (
    ArgumentOrderError,
    CoercionError,
    CombinedShortOptionError,
    ConsumeMultipleError,
    CycloptsError,
    MissingArgumentError,
    RequiresEqualsError,
    UnknownOptionError,
    ValidationError,
)
from cyclopts.field_info import POSITIONAL_ONLY, POSITIONAL_OR_KEYWORD, VAR_POSITIONAL
from cyclopts.token import Token
from cyclopts.utils import UNSET, is_option_like

if sys.version_info < (3, 11):  # pragma: no cover
    pass
else:  # pragma: no cover
    pass


if TYPE_CHECKING:
    from cyclopts.group import Group

CliToken = partial(Token, source="cli")


class _KeywordMatch(NamedTuple):
    """Represents a matched CLI token with its corresponding argument."""

    matched_token: str
    """The actual CLI token that was matched (e.g., '-o', '--option')."""

    argument: Argument
    """The matched Argument object."""

    keys: tuple[str, ...]
    """Leftover keys for nested arguments."""

    implicit_value: Any
    """Implicit value if this is a flag, otherwise UNSET."""


def normalize_tokens(tokens: None | str | Iterable[str]) -> list[str]:
    if tokens is None:
        tokens = sys.argv[1:]  # Remove the executable
    elif isinstance(tokens, str):
        tokens = shlex.split(tokens)
    else:
        tokens = list(tokens)
    return tokens


class _ProbeResult(NamedTuple):
    """Result of :func:`_probe_unclaimed`."""

    unclaimed: list[tuple[int, str]]
    """Ordered ``(original_index, token)`` pairs the collection leaves
    unconsumed. For partially-consumed combined short options (e.g. ``-vd``
    where only ``-v`` is known), the unconsumed remainder appears as synthetic
    single-flag tokens (``-d``) sharing the original index."""

    kw_claims: dict[int, tuple[str, str | None]]
    """The keyword pass's exact per-index claims (see
    :func:`_parse_kw_and_flags`). Tokens consumed by the positional pass
    (``include_positionals=True``) are NOT reflected here — they only
    disappear from ``unclaimed``."""


def _probe_unclaimed(
    argument_collection: ArgumentCollection,
    tokens: list[str],
    *,
    end_of_options_delimiter: str = "--",
    include_positionals: bool = False,
) -> _ProbeResult | None:
    """Determine which tokens ``argument_collection`` would NOT consume.

    Runs the real parsing passes (:func:`_parse_kw_and_flags`, and optionally
    :func:`_parse_pos`) on a throwaway copy of the collection, so all matching
    edge cases (combined short flags, GNU-style attached values, ``=``
    splitting, positional ``token_count``/``consume_all`` semantics, etc.)
    behave exactly like the eventual real parse.

    Returns
    -------
    _ProbeResult | None
        ``None`` if the keyword/flag pass raised a :class:`CycloptsError`
        (e.g. a known option missing its value) — the claims cannot be
        determined; the caller decides how to proceed.
    """
    collection_copy = argument_collection.copy(reset_tokens=True)
    try:
        unused, unused_indices, contiguous_positional_count, claims = _parse_kw_and_flags(
            collection_copy, tokens, end_of_options_delimiter=end_of_options_delimiter
        )
    except CycloptsError:
        return None
    if not include_positionals:
        return _ProbeResult(list(zip(unused_indices, unused, strict=True)), claims)

    try:
        leftover = _parse_pos(
            collection_copy,
            unused,
            end_of_options_delimiter=end_of_options_delimiter,
            contiguous_positional_count=contiguous_positional_count,
        )
    except CycloptsError:
        # Positional binding failed mid-stream (e.g. an option-like token in a
        # non-allow_leading_hyphen slot). Treat the positional pass as claiming
        # nothing; callers typically re-probe after another collection has
        # claimed the offending token.
        return _ProbeResult(list(zip(unused_indices, unused, strict=True)), claims)

    # ``_parse_pos`` consumes from the front of a preprocessed stream that
    # excludes the end_of_options_delimiter token itself; ``leftover`` is a
    # suffix of that stream. Map leftover entries back to ``unused`` positions.
    if end_of_options_delimiter and end_of_options_delimiter in unused:
        delimiter_pos = unused.index(end_of_options_delimiter)
        preprocessed_to_unused = [p for p in range(len(unused)) if p != delimiter_pos]
    else:
        preprocessed_to_unused = list(range(len(unused)))
    leftover_positions = preprocessed_to_unused[len(preprocessed_to_unused) - len(leftover) :]
    return _ProbeResult([(unused_indices[p], unused[p]) for p in leftover_positions], claims)


class _MergedScanResult(NamedTuple):
    """Result of :func:`_merged_combined_short_scan`."""

    child_part: str | None
    """Reconstructed token for the child's stream (its flag characters, any
    unknown characters, and any attached value it absorbed), or ``None`` if the
    child keeps nothing."""

    meta_part: str | None
    """Reconstructed token for the meta's keyword stream, or ``None``."""

    meta_awaits_value: bool
    """A meta value-taking option ended the token with no attached value; the
    next stream token is its value."""


def _is_combined_short_candidate(
    token: str,
    collections: "Sequence[ArgumentCollection | None]",
) -> bool:
    """Whether ``token`` should be resolved by the merged combined-short scan.

    Mirrors the gate in :func:`_parse_kw_and_flags`'s combined-short branch:
    single-dash, multi-character, non-numeric, no ``=``, and not an exact match
    of any collection (exact matches are ordinary options, handled by the
    normal probing paths).
    """
    if "=" in token:
        return False
    if not (token.startswith("-") and not token.startswith("--") and len(token) > 2):
        return False
    if not is_option_like(token, allow_numbers=False):
        return False
    for collection in collections:
        if collection is None:
            continue
        try:
            collection.match(token)
        except ValueError:
            continue
        return False
    return True


def _merged_combined_short_scan(
    token: str,
    child_collection: "ArgumentCollection | None",
    meta_collection: ArgumentCollection,
) -> _MergedScanResult:
    """Resolve a combined short-option token against the MERGED flag namespace.

    Fallthrough mode presents the user with one flat flag namespace; this scan
    makes that literal: a single GNU left-to-right pass where each character is
    matched against the child first (child wins name collisions after its
    command), then the meta. Standard rules apply to the merged table:

    - a flag/count match consumes its character;
    - the first value-taking match absorbs the rest of the token as an attached
      value (or, with no remainder, the next stream token) and ends the scan;
    - an unknown character is routed to the child's stream, which reports it.

    Characters are routed to per-owner reconstructed tokens in scan order, so
    each level's real parse of its part reproduces exactly this reading.
    """
    chars = token.lstrip("-")
    child_chars: list[str] = []
    meta_chars: list[str] = []
    meta_awaits_value = False
    position = 0
    while position < len(chars):
        char = chars[position]
        matched = None
        for owner_chars, collection in ((child_chars, child_collection), (meta_chars, meta_collection)):
            if collection is None:
                continue
            try:
                argument, _, implicit = collection.match(f"-{char}")
            except ValueError:
                continue
            matched = (owner_chars, argument, implicit)
            break
        if matched is None:
            child_chars.append(char)  # Unknown flag; the child's parse reports it.
            position += 1
            continue
        owner_chars, argument, implicit = matched
        owner_chars.append(char)
        if implicit is not UNSET or argument.parameter.count:
            position += 1
            continue
        # Value-taking option: the rest of the token is its attached value.
        remainder = chars[position + 1 :]
        if remainder:
            owner_chars.extend(remainder)
        elif owner_chars is meta_chars:
            meta_awaits_value = True
        break
    return _MergedScanResult(
        "-" + "".join(child_chars) if child_chars else None,
        "-" + "".join(meta_chars) if meta_chars else None,
        meta_awaits_value,
    )


def _claimed_tokens(claims: dict[int, tuple[str, str | None]]) -> list[str]:
    """Ordered claimed parts from a keyword-pass claims map (see :func:`_parse_kw_and_flags`)."""
    return [claimed for _, (claimed, _) in sorted(claims.items())]


def _scope_tokens_for_meta(
    meta_collection: ArgumentCollection,
    child_collection: "ArgumentCollection | None",
    tokens: list[str],
    command_indices: list[int],
    *,
    parse_mode: str,
    end_of_options_delimiter: str = "--",
) -> tuple[list[str], list[str], int | None]:
    """Scope tokens between a meta-app level and the subcommand it forwards to.

    Decides which tokens the meta app's keyword parameters may bind
    (``meta_kw_tokens``) and which tokens are forwarded through the meta's
    positional parameters to the child command (``positional_tokens``),
    using the real parser passes on throwaway collection copies so the
    decision exactly matches what each level's eventual parse will do.

    In ``"strict"`` mode the meta only binds tokens appearing before the first
    command token. In ``"fallthrough"`` mode, post-command tokens the child
    would leave unconsumed additionally "bubble up" to the meta (child wins
    on conflicts, computed child-first).

    Parameters
    ----------
    meta_collection: ArgumentCollection
        The current (meta) level's argument collection.
    child_collection: ArgumentCollection | None
        The resolved deepest command's argument collection. ``None`` means the
        child has no bindable parameters (claims nothing).
    tokens: list[str]
        The full normalized token list.
    command_indices: list[int]
        Indices into ``tokens`` of the command tokens (from
        ``App._parse_commands``), help/version pseudo-commands excluded.
    parse_mode: str
        ``"fallthrough"`` or ``"strict"``.
    end_of_options_delimiter: str
        Token that marks the end of options.

    Returns
    -------
    meta_kw_tokens: list[str]
        Tokens eligible for the meta level's keyword/flag binding.
    positional_tokens: list[str]
        Tokens for the meta level's positional binding (command name(s) plus
        everything forwarded to the child), in original order.
    contiguous_positional_count: int | None
        First-gap index for ``positional_tokens`` (see
        :func:`_parse_kw_and_flags`), preserving issue-#763 protection.
    """
    if parse_mode not in ("fallthrough", "strict"):
        raise ValueError(f"Unknown parse_mode: {parse_mode!r}")

    first = command_indices[0]
    last = command_indices[-1]
    pre = tokens[:first]

    # Pre-command region: the meta claims what its keyword parameters match;
    # leftovers pass through to the positional stream (relevant for nested
    # meta patterns where pre-command tokens belong to an inner meta level).
    pre_probe = _probe_unclaimed(
        meta_collection, pre, end_of_options_delimiter=end_of_options_delimiter, include_positionals=False
    )
    if pre_probe is None:
        # The meta's own region is malformed (e.g. option missing its value).
        # Hand everything to the meta's real keyword pass so it raises the
        # proper user-facing error.
        meta_kw_tokens = list(pre)
        pre_passthrough: list[tuple[int, str]] = []
    else:
        meta_kw_tokens = _claimed_tokens(pre_probe.kw_claims)
        pre_passthrough = pre_probe.unclaimed

    positional_indices: list[int] = [position for position, _ in pre_passthrough]
    positional_tokens: list[str] = [token for _, token in pre_passthrough]

    if parse_mode == "strict":
        # Post-command tokens are exclusively the child's; no bubble-up.
        positional_indices.extend(range(first, len(tokens)))
        positional_tokens.extend(tokens[first:])
        return meta_kw_tokens, positional_tokens, _first_gap(positional_indices)

    # Tokens between command tokens (e.g. ``--verbose`` in ``sub --verbose leaf``):
    # the meta claims what its keyword parameters match, exactly like the
    # pre-command region; leftovers pass through positionally. Probe each
    # inter-command segment separately so option/value adjacency is never
    # fabricated across a command token.
    inter_passthrough: list[tuple[int, str]] = []  # (original index, token)
    for segment_number, command_index in enumerate(command_indices[:-1]):
        segment_start = command_index + 1
        segment = tokens[segment_start : command_indices[segment_number + 1]]
        if not segment:
            continue
        segment_probe = _probe_unclaimed(meta_collection, segment, end_of_options_delimiter=end_of_options_delimiter)
        if segment_probe is None:
            # Malformed for the meta (e.g. option missing its value); hand the
            # segment to the meta's real pass so it raises the proper error.
            meta_kw_tokens.extend(segment)
            continue
        meta_kw_tokens.extend(_claimed_tokens(segment_probe.kw_claims))
        inter_passthrough.extend((segment_start + position, token) for position, token in segment_probe.unclaimed)

    # Fallthrough: compute the child's claims first (child wins), then let the
    # meta claim from the child's leftovers. Iterate because each side's
    # claims can unblock the other (e.g. the child can only bind its option's
    # value after the meta claims an interleaved flag). The loop is monotone:
    # ``child_stream`` only ever shrinks, so it terminates.
    child_stream: list[tuple[int, str]] = [(position, token) for position, token in enumerate(tokens[last + 1 :])]
    bubbled: list[str] = []
    while True:
        stream_tokens = [token for _, token in child_stream]
        if child_collection is None:
            child_unclaimed = list(enumerate(stream_tokens))
        else:
            child_probe = _probe_unclaimed(
                child_collection,
                stream_tokens,
                end_of_options_delimiter=end_of_options_delimiter,
                include_positionals=True,
            )
            if child_probe is None:
                # Cannot determine the child's claims this round (e.g. a child
                # option is missing its value because a meta flag sits between
                # them); treat the child as claiming nothing and let the meta
                # claim, then re-probe.
                child_unclaimed = list(enumerate(stream_tokens))
            else:
                child_unclaimed = child_probe.unclaimed

        # Candidates the meta may claim: the child's leftovers, but never
        # tokens at/after the end-of-options delimiter (those are positional
        # by definition). Probe per contiguous run so the meta can only pair
        # an option with a value that was actually adjacent in the input.
        delimiter_pos = (
            stream_tokens.index(end_of_options_delimiter)
            if end_of_options_delimiter and end_of_options_delimiter in stream_tokens
            else len(stream_tokens)
        )
        # Maps compacted stream position -> the child-side replacement token
        # (``None`` removes the token from the child's stream entirely).
        newly_replaced: dict[int, str | None] = {}

        # Combined short-option tokens are resolved against the MERGED flag
        # namespace of both levels (see :func:`_merged_combined_short_scan`):
        # fallthrough mode presents the user one flat namespace, so a token
        # like ``-xvf`` may mix child and meta flags, and ``-uroot`` reads as
        # the meta's ``-u`` + attached value even when the child owns ``-r``.
        # This applies to tokens the child leaves (fully or partially)
        # unclaimed; a token the child claims WHOLLY (e.g. captured
        # positionally by an ``allow_leading_hyphen`` ``*args``) stays the
        # child's, per child-wins.
        child_unclaimed_by_position: dict[int, list[str]] = {}
        for position, token in child_unclaimed:
            child_unclaimed_by_position.setdefault(position, []).append(token)
        scanned_positions: set[int] = set()
        for position in sorted(child_unclaimed_by_position):
            if position >= delimiter_pos or position in scanned_positions:
                continue
            original = stream_tokens[position]
            synthetics = child_unclaimed_by_position[position]
            partially_claimed = not (len(synthetics) == 1 and synthetics[0] == original)
            if not partially_claimed and not _is_combined_short_candidate(
                original, (child_collection, meta_collection)
            ):
                continue
            scan = _merged_combined_short_scan(original, child_collection, meta_collection)
            if scan.meta_part is None:
                if partially_claimed:
                    # Nothing for the meta; keep the child's own reading and
                    # exclude the synthetic residuals from long-option runs.
                    scanned_positions.add(position)
                continue
            scanned_positions.add(position)
            newly_replaced[position] = scan.child_part
            bubbled.append(scan.meta_part)
            if scan.meta_awaits_value:
                # The meta's value-taking option ended the token; the NEXT
                # stream token is its value — if the child didn't claim it.
                value_position = position + 1
                value_synthetics = child_unclaimed_by_position.get(value_position)
                if (
                    value_position < delimiter_pos
                    and value_synthetics is not None
                    and len(value_synthetics) == 1
                    and value_synthetics[0] == stream_tokens[value_position]
                ):
                    scanned_positions.add(value_position)
                    newly_replaced[value_position] = None
                    bubbled.append(stream_tokens[value_position])
                # Otherwise the meta's real parse raises the proper
                # missing-value error.

        candidates = [
            (position, token)
            for position, token in child_unclaimed
            if position < delimiter_pos and position not in scanned_positions and position not in newly_replaced
        ]

        for run in _contiguous_runs(candidates):
            run_tokens = [token for _, token in run]
            if not any(is_option_like(token, allow_numbers=True) for token in run_tokens):
                # The keyword pass can only claim option-like tokens (and their
                # values); a pure-positional run needs no probe. This is the
                # common terminating state of the loop.
                continue
            run_probe = _probe_unclaimed(meta_collection, run_tokens, end_of_options_delimiter=end_of_options_delimiter)
            if run_probe is None:
                # The meta recognized an option in this run but the run is
                # malformed for it (e.g. an option missing its value).
                # Attribute the run to the meta so its real keyword pass raises
                # the proper user-facing error; leaving it with the child would
                # misreport a valid meta option as "Unknown option".
                for position, token in run:
                    newly_replaced[position] = None
                    bubbled.append(token)
                continue
            for run_pos, (stream_pos, _) in enumerate(run):
                claim = run_probe.kw_claims.get(run_pos)
                if claim is None:
                    continue  # Meta claimed nothing from this token.
                # ``remainder`` is the exact unclaimed residue recorded by the
                # scan itself ((token, None) for a wholly-claimed token).
                claimed_part, remainder = claim
                newly_replaced[stream_pos] = remainder
                bubbled.append(claimed_part)

        if not newly_replaced:
            break

        # Apply the replacements to the child stream and re-probe.
        # ``newly_replaced`` is keyed by positions in the current (compacted)
        # ``stream_tokens``, i.e. list indices of ``child_stream``, NOT the
        # original positions stored inside each entry.
        new_child_stream: list[tuple[int, str]] = []
        for current_pos, (stream_pos, token) in enumerate(child_stream):
            if current_pos not in newly_replaced:
                new_child_stream.append((stream_pos, token))
                continue
            replacement = newly_replaced[current_pos]
            if replacement is not None:
                new_child_stream.append((stream_pos, replacement))
        child_stream = new_child_stream

    meta_kw_tokens.extend(bubbled)
    # Forwarded stream: pre-command passthrough, then the command token(s)
    # interleaved (in original order) with unclaimed inter-command tokens,
    # then whatever remains of the child segment.
    chain_entries: list[tuple[int, str]] = [(index, tokens[index]) for index in command_indices]
    chain_entries.extend(inter_passthrough)
    chain_entries.sort()
    positional_indices.extend(index for index, _ in chain_entries)
    positional_tokens.extend(token for _, token in chain_entries)
    positional_indices.extend(last + 1 + position for position, _ in child_stream)
    positional_tokens.extend(token for _, token in child_stream)
    return meta_kw_tokens, positional_tokens, _first_gap(positional_indices)


def _first_gap(indices: list[int]) -> int | None:
    """Index of the first non-contiguous jump in ``indices``, or ``None`` if contiguous.

    Repeated indices (synthetic residuals of one combined short-option token)
    count as contiguous. This is the ``contiguous_positional_count``
    computation used by both :func:`_parse_kw_and_flags` and
    :func:`_scope_tokens_for_meta`.
    """
    for j in range(1, len(indices)):
        if indices[j] not in (indices[j - 1], indices[j - 1] + 1):
            return j
    return None


def _contiguous_runs(entries: list[tuple[int, str]]) -> Iterator[list[tuple[int, str]]]:
    """Group ``(position, token)`` entries into runs of contiguous positions.

    Entries sharing a position (synthetic residuals of one combined
    short-option token) belong to the same run.
    """
    run: list[tuple[int, str]] = []
    for entry in entries:
        if run and entry[0] not in (run[-1][0], run[-1][0] + 1):
            yield run
            run = []
        run.append(entry)
    if run:
        yield run


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
) -> tuple[list[str], list[int], int | None, dict[int, tuple[str, str | None]]]:
    """Extract keyword arguments and flags from the token stream.

    Returns
    -------
    unused_tokens: list[str]
        Tokens not consumed by any keyword or flag.
    unused_token_original_indices: list[int]
        Parallel list to ``unused_tokens`` giving each token's original
        index in the input ``tokens`` sequence. ``len(unused_tokens) ==
        len(unused_token_original_indices)``.
    contiguous_positional_count: int | None
        Number of leading contiguous non-option tokens before the first gap
        caused by keyword extraction. ``None`` if all non-option tokens are
        contiguous (i.e. no keywords were interleaved among positional tokens).

        For example, given ``a b c --bar 8 --baz 10 d``, the unused tokens are
        ``['a', 'b', 'c', 'd']`` with original indices ``[0, 1, 2, 6]``.
        The gap between indices 2 and 6 yields ``contiguous_positional_count=3``.
        This is used by ``_parse_pos`` to prevent positional-only list parameters
        from consuming tokens that appeared after keyword arguments.
    claims: dict[int, tuple[str, str | None]]
        Maps each consumed token's original index to ``(claimed_part,
        remainder)``, recorded exactly as the scan consumed it:

        - A wholly-consumed token (option, flag, or an option's value) maps to
          ``(token, None)``.
        - A partially-consumed combined short-option token maps to the exact
          claimed characters (plus any GNU-style attached value) and the exact
          unmatched-character remainder, in scan order — e.g. ``-abc`` with
          only ``-a``/``-c`` known yields ``("-ac", "-b")``.

        Untouched tokens have no entry. Hierarchical scoping consumes this to
        route token fragments between command levels without reconstructing
        them from the unused-token stream.
    """
    unused_tokens, positional_only_tokens = [], []
    positional_only_start: int | None = None
    unused_token_original_indices: list[int] = []
    claims: dict[int, tuple[str, str | None]] = {}
    skip_next_iterations = 0
    stop_parsing = False
    if end_of_options_delimiter:
        try:
            delimiter_index = tokens.index(end_of_options_delimiter)
        except ValueError:
            pass  # end_of_options_delimiter not in token stream
        else:
            positional_only_tokens = tokens[delimiter_index:]
            positional_only_start = delimiter_index
            tokens = tokens[:delimiter_index]
    for i, token in enumerate(tokens):
        # If the previous argument was a keyword, then this is its value
        if skip_next_iterations > 0:
            skip_next_iterations -= 1
            claims[i] = (token, None)
            continue

        if not is_option_like(token, allow_numbers=True):
            if stop_at_first_unknown:
                # Stop parsing and return all remaining tokens as unused
                unused_tokens.extend(tokens[i:])
                unused_token_original_indices.extend(range(i, len(tokens)))
                break
            unused_tokens.append(token)
            unused_token_original_indices.append(i)
            continue

        cli_values: list[str] = []
        consume_count = 0

        # startswith("-") is redundant, but it's cheap safety.
        allow_combined_flags = token.startswith("-") and not token.startswith("--")

        # Try splitting on "=" for long options or short options that match exactly
        if "=" in token:
            cli_option, cli_value = token.split("=", 1)
            # Try to match the part before "="
            try:
                argument_collection.match(cli_option)
                # Matched! Use the split
                cli_values.append(cli_value)
                consume_count -= 1
                allow_combined_flags = False
            except ValueError:
                # No match - might be GNU-style like "-pfile=value"
                # Don't split, treat whole token as the option
                cli_option = token
        else:
            cli_option = token

        matches: list[_KeywordMatch] = []
        attached_value: str | None = None  # Track value attached to a GNU-style combined option
        claimed_part: str = token
        partial_remainder: str | None = None
        try:
            matches.append(_KeywordMatch(cli_option, *argument_collection.match(cli_option)))
        except ValueError:
            # Length has to be greater than 2 (hyphen + character) to be exploded.
            # Also exclude numeric values (e.g., -10, -3.14) from combined flag parsing.
            if allow_combined_flags and len(token) > 2 and is_option_like(token, allow_numbers=False):
                # GNU-style combined short options: process left-to-right
                # Once we hit an option that takes a value, the rest is the value
                chars = cli_option.lstrip("-")
                position = 0
                unmatched_flags: list[str] = []

                while position < len(chars):
                    char = chars[position]
                    test_flag = f"-{char}"

                    try:
                        arg, keys, implicit = argument_collection.match(test_flag)

                        if implicit is not UNSET or arg.parameter.count:
                            # This is a flag (boolean or counting) - consume just this character
                            matches.append(_KeywordMatch(test_flag, arg, keys, implicit))
                            position += 1
                        else:
                            # This option takes a value - rest of the string is the value
                            remainder = chars[position + 1 :]
                            matches.append(_KeywordMatch(test_flag, arg, keys, implicit))
                            if remainder:
                                # Value is attached: -uroot or -fvuroot
                                # Store it separately, will be added to cli_values when processing this match
                                attached_value = remainder
                                consume_count -= 1
                            # Stop processing further characters
                            break

                    except ValueError:
                        # Unknown flag
                        if stop_at_first_unknown:
                            unused_tokens.extend(tokens[i:])
                            unused_token_original_indices.extend(range(i, len(tokens)))
                            stop_parsing = True
                            break
                        unmatched_flags.append(test_flag)
                        position += 1

                if stop_parsing:
                    break
                if not matches:
                    # No character matched a known short option, so this wasn't a
                    # combined-short-option token after all; keep the original token intact.
                    unused_tokens.append(token)
                    unused_token_original_indices.append(i)
                    continue
                for unmatched_flag in unmatched_flags:
                    unused_tokens.append(unmatched_flag)
                    unused_token_original_indices.append(i)
                # Record the exact claimed/unclaimed split of this combined
                # short-option token, in scan order.
                claimed_part = "-" + "".join(m.matched_token.lstrip("-") for m in matches)
                if attached_value is not None:
                    claimed_part += attached_value
                if unmatched_flags:
                    partial_remainder = "-" + "".join(f.lstrip("-") for f in unmatched_flags)
            else:
                if stop_at_first_unknown:
                    # Unknown option, stop parsing and return all remaining tokens
                    unused_tokens.extend(tokens[i:])
                    unused_token_original_indices.extend(range(i, len(tokens)))
                    break
                unused_tokens.append(token)
                unused_token_original_indices.append(i)
                continue
        for match_index, match in enumerate(matches):
            # For GNU-style combined options, add the attached value only when processing
            # the last match (the value-taking option), not for preceding flags
            if attached_value is not None and match_index == len(matches) - 1:
                cli_values.append(attached_value)

            if match.argument.parameter.count:
                match.argument.append(CliToken(keyword=match.matched_token, implicit_value=1))
            elif match.implicit_value is not UNSET:
                # A flag was parsed
                if cli_values:
                    try:
                        coerced_value = _bool(cli_values[-1])
                    except CoercionError as e:
                        if e.token is None:
                            e.token = CliToken(keyword=match.matched_token)
                        if e.argument is None:
                            e.argument = match.argument
                        raise
                    if coerced_value:  # --positive-flag=true or --negative-flag=true or --empty-flag=true
                        match.argument.append(
                            CliToken(keyword=match.matched_token, implicit_value=match.implicit_value)
                        )
                    else:  # --positive-flag=false or --negative-flag=false or --empty-flag=false
                        if isinstance(match.implicit_value, bool):
                            match.argument.append(
                                CliToken(keyword=match.matched_token, implicit_value=not match.implicit_value)
                            )
                        else:
                            # A negative for a non-bool field doesn't really make sense;
                            # e.g. --empty-list=False
                            # So we'll just silently skip it, as it may make bash scripting easier.
                            pass
                else:
                    match.argument.append(CliToken(keyword=match.matched_token, implicit_value=match.implicit_value))
            else:
                # This is a value-taking option (not a flag or counting parameter)
                # Error only if we're trying to combine multiple value-taking options without values
                # (e.g., -fu where both -f and -u take values would be invalid)
                # But -fu where -f is a flag and -u takes a value is valid (GNU-style)
                if len(matches) > 1:
                    # Count how many value-taking options we have
                    value_taking_count = sum(
                        1 for m in matches if m.implicit_value is UNSET and not m.argument.parameter.count
                    )
                    if value_taking_count > 1:
                        raise CombinedShortOptionError(
                            msg=f"Cannot combine multiple value-taking options in token {cli_option}"
                        )
                # Create Token objects upfront for all upcoming tokens.
                # Token creation is cheap (small frozen dataclass), and this enables
                # identity-based caching since the same Token objects will be used
                # for both probing (in token_count) and actual conversion.
                # Note: index is 0-based per invocation (not cumulative) for proper
                # repeat argument detection via Token.address.

                # Include any values already extracted from "=" syntax (e.g., --key=value)
                # These need to be part of the token sequence for proper probing.
                pre_extracted_values = list(cli_values)  # Values from "=" or attached GNU-style
                all_upcoming_values = pre_extracted_values + list(tokens[i + 1 :])
                upcoming_tokens = [
                    CliToken(keyword=match.matched_token, value=v, index=j, keys=match.keys)
                    for j, v in enumerate(all_upcoming_values)
                ]
                tokens_per_element, consume_all = match.argument.token_count(
                    match.keys, upcoming_tokens=upcoming_tokens
                )

                if match.argument.parameter.requires_equals and match.matched_token.startswith("--") and not cli_values:
                    raise RequiresEqualsError(
                        argument=match.argument,
                        keyword=match.matched_token,
                    )

                # Consume the appropriate number of tokens
                consumed_tokens: list[Token] = []
                pre_extracted_count = len(pre_extracted_values)

                # cm_bounds is either None or (min, max) — guaranteed by _consume_multiple_converter
                cm_bounds = match.argument.parameter.consume_multiple
                assert cm_bounds is None or isinstance(cm_bounds, tuple)
                cm_min, cm_max = cm_bounds if cm_bounds is not None else (0, None)

                with suppress(IndexError):
                    if consume_all and cm_bounds is not None:
                        # First, include the pre-extracted tokens
                        for j in range(pre_extracted_count):
                            consumed_tokens.append(upcoming_tokens[j])
                        # Then consume from the remaining tokens
                        for j in itertools.count(pre_extracted_count):
                            token = upcoming_tokens[j]
                            if not match.argument.parameter.allow_leading_hyphen and is_option_like(token.value):
                                break
                            consumed_tokens.append(token)
                            cli_values.append(token.value)
                            skip_next_iterations += 1
                    else:
                        # consume_count is negative if we already have pre-extracted values
                        additional_to_consume = consume_count + tokens_per_element

                        # First, include pre-extracted tokens (up to tokens_per_element)
                        for j in range(min(pre_extracted_count, tokens_per_element)):
                            consumed_tokens.append(upcoming_tokens[j])

                        # Then consume additional tokens from CLI
                        for j in range(additional_to_consume):
                            idx = pre_extracted_count + j
                            if len(cli_values) == 1 and (
                                match.argument._should_attempt_json_dict(cli_values)
                                or match.argument._should_attempt_json_list(cli_values, match.keys)
                            ):
                                tokens_per_element = 1
                                # Assume that the contents are json and that we shouldn't
                                # consume any additional tokens.
                                break

                            token = upcoming_tokens[idx]
                            if not match.argument.parameter.allow_leading_hyphen and is_option_like(token.value):
                                raise MissingArgumentError(
                                    argument=match.argument,
                                    tokens_so_far=cli_values,
                                    keyword=match.matched_token,
                                )
                            consumed_tokens.append(token)
                            cli_values.append(token.value)
                            skip_next_iterations += 1

                if not consumed_tokens:
                    # No values were consumed after the keyword
                    if consume_all and cm_bounds is not None:
                        if cm_min > 0:
                            # Minimum count not met — treat as missing argument
                            raise ConsumeMultipleError(
                                argument=match.argument,
                                tokens_so_far=cli_values,
                                keyword=match.matched_token,
                                min_required=cm_min,
                                max_allowed=cm_max,
                                actual_count=0,
                            )
                        # Allow empty iterables (e.g., --urls with no values behaves like --empty-urls)
                        empty_container = (get_origin(match.argument.resolved_hint) or match.argument.resolved_hint)()
                        match.argument.append(
                            CliToken(keyword=match.matched_token, implicit_value=empty_container, keys=match.keys)
                        )
                    else:
                        # Non-iterables or consume_multiple=False require at least one value
                        raise MissingArgumentError(
                            argument=match.argument, tokens_so_far=cli_values, keyword=match.matched_token
                        )
                elif len(consumed_tokens) % tokens_per_element:
                    # For multi-token elements (e.g., tuples), ensure we have complete sets
                    raise MissingArgumentError(
                        argument=match.argument, tokens_so_far=cli_values, keyword=match.matched_token
                    )
                else:
                    # Check min/max count for consume_multiple
                    if cm_bounds is not None:
                        n_elements = len(cli_values) // max(1, tokens_per_element)
                        if n_elements < cm_min:
                            raise ConsumeMultipleError(
                                argument=match.argument,
                                tokens_so_far=cli_values,
                                keyword=match.matched_token,
                                min_required=cm_min,
                                max_allowed=cm_max,
                                actual_count=n_elements,
                            )
                        if cm_max is not None and n_elements > cm_max:
                            raise ConsumeMultipleError(
                                argument=match.argument,
                                tokens_so_far=cli_values,
                                keyword=match.matched_token,
                                min_required=cm_min,
                                max_allowed=cm_max,
                                actual_count=n_elements,
                            )
                    # Normal case: append the pre-created Token objects directly
                    for consumed_token in consumed_tokens:
                        match.argument.append(consumed_token)
        claims[i] = (claimed_part, partial_remainder)

    # Compute the number of contiguous positional (non-option-like) unused tokens
    # before the first gap caused by keyword extraction. This prevents positional-only
    # list parameters from consuming tokens that appeared after keyword arguments.
    # Only set when a gap is detected; None means no gap (all tokens are contiguous).
    # Synthetic residuals of one combined short-option token share an index and
    # count as contiguous.
    contiguous_positional_count = _first_gap(unused_token_original_indices)

    unused_tokens.extend(positional_only_tokens)
    if positional_only_start is not None:
        unused_token_original_indices.extend(
            range(positional_only_start, positional_only_start + len(positional_only_tokens))
        )
    return unused_tokens, unused_token_original_indices, contiguous_positional_count, claims


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


def _captures_raw_stream(argument_collection: ArgumentCollection) -> bool:
    """Whether the collection has a raw-stream capture parameter.

    A ``*args`` parameter with ``allow_leading_hyphen=True`` captures a raw
    token stream suitable for re-parsing (the meta-app forwarding pattern).
    """
    return any(
        argument.field_info.kind is VAR_POSITIONAL and argument.parameter.allow_leading_hyphen
        for argument in argument_collection
    )


def _preprocess_positional_tokens(
    tokens: Sequence[str],
    end_of_options_delimiter: str,
    *,
    preserve_delimiter: bool = False,
) -> list[tuple[str, bool]]:
    try:
        delimiter_index = tokens.index(end_of_options_delimiter)
    except ValueError:  # delimiter not found
        return [(t, False) for t in tokens]
    delimiter = [(tokens[delimiter_index], True)] if preserve_delimiter else []
    return (
        [(t, False) for t in tokens[:delimiter_index]] + delimiter + [(t, True) for t in tokens[delimiter_index + 1 :]]
    )


def _parse_pos(
    argument_collection: ArgumentCollection,
    tokens: list[str],
    *,
    end_of_options_delimiter: str = "--",
    contiguous_positional_count: int | None = None,
    preserve_delimiter: bool = False,
) -> list[str]:
    """Assign positional tokens to positional parameters.

    Parameters
    ----------
    argument_collection: ArgumentCollection
        Arguments whose keyword/flag tokens have already been consumed.
    tokens: list[str]
        Unused tokens from ``_parse_kw_and_flags``.
    end_of_options_delimiter: str
        Delimiter after which all tokens are forced positional. Consumed as a
        marker (standard CLI behavior), unless ``preserve_delimiter``.
    preserve_delimiter: bool
        Keep the delimiter token itself in the captured values (force-positional)
        when the collection has a raw-stream capture parameter. Set when the
        bound tokens are forwarded to another parse — a meta app's
        ``app(tokens)`` — which needs the delimiter to keep the trailing tokens
        protected. Leaf commands keep the standard consume-as-marker behavior.
    contiguous_positional_count: int | None
        If not ``None``, the number of leading contiguous positional tokens
        that were adjacent in the original CLI input (before keyword extraction
        created a gap). Used to cap how many tokens a ``POSITIONAL_ONLY``
        list/iterable parameter may consume, preventing it from greedily
        swallowing tokens that originally appeared after keyword arguments.
        See ``_parse_kw_and_flags`` for how this value is computed.
    """
    prior_positional_or_keyword_supplied_as_keyword_arguments = []

    if not tokens:
        return []

    tokens_and_force_positional = _preprocess_positional_tokens(
        tokens,
        end_of_options_delimiter,
        preserve_delimiter=preserve_delimiter and _captures_raw_stream(argument_collection),
    )

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
                if not tokens_and_force_positional:
                    # ``tokens`` contained only the ``--`` end-of-options delimiter;
                    # there are no positional tokens to misassign.
                    break
                # Use the preprocessed token: ``tokens`` still contains the ``--``
                # end-of-options delimiter, and ``force_positional`` marks tokens
                # after it, which must not be treated as options.
                token, force_positional = tokens_and_force_positional[0]
                if not force_positional and not argument.parameter.allow_leading_hyphen and is_option_like(token):
                    # It's more meaningful to interpret the token as an intended option,
                    # rather than an intended positional value for ``argument``.
                    raise UnknownOptionError(token=CliToken(value=token), argument_collection=argument_collection)
                else:
                    raise ArgumentOrderError(
                        argument=argument,
                        prior_positional_or_keyword_supplied_as_keyword_arguments=prior_positional_or_keyword_supplied_as_keyword_arguments,
                        token=token,
                    )

        # Create Token objects for token_count() to enable union type probing.
        # Token creation is cheap (small frozen dataclass). For positional args,
        # we create separate tokens for actual use with per-element indices.
        upcoming_tokens = [CliToken(value=t[0], index=j) for j, t in enumerate(tokens_and_force_positional)]
        tokens_per_element, consume_all = argument.token_count(upcoming_tokens=upcoming_tokens)
        tokens_per_element = max(1, tokens_per_element)

        if consume_all and argument.field_info.kind is POSITIONAL_ONLY:
            # POSITIONAL_ONLY parameters can come after a POSITIONAL_ONLY list/iterable.
            # This makes it easier to create programs that do something like:
            #    $ python my-program.py input_folder/*.csv output.csv

            # Need to see how many tokens we need to leave for subsequent POSITIONAL_ONLY parameters.
            n_tokens_to_leave = _future_positional_only_token_count(argument_collection, i + 1)

            # Cap at the contiguous positional count to prevent consuming tokens
            # that appeared after keyword arguments (issue #763).
            if contiguous_positional_count is not None:
                n_tokens_to_leave = max(
                    n_tokens_to_leave, len(tokens_and_force_positional) - contiguous_positional_count
                )
        else:
            n_tokens_to_leave = 0

        new_tokens = []
        while (len(tokens_and_force_positional) - n_tokens_to_leave) > 0:
            if (len(tokens_and_force_positional) - n_tokens_to_leave) < tokens_per_element:
                raise MissingArgumentError(
                    argument=argument,
                    tokens_so_far=[x[0] for x in tokens_and_force_positional],
                )

            for index, (token_str, force_positional) in enumerate(tokens_and_force_positional[:tokens_per_element]):
                if not force_positional and not argument.parameter.allow_leading_hyphen and is_option_like(token_str):
                    raise UnknownOptionError(token=CliToken(value=token_str), argument_collection=argument_collection)
                new_tokens.append(CliToken(value=token_str, index=index))
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
    positional_tokens: list[str] | None = None,
    positional_contiguous_count: int | None = None,
    preserve_delimiter: bool = False,
) -> tuple[inspect.BoundArguments, list[str]]:
    """Parse and coerce CLI tokens to match a function's signature.

    Parameters
    ----------
    func: Callable
        Function.
    argument_collection: ArgumentCollection
    tokens: list[str]
        CLI tokens to parse and coerce to match ``f``'s signature.
        If ``positional_tokens`` is provided, only used for keyword/flag parsing.
    configs: Iterable[Callable]
    end_of_options_delimiter: str
        Everything after this special token is forced to be supplied as a positional argument.
    positional_tokens: list[str] | None
        If provided, these tokens are used for positional argument parsing
        instead of the leftover tokens from keyword/flag parsing. This is
        used by flag scoping to separate which tokens are eligible for
        keyword/flag matching vs positional assignment.
    positional_contiguous_count: int | None
        ``contiguous_positional_count`` (see :func:`_parse_kw_and_flags`) for
        ``positional_tokens``. Only used when ``positional_tokens`` is provided.
    preserve_delimiter: bool
        Keep the end-of-options delimiter in a raw-stream capture parameter's
        values (see :func:`_parse_pos`). Set when binding a meta level, whose
        captured tokens are forwarded to another parse.

    Returns
    -------
    bound: inspect.BoundArguments
        The converted and bound positional and keyword arguments for ``f``.

    unused_tokens: list[str]
        Remaining tokens that couldn't be matched to ``f``'s signature.
    """
    unused_tokens = tokens

    try:
        unused_tokens, _, contiguous_positional_count, _ = _parse_kw_and_flags(
            argument_collection, unused_tokens, end_of_options_delimiter=end_of_options_delimiter
        )
        leftover_kw_tokens: list[str] = []
        if positional_tokens is not None:
            # A scoped keyword stream consists solely of probe-predicted claims,
            # so the real pass should consume it entirely. If the probe and the
            # real parse ever disagree, surface the leftovers as ordinary unused
            # tokens rather than silently dropping them.
            leftover_kw_tokens = unused_tokens
            unused_tokens = positional_tokens
            contiguous_positional_count = positional_contiguous_count
        unused_tokens = _parse_pos(
            argument_collection,
            unused_tokens,
            end_of_options_delimiter=end_of_options_delimiter,
            contiguous_positional_count=contiguous_positional_count,
            preserve_delimiter=preserve_delimiter,
        )
        if leftover_kw_tokens:
            unused_tokens = leftover_kw_tokens + unused_tokens

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
            if argument.parse and argument.field_info.required and not argument.keys and not argument.has_tokens:
                raise MissingArgumentError(argument=argument)

        bound = _bind(argument_collection, func)
    except CycloptsError as e:
        e.root_input_tokens = tokens
        e.unused_tokens = unused_tokens
        raise

    return bound, unused_tokens
