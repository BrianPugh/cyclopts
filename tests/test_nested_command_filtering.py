"""Tests for nested command filtering in docs generation."""

import pytest

from cyclopts import App
from cyclopts.docs.markdown import generate_markdown_docs
from cyclopts.docs.rst import generate_rst_docs


@pytest.fixture
def nested_app():
    """Create a nested app structure for testing filtering."""
    app = App(name="myapp", help="My application")

    training = App(name="training", help="Training commands")
    app.command(training, name="training")

    @training.command
    def create_dataset():
        """Create a new dataset."""
        pass

    @training.command
    def run():
        """Run training."""
        pass

    # Add a deeper nesting level
    dataset = App(name="dataset", help="Dataset operations")
    training.command(dataset, name="dataset")

    @dataset.command
    def validate():
        """Validate the dataset."""
        pass

    deploy = App(name="deploy", help="Deployment commands")
    app.command(deploy, name="deploy")

    @deploy.command
    def production():
        """Deploy to production."""
        pass

    return app


class TestMarkdownNestedFiltering:
    """Test nested command filtering in Markdown generation."""

    def test_filter_nested_command_include_only(self, nested_app):
        """Test that :commands: training.create-dataset shows only that command."""
        docs = generate_markdown_docs(nested_app, commands_filter=["training.create-dataset"])

        # Should include training and create-dataset
        assert "training" in docs.lower()
        assert "create-dataset" in docs or "create_dataset" in docs

        # Should NOT include run, dataset, deploy
        assert "run" not in docs.lower() or "run training" not in docs.lower()
        assert "dataset" not in docs.lower() or "create a new dataset" in docs.lower()  # Allow in description
        assert "deploy" not in docs.lower()
        assert "production" not in docs.lower()

    def test_filter_nested_command_exclude(self, nested_app):
        """Test that :exclude-commands: training.create-dataset excludes that command."""
        docs = generate_markdown_docs(nested_app, exclude_commands=["training.create-dataset"])

        # Should include training, run, deploy, production
        assert "training" in docs.lower()
        assert "run" in docs.lower()
        assert "deploy" in docs.lower()
        assert "production" in docs.lower()

        # Should NOT include create-dataset
        lines = docs.split("\n")
        # Check that create-dataset doesn't appear as a command
        for i, line in enumerate(lines):
            if "create-dataset" in line.lower() or "create_dataset" in line.lower():
                # It's only OK if it's in the description of another command
                if i > 0 and "create a new dataset" not in line.lower():
                    pytest.fail(f"create-dataset should be excluded but found in: {line}")

    def test_filter_deeply_nested_command(self, nested_app):
        """Test filtering a deeply nested command."""
        docs = generate_markdown_docs(nested_app, commands_filter=["training.dataset.validate"])

        # Should include training, dataset, validate
        assert "training" in docs.lower()
        assert "dataset" in docs.lower()
        assert "validate" in docs.lower()

        # Should NOT include run, create-dataset, deploy, production
        # Allow "run" in usage strings
        for line in docs.split("\n"):
            if "run" in line.lower() and "training" in line.lower():
                # Only OK if it's in a usage string
                if "usage" not in docs[: docs.find(line)].lower()[-100:]:
                    pytest.fail(f"'run' command should be excluded but found in: {line}")

    def test_filter_parent_command_includes_all_children(self, nested_app):
        """Test that filtering to a parent command includes all its children."""
        docs = generate_markdown_docs(nested_app, commands_filter=["training"])

        # Should include training and ALL its subcommands
        assert "training" in docs.lower()
        assert "create-dataset" in docs or "create_dataset" in docs
        assert "run" in docs.lower()
        assert "dataset" in docs.lower()
        assert "validate" in docs.lower()

        # Should NOT include deploy
        assert "deploy" not in docs.lower()
        assert "production" not in docs.lower()

    def test_exclude_parent_command_excludes_all_children(self, nested_app):
        """Test that excluding a parent command excludes all its children."""
        docs = generate_markdown_docs(nested_app, exclude_commands=["training"])

        # Should include deploy and production
        assert "deploy" in docs.lower()
        assert "production" in docs.lower()

        # Should NOT include training or any of its subcommands
        # Check carefully as "training" might appear in app description
        lines = docs.split("\n")
        in_commands_section = False
        for line in lines:
            if "**commands**" in line.lower():
                in_commands_section = True
            elif line.startswith("#"):
                in_commands_section = False

            if in_commands_section or line.startswith("#"):
                if "training" in line.lower() and "training" not in nested_app.help.lower():
                    # Skip if it's just in the description
                    if "## " not in line and "* `" not in line:
                        continue
                    pytest.fail(f"training should be excluded but found in: {line}")


class TestRSTNestedFiltering:
    """Test nested command filtering in RST generation."""

    def test_filter_nested_command_include_only(self, nested_app):
        """Test that :commands: training.create-dataset shows only that command."""
        docs = generate_rst_docs(nested_app, commands_filter=["training.create-dataset"])

        # Should include training and create-dataset sections
        assert ".. _cyclopts-myapp-training:" in docs
        assert (
            ".. _cyclopts-myapp-training-create-dataset:" in docs
            or ".. _cyclopts-myapp-training-create_dataset:" in docs
        )

        # Should NOT include run, dataset, deploy sections
        assert ".. _cyclopts-myapp-training-run:" not in docs
        assert ".. _cyclopts-myapp-training-dataset:" not in docs
        assert ".. _cyclopts-myapp-deploy:" not in docs
        assert ".. _cyclopts-myapp-deploy-production:" not in docs

    def test_filter_nested_command_exclude(self, nested_app):
        """Test that :exclude-commands: training.create-dataset excludes that command."""
        docs = generate_rst_docs(nested_app, exclude_commands=["training.create-dataset"])

        # Should include training, run, deploy sections
        assert ".. _cyclopts-myapp-training:" in docs
        assert ".. _cyclopts-myapp-training-run:" in docs
        assert ".. _cyclopts-myapp-deploy:" in docs
        assert ".. _cyclopts-myapp-deploy-production:" in docs

        # Should NOT include create-dataset section
        assert ".. _cyclopts-myapp-training-create-dataset:" not in docs
        assert ".. _cyclopts-myapp-training-create_dataset:" not in docs

    def test_filter_deeply_nested_command(self, nested_app):
        """Test filtering a deeply nested command."""
        docs = generate_rst_docs(nested_app, commands_filter=["training.dataset.validate"])

        # Should include training, dataset, validate sections
        assert ".. _cyclopts-myapp-training:" in docs
        assert ".. _cyclopts-myapp-training-dataset:" in docs
        assert ".. _cyclopts-myapp-training-dataset-validate:" in docs

        # Should NOT include run, create-dataset, deploy sections
        assert ".. _cyclopts-myapp-training-run:" not in docs
        assert ".. _cyclopts-myapp-training-create-dataset:" not in docs
        assert ".. _cyclopts-myapp-deploy:" not in docs

    def test_filter_parent_command_includes_all_children(self, nested_app):
        """Test that filtering to a parent command includes all its children."""
        docs = generate_rst_docs(nested_app, commands_filter=["training"])

        # Should include training and ALL its subcommands
        assert ".. _cyclopts-myapp-training:" in docs
        assert (
            ".. _cyclopts-myapp-training-create-dataset:" in docs
            or ".. _cyclopts-myapp-training-create_dataset:" in docs
        )
        assert ".. _cyclopts-myapp-training-run:" in docs
        assert ".. _cyclopts-myapp-training-dataset:" in docs

        # Should NOT include deploy
        assert ".. _cyclopts-myapp-deploy:" not in docs

    def test_exclude_parent_command_excludes_all_children(self, nested_app):
        """Test that excluding a parent command excludes all its children."""
        docs = generate_rst_docs(nested_app, exclude_commands=["training"])

        # Should include deploy and production
        assert ".. _cyclopts-myapp-deploy:" in docs
        assert ".. _cyclopts-myapp-deploy-production:" in docs

        # Should NOT include training or any of its subcommands
        assert ".. _cyclopts-myapp-training:" not in docs
        assert ".. _cyclopts-myapp-training-create-dataset:" not in docs
        assert ".. _cyclopts-myapp-training-run:" not in docs
        assert ".. _cyclopts-myapp-training-dataset:" not in docs
