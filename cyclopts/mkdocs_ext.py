"""MkDocs plugin for automatic Cyclopts CLI documentation."""

import re
from typing import TYPE_CHECKING, Any

import attrs

from cyclopts.sphinx_ext import _import_app

if TYPE_CHECKING:
    from mkdocs.config.defaults import MkDocsConfig
    from mkdocs.structure.files import Files
    from mkdocs.structure.pages import Page

try:
    from mkdocs.config import base
    from mkdocs.config import config_options as c
    from mkdocs.exceptions import PluginError
    from mkdocs.plugins import BasePlugin, get_plugin_logger

    logger = get_plugin_logger(__name__)
    MKDOCS_AVAILABLE = True
except ImportError:
    base = None  # type: ignore[assignment]
    c = None  # type: ignore[assignment]
    PluginError = Exception  # type: ignore[assignment,misc]
    MKDOCS_AVAILABLE = False
    if not TYPE_CHECKING:
        BasePlugin = object  # type: ignore[assignment,misc]
        logger = None


@attrs.define(kw_only=True)
class DirectiveOptions:
    """Configuration for the ::: cyclopts directive."""

    module: str
    heading_level: int = 2
    commands: list[str] | None = None
    exclude_commands: list[str] | None = None
    recursive: bool = True
    include_hidden: bool = False
    flatten_commands: bool = False
    generate_toc: bool = True

    @classmethod
    def from_directive_block(
        cls, directive_text: str, *, default_heading_level: int | None = None
    ) -> "DirectiveOptions":
        """Parse options from a ::: cyclopts directive block.

        Expected format:
            ::: cyclopts
                :module: myapp.cli:app
                :heading-level: 2
                :recursive: true
                :commands: cmd1, cmd2

        Parameters
        ----------
        directive_text : str
            The directive text to parse.
        default_heading_level : int | None
            Default heading level from plugin config. Used if :heading-level: not specified.
        """
        lines = directive_text.strip().split("\n")

        # Remove the ::: cyclopts line
        if lines and lines[0].strip().startswith("::: cyclopts"):
            lines = lines[1:]

        options = {}

        for line in lines:
            line = line.strip()
            if not line or not line.startswith(":"):
                continue

            # Parse :key: value format
            match = re.match(r":([a-z-]+):\s*(.*)", line)
            if not match:
                continue

            key, value = match.groups()
            value = value.strip()

            # Convert dash-separated to underscore for Python
            key = key.replace("-", "_")

            # Parse value based on key
            if key in ("commands", "exclude_commands"):
                # Comma-separated list
                if value:
                    options[key] = [cmd.strip() for cmd in value.split(",") if cmd.strip()]
            elif key == "heading_level":
                options[key] = int(value)
            elif key in ("recursive", "include_hidden", "flatten_commands", "generate_toc"):
                # Boolean values
                options[key] = value.lower() in ("true", "yes", "1")
            else:
                options[key] = value

        if "module" not in options:
            raise ValueError("The :module: option is required for ::: cyclopts directive")

        # Apply default heading level if not specified in directive
        if "heading_level" not in options and default_heading_level is not None:
            options["heading_level"] = default_heading_level

        return cls(**options)


# Regex to match ::: cyclopts directive blocks
# The pattern matches:
# - "^::: cyclopts\n" - the directive start on its own line
# - "(?:[ \t]+:[a-z-]+:.*\n?)*" - zero or more option lines (with optional trailing newline for EOF)
DIRECTIVE_PATTERN = re.compile(
    r"^::: cyclopts\n(?:[ \t]+:[a-z-]+:.*\n?)*",
    re.MULTILINE,
)


def process_cyclopts_directives(markdown: str, plugin_config: Any) -> str:
    """Process all ::: cyclopts directives in markdown content.

    Parameters
    ----------
    markdown : str
        The markdown content containing ::: cyclopts directives.
    plugin_config : CycloptsPluginConfig
        The plugin configuration with default values. If None, uses DirectiveOptions defaults.

    Returns
    -------
    str
        The markdown content with directives replaced by generated documentation.
    """
    from cyclopts.docs.markdown import generate_markdown_docs

    # Find all code blocks to exclude from processing
    code_blocks = []

    # Find fenced code blocks (triple backticks or tildes)
    fenced_pattern = re.compile(r"^[`~]{3,}.*?^[`~]{3,}", re.MULTILINE | re.DOTALL)
    for match in fenced_pattern.finditer(markdown):
        code_blocks.append((match.start(), match.end()))

    # Find indented code blocks (lines starting with 4 spaces or tab)
    # Indented code blocks are preceded by a blank line and consist of lines starting with 4 spaces/tab
    lines = markdown.split("\n")
    in_indented_block = False
    block_start = 0
    current_pos = 0

    for i, line in enumerate(lines):
        line_len = len(line) + 1  # +1 for the newline

        # Check if this line starts an indented code block
        if not in_indented_block:
            # Previous line must be blank (or be the first line)
            prev_blank = i == 0 or not lines[i - 1].strip()
            # Current line must start with 4 spaces or a tab and have content
            is_indented = (line.startswith("    ") or line.startswith("\t")) and line.strip()

            if prev_blank and is_indented:
                in_indented_block = True
                block_start = current_pos
        else:
            # Check if we're still in the indented block
            is_indented = (line.startswith("    ") or line.startswith("\t")) and line.strip()
            is_blank = not line.strip()

            # End block if we hit a non-indented, non-blank line
            if not is_indented and not is_blank:
                code_blocks.append((block_start, current_pos))
                in_indented_block = False

        current_pos += line_len

    # If we ended while still in an indented block, add it
    if in_indented_block:
        code_blocks.append((block_start, current_pos))

    def is_in_code_block(pos: int) -> bool:
        """Check if a position is inside a code block."""
        for start, end in code_blocks:
            if start <= pos < end:
                return True
        return False

    def replace_directive(match: re.Match) -> str:
        # Skip if this match is inside a code block
        if is_in_code_block(match.start()):
            return match.group(0)

        directive_text = match.group(0)

        try:
            # Parse directive options, using plugin config defaults
            default_heading = plugin_config.default_heading_level if plugin_config else None
            options = DirectiveOptions.from_directive_block(directive_text, default_heading_level=default_heading)

            # Import the app
            app = _import_app(options.module)

            # Generate markdown documentation
            markdown_docs = generate_markdown_docs(
                app,
                recursive=options.recursive,
                include_hidden=options.include_hidden,
                heading_level=options.heading_level,
                generate_toc=options.generate_toc,
                flatten_commands=options.flatten_commands,
                commands_filter=options.commands,
                exclude_commands=options.exclude_commands,
                no_root_title=True,  # Skip root title in plugin context
            )

            return markdown_docs

        except Exception as e:
            raise PluginError(f"Error processing ::: cyclopts directive: {e}") from e

    # Replace all directives in the markdown
    processed = DIRECTIVE_PATTERN.sub(replace_directive, markdown)
    return processed


if MKDOCS_AVAILABLE:
    assert base is not None
    assert c is not None

    class CycloptsPluginConfig(base.Config):  # type: ignore[misc]
        """Configuration schema for the Cyclopts MkDocs plugin."""

        default_heading_level = c.Type(int, default=2)  # type: ignore[attr-defined]

    class CycloptsPlugin(BasePlugin[CycloptsPluginConfig]):  # type: ignore[misc]
        """MkDocs plugin to generate Cyclopts CLI documentation.

        Usage in mkdocs.yml:
            plugins:
              - cyclopts:
                  default_heading_level: 2

        Usage in Markdown files:
            ::: cyclopts
                :module: myapp.cli:app
                :heading-level: 2
                :recursive: true
                :commands: init, build
                :exclude-commands: debug
        """

        def on_page_markdown(
            self, markdown: str, *, page: "Page", config: "MkDocsConfig", files: "Files", **kwargs
        ) -> str:
            """Process ::: cyclopts directives in markdown content.

            This event is called after the page's markdown is loaded from file
            but before it's converted to HTML.
            """
            if "::: cyclopts" not in markdown:
                return markdown

            return process_cyclopts_directives(markdown, self.config)

else:

    class CycloptsPluginConfig:  # type: ignore[no-redef]
        """Fallback config class when MkDocs is not installed."""

    class CycloptsPlugin:  # type: ignore[no-redef]
        """Fallback plugin class when MkDocs is not installed."""
