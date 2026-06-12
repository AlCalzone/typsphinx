"""
Tests for inline and substitution images.

Covers three related problems:

- ``.. |logo| image:: x.png`` (substitution definitions) produced an
  "unknown node type" warning and emitted a stray image at the
  definition site.
- Inline images inside paragraphs were emitted as bare ``image(...)``
  calls, which Typst drops at layout time ("block may not occur inside
  of a paragraph"); they must be wrapped in ``box(...)``.
- ``px`` and unitless lengths (docutils treats unitless as px) are not
  valid Typst lengths and caused compile errors; they must be converted
  to ``pt`` (1px = 0.75pt).
"""

import re
import subprocess
from pathlib import Path

import pytest
from docutils import nodes
from docutils.parsers.rst import states
from docutils.utils import Reporter


@pytest.fixture
def simple_document():
    """Create a simple document for testing."""
    reporter = Reporter("", 2, 4)
    doc = nodes.document("", reporter=reporter)
    doc.settings = states.Struct()
    doc.settings.env = None
    doc.settings.language_code = "en"
    doc.settings.strict_visitor = False
    return doc


@pytest.fixture(scope="module")
def built_project(tmp_path_factory):
    """Build the integration_inline_images project once for all tests."""
    project_dir = Path(__file__).parent / "fixtures" / "integration_inline_images"
    build_dir = tmp_path_factory.mktemp("inline_images_build")
    result = subprocess.run(
        [
            "uv",
            "run",
            "sphinx-build",
            "-b",
            "typst",
            str(project_dir),
            str(build_dir),
        ],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, (
        f"sphinx-build failed:\nSTDOUT:\n{result.stdout}\n" f"STDERR:\n{result.stderr}"
    )
    return result, (build_dir / "index.typ").read_text()


class TestSubstitutionImages:
    """Substitution definitions must be skipped, their uses inlined."""

    def test_no_unknown_node_warning(self, built_project):
        """Substitution definitions must not trigger unknown-node warnings."""
        result, _ = built_project
        combined = result.stdout + result.stderr
        assert "unknown node type" not in combined
        assert "substitution_definition" not in combined

    def test_definition_site_emits_no_image(self, built_project):
        """The definition site must not leak a stray standalone image."""
        _, content = built_project
        # One inline use in the paragraph + one standalone image directive.
        assert content.count('image("logo.png"') == 2

    def test_substitution_image_is_inline_in_paragraph(self, built_project):
        """The substituted image must appear box()-wrapped inside par()."""
        _, content = built_project
        paragraph = re.search(r"par\(\{.*?Inline image.*?\}\)", content, re.DOTALL)
        assert paragraph is not None, "paragraph with inline image not found"
        assert 'box(image("logo.png"' in paragraph.group(0)


class TestImageLengthUnits:
    """px and unitless lengths must be converted to pt for Typst."""

    def test_px_width_converted_to_pt(self, built_project):
        """:width: 15px must become 11.25pt (1px = 0.75pt)."""
        _, content = built_project
        assert "width: 11.25pt" in content
        assert "px" not in content

    def test_unitless_width_converted_to_pt(self, built_project):
        """:width: 20 (docutils default unit is px) must become 15pt."""
        _, content = built_project
        assert "width: 15pt" in content


class TestImageUnitConversionUnit:
    """Translator-level unit tests for length conversion and box wrapping."""

    def test_px_units_converted(self, simple_document, mock_builder):
        from typsphinx.translator import TypstTranslator

        translator = TypstTranslator(simple_document, mock_builder)
        image = nodes.image(uri="diagram.png")
        image["width"] = "15px"
        image["height"] = "10px"
        translator.visit_image(image)
        translator.depart_image(image)

        output = translator.astext()
        assert "width: 11.25pt" in output
        assert "height: 7.5pt" in output

    def test_real_units_preserved(self, simple_document, mock_builder):
        from typsphinx.translator import TypstTranslator

        translator = TypstTranslator(simple_document, mock_builder)
        image = nodes.image(uri="diagram.png")
        image["width"] = "5cm"
        image["height"] = "50%"
        translator.visit_image(image)
        translator.depart_image(image)

        output = translator.astext()
        assert "width: 5cm" in output
        assert "height: 50%" in output

    def test_non_figure_image_wrapped_in_box(self, simple_document, mock_builder):
        from typsphinx.translator import TypstTranslator

        translator = TypstTranslator(simple_document, mock_builder)
        image = nodes.image(uri="diagram.png")
        translator.visit_image(image)
        translator.depart_image(image)

        output = translator.astext()
        assert 'box(image("diagram.png"))' in output

    def test_figure_image_not_wrapped_in_box(self, simple_document, mock_builder):
        from typsphinx.translator import TypstTranslator

        translator = TypstTranslator(simple_document, mock_builder)
        figure = nodes.figure()
        figure += nodes.image(uri="diagram.png")
        figure.walkabout(translator)

        output = translator.astext()
        assert "box(" not in output
