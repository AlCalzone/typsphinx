"""
Tests for overriding the translator via app.set_translator().

Sphinx provides app.set_translator(builder_name, translator_class) as the
official extension point for customizing output. The Typst builders must
honor it instead of always instantiating TypstTranslator directly.
"""

from docutils import nodes

from typsphinx.translator import TypstTranslator

MARKER = "/* custom-translator-marker */"


class MarkerTranslator(TypstTranslator):
    """TypstTranslator subclass that emits a marker before each paragraph."""

    def visit_paragraph(self, node: nodes.paragraph) -> None:
        self.body.append(MARKER)
        super().visit_paragraph(node)


def _make_project(tmp_path):
    srcdir = tmp_path / "source"
    srcdir.mkdir()

    conf_content = """
extensions = ['typsphinx']

project = 'Test Project'

typst_documents = [('index', 'index', 'Test', 'Author')]
"""
    (srcdir / "conf.py").write_text(conf_content)
    (srcdir / "index.rst").write_text("""
Test Document
=============

Some paragraph content.
""")
    return srcdir


def test_set_translator_overrides_typst_translator(make_app, tmp_path):
    """A translator registered via app.set_translator('typst', ...) is used."""
    srcdir = _make_project(tmp_path)

    app = make_app(srcdir=srcdir, buildername="typst")
    app.set_translator("typst", MarkerTranslator, override=True)
    app.build()

    content = (app.outdir / "index.typ").read_text()
    assert MARKER in content


def test_default_translator_used_without_override(make_app, tmp_path):
    """Without set_translator, the default TypstTranslator is used."""
    srcdir = _make_project(tmp_path)

    app = make_app(srcdir=srcdir, buildername="typst")
    app.build()

    content = (app.outdir / "index.typ").read_text()
    assert MARKER not in content
    assert "Some paragraph content." in content
