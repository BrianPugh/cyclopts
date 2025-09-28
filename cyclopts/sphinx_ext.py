"""Sphinx extension for automatic Cyclopts CLI documentation."""

import importlib
from typing import TYPE_CHECKING, Any, Dict, List

import attrs

if TYPE_CHECKING:
    from docutils import nodes
    from sphinx.application import Sphinx
    from sphinx.util.docutils import SphinxDirective

try:
    from docutils import nodes  # noqa: F401
    from sphinx.application import Sphinx
    from sphinx.util import logging
    from sphinx.util.docutils import SphinxDirective

    logger = logging.getLogger(__name__)
    SPHINX_AVAILABLE = True
except ImportError:
    SPHINX_AVAILABLE = False
    if not TYPE_CHECKING:
        SphinxDirective = object  # Fallback base class
        logger = None


def _import_app(module_path: str) -> Any:
    """Import a Cyclopts App from a module path."""
    from cyclopts import App

    if ":" in module_path:
        module_name, app_name = module_path.rsplit(":", 1)
    else:
        module_name, app_name = module_path, None

    try:
        module = importlib.import_module(module_name)
    except ImportError as e:
        raise ImportError(f"Cannot import module '{module_name}': {e}") from e

    if app_name:
        if not hasattr(module, app_name):
            raise AttributeError(f"Module '{module_name}' has no attribute '{app_name}'")
        app = getattr(module, app_name)
        if not isinstance(app, App):
            raise TypeError(f"'{app_name}' is not a Cyclopts App instance")
        return app

    # Auto-discovery: search for App instance
    for name in ["app", "cli", "main"]:
        obj = getattr(module, name, None)
        if isinstance(obj, App):
            return obj

    # Search all public attributes
    for name in dir(module):
        if not name.startswith("_"):
            obj = getattr(module, name)
            if isinstance(obj, App):
                return obj

    raise AttributeError(f"No Cyclopts App found in '{module_name}'. Specify explicitly: '{module_name}:app_name'")


@attrs.define(kw_only=True)
class DirectiveOptions:
    """Configuration for the Cyclopts directive."""

    heading_level: int = 2
    command_prefix: str = ""

    # All booleans must have ``False`` default.
    no_recursive: bool = False
    include_hidden: bool = False
    flatten_commands: bool = False

    @classmethod
    def from_dict(cls, options: dict) -> "DirectiveOptions":
        """Create options from directive options dictionary."""
        kwargs = {}
        for field in attrs.fields(cls):
            # Convert underscore to dash for looking up in options
            option_name = field.name.replace("_", "-")

            if field.type is bool:
                # For boolean fields using directives.flag, presence means True
                # The value is None when present, absent from dict when not specified
                if option_name in options:
                    kwargs[field.name] = True
                # Use default value if not specified
            elif option_name in options:
                # For non-boolean fields, get the value from options
                kwargs[field.name] = options[option_name]
            # If not specified, the dataclass default will be used

        return cls(**kwargs)

    @staticmethod
    def spec() -> Dict[str, Any]:
        """Generate Sphinx option_spec from DirectiveOptions fields."""
        if not SPHINX_AVAILABLE:
            return {}

        from docutils.parsers.rst import directives

        type_mapping = {
            bool: directives.flag,
            int: directives.nonnegative_int,
            str: directives.unchanged,
        }

        option_spec = {}
        for field in attrs.fields(DirectiveOptions):
            option_name = field.name.replace("_", "-")
            validator = type_mapping.get(field.type, directives.unchanged)
            option_spec[option_name] = validator

        return option_spec


def _process_rst_content(content: str, skip_title: bool = False) -> List[str]:
    """Process RST content to remove problematic elements."""
    lines = content.splitlines()
    processed = []
    i = 0

    while i < len(lines):
        line = lines[i]

        # Skip title and underline if requested
        if skip_title and i == 0 and line.strip() and i + 1 < len(lines):
            next_line = lines[i + 1].strip()
            if next_line and set(next_line) <= {"-", "=", "^", "~", '"'}:
                i += 2
                continue

        # Skip .. contents:: directive
        if line.strip().startswith(".. contents::"):
            i += 1
            while i < len(lines) and lines[i].strip() and lines[i][0] in " \t":
                i += 1
            if i < len(lines) and not lines[i].strip():
                i += 1
            continue

        processed.append(line)
        i += 1

    return processed


def _create_section_nodes(lines: List[str], state: Any) -> List["nodes.Node"]:
    """Create section nodes from RST lines."""
    if not SPHINX_AVAILABLE:
        return []

    from docutils import nodes
    from docutils.statemachine import StringList

    result = []
    i = 0

    while i < len(lines):
        line = lines[i]

        # Check for section header
        if i + 1 < len(lines):
            next_line = lines[i + 1]
            if next_line and all(c == "-" for c in next_line.strip()):
                # Create section
                section = nodes.section()
                title_text = line.strip()
                section["ids"] = [title_text.lower().replace(" ", "-").replace("cyclopts-", "cli-cyclopts-")]

                section += nodes.title(text=title_text)

                # Collect section content
                content_lines = []
                i += 2  # Skip title and underline

                while i < len(lines):
                    if i + 1 < len(lines) and all(c == "-" for c in lines[i + 1].strip()):
                        break
                    content_lines.append(lines[i])
                    i += 1

                if content_lines:
                    state.nested_parse(StringList(content_lines), 0, section)

                result.append(section)
                continue

        # Check for literal block (::)
        if line.strip() == "::":
            # Skip the :: line
            i += 1

            # Skip blank line after ::
            if i < len(lines) and not lines[i].strip():
                i += 1

            # Collect indented content for the literal block
            literal_content = []
            while i < len(lines) and lines[i].startswith("    "):
                # Remove the 4-space indentation
                literal_content.append(lines[i][4:])
                i += 1

            # Create a literal block node directly
            if literal_content:
                literal_block = nodes.literal_block()
                literal_block.rawsource = "\n".join(literal_content)
                literal_block.append(nodes.Text("\n".join(literal_content)))
                result.append(literal_block)

            # Skip any trailing blank line
            if i < len(lines) and not lines[i].strip():
                i += 1

            continue

        # Regular content
        if line.strip():
            para = nodes.paragraph()
            state.nested_parse(StringList([line]), 0, para)
            if para.children:
                result.extend(para.children)
        i += 1

    return result


class CycloptsDirective(SphinxDirective):  # type: ignore[misc,valid-type]
    """Sphinx directive for documenting Cyclopts CLI applications."""

    has_content = False
    required_arguments = 1
    optional_arguments = 0
    final_argument_whitespace = False
    option_spec = DirectiveOptions.spec()

    def run(self) -> List["nodes.Node"]:
        """Generate documentation nodes for the Cyclopts app."""
        if not SPHINX_AVAILABLE:
            return []

        module_path = self.arguments[0]
        opts = DirectiveOptions.from_dict(self.options)

        try:
            rst_content = self._generate_documentation(module_path, opts)
            return self._create_nodes(rst_content, opts)
        except (ImportError, AttributeError, TypeError) as e:
            return self._error_node(f"Error generating Cyclopts documentation: {e}")
        except Exception as e:
            return self._error_node(f"Unexpected error: {e}")

    def _generate_documentation(self, module_path: str, opts: DirectiveOptions) -> str:
        """Generate RST documentation for the app."""
        from cyclopts.docs.rst import generate_rst_docs

        app = _import_app(module_path)

        # Call generate_rst_docs directly to access internal no_root_title parameter
        return generate_rst_docs(
            app,
            recursive=not opts.no_recursive,
            include_hidden=opts.include_hidden,
            heading_level=opts.heading_level,
            flatten_commands=opts.flatten_commands,
            command_prefix=opts.command_prefix,
            no_root_title=True,  # Always skip root title in Sphinx context
            sections_only=True,  # Always use sections-only mode for better Sphinx integration
        )

    def _create_nodes(self, rst_content: str, opts: DirectiveOptions) -> List["nodes.Node"]:
        """Create docutils nodes from RST content."""
        if not SPHINX_AVAILABLE:
            return []

        lines = _process_rst_content(rst_content, skip_title=False)  # Title already skipped in generate_docs

        # Always use section nodes for better Sphinx integration
        return _create_section_nodes(lines, self.state)

    def _error_node(self, message: str) -> List["nodes.Node"]:
        """Create an error node with the given message."""
        if not SPHINX_AVAILABLE:
            return []

        from docutils import nodes

        if logger:
            logger.error(message)
        return [nodes.error("", nodes.paragraph(text=message))]


def setup(app: "Sphinx") -> Dict[str, Any]:
    """Setup function for the Sphinx extension."""
    if SPHINX_AVAILABLE:
        app.add_directive("cyclopts", CycloptsDirective)
    return {
        "version": "1.0.0",
        "parallel_read_safe": True,
        "parallel_write_safe": True,
    }
