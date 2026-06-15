"""
Tests for admonition node conversion to Typst gentle-clues.

Task 3.4: アドモニション（Admonition）の変換
"""

from pathlib import Path

import pytest
from docutils import nodes
from docutils.parsers.rst import states
from docutils.utils import Reporter
from sphinx import addnodes
from sphinx.testing.util import SphinxTestApp

from typsphinx.translator import TypstTranslator
from typsphinx.writer import TypstWriter


def create_document():
    """Helper function to create a minimal document with reporter."""
    reporter = Reporter("", 2, 4)
    doc = nodes.document("", reporter=reporter)
    doc.settings = states.Struct()
    doc.settings.env = None
    doc.settings.language_code = "en"
    doc.settings.strict_visitor = False
    return doc


class TestAdmonitionConversion:
    """Test admonition node conversion using gentle-clues package."""

    def test_note_converts_to_info(self, temp_sphinx_app: SphinxTestApp):
        """Test that nodes.note converts to info({})."""
        # Create a note admonition
        note = nodes.note()
        para = nodes.paragraph(text="This is a note.")
        note += para

        # Create document
        doc = create_document()
        doc += note

        # Translate
        writer = TypstWriter(temp_sphinx_app.builder)
        writer.document = doc
        translator = TypstTranslator(doc, temp_sphinx_app.builder)
        doc.walkabout(translator)

        output = translator.astext()
        assert "info({" in output
        assert "This is a note." in output
        assert "})" in output

    def test_warning_converts_to_warning(self, temp_sphinx_app: SphinxTestApp):
        """Test that nodes.warning converts to warning({})."""
        warning = nodes.warning()
        para = nodes.paragraph(text="This is a warning.")
        warning += para

        doc = create_document()
        doc += warning

        writer = TypstWriter(temp_sphinx_app.builder)
        writer.document = doc
        translator = TypstTranslator(doc, temp_sphinx_app.builder)
        doc.walkabout(translator)

        output = translator.astext()
        assert "warning({" in output
        assert "This is a warning." in output

    def test_tip_converts_to_tip(self, temp_sphinx_app: SphinxTestApp):
        """Test that nodes.tip converts to tip({})."""
        tip = nodes.tip()
        para = nodes.paragraph(text="Here's a tip.")
        tip += para

        doc = create_document()
        doc += tip

        writer = TypstWriter(temp_sphinx_app.builder)
        writer.document = doc
        translator = TypstTranslator(doc, temp_sphinx_app.builder)
        doc.walkabout(translator)

        output = translator.astext()
        assert "tip({" in output
        assert "Here's a tip." in output

    def test_important_converts_to_warning_with_title(
        self, temp_sphinx_app: SphinxTestApp
    ):
        """Test that nodes.important converts to warning(title: "Important", {})."""
        important = nodes.important()
        para = nodes.paragraph(text="This is important.")
        important += para

        doc = create_document()
        doc += important

        writer = TypstWriter(temp_sphinx_app.builder)
        writer.document = doc
        translator = TypstTranslator(doc, temp_sphinx_app.builder)
        doc.walkabout(translator)

        output = translator.astext()
        assert 'warning(title: "Important", {' in output
        assert "This is important." in output

    def test_caution_converts_to_warning(self, temp_sphinx_app: SphinxTestApp):
        """Test that nodes.caution converts to warning({})."""
        caution = nodes.caution()
        para = nodes.paragraph(text="Be cautious.")
        caution += para

        doc = create_document()
        doc += caution

        writer = TypstWriter(temp_sphinx_app.builder)
        writer.document = doc
        translator = TypstTranslator(doc, temp_sphinx_app.builder)
        doc.walkabout(translator)

        output = translator.astext()
        assert "warning({" in output
        assert "Be cautious." in output

    def test_seealso_converts_to_info_with_title(self, temp_sphinx_app: SphinxTestApp):
        """Test that addnodes.seealso converts to info(title: "See Also", {})."""
        seealso = addnodes.seealso()
        para = nodes.paragraph(text="See related documentation.")
        seealso += para

        doc = create_document()
        doc += seealso

        writer = TypstWriter(temp_sphinx_app.builder)
        writer.document = doc
        translator = TypstTranslator(doc, temp_sphinx_app.builder)
        doc.walkabout(translator)

        output = translator.astext()
        assert 'info(title: "See Also", {' in output
        assert "See related documentation." in output

    def test_admonition_with_multiple_paragraphs(self, temp_sphinx_app: SphinxTestApp):
        """Test admonition with multiple paragraphs."""
        note = nodes.note()
        para1 = nodes.paragraph(text="First paragraph.")
        para2 = nodes.paragraph(text="Second paragraph.")
        note += para1
        note += para2

        doc = create_document()
        doc += note

        writer = TypstWriter(temp_sphinx_app.builder)
        writer.document = doc
        translator = TypstTranslator(doc, temp_sphinx_app.builder)
        doc.walkabout(translator)

        output = translator.astext()
        assert "info({" in output
        assert "First paragraph." in output
        assert "Second paragraph." in output

    def test_nested_admonitions(self, temp_sphinx_app: SphinxTestApp):
        """Test nested admonitions."""
        outer_note = nodes.note()
        para1 = nodes.paragraph(text="Outer note.")
        inner_warning = nodes.warning()
        para2 = nodes.paragraph(text="Inner warning.")
        inner_warning += para2
        outer_note += para1
        outer_note += inner_warning

        doc = create_document()
        doc += outer_note

        writer = TypstWriter(temp_sphinx_app.builder)
        writer.document = doc
        translator = TypstTranslator(doc, temp_sphinx_app.builder)
        doc.walkabout(translator)

        output = translator.astext()
        assert "info({" in output
        assert "Outer note." in output
        assert "warning({" in output
        assert "Inner warning." in output

    def test_admonition_with_title_in_content(self, temp_sphinx_app: SphinxTestApp):
        """Test admonition with custom title in first paragraph."""
        # In Sphinx, custom admonitions have the title as the first child
        note = nodes.note()
        title = nodes.title(text="Custom Title")
        para = nodes.paragraph(text="Content here.")
        note += title
        note += para

        doc = create_document()
        doc += note

        writer = TypstWriter(temp_sphinx_app.builder)
        writer.document = doc
        translator = TypstTranslator(doc, temp_sphinx_app.builder)
        doc.walkabout(translator)

        output = translator.astext()
        # Should use custom title
        assert "info(title:" in output
        assert "Custom Title" in output
        assert "Content here." in output


class TestBodyCodeMode:
    """Admonition and block quote bodies must be code blocks, not markup.

    Children (paragraphs, text) are emitted in code-mode form such as
    par({text("...")}).  If the surrounding body is a markup block
    ([...]), Typst renders those expressions as literal source text in
    the PDF (or fails to compile when brackets unbalance).  The bodies
    must therefore be {} code blocks.
    """

    INDEX_RST = """\
Test Document
=============

.. note::

   This is a note.

.. warning::

   This is a warning.

Some text.

    This is a block quote.

.. epigraph::

   Quote with attribution.

   -- Someone
"""

    @pytest.fixture
    def built_typ(self, tmp_path) -> str:
        """Build a project with admonitions and return index.typ content."""
        srcdir = tmp_path / "source"
        srcdir.mkdir()
        (srcdir / "conf.py").write_text(
            "extensions = ['typsphinx']\n"
            "project = 'Test Project'\n"
            "author = 'Test Author'\n"
            "typst_documents = [('index', 'index.typ', 'Test', 'Author')]\n"
        )
        (srcdir / "index.rst").write_text(self.INDEX_RST)

        app = SphinxTestApp(
            buildername="typst",
            srcdir=srcdir,
            builddir=tmp_path / "build",
        )
        app.build()

        return (Path(app.outdir) / "index.typ").read_text()

    def test_note_body_is_code_block(self, built_typ):
        """Note bodies must be {} code blocks, not [] markup blocks."""
        assert "info({" in built_typ
        assert "info[" not in built_typ
        assert 'text("This is a note.")' in built_typ

    def test_warning_body_is_code_block(self, built_typ):
        """Warning bodies must be {} code blocks, not [] markup blocks."""
        assert "warning({" in built_typ
        assert "warning[" not in built_typ
        assert 'text("This is a warning.")' in built_typ

    def test_block_quote_body_is_code_block(self, built_typ):
        """Block quote bodies must be {} code blocks, not [] markup blocks."""
        assert "quote(block: true, {" in built_typ
        assert "quote[" not in built_typ
        assert 'text("This is a block quote.")' in built_typ

    def test_attribution_is_code_block_argument(self, built_typ):
        """Attributions must be passed as a code-block named argument."""
        assert "}, attribution: {" in built_typ
        # The old form closed a markup block that was never opened
        assert "], attribution: [" not in built_typ
        assert 'text("Someone")' in built_typ

    def test_no_code_mode_text_inside_markup_blocks(self, built_typ):
        """No [par({ ... sequences: code mode leaking into markup mode."""
        assert "[par({" not in built_typ

    def test_generated_typ_compiles(self, built_typ, tmp_path):
        """The generated document must be valid Typst and compile to PDF."""
        import typst

        # Compile a standalone document with the same admonition/quote
        # constructs (the project template lives in a separate file, so
        # rebuild the preamble minimally).
        body = built_typ[built_typ.index("#{") :]
        source = '#import "@preview/gentle-clues:1.2.0": *\n' "\n" + body
        typ_file = tmp_path / "standalone.typ"
        typ_file.write_text(source)
        pdf_file = tmp_path / "standalone.pdf"
        typst.compile(str(typ_file), output=str(pdf_file))
        assert pdf_file.exists()
