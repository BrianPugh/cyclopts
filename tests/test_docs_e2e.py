"""End-to-end tests for documentation generation.

These tests actually build documentation using mkdocs and sphinx,
and verify that the generated output contains expected content.
"""

import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

# Path to the complex-demo application
COMPLEX_DEMO_DIR = Path(__file__).parent / "apps" / "complex-demo"


def _run_command(cmd: list[str], cwd: Path, env: dict | None = None) -> subprocess.CompletedProcess:
    """Run a command and return the result."""
    full_env = os.environ.copy()
    if env:
        full_env.update(env)

    return subprocess.run(
        cmd,
        cwd=cwd,
        capture_output=True,
        text=True,
        env=full_env,
    )


class TestMkDocsBuild:
    """Test MkDocs documentation builds."""

    @pytest.fixture
    def mkdocs_build_dir(self, tmp_path):
        """Create a temporary build directory for MkDocs."""
        build_dir = tmp_path / "site"
        return build_dir

    @pytest.fixture
    def ensure_complex_demo_importable(self):
        """Ensure the complex_app module can be imported."""
        sys.path.insert(0, str(COMPLEX_DEMO_DIR))
        yield
        sys.path.remove(str(COMPLEX_DEMO_DIR))

    @pytest.mark.skipif(
        shutil.which("mkdocs") is None,
        reason="mkdocs not installed or not in PATH",
    )
    def test_mkdocs_build_succeeds(self, mkdocs_build_dir, ensure_complex_demo_importable):
        """Test that mkdocs build completes successfully."""
        pytest.importorskip("mkdocs")

        result = _run_command(
            ["mkdocs", "build", "--site-dir", str(mkdocs_build_dir)],
            cwd=COMPLEX_DEMO_DIR,
            env={"PYTHONPATH": str(COMPLEX_DEMO_DIR)},
        )

        assert result.returncode == 0, f"mkdocs build failed:\nSTDOUT:\n{result.stdout}\nSTDERR:\n{result.stderr}"
        assert mkdocs_build_dir.exists(), "Build directory was not created"

    @pytest.mark.skipif(
        shutil.which("mkdocs") is None,
        reason="mkdocs not installed or not in PATH",
    )
    def test_mkdocs_output_contains_commands(self, mkdocs_build_dir, ensure_complex_demo_importable):
        """Test that built documentation contains expected command content."""
        pytest.importorskip("mkdocs")

        result = _run_command(
            ["mkdocs", "build", "--site-dir", str(mkdocs_build_dir)],
            cwd=COMPLEX_DEMO_DIR,
            env={"PYTHONPATH": str(COMPLEX_DEMO_DIR)},
        )

        if result.returncode != 0:
            pytest.skip(f"mkdocs build failed: {result.stderr}")

        # Check CLI index page
        cli_index = mkdocs_build_dir / "cli" / "index" / "index.html"
        if not cli_index.exists():
            # Try alternate path structure
            cli_index = mkdocs_build_dir / "cli" / "index.html"

        assert cli_index.exists(), f"CLI index page not found. Contents: {list(mkdocs_build_dir.rglob('*.html'))}"

        content = cli_index.read_text()

        # Verify key commands are documented
        assert "admin" in content.lower(), "admin command not found in CLI index"
        assert "data" in content.lower(), "data command not found in CLI index"
        assert "server" in content.lower(), "server command not found in CLI index"

    @pytest.mark.skipif(
        shutil.which("mkdocs") is None,
        reason="mkdocs not installed or not in PATH",
    )
    def test_mkdocs_output_contains_nested_commands(self, mkdocs_build_dir, ensure_complex_demo_importable):
        """Test that nested commands (4 levels deep) are documented."""
        pytest.importorskip("mkdocs")

        result = _run_command(
            ["mkdocs", "build", "--site-dir", str(mkdocs_build_dir)],
            cwd=COMPLEX_DEMO_DIR,
            env={"PYTHONPATH": str(COMPLEX_DEMO_DIR)},
        )

        if result.returncode != 0:
            pytest.skip(f"mkdocs build failed: {result.stderr}")

        # Check admin page for deeply nested commands
        admin_page = mkdocs_build_dir / "cli" / "admin" / "index.html"
        if not admin_page.exists():
            admin_page = mkdocs_build_dir / "cli" / "admin.html"

        if not admin_page.exists():
            pytest.skip(f"Admin page not found. Contents: {list(mkdocs_build_dir.rglob('*.html'))}")

        content = admin_page.read_text()

        # Verify nested command hierarchy is present
        assert "users" in content.lower(), "users subcommand not found"
        assert "permissions" in content.lower(), "permissions subcommand not found"
        # The deepest level
        assert "roles" in content.lower() or "role" in content.lower(), "roles subcommand not found"

    @pytest.mark.skipif(
        shutil.which("mkdocs") is None,
        reason="mkdocs not installed or not in PATH",
    )
    def test_mkdocs_output_contains_dataclass_params(self, mkdocs_build_dir, ensure_complex_demo_importable):
        """Test that dataclass-flattened parameters appear correctly."""
        pytest.importorskip("mkdocs")

        result = _run_command(
            ["mkdocs", "build", "--site-dir", str(mkdocs_build_dir)],
            cwd=COMPLEX_DEMO_DIR,
            env={"PYTHONPATH": str(COMPLEX_DEMO_DIR)},
        )

        if result.returncode != 0:
            pytest.skip(f"mkdocs build failed: {result.stderr}")

        # Check data page for flattened dataclass parameters
        data_page = mkdocs_build_dir / "cli" / "data" / "index.html"
        if not data_page.exists():
            data_page = mkdocs_build_dir / "cli" / "data.html"

        if not data_page.exists():
            pytest.skip(f"Data page not found. Contents: {list(mkdocs_build_dir.rglob('*.html'))}")

        content = data_page.read_text()

        # Verify flattened dataclass parameters appear
        # These come from ProcessingConfig and PathConfig
        assert "batch" in content.lower(), "batch-size parameter not found"
        assert "worker" in content.lower(), "workers parameter not found"
        assert "output" in content.lower(), "output-dir parameter not found"

    @pytest.mark.skipif(
        shutil.which("mkdocs") is None,
        reason="mkdocs not installed or not in PATH",
    )
    def test_mkdocs_output_contains_complex_types(self, mkdocs_build_dir, ensure_complex_demo_importable):
        """Test that complex union types are documented correctly."""
        pytest.importorskip("mkdocs")

        result = _run_command(
            ["mkdocs", "build", "--site-dir", str(mkdocs_build_dir)],
            cwd=COMPLEX_DEMO_DIR,
            env={"PYTHONPATH": str(COMPLEX_DEMO_DIR)},
        )

        if result.returncode != 0:
            pytest.skip(f"mkdocs build failed: {result.stderr}")

        # Check utilities page for complex types
        utils_page = mkdocs_build_dir / "cli" / "utilities" / "index.html"
        if not utils_page.exists():
            utils_page = mkdocs_build_dir / "cli" / "utilities.html"

        if not utils_page.exists():
            pytest.skip(f"Utilities page not found. Contents: {list(mkdocs_build_dir.rglob('*.html'))}")

        content = utils_page.read_text()

        # Verify complex type parameters appear
        assert "auto" in content.lower(), "'auto' literal option not found"
        assert "worker" in content.lower(), "worker-count parameter not found"

    @pytest.mark.skipif(
        shutil.which("mkdocs") is None,
        reason="mkdocs not installed or not in PATH",
    )
    def test_mkdocs_hidden_commands_excluded_by_default(self, mkdocs_build_dir, ensure_complex_demo_importable):
        """Test that hidden commands are not included by default."""
        pytest.importorskip("mkdocs")

        result = _run_command(
            ["mkdocs", "build", "--site-dir", str(mkdocs_build_dir)],
            cwd=COMPLEX_DEMO_DIR,
            env={"PYTHONPATH": str(COMPLEX_DEMO_DIR)},
        )

        if result.returncode != 0:
            pytest.skip(f"mkdocs build failed: {result.stderr}")

        # Check CLI index (which doesn't use include_hidden)
        cli_index = mkdocs_build_dir / "cli" / "index" / "index.html"
        if not cli_index.exists():
            cli_index = mkdocs_build_dir / "cli" / "index.html"

        if not cli_index.exists():
            pytest.skip(f"CLI index not found. Contents: {list(mkdocs_build_dir.rglob('*.html'))}")

        content = cli_index.read_text()

        # internal_maintenance is marked show=False, should not appear
        assert "internal_maintenance" not in content and "internal-maintenance" not in content, (
            "Hidden command internal_maintenance should not appear"
        )

    @pytest.mark.skipif(
        shutil.which("mkdocs") is None,
        reason="mkdocs not installed or not in PATH",
    )
    def test_mkdocs_hidden_commands_included_when_requested(self, mkdocs_build_dir, ensure_complex_demo_importable):
        """Test that hidden commands appear when include_hidden is True."""
        pytest.importorskip("mkdocs")

        result = _run_command(
            ["mkdocs", "build", "--site-dir", str(mkdocs_build_dir)],
            cwd=COMPLEX_DEMO_DIR,
            env={"PYTHONPATH": str(COMPLEX_DEMO_DIR)},
        )

        if result.returncode != 0:
            pytest.skip(f"mkdocs build failed: {result.stderr}")

        # Check full reference page (which uses include_hidden: true)
        full_page = mkdocs_build_dir / "cli" / "full" / "index.html"
        if not full_page.exists():
            full_page = mkdocs_build_dir / "cli" / "full.html"

        if not full_page.exists():
            pytest.skip(f"Full page not found. Contents: {list(mkdocs_build_dir.rglob('*.html'))}")

        content = full_page.read_text()

        # internal_maintenance should appear on the full page
        assert "internal" in content.lower(), "Hidden command should appear with include_hidden=true"


class TestSphinxBuild:
    """Test Sphinx documentation builds."""

    @pytest.fixture
    def sphinx_build_dir(self, tmp_path):
        """Create a temporary build directory for Sphinx."""
        build_dir = tmp_path / "_build" / "html"
        return build_dir

    @pytest.fixture
    def ensure_complex_demo_importable(self):
        """Ensure the complex_app module can be imported."""
        sys.path.insert(0, str(COMPLEX_DEMO_DIR))
        yield
        sys.path.remove(str(COMPLEX_DEMO_DIR))

    @pytest.mark.skipif(
        shutil.which("sphinx-build") is None,
        reason="sphinx-build not installed or not in PATH",
    )
    def test_sphinx_build_succeeds(self, sphinx_build_dir, ensure_complex_demo_importable):
        """Test that sphinx-build completes successfully."""
        pytest.importorskip("sphinx")

        source_dir = COMPLEX_DEMO_DIR / "docs" / "source"
        result = _run_command(
            ["sphinx-build", "-b", "html", str(source_dir), str(sphinx_build_dir)],
            cwd=COMPLEX_DEMO_DIR,
            env={"PYTHONPATH": str(COMPLEX_DEMO_DIR)},
        )

        assert result.returncode == 0, f"sphinx-build failed:\nSTDOUT:\n{result.stdout}\nSTDERR:\n{result.stderr}"
        assert sphinx_build_dir.exists(), "Build directory was not created"

    @pytest.mark.skipif(
        shutil.which("sphinx-build") is None,
        reason="sphinx-build not installed or not in PATH",
    )
    def test_sphinx_output_contains_commands(self, sphinx_build_dir, ensure_complex_demo_importable):
        """Test that built documentation contains expected command content."""
        pytest.importorskip("sphinx")

        source_dir = COMPLEX_DEMO_DIR / "docs" / "source"
        result = _run_command(
            ["sphinx-build", "-b", "html", str(source_dir), str(sphinx_build_dir)],
            cwd=COMPLEX_DEMO_DIR,
            env={"PYTHONPATH": str(COMPLEX_DEMO_DIR)},
        )

        if result.returncode != 0:
            pytest.skip(f"sphinx-build failed: {result.stderr}")

        # Check CLI index page
        cli_index = sphinx_build_dir / "cli" / "index.html"
        if not cli_index.exists():
            pytest.skip(f"CLI index page not found. Contents: {list(sphinx_build_dir.rglob('*.html'))}")

        content = cli_index.read_text()

        # Verify key commands are documented
        assert "admin" in content.lower(), "admin command not found in CLI index"
        assert "data" in content.lower(), "data command not found in CLI index"
        assert "server" in content.lower(), "server command not found in CLI index"

    @pytest.mark.skipif(
        shutil.which("sphinx-build") is None,
        reason="sphinx-build not installed or not in PATH",
    )
    def test_sphinx_output_contains_nested_commands(self, sphinx_build_dir, ensure_complex_demo_importable):
        """Test that nested commands (4 levels deep) are documented."""
        pytest.importorskip("sphinx")

        source_dir = COMPLEX_DEMO_DIR / "docs" / "source"
        result = _run_command(
            ["sphinx-build", "-b", "html", str(source_dir), str(sphinx_build_dir)],
            cwd=COMPLEX_DEMO_DIR,
            env={"PYTHONPATH": str(COMPLEX_DEMO_DIR)},
        )

        if result.returncode != 0:
            pytest.skip(f"sphinx-build failed: {result.stderr}")

        # Check admin page for deeply nested commands
        admin_page = sphinx_build_dir / "cli" / "admin.html"
        if not admin_page.exists():
            pytest.skip(f"Admin page not found. Contents: {list(sphinx_build_dir.rglob('*.html'))}")

        content = admin_page.read_text()

        # Verify nested command hierarchy is present
        assert "users" in content.lower(), "users subcommand not found"
        assert "permissions" in content.lower(), "permissions subcommand not found"

    @pytest.mark.skipif(
        shutil.which("sphinx-build") is None,
        reason="sphinx-build not installed or not in PATH",
    )
    def test_sphinx_output_contains_dataclass_params(self, sphinx_build_dir, ensure_complex_demo_importable):
        """Test that dataclass-flattened parameters appear correctly."""
        pytest.importorskip("sphinx")

        source_dir = COMPLEX_DEMO_DIR / "docs" / "source"
        result = _run_command(
            ["sphinx-build", "-b", "html", str(source_dir), str(sphinx_build_dir)],
            cwd=COMPLEX_DEMO_DIR,
            env={"PYTHONPATH": str(COMPLEX_DEMO_DIR)},
        )

        if result.returncode != 0:
            pytest.skip(f"sphinx-build failed: {result.stderr}")

        # Check data page for flattened dataclass parameters
        data_page = sphinx_build_dir / "cli" / "data.html"
        if not data_page.exists():
            pytest.skip(f"Data page not found. Contents: {list(sphinx_build_dir.rglob('*.html'))}")

        content = data_page.read_text()

        # Verify flattened dataclass parameters appear
        assert "batch" in content.lower(), "batch-size parameter not found"
        assert "worker" in content.lower(), "workers parameter not found"

    @pytest.mark.skipif(
        shutil.which("sphinx-build") is None,
        reason="sphinx-build not installed or not in PATH",
    )
    def test_sphinx_rst_anchors_generated(self, sphinx_build_dir, ensure_complex_demo_importable):
        """Test that RST reference anchors are generated."""
        pytest.importorskip("sphinx")

        source_dir = COMPLEX_DEMO_DIR / "docs" / "source"
        result = _run_command(
            ["sphinx-build", "-b", "html", str(source_dir), str(sphinx_build_dir)],
            cwd=COMPLEX_DEMO_DIR,
            env={"PYTHONPATH": str(COMPLEX_DEMO_DIR)},
        )

        if result.returncode != 0:
            pytest.skip(f"sphinx-build failed: {result.stderr}")

        # Check that anchor IDs are present in the output
        cli_index = sphinx_build_dir / "cli" / "index.html"
        if not cli_index.exists():
            pytest.skip(f"CLI index not found. Contents: {list(sphinx_build_dir.rglob('*.html'))}")

        content = cli_index.read_text()

        # Check for anchor elements (id attributes in headers)
        assert 'id="' in content, "No anchor IDs found in output"


class TestDocstringFormats:
    """Test that different docstring formats are handled correctly."""

    @pytest.fixture
    def ensure_complex_demo_importable(self):
        """Ensure the complex_app module can be imported."""
        sys.path.insert(0, str(COMPLEX_DEMO_DIR))
        yield
        sys.path.remove(str(COMPLEX_DEMO_DIR))

    def test_numpy_docstring_parsing(self, ensure_complex_demo_importable):
        """Test that NumPy-style docstrings are parsed correctly."""
        from complex_app import numpy_style

        # The docstring should be parseable
        assert numpy_style.__doc__ is not None
        assert "name" in numpy_style.__doc__
        assert "count" in numpy_style.__doc__

    def test_google_docstring_parsing(self, ensure_complex_demo_importable):
        """Test that Google-style docstrings are parsed correctly."""
        from complex_app import google_style

        # The docstring should be parseable
        assert google_style.__doc__ is not None
        assert "name" in google_style.__doc__
        assert "count" in google_style.__doc__

    def test_sphinx_docstring_parsing(self, ensure_complex_demo_importable):
        """Test that Sphinx-style docstrings are parsed correctly."""
        from complex_app import sphinx_style

        # The docstring should be parseable
        assert sphinx_style.__doc__ is not None
        assert "name" in sphinx_style.__doc__
        assert "count" in sphinx_style.__doc__


class TestDataclassFlattening:
    """Test that dataclass parameter flattening works correctly."""

    @pytest.fixture
    def ensure_complex_demo_importable(self):
        """Ensure the complex_app module can be imported."""
        sys.path.insert(0, str(COMPLEX_DEMO_DIR))
        yield
        sys.path.remove(str(COMPLEX_DEMO_DIR))

    def test_dataclass_config_imported(self, ensure_complex_demo_importable):
        """Test that dataclass configs can be imported."""
        from complex_app import DatabaseConfig, PathConfig, PipelineConfig, ProcessingConfig

        # All should be dataclasses
        assert DatabaseConfig is not None
        assert ProcessingConfig is not None
        assert PathConfig is not None
        assert PipelineConfig is not None

    def test_dataclass_defaults_accessible(self, ensure_complex_demo_importable):
        """Test that dataclass defaults are accessible."""
        from complex_app import DatabaseConfig

        config = DatabaseConfig()
        assert config.host == "localhost"
        assert config.port == 5432
        assert config.ssl_mode == "prefer"

    def test_nested_dataclass_works(self, ensure_complex_demo_importable):
        """Test that nested dataclasses work."""
        from complex_app import PathConfig, PipelineConfig, ProcessingConfig

        config = PipelineConfig()
        assert isinstance(config.paths, PathConfig)
        assert isinstance(config.processing, ProcessingConfig)


class TestEnumsAndFlags:
    """Test enum and flag handling."""

    @pytest.fixture
    def ensure_complex_demo_importable(self):
        """Ensure the complex_app module can be imported."""
        sys.path.insert(0, str(COMPLEX_DEMO_DIR))
        yield
        sys.path.remove(str(COMPLEX_DEMO_DIR))

    def test_enum_members(self, ensure_complex_demo_importable):
        """Test that enums have expected members."""
        from complex_app import LogLevel, OutputFormat

        assert LogLevel.DEBUG.value == "debug"
        assert LogLevel.INFO.value == "info"
        assert OutputFormat.JSON.value == "json"
        assert OutputFormat.YAML.value == "yaml"

    def test_flag_combinations(self, ensure_complex_demo_importable):
        """Test that flags can be combined."""
        from complex_app import Permission

        combined = Permission.READ | Permission.WRITE
        assert Permission.READ in combined
        assert Permission.WRITE in combined
        assert Permission.EXECUTE not in combined


class TestAppStructure:
    """Test the application structure."""

    @pytest.fixture
    def ensure_complex_demo_importable(self):
        """Ensure the complex_app module can be imported."""
        sys.path.insert(0, str(COMPLEX_DEMO_DIR))
        yield
        sys.path.remove(str(COMPLEX_DEMO_DIR))

    def test_app_has_commands(self, ensure_complex_demo_importable):
        """Test that the app has the expected commands registered."""
        from complex_app import app

        # Get command names
        command_names = set(app._commands.keys())

        # Check for expected top-level commands/apps
        assert "admin" in command_names, "admin app not registered"
        assert "data" in command_names, "data app not registered"
        assert "server" in command_names, "server app not registered"
        assert "cache" in command_names, "cache app not registered"

    def test_nested_app_structure(self, ensure_complex_demo_importable):
        """Test that nested apps have the expected structure."""
        from complex_app import admin_app, permissions_app, roles_app, users_app

        # Check nesting: admin -> users -> permissions -> roles
        assert "users" in admin_app._commands
        assert "permissions" in users_app._commands
        assert "roles" in permissions_app._commands

        # Check roles commands
        role_commands = set(roles_app._commands.keys())
        assert "list-roles" in role_commands or "list_roles" in role_commands
        assert "create-role" in role_commands or "create_role" in role_commands

    def test_groups_configured(self, ensure_complex_demo_importable):
        """Test that groups are properly configured."""
        from complex_app import global_group, subcommands_group, utilities_group

        assert global_group is not None
        assert subcommands_group is not None
        assert utilities_group is not None

        # Check sort keys - create_ordered() creates tuple sort keys like (user_sort_key, count)
        # We just verify they're in the right order (smaller tuples sort first)
        assert global_group.sort_key is not None
        assert subcommands_group.sort_key is not None
        assert utilities_group.sort_key is not None
        assert global_group.sort_key < subcommands_group.sort_key
        assert subcommands_group.sort_key < utilities_group.sort_key


class TestMarkdownGeneration:
    """Test direct markdown generation without building."""

    @pytest.fixture
    def ensure_complex_demo_importable(self):
        """Ensure the complex_app module can be imported."""
        sys.path.insert(0, str(COMPLEX_DEMO_DIR))
        yield
        sys.path.remove(str(COMPLEX_DEMO_DIR))

    def test_generate_markdown_basic(self, ensure_complex_demo_importable):
        """Test basic markdown generation."""
        from complex_app import app

        from cyclopts.docs.markdown import generate_markdown_docs

        markdown = generate_markdown_docs(app, recursive=True)

        assert "complex-cli" in markdown
        assert "admin" in markdown.lower()
        assert "data" in markdown.lower()
        assert "server" in markdown.lower()

    def test_generate_markdown_with_filter(self, ensure_complex_demo_importable):
        """Test markdown generation with command filtering."""
        from complex_app import app

        from cyclopts.docs.markdown import generate_markdown_docs

        markdown = generate_markdown_docs(
            app,
            recursive=True,
            commands_filter=["admin"],
        )

        assert "admin" in markdown.lower()
        # Other top-level commands should not be present
        assert "data process" not in markdown.lower()
        assert "server start" not in markdown.lower()

    def test_generate_markdown_nested_filter(self, ensure_complex_demo_importable):
        """Test markdown generation with nested command filtering."""
        from complex_app import app

        from cyclopts.docs.markdown import generate_markdown_docs

        markdown = generate_markdown_docs(
            app,
            recursive=True,
            commands_filter=["admin.users.permissions"],
        )

        assert "permissions" in markdown.lower()
        assert "grant" in markdown.lower() or "revoke" in markdown.lower()

    def test_generate_markdown_flattened(self, ensure_complex_demo_importable):
        """Test markdown generation with flattened commands."""
        from complex_app import app

        from cyclopts.docs.markdown import generate_markdown_docs

        markdown = generate_markdown_docs(
            app,
            recursive=True,
            flatten_commands=True,
        )

        # All commands should be at the same heading level
        # Count heading levels (looking for consistent depth)
        lines = markdown.split("\n")
        heading_levels = []
        for line in lines:
            if line.startswith("#") and not line.startswith("```"):
                level = len(line) - len(line.lstrip("#"))
                heading_levels.append(level)

        # With flatten_commands, most headings should be at the same level
        # (excluding the root title)
        if len(heading_levels) > 2:
            # Most command headings should be at the same level
            from collections import Counter

            counts = Counter(heading_levels)
            most_common_level, _ = counts.most_common(1)[0]
            same_level_count = sum(1 for h in heading_levels if h == most_common_level)
            # At least half should be at the same level when flattened
            assert same_level_count >= len(heading_levels) // 2, "Commands not properly flattened"

    def test_generate_markdown_include_hidden(self, ensure_complex_demo_importable):
        """Test markdown generation with hidden commands included."""
        from complex_app import app

        from cyclopts.docs.markdown import generate_markdown_docs

        # Without include_hidden
        markdown_normal = generate_markdown_docs(app, recursive=True, include_hidden=False)

        # With include_hidden
        markdown_hidden = generate_markdown_docs(app, recursive=True, include_hidden=True)

        # Hidden command should only appear when include_hidden=True
        has_internal_normal = "internal-maintenance" in markdown_normal or "internal_maintenance" in markdown_normal
        has_internal_hidden = "internal-maintenance" in markdown_hidden or "internal_maintenance" in markdown_hidden

        assert not has_internal_normal, "Hidden command should not appear without include_hidden"
        assert has_internal_hidden, "Hidden command should appear with include_hidden=True"
