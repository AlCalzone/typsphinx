"""
Tests for label attachment in generated Typst output.

Typst labels can only be attached to an element in markup mode. The document
body is emitted in unified code mode (``#{ ... }``), where ``element <label>``
is a syntax error ("expected semicolon or line break") and a bare
``label("id")`` statement attaches to nothing ("cannot join label with
content"). Labelled elements must therefore be wrapped in a markup block
(``[#figure(...) <label>]``) and standalone targets must produce an invisible
attachable anchor (``[#metadata(none) <label>]``).
"""

import subprocess
from pathlib import Path

import pytest
import typst


@pytest.fixture
def label_project_dir():
    """Return the path to the label_attachment test project."""
    return Path(__file__).parent / "fixtures" / "label_attachment"


@pytest.fixture
def built_typ_file(label_project_dir, tmp_path):
    """Build the label_attachment project and return the generated index.typ."""
    build_dir = tmp_path / "_build"
    result = subprocess.run(
        [
            "uv",
            "run",
            "sphinx-build",
            "-b",
            "typst",
            str(label_project_dir),
            str(build_dir),
        ],
        capture_output=True,
        text=True,
    )
    assert (
        result.returncode == 0
    ), f"sphinx-build failed:\nSTDOUT:\n{result.stdout}\nSTDERR:\n{result.stderr}"

    typ_file = build_dir / "index.typ"
    assert typ_file.exists(), "index.typ should be generated"
    return typ_file


class TestLabelAttachment:
    """Labels must be valid Typst and attached to an element."""

    def test_section_label_attached_to_heading(self, built_typ_file):
        """Explicit section targets must be attached to the heading."""
        content = built_typ_file.read_text()

        # Heading with a label must be wrapped in a markup block, with the
        # primary id attached and the explicit `.. _intro-section:` target
        # emitted as an invisible anchor inside the same block.
        assert "[#heading(" in content, "Labelled heading should open a markup block"
        assert ") <introduction>" in content, "Primary section id should be attached"
        assert (
            "#metadata(none) <intro-section>" in content
        ), "Explicit section target should produce an attachable anchor"

    def test_standalone_target_emits_attached_anchor(self, built_typ_file):
        """A standalone `.. _name:` target must produce an invisible anchor."""
        content = built_typ_file.read_text()

        assert "[#metadata(none) <standalone-target>]" in content

    def test_trailing_target_emits_attached_anchor(self, built_typ_file):
        """A target that keeps its ids must not emit a bare label() call."""
        content = built_typ_file.read_text()

        assert "[#metadata(none) <trailing-target>]" in content
        # A bare label() statement attaches to nothing in code mode
        assert 'label("' not in content

    def test_figure_label_wrapped_in_markup_block(self, built_typ_file):
        """`figure(...) <label>` is a syntax error in code mode."""
        content = built_typ_file.read_text()

        assert "[#figure(" in content, "Labelled figure should open a markup block"
        assert ") <my-figure>]" in content, "Figure label should close the block"

    def test_code_block_label_attached(self, built_typ_file):
        """A `:name:`-only code block label must attach to the raw block."""
        content = built_typ_file.read_text()

        assert "<my-code>]" in content, "Code block label should close a markup block"

    def test_captioned_code_block_label_attached(self, built_typ_file):
        """A captioned code block label must attach to the wrapping figure."""
        content = built_typ_file.read_text()

        assert "[#figure(caption: [Captioned code])[" in content
        assert "<my-captioned-code>]" in content

    def test_equation_label_attached(self, built_typ_file):
        """An equation label must be wrapped in a markup block."""
        content = built_typ_file.read_text()

        assert "<equation-my-equation>]" in content

    def test_generated_typst_compiles(self, built_typ_file, tmp_path):
        """The generated Typst document must compile to PDF."""
        pdf_output = tmp_path / "index.pdf"

        typst.compile(str(built_typ_file), output=str(pdf_output))

        assert pdf_output.exists(), "PDF file was not created"
        assert pdf_output.stat().st_size > 0, "PDF file is empty"

        with open(pdf_output, "rb") as f:
            assert f.read(4) == b"%PDF", "Generated file is not a valid PDF"
