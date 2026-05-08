"""测试 P2 评估报告：EvaluationReport / ComplianceHit + render_report。"""

from __future__ import annotations

import pytest


def _build_empty_report():
    from peilian.report import EvaluationReport

    return EvaluationReport(
        total_categories=6,
        covered_categories=(),
        missed_categories=(
            "family_structure",
            "occupation",
            "income",
            "existing_coverage",
            "future_planning",
            "health_status",
        ),
        compliance_hits=(),
    )


def _build_report_with_hits():
    from peilian.report import ComplianceHit, EvaluationReport

    hit = ComplianceHit(
        turn_index=5,
        agent_turn_number=3,
        excerpt="...保证收益 4.5%...",
        rule_id="guarantee_return",
        rule_label="保证收益",
        matched_keyword="保证收益",
    )
    return EvaluationReport(
        total_categories=6,
        covered_categories=("family_structure", "occupation"),
        missed_categories=("income", "existing_coverage", "future_planning", "health_status"),
        compliance_hits=(hit,),
    )


def test_evaluation_report_can_be_instantiated():
    report = _build_empty_report()
    assert report.total_categories == 6
    assert report.compliance_hits == ()
    assert len(report.missed_categories) == 6


def test_evaluation_report_is_frozen():
    report = _build_empty_report()
    with pytest.raises(Exception):
        report.total_categories = 999  # type: ignore[misc]


def test_compliance_hit_is_frozen_and_has_required_fields():
    from peilian.report import ComplianceHit

    hit = ComplianceHit(
        turn_index=1,
        agent_turn_number=1,
        excerpt="...保证收益...",
        rule_id="guarantee_return",
        rule_label="保证收益",
        matched_keyword="保证收益",
    )
    assert hit.turn_index == 1
    assert hit.agent_turn_number == 1
    assert hit.rule_id == "guarantee_return"
    assert hit.rule_label == "保证收益"
    assert hit.matched_keyword == "保证收益"

    with pytest.raises(Exception):
        hit.rule_id = "x"  # type: ignore[misc]


def test_render_report_contains_section_headers_for_empty_report():
    from peilian.report import render_report

    output = render_report(_build_empty_report())
    assert isinstance(output, str)
    assert "必问点覆盖率" in output
    assert "合规红线扫描" in output


def test_render_report_with_hit_includes_rule_label():
    from peilian.report import render_report

    output = render_report(_build_report_with_hits())
    assert "保证收益" in output, "渲染应包含命中规则的中文标签"
