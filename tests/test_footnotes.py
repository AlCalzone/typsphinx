"""
Tests for footnote support.

Footnotes (auto-numbered ``[#]_`` and manually numbered ``[1]_``) must be
translated to native Typst ``footnote()`` calls at the reference site,
without "unknown node type" warnings.
"""

from pathlib import Path

import pytest
from sphinx.testing.util import SphinxTestApp


@pytest.fixture
def footnote_app(tmp_path: Path) -> SphinxTestApp:
    """Create a Sphinx app for a project containing footnotes."""
    srcdir = tmp_path / "source"
    srcdir.mkdir()

    (srcdir / "conf.py").write_text(
        "project = 'Test'\n"
        "extensions = ['typsphinx']\n"
        "typst_documents = [('index', 'index', 'Test', 'Author')]\n"
    )

    (srcdir / "index.rst").write_text(
        "Test Document\n"
        "=============\n"
        "\n"
        "Auto reference [#]_ in text.\n"
        "\n"
        "Numbered reference [1]_ in text.\n"
        "\n"
        ".. [#] Auto-numbered footnote content.\n"
        "\n"
        ".. [1] Manually numbered footnote content.\n"
    )

    return SphinxTestApp(
        buildername="typst", srcdir=srcdir, builddir=tmp_path / "build"
    )


def _build_and_read(app: SphinxTestApp) -> str:
    app.build()
    output_file = Path(app.outdir) / "index.typ"
    assert output_file.exists(), "index.typ was not generated"
    return output_file.read_text()


def test_footnotes_no_unknown_node_warnings(footnote_app):
    """Footnote nodes must not trigger 'unknown node type' warnings."""
    _build_and_read(footnote_app)
    warnings = footnote_app._warning.getvalue()
    assert (
        "unknown node type" not in warnings
    ), f"Unexpected unknown-node warnings:\n{warnings}"


def test_footnotes_rendered_as_typst_footnote(footnote_app):
    """Footnote content must appear inside footnote() at the reference site."""
    output = _build_and_read(footnote_app)

    # Both footnotes are emitted as native Typst footnote() calls
    assert output.count("footnote(") == 2, output

    # Footnote content is present (it was previously lost)
    assert "Auto-numbered footnote content." in output
    assert "Manually numbered footnote content." in output

    # Content is emitted at the reference site, i.e. inside the paragraph
    # that contains the reference.
    auto_ref_pos = output.index("Auto reference")
    auto_content_pos = output.index("Auto-numbered footnote content.")
    numbered_ref_pos = output.index("Numbered reference")
    assert auto_ref_pos < auto_content_pos < numbered_ref_pos

    # The footnote label ("1") must not leak into the body as plain text
    assert 'text("1")' not in output


def test_footnotes_output_compiles(footnote_app, tmp_path):
    """The generated .typ document must compile with the typst package."""
    typst = pytest.importorskip("typst")

    _build_and_read(footnote_app)
    output_file = Path(footnote_app.outdir) / "index.typ"
    pdf_file = tmp_path / "index.pdf"
    typst.compile(str(output_file), output=str(pdf_file))
    assert pdf_file.exists()
    assert pdf_file.stat().st_size > 0
