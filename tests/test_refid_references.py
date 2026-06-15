"""
Tests for same-document references (``refid`` attribute).

Sphinx resolves same-document ``:ref:``/``:numref:`` targets into reference
nodes that carry a ``refid`` attribute (instead of ``refuri``). The translator
must emit a Typst ``link()`` to a matching in-document label so these
references survive the conversion instead of degrading to plain text.
"""

import pytest


@pytest.fixture
def build_typst(make_app, tmp_path):
    """Build a single-document project and return (index.typ content, warnings)."""

    def _build(index_rst: str) -> tuple:
        srcdir = tmp_path / "source"
        srcdir.mkdir()
        (srcdir / "conf.py").write_text(
            "extensions = ['typsphinx']\nproject = 'Test'\n"
        )
        (srcdir / "index.rst").write_text(index_rst)

        app = make_app("typst", srcdir=srcdir)
        app.build()

        output = (app.outdir / "index.typ").read_text()
        warnings = app.warning.getvalue()
        return output, warnings

    return _build


class TestSameDocumentReferences:
    """Same-document :ref: targets must produce resolvable Typst links."""

    def test_ref_to_section_target_generates_link(self, build_typst):
        """A :ref: to a section target must emit link() to the section label."""
        output, warnings = build_typst(
            "Test Document\n"
            "=============\n"
            "\n"
            ".. _mytarget:\n"
            "\n"
            "Target Section\n"
            "--------------\n"
            "\n"
            "Some content.\n"
            "\n"
            "Another Section\n"
            "---------------\n"
            "\n"
            "See :ref:`mytarget` for details.\n"
        )

        # The reference must be emitted as a link to an in-document label
        assert "link(<target-section>, " in output
        # The section heading carries its id as a label (attached in a markup
        # block, since labels can only be attached in markup mode); the
        # explicit `.. _mytarget:` id is emitted as an additional anchor.
        assert (
            '[#heading(depth: 2, text("Target Section")) '
            "<target-section>#metadata(none) <mytarget>]" in output
        )
        # No "empty URL" warning may be emitted for a resolvable reference
        assert "Reference node has empty URL" not in warnings

    def test_ref_with_explicit_title_to_paragraph_target(self, build_typst):
        """A :ref:`text <target>` to a paragraph target must emit link()."""
        output, warnings = build_typst(
            "Test Document\n"
            "=============\n"
            "\n"
            ".. _para-target:\n"
            "\n"
            "Some paragraph content.\n"
            "\n"
            "See :ref:`here <para-target>` for details.\n"
        )

        # The reference must link to the paragraph's label
        assert "link(<para-target>, " in output
        # The paragraph must carry the matching label
        assert '[#par({text("Some paragraph content.")}) <para-target>]' in output
        assert "Reference node has empty URL" not in warnings

    def test_ref_to_table_target_generates_link(self, build_typst):
        """A :ref: to a table target must emit link() to the table label."""
        output, warnings = build_typst(
            "Test Document\n"
            "=============\n"
            "\n"
            ".. _mytable:\n"
            "\n"
            ".. list-table::\n"
            "\n"
            "   * - A\n"
            "     - B\n"
            "\n"
            "See :ref:`the table <mytable>` for details.\n"
        )

        # The reference must link to the table's label
        assert "link(<mytable>, " in output
        # The table must carry the matching label
        assert "[#table(" in output
        assert ") <mytable>]" in output
        assert "Reference node has empty URL" not in warnings

    def test_all_sections_carry_a_label(self, build_typst):
        """Every section carries its id as a label so any :ref: can resolve.

        (Originally this asserted unreferenced sections stay label-free; once
        label attachment landed, all sections are labelled unconditionally,
        which is what makes same-document references resolvable by construction.)
        """
        output, _ = build_typst(
            "Test Document\n"
            "=============\n"
            "\n"
            "Plain Section\n"
            "-------------\n"
            "\n"
            "Some content.\n"
        )

        assert '[#heading(depth: 2, text("Plain Section")) <plain-section>]' in output
