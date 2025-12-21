"""Snapshot tests for documentation generation.

These tests capture the generated markdown and RST output to detect
unintended changes to the documentation plugins.
"""

import sys
from pathlib import Path

import pytest

# Skip all snapshot tests on Windows due to platform-specific output differences
pytestmark = pytest.mark.skipif(sys.platform == "win32", reason="Snapshot tests not supported on Windows")

# Path to the complex-demo application
COMPLEX_DEMO_DIR = Path(__file__).parent / "apps" / "complex-demo"


@pytest.fixture
def ensure_complex_demo_importable():
    """Ensure the complex_app module can be imported."""
    sys.path.insert(0, str(COMPLEX_DEMO_DIR))
    yield
    sys.path.remove(str(COMPLEX_DEMO_DIR))
    # Clean up any cached imports
    modules_to_remove = [k for k in sys.modules.keys() if k.startswith("complex_app")]
    for mod in modules_to_remove:
        del sys.modules[mod]


class TestMarkdownSnapshots:
    """Snapshot tests for markdown generation."""

    def test_full_app_markdown(self, ensure_complex_demo_importable, md_snapshot):
        """Snapshot the full app markdown output."""
        from complex_app import app

        from cyclopts.docs.markdown import generate_markdown_docs

        markdown = generate_markdown_docs(
            app,
            recursive=True,
            include_hidden=False,
            heading_level=1,
            generate_toc=True,
        )

        assert markdown == md_snapshot

    def test_admin_commands_markdown(self, ensure_complex_demo_importable, md_snapshot):
        """Snapshot markdown for admin commands (tests deep nesting)."""
        from complex_app import app

        from cyclopts.docs.markdown import generate_markdown_docs

        markdown = generate_markdown_docs(
            app,
            recursive=True,
            include_hidden=False,
            heading_level=2,
            generate_toc=False,
            commands_filter=["admin"],
        )

        assert markdown == md_snapshot

    def test_nested_permissions_markdown(self, ensure_complex_demo_importable, md_snapshot):
        """Snapshot markdown for deeply nested permissions commands."""
        from complex_app import app

        from cyclopts.docs.markdown import generate_markdown_docs

        markdown = generate_markdown_docs(
            app,
            recursive=True,
            include_hidden=False,
            heading_level=2,
            generate_toc=False,
            commands_filter=["admin.users.permissions"],
        )

        assert markdown == md_snapshot

    def test_data_commands_markdown(self, ensure_complex_demo_importable, md_snapshot):
        """Snapshot markdown for data commands (tests dataclass flattening)."""
        from complex_app import app

        from cyclopts.docs.markdown import generate_markdown_docs

        markdown = generate_markdown_docs(
            app,
            recursive=True,
            include_hidden=False,
            heading_level=2,
            generate_toc=False,
            commands_filter=["data"],
        )

        assert markdown == md_snapshot

    def test_flattened_commands_markdown(self, ensure_complex_demo_importable, md_snapshot):
        """Snapshot markdown with flatten_commands=True."""
        from complex_app import app

        from cyclopts.docs.markdown import generate_markdown_docs

        markdown = generate_markdown_docs(
            app,
            recursive=True,
            include_hidden=False,
            heading_level=2,
            generate_toc=False,
            flatten_commands=True,
            commands_filter=["admin.users"],  # Limit scope for readable snapshot
        )

        assert markdown == md_snapshot

    def test_hidden_commands_markdown(self, ensure_complex_demo_importable, md_snapshot):
        """Snapshot markdown with include_hidden=True."""
        from complex_app import app

        from cyclopts.docs.markdown import generate_markdown_docs

        markdown = generate_markdown_docs(
            app,
            recursive=False,  # Just top-level to keep snapshot small
            include_hidden=True,
            heading_level=2,
            generate_toc=False,
        )

        assert markdown == md_snapshot

    def test_exclude_commands_markdown(self, ensure_complex_demo_importable, md_snapshot):
        """Snapshot markdown with exclude_commands."""
        from complex_app import app

        from cyclopts.docs.markdown import generate_markdown_docs

        markdown = generate_markdown_docs(
            app,
            recursive=True,
            include_hidden=False,
            heading_level=2,
            generate_toc=False,
            commands_filter=["admin"],
            exclude_commands=["admin.users.permissions"],
        )

        assert markdown == md_snapshot

    def test_server_commands_markdown(self, ensure_complex_demo_importable, md_snapshot):
        """Snapshot markdown for server commands (tests Pydantic if available)."""
        from complex_app import app

        from cyclopts.docs.markdown import generate_markdown_docs

        markdown = generate_markdown_docs(
            app,
            recursive=True,
            include_hidden=False,
            heading_level=2,
            generate_toc=False,
            commands_filter=["server"],
        )

        assert markdown == md_snapshot

    def test_utilities_markdown(self, ensure_complex_demo_importable, md_snapshot):
        """Snapshot markdown for utility commands (tests enums, complex types)."""
        from complex_app import app

        from cyclopts.docs.markdown import generate_markdown_docs

        markdown = generate_markdown_docs(
            app,
            recursive=True,
            include_hidden=False,
            heading_level=2,
            generate_toc=False,
            commands_filter=["cache", "complex-types", "version", "info"],
        )

        assert markdown == md_snapshot


class TestRstSnapshots:
    """Snapshot tests for RST generation."""

    def test_full_app_rst(self, ensure_complex_demo_importable, rst_snapshot):
        """Snapshot the full app RST output."""
        from complex_app import app

        from cyclopts.docs.rst import generate_rst_docs

        rst = generate_rst_docs(
            app,
            recursive=True,
            include_hidden=False,
            heading_level=1,
        )

        assert rst == rst_snapshot

    def test_admin_commands_rst(self, ensure_complex_demo_importable, rst_snapshot):
        """Snapshot RST for admin commands (tests deep nesting)."""
        from complex_app import app

        from cyclopts.docs.rst import generate_rst_docs

        rst = generate_rst_docs(
            app,
            recursive=True,
            include_hidden=False,
            heading_level=2,
            commands_filter=["admin"],
        )

        assert rst == rst_snapshot

    def test_nested_permissions_rst(self, ensure_complex_demo_importable, rst_snapshot):
        """Snapshot RST for deeply nested permissions commands."""
        from complex_app import app

        from cyclopts.docs.rst import generate_rst_docs

        rst = generate_rst_docs(
            app,
            recursive=True,
            include_hidden=False,
            heading_level=2,
            commands_filter=["admin.users.permissions"],
        )

        assert rst == rst_snapshot

    def test_data_commands_rst(self, ensure_complex_demo_importable, rst_snapshot):
        """Snapshot RST for data commands (tests dataclass flattening)."""
        from complex_app import app

        from cyclopts.docs.rst import generate_rst_docs

        rst = generate_rst_docs(
            app,
            recursive=True,
            include_hidden=False,
            heading_level=2,
            commands_filter=["data"],
        )

        assert rst == rst_snapshot

    def test_flattened_commands_rst(self, ensure_complex_demo_importable, rst_snapshot):
        """Snapshot RST with flatten_commands=True."""
        from complex_app import app

        from cyclopts.docs.rst import generate_rst_docs

        rst = generate_rst_docs(
            app,
            recursive=True,
            include_hidden=False,
            heading_level=2,
            flatten_commands=True,
            commands_filter=["admin.users"],  # Limit scope for readable snapshot
        )

        assert rst == rst_snapshot

    def test_hidden_commands_rst(self, ensure_complex_demo_importable, rst_snapshot):
        """Snapshot RST with include_hidden=True."""
        from complex_app import app

        from cyclopts.docs.rst import generate_rst_docs

        rst = generate_rst_docs(
            app,
            recursive=False,  # Just top-level to keep snapshot small
            include_hidden=True,
            heading_level=2,
        )

        assert rst == rst_snapshot

    def test_server_commands_rst(self, ensure_complex_demo_importable, rst_snapshot):
        """Snapshot RST for server commands (tests Pydantic if available)."""
        from complex_app import app

        from cyclopts.docs.rst import generate_rst_docs

        rst = generate_rst_docs(
            app,
            recursive=True,
            include_hidden=False,
            heading_level=2,
            commands_filter=["server"],
        )

        assert rst == rst_snapshot


class TestMkDocsDirectiveSnapshots:
    """Snapshot tests for MkDocs directive processing."""

    def test_simple_directive_output(self, ensure_complex_demo_importable, md_snapshot):
        """Snapshot the output of a simple directive."""
        import textwrap

        from cyclopts.ext.mkdocs import process_cyclopts_directives

        markdown = textwrap.dedent(
            """\
            # CLI Reference

            ::: cyclopts
                module: complex_app:app
                heading_level: 2
                recursive: false
                generate_toc: false
            """
        )

        result = process_cyclopts_directives(markdown, None)
        assert result == md_snapshot

    def test_filtered_directive_output(self, ensure_complex_demo_importable, md_snapshot):
        """Snapshot the output of a filtered directive."""
        import textwrap

        from cyclopts.ext.mkdocs import process_cyclopts_directives

        markdown = textwrap.dedent(
            """\
            # Admin Commands

            ::: cyclopts
                module: complex_app:app
                heading_level: 2
                recursive: true
                commands: [admin.users]
                generate_toc: false
            """
        )

        result = process_cyclopts_directives(markdown, None)
        assert result == md_snapshot

    def test_nested_directive_output(self, ensure_complex_demo_importable, md_snapshot):
        """Snapshot the output for deeply nested commands."""
        import textwrap

        from cyclopts.ext.mkdocs import process_cyclopts_directives

        markdown = textwrap.dedent(
            """\
            # Permissions

            ::: cyclopts
                module: complex_app:app
                heading_level: 3
                recursive: true
                commands: [admin.users.permissions.roles]
                generate_toc: false
            """
        )

        result = process_cyclopts_directives(markdown, None)
        assert result == md_snapshot

    def test_multiple_directives_output(self, ensure_complex_demo_importable, md_snapshot):
        """Snapshot the output of multiple directives on one page."""
        import textwrap

        from cyclopts.ext.mkdocs import process_cyclopts_directives

        markdown = textwrap.dedent(
            """\
            # CLI Reference

            ## Data Commands

            ::: cyclopts
                module: complex_app:app
                heading_level: 3
                commands: [data]
                generate_toc: false

            ## Server Commands

            ::: cyclopts
                module: complex_app:app
                heading_level: 3
                commands: [server]
                generate_toc: false
            """
        )

        result = process_cyclopts_directives(markdown, None)
        assert result == md_snapshot


class TestSphinxDirectiveSnapshots:
    """Snapshot tests for Sphinx directive output."""

    def test_simple_directive_rst(self, ensure_complex_demo_importable, rst_snapshot):
        """Snapshot the RST output for a simple directive."""
        from unittest.mock import MagicMock

        from docutils.statemachine import StringList

        from cyclopts.ext.sphinx import CycloptsDirective

        mock_state = MagicMock()
        captured_content = []

        def capture_nested_parse(string_list, offset, parent):
            captured_content.extend(string_list)

        mock_state.nested_parse = capture_nested_parse

        directive = CycloptsDirective(
            name="cyclopts",
            arguments=["complex_app:app"],
            options={"heading-level": 2, "recursive": False},
            content=StringList(),
            lineno=1,
            content_offset=0,
            block_text="",
            state=mock_state,
            state_machine=MagicMock(),
        )

        directive.run()
        rst_output = "\n".join(captured_content)
        assert rst_output == rst_snapshot

    def test_filtered_directive_rst(self, ensure_complex_demo_importable, rst_snapshot):
        """Snapshot the RST output for a filtered directive."""
        from unittest.mock import MagicMock

        from docutils.statemachine import StringList

        from cyclopts.ext.sphinx import CycloptsDirective

        mock_state = MagicMock()
        captured_content = []

        def capture_nested_parse(string_list, offset, parent):
            captured_content.extend(string_list)

        mock_state.nested_parse = capture_nested_parse

        directive = CycloptsDirective(
            name="cyclopts",
            arguments=["complex_app:app"],
            options={"heading-level": 2, "recursive": True, "commands": "admin.users"},
            content=StringList(),
            lineno=1,
            content_offset=0,
            block_text="",
            state=mock_state,
            state_machine=MagicMock(),
        )

        directive.run()
        rst_output = "\n".join(captured_content)
        assert rst_output == rst_snapshot

    def test_nested_commands_rst(self, ensure_complex_demo_importable, rst_snapshot):
        """Snapshot the RST output for deeply nested commands."""
        from unittest.mock import MagicMock

        from docutils.statemachine import StringList

        from cyclopts.ext.sphinx import CycloptsDirective

        mock_state = MagicMock()
        captured_content = []

        def capture_nested_parse(string_list, offset, parent):
            captured_content.extend(string_list)

        mock_state.nested_parse = capture_nested_parse

        directive = CycloptsDirective(
            name="cyclopts",
            arguments=["complex_app:app"],
            options={"heading-level": 3, "recursive": True, "commands": "admin.users.permissions"},
            content=StringList(),
            lineno=1,
            content_offset=0,
            block_text="",
            state=mock_state,
            state_machine=MagicMock(),
        )

        directive.run()
        rst_output = "\n".join(captured_content)
        assert rst_output == rst_snapshot

    def test_flattened_commands_rst(self, ensure_complex_demo_importable, rst_snapshot):
        """Snapshot the RST output with flatten-commands."""
        from unittest.mock import MagicMock

        from docutils.statemachine import StringList

        from cyclopts.ext.sphinx import CycloptsDirective

        mock_state = MagicMock()
        captured_content = []

        def capture_nested_parse(string_list, offset, parent):
            captured_content.extend(string_list)

        mock_state.nested_parse = capture_nested_parse

        directive = CycloptsDirective(
            name="cyclopts",
            arguments=["complex_app:app"],
            options={"heading-level": 2, "recursive": True, "flatten-commands": True, "commands": "admin.users"},
            content=StringList(),
            lineno=1,
            content_offset=0,
            block_text="",
            state=mock_state,
            state_machine=MagicMock(),
        )

        directive.run()
        rst_output = "\n".join(captured_content)
        assert rst_output == rst_snapshot
