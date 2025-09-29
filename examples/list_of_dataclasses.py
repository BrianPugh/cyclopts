#!/usr/bin/env python
"""Example demonstrating list[dataclass] support with JSON string inputs.

This example shows the flexible ways to provide lists of dataclasses via CLI:
1. Individual JSON objects: --matcher '{"name": "env", "value": "prod"}'
2. JSON arrays: --matcher '[{"name": "env", "value": "prod"}, {"name": "region", "value": "us"}]'
3. Mixed: combining both approaches in a single command
"""

from dataclasses import dataclass
from typing import Optional

import cyclopts


@dataclass
class Matcher:
    """Configuration for matching rules."""

    name: str
    """Field name to match against."""

    value: str
    """Expected value for the field."""

    isEqual: bool = True
    """If True, match when field equals value. If False, match when not equal."""

    isRegex: bool = False
    """If True, treat value as a regular expression pattern."""


@dataclass
class FilterConfig:
    """Configuration for filtering operations."""

    include: list[Matcher] = None  # pyright: ignore
    """List of matchers - include items that match ALL of these."""

    exclude: list[Matcher] = None  # pyright: ignore
    """List of matchers - exclude items that match ANY of these."""


app = cyclopts.App()


@app.default
def filter_data(
    config: Optional[FilterConfig] = None,
    verbose: bool = False,
):
    """Apply filtering rules to data based on matcher configurations.

    Parameters
    ----------
    config : FilterConfig, optional
        Filtering configuration with include/exclude rules.
    verbose : bool
        Enable verbose output showing applied rules.
    """
    if config is None:
        print("No filter configuration provided.")
        return

    if verbose:
        print("Filter Configuration:")
        print("-" * 50)

    if config.include:
        print(f"Include rules ({len(config.include)}):")
        for i, matcher in enumerate(config.include, 1):
            regex_str = " (regex)" if matcher.isRegex else ""
            equal_str = "==" if matcher.isEqual else "!="
            print(f"  {i}. {matcher.name} {equal_str} {matcher.value!r}{regex_str}")

    if config.exclude:
        print(f"\nExclude rules ({len(config.exclude)}):")
        for i, matcher in enumerate(config.exclude, 1):
            regex_str = " (regex)" if matcher.isRegex else ""
            equal_str = "==" if matcher.isEqual else "!="
            print(f"  {i}. {matcher.name} {equal_str} {matcher.value!r}{regex_str}")

    if not config.include and not config.exclude:
        print("No filtering rules defined.")


if __name__ == "__main__":
    # Example usage:
    #
    # Individual JSON objects (each --config.include adds one matcher):
    # $ python list_of_dataclasses.py --config.include '{"name": "env", "value": "prod"}' \
    #                                  --config.include '{"name": "region", "value": "us-east"}'
    #
    # JSON array (single --config.include with multiple matchers):
    # $ python list_of_dataclasses.py \
    #     --config.include '[{"name": "env", "value": "prod"}, {"name": "region", "value": "us-east"}]'
    #
    # Mixed (combining individual objects and arrays):
    # $ python list_of_dataclasses.py \
    #     --config.include '{"name": "env", "value": "prod"}' \
    #     --config.include '[{"name": "region", "value": "us-east"}, {"name": "tier", "value": "critical"}]' \
    #     --config.exclude '{"name": "status", "value": "deprecated", "isRegex": true}'
    #
    # With custom matcher settings:
    # $ python list_of_dataclasses.py \
    #     --config.include '{"name": "version", "value": "^v[2-9]", "isRegex": true}' \
    #     --config.exclude '{"name": "enabled", "value": "true", "isEqual": false}'

    app()
