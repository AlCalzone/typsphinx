"""
Tests for table column specifications.

Covers:
- ``.. tabularcolumns::`` directives (LaTeX-style colspecs) mapping to
  Typst ``columns:`` / ``align:`` arguments
- ``.. list-table:: :widths:`` (``colwidths-given``) mapping to
  proportional Typst column widths
"""

import subprocess
from pathlib import Path

import pytest
from docutils.frontend import get_default_settings
from docutils.parsers.rst import Parser as RstParser
from docutils.utils import new_document

GRID_TABLE = """
+----------+----------+----------+
| Header1  | Header2  | Header3  |
+==========+==========+==========+
| CellA    | CellB    | CellC    |
+----------+----------+----------+
"""


def _translate(rst_content, mock_builder):
    """Parse RST with docutils and translate it to Typst."""
    from typsphinx.translator import TypstTranslator

    settings = get_default_settings(RstParser)
    document = new_document("<test>", settings=settings)
    RstParser().parse(rst_content, document)

    translator = TypstTranslator(document, mock_builder)
    document.walkabout(translator)
    return translator.astext()


def _translate_with_colspec(spec, rst_content, mock_builder):
    """Translate a table preceded by a tabular_col_spec node.

    ``.. tabularcolumns::`` is a Sphinx directive (not available in plain
    docutils parsing), so insert the node it produces manually.
    """
    from sphinx import addnodes

    from typsphinx.translator import TypstTranslator

    settings = get_default_settings(RstParser)
    document = new_document("<test>", settings=settings)
    RstParser().parse(rst_content, document)

    colspec_node = addnodes.tabular_col_spec()
    colspec_node["spec"] = spec
    table_index = document.index(document.next_node(lambda n: n.tagname == "table"))
    document.insert(table_index, colspec_node)

    translator = TypstTranslator(document, mock_builder)
    document.walkabout(translator)
    return translator.astext()


def test_tabularcolumns_alignment(mock_builder):
    """|l|c|r| sets per-column alignment."""
    output = _translate_with_colspec("|l|c|r|", GRID_TABLE, mock_builder)
    assert "columns: (auto, auto, auto)" in output
    assert "align: (left, center, right)" in output


def test_tabularcolumns_uniform_letters_equal_widths(mock_builder):
    """A uniform spec like |C|C|C| produces equal-width columns."""
    output = _translate_with_colspec("|C|C|C|", GRID_TABLE, mock_builder)
    assert "columns: (1fr, 1fr, 1fr)" in output
    assert "align: center" in output


def test_tabularcolumns_fraction_widths(mock_builder):
    r"""Sphinx \X{a}{b} and \Y{f} fractions map to fr units."""
    output = _translate_with_colspec(
        r"\X{1}{4}\X{1}{4}\Y{0.5}", GRID_TABLE, mock_builder
    )
    assert "columns: (0.25fr, 0.25fr, 0.5fr)" in output


def test_tabularcolumns_p_lengths(mock_builder):
    """p{<len>} columns map to fixed Typst lengths."""
    output = _translate_with_colspec(
        "|p{3cm}|p{20mm}|p{1in}|", GRID_TABLE, mock_builder
    )
    assert "columns: (3cm, 20mm, 1in)" in output


def test_tabularcolumns_unparseable_falls_back(mock_builder):
    """An unsupported spec falls back to equal columns instead of crashing."""
    output = _translate_with_colspec(
        ">{\\raggedright}p{3cm}ll", GRID_TABLE, mock_builder
    )
    assert "columns: 3" in output


def test_list_table_widths(mock_builder):
    """list-table :widths: values become proportional column widths."""
    rst = """
.. list-table::
   :widths: 1 2 3
   :header-rows: 1

   * - Header1
     - Header2
     - Header3
   * - CellA
     - CellB
     - CellC
"""
    output = _translate(rst, mock_builder)
    assert "columns: (1fr, 2fr, 3fr)" in output


def test_list_table_without_widths_keeps_equal_columns(mock_builder):
    """Without :widths:, tables keep the plain integer column count."""
    rst = """
.. list-table::
   :header-rows: 1

   * - Header1
     - Header2
   * - CellA
     - CellB
"""
    output = _translate(rst, mock_builder)
    assert "columns: 2" in output


def test_colspec_applies_only_to_next_table(mock_builder):
    """A tabularcolumns spec must not leak into subsequent tables."""
    output = _translate_with_colspec(
        "|l|c|r|", GRID_TABLE + "\n\nSome text.\n" + GRID_TABLE, mock_builder
    )
    assert output.count("align: (left, center, right)") == 1
    assert "columns: 3" in output


class TestTabularColumnsIntegration:
    """Full sphinx-build of a project using .. tabularcolumns::."""

    @pytest.fixture
    def project_dir(self, tmp_path):
        srcdir = tmp_path / "source"
        srcdir.mkdir()
        (srcdir / "conf.py").write_text(
            "extensions = ['typsphinx']\n"
            "project = 'Test'\n"
            "typst_documents = [('index', 'index', 'Test', 'Author')]\n"
        )
        (srcdir / "index.rst").write_text(
            "Test\n" "====\n" "\n" ".. tabularcolumns:: |l|c|r|\n" + GRID_TABLE
        )
        return srcdir

    def test_build_emits_colspec_without_warning(self, project_dir, tmp_path):
        build_dir = tmp_path / "_build"
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
            cwd=Path(__file__).parent.parent,
        )
        assert result.returncode == 0, result.stderr
        assert "unknown node type" not in result.stderr

        output = (build_dir / "index.typ").read_text()
        assert "columns: (auto, auto, auto)" in output
        assert "align: (left, center, right)" in output
