"""
Tests for the ``.. meta::`` directive.

Meta nodes carry HTML head metadata (e.g. description, keywords) which has
no representation in a PDF, so the Typst builder must skip them silently
instead of emitting "unknown node type" warnings.
"""

from io import StringIO

from sphinx.testing.util import SphinxTestApp


def test_meta_directive_is_skipped_without_warning(tmp_path):
    """Building a document with ``.. meta::`` emits no warning and no output."""
    srcdir = tmp_path / "source"
    srcdir.mkdir()
    (srcdir / "conf.py").write_text(
        "extensions = ['typsphinx']\n"
        "project = 'Test Project'\n"
        "author = 'Test Author'\n"
    )
    (srcdir / "index.rst").write_text(
        "Test Document\n"
        "=============\n"
        "\n"
        ".. meta::\n"
        "   :description: METADESCRIPTION\n"
        "   :keywords: METAKEYWORDS\n"
        "\n"
        "Body text.\n"
    )

    warnings = StringIO()
    app = SphinxTestApp(
        "typst",
        srcdir=srcdir,
        builddir=tmp_path / "build",
        warning=warnings,
    )
    try:
        app.build()
        output = (app.outdir / "index.typ").read_text()
    finally:
        app.cleanup()

    assert "unknown node type" not in warnings.getvalue()
    assert "METADESCRIPTION" not in output
    assert "METAKEYWORDS" not in output
    assert "Body text." in output
