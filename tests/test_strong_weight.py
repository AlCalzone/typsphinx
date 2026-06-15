"""
Tests for strong (bold) font weight handling in the default template.

Typst's built-in `strong` element applies a +300 font weight *delta* per
nesting level. Nested strong content (e.g. ``**bold**`` inside a bold
rubric or API signature, both of which typsphinx wraps in ``strong({...})``)
therefore escalates to weight 1000+, rendering heavier than either level.
Sphinx/docutils semantics are "bold", not "bolder than surrounding", and no
HTML/LaTeX output escalates like this.

The default template must replace strong's delta-based realization with an
absolute weight so nested strong renders identically to single strong.
"""

import json
from pathlib import Path

import pytest

TEMPLATE_PATH = Path(__file__).parent.parent / "typsphinx" / "templates" / "base.typ"


@pytest.fixture
def template_content():
    """Read default template content."""
    assert TEMPLATE_PATH.exists(), "Base template should exist"
    return TEMPLATE_PATH.read_text()


class TestStrongWeightShowRule:
    """The default template must render strong at an absolute weight."""

    def test_template_has_absolute_strong_show_rule(self, template_content):
        """
        Test that base template contains a show rule replacing strong's
        cumulative weight delta with an absolute weight.
        """
        assert "show strong: it => text(weight: 700, it.body)" in template_content, (
            "Template should rewrite strong to an absolute font weight to "
            "prevent weight escalation when strong is nested"
        )


class TestStrongWeightCompiled:
    """Verify the effective text weight with the real Typst compiler."""

    @pytest.fixture
    def query_weights(self, tmp_path):
        """
        Compile a document using the default template and return the
        effective text weight inside single and nested strong content.
        """
        import typst

        template = tmp_path / "template.typ"
        template.write_text(TEMPLATE_PATH.read_text())

        main = tmp_path / "main.typ"
        main.write_text(
            '#import "template.typ": project\n'
            '#show: project.with(title: "T", authors: ("A",), date: none)\n'
            "\n"
            "#strong[single #context [#metadata(text.weight)<w-single>]]\n"
            "\n"
            "#strong[#strong[nested #context [#metadata(text.weight)<w-nested>]]]\n"
        )

        weights = {}
        for label in ("w-single", "w-nested"):
            result = json.loads(typst.query(str(main), f"<{label}>", format="json"))
            weights[label] = result[0]["value"]
        return weights

    def test_single_strong_renders_bold(self, query_weights):
        """
        Single strong must render at absolute bold weight (700) instead of
        relying on Typst's relative +300 delta.
        """
        assert query_weights["w-single"] == "bold"

    def test_nested_strong_does_not_escalate(self, query_weights):
        """
        Nested strong must render at the same absolute bold weight as
        single strong (no cumulative +300 delta per nesting level).
        """
        assert query_weights["w-nested"] == "bold"
        assert query_weights["w-nested"] == query_weights["w-single"]
