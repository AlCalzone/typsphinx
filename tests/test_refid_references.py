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

        # The reference must be emitted as a link to an in-document label.
        # Labels are docname-qualified (docname "index" for this one-file
        # project) so they stay unique in the combined root document. The
        # ``:ref:`` resolves to the explicit ``mytarget`` id, which the section
        # emits as an additional anchor, so the link points at <index:mytarget>.
        assert "link(<index:mytarget>, " in output
        # The section heading carries its primary id as a label (attached in a
        # markup block, since labels can only be attached in markup mode); the
        # explicit `.. _mytarget:` id is emitted as an additional anchor that
        # the reference above links to.
        assert (
            '[#heading(depth: 2, text("Target Section")) '
            "<index:target-section>#metadata(none) <index:mytarget>]" in output
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

        # The reference must link to the paragraph's label (docname-qualified)
        assert "link(<index:para-target>, " in output
        # The paragraph's propagated id is anchored just before it via an
        # invisible metadata element (the par() itself is not label-wrapped,
        # so the id is never emitted twice).
        assert "[#metadata(none) <index:para-target>]" in output
        assert '[#par({text("Some paragraph content.")})' not in output
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

        # The reference must link to the table's label (docname-qualified)
        assert "link(<index:mytable>, " in output
        # The table must carry the matching label
        assert "[#table(" in output
        assert ") <index:mytable>]" in output
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

        assert (
            '[#heading(depth: 2, text("Plain Section")) <index:plain-section>]'
            in output
        )

    def test_no_duplicate_labels_across_target_types(self, build_typst):
        """No label definition may be emitted more than once.

        Typst hard-errors on duplicate labels. A target whose id is propagated
        onto a following section, paragraph or table must be anchored exactly
        once (by the receiving element, not also by the target node), and an
        explicit `.. _name:` id must not collide with the element's own label.
        This guards against the double-labeling regression that can arise when
        several label-attachment mechanisms cover the same id.
        """
        import re

        output, warnings = build_typst(
            "Test Document\n"
            "=============\n"
            "\n"
            ".. _sec-target:\n"
            "\n"
            "Target Section\n"
            "--------------\n"
            "\n"
            ".. _para-target:\n"
            "\n"
            "Some paragraph content.\n"
            "\n"
            ".. _table-target:\n"
            "\n"
            ".. list-table::\n"
            "\n"
            "   * - A\n"
            "     - B\n"
            "\n"
            ".. _standalone-target:\n"
            "\n"
            "See :ref:`sec-target`, :ref:`para-target`, "
            "and :ref:`the table <table-target>`.\n"
        )

        # Collect every label *definition* (``<name>`` not preceded by the
        # ``link(`` / ``ref(`` that marks a reference). Label uses are always
        # ``link(<name>, ...)`` here, so excluding that prefix isolates defs.
        defs = [m.group(1) for m in re.finditer(r"(?<!link\()<([^>]+)>", output)]
        duplicates = {label for label in defs if defs.count(label) > 1}
        assert not duplicates, f"Duplicate Typst labels emitted: {duplicates}"
        assert "Reference node has empty URL" not in warnings
