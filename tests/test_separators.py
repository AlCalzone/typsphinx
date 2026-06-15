"""
Tests for statement separators between adjacent expressions.

In unified code mode, adjacent expressions must be separated by a
statement separator (newline or semicolon). visit_Text follows this
protocol, but some visitors (math, math_block, block_quote, image, raw)
did not, producing invalid Typst such as ``mi(`T_n`)text(" - ")``.
"""

from pathlib import Path

import typst
from sphinx.testing.util import SphinxTestApp

ICON_PNG = (Path(__file__).parent / "fixtures" / "separators" / "icon.png").read_bytes()


def build_index_typ(tmp_path: Path, index_rst: str, files: dict = None) -> Path:
    """Build a minimal Sphinx project with the typst builder.

    Returns the path to the generated index.typ.
    """
    srcdir = tmp_path / "source"
    srcdir.mkdir()
    (srcdir / "conf.py").write_text(
        "extensions = ['typsphinx']\n" "project = 'Test'\n" "author = 'Test'\n"
    )
    (srcdir / "index.rst").write_text(index_rst)
    for name, content in (files or {}).items():
        mode = "wb" if isinstance(content, bytes) else "w"
        with open(srcdir / name, mode) as f:
            f.write(content)

    builddir = tmp_path / "build"
    app = SphinxTestApp(srcdir=srcdir, builddir=builddir, buildername="typst")
    app.build()

    return builddir / "typst" / "index.typ"


def assert_compiles(typ_file: Path) -> None:
    """Assert that the generated Typst file compiles to a PDF."""
    pdf_output = typ_file.parent / (typ_file.stem + ".pdf")
    typst.compile(str(typ_file), output=str(pdf_output))
    assert pdf_output.exists(), "PDF file was not created"


class TestInlineMathSeparators:
    """Inline math must be separated from adjacent expressions."""

    def test_math_first_in_list_item(self, tmp_path):
        """Math at the start of a list item needs a separator after it."""
        typ_file = build_index_typ(
            tmp_path,
            "Test\n" "====\n" "\n" "- :math:`T_n` - description\n",
        )
        output = typ_file.read_text()

        assert "mi(`T_n`)text(" not in output, (
            "Missing separator between inline math and following text:\n" + output
        )
        assert "mi(`T_n`)\ntext(" in output
        assert_compiles(typ_file)

    def test_math_after_text_in_list_item(self, tmp_path):
        """Math after text in a list item needs a separator before it."""
        typ_file = build_index_typ(
            tmp_path,
            "Test\n" "====\n" "\n" "- Term :math:`T_n` rest\n",
        )
        output = typ_file.read_text()

        assert 'text("Term ")mi(' not in output, (
            "Missing separator between text and inline math:\n" + output
        )
        assert 'text("Term ")\nmi(' in output
        assert_compiles(typ_file)


class TestMathBlockSeparators:
    """Block math in a list item must be separated from preceding text."""

    def test_math_block_after_text_in_list_item(self, tmp_path):
        typ_file = build_index_typ(
            tmp_path,
            "Test\n"
            "====\n"
            "\n"
            "- Item text\n"
            "\n"
            "  .. math::\n"
            "\n"
            "     x = 1\n",
        )
        output = typ_file.read_text()

        assert 'text("Item text")mitex(' not in output, (
            "Missing separator between text and block math:\n" + output
        )
        assert 'text("Item text")\nmitex(' in output
        assert_compiles(typ_file)


class TestRawSeparators:
    """Raw typst nodes must be separated from preceding inline content."""

    def test_raw_after_text_in_paragraph(self, tmp_path):
        typ_file = build_index_typ(
            tmp_path,
            "Test\n"
            "====\n"
            "\n"
            ".. role:: rawtypst(raw)\n"
            "   :format: typst\n"
            "\n"
            "The value is: :rawtypst:`emph[raw]`\n",
        )
        output = typ_file.read_text()

        assert 'text("The value is: ")emph[raw]' not in output, (
            "Missing separator between text and raw typst output:\n" + output
        )
        assert 'text("The value is: ")\nemph[raw]' in output
        assert_compiles(typ_file)

    def test_raw_after_text_in_list_item(self, tmp_path):
        typ_file = build_index_typ(
            tmp_path,
            "Test\n"
            "====\n"
            "\n"
            ".. role:: rawtypst(raw)\n"
            "   :format: typst\n"
            "\n"
            "- Value: :rawtypst:`emph[raw]`\n",
        )
        output = typ_file.read_text()

        assert 'text("Value: ")emph[raw]' not in output, (
            "Missing separator between text and raw typst output:\n" + output
        )
        assert 'text("Value: ")\nemph[raw]' in output
        assert_compiles(typ_file)


class TestBlockQuoteSeparators:
    """Block quotes in list items must be separated from preceding text."""

    def test_block_quote_after_text_in_list_item(self, tmp_path):
        typ_file = build_index_typ(
            tmp_path,
            "Test\n" "====\n" "\n" "- Item text\n" "\n" "      Quoted text\n",
        )
        output = typ_file.read_text()

        assert 'text("Item text")quote' not in output, (
            "Missing separator between text and block quote:\n" + output
        )
        assert 'text("Item text")\nquote' in output
        assert_compiles(typ_file)


class TestImageSeparators:
    """Inline images must be separated from adjacent expressions."""

    def test_inline_image_in_paragraph(self, tmp_path):
        typ_file = build_index_typ(
            tmp_path,
            "Test\n"
            "====\n"
            "\n"
            "Here is an image |icon| inline.\n"
            "\n"
            ".. |icon| image:: icon.png\n",
            files={"icon.png": ICON_PNG},
        )
        output = typ_file.read_text()

        assert 'text("Here is an image ")image(' not in output, (
            "Missing separator between text and inline image:\n" + output
        )
        assert 'text("Here is an image ")\nimage(' in output
        assert_compiles(typ_file)

    def test_image_after_text_in_list_item(self, tmp_path):
        typ_file = build_index_typ(
            tmp_path,
            "Test\n"
            "====\n"
            "\n"
            "- Icon: |icon|\n"
            "\n"
            ".. |icon| image:: icon.png\n",
            files={"icon.png": ICON_PNG},
        )
        output = typ_file.read_text()

        assert 'text("Icon: ")image(' not in output, (
            "Missing separator between text and inline image:\n" + output
        )
        assert 'text("Icon: ")\nimage(' in output
        assert_compiles(typ_file)
