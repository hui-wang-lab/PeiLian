"""测试 P3 综合报告渲染。"""

from __future__ import annotations


def _build_result(no_issues: bool = False):
    from peilian.judge import (
        AgentJudgeReport,
        CustomerJudgeReport,
        DimensionScore,
        Issue,
        JudgeResult,
    )
    from peilian.report import EvaluationReport

    agent_report = AgentJudgeReport(
        scores=(
            DimensionScore("professionalism", "话术专业度", 3, "术语基本准确。"),
            DimensionScore("empathy", "共情度", 4, "能回应情绪。"),
            DimensionScore("structure", "逻辑结构", 2, "流程跳跃。"),
            DimensionScore("objection_handling", "异议处理", 3, "回应模板化。"),
        ),
        overall_comment="节奏需调整。",
        raw_response="{}",
    )
    issue = Issue(
        turn_index=2,
        agent_turn_number=1,
        related_turn_indices=(),
        excerpt="我家里 5 口人",
        violation_type="premature_disclosure",
        protected_field="family_structure",
        reasoning="尚未问家庭结构。",
    )
    customer_report = CustomerJudgeReport(
        premature_disclosure_issues=() if no_issues else (issue,),
        inconsistency_issues=(),
        overall_comment="客户行为有异常。" if not no_issues else "未发现异常。",
        raw_response="{}",
    )
    return JudgeResult(
        evaluation_report=EvaluationReport(6, ("occupation",), ("income",), ()),
        agent_report=agent_report,
        customer_report=customer_report,
    )


def test_render_judge_result_contains_three_sections():
    from peilian.judge import render_judge_result

    output = render_judge_result(_build_result())

    assert "规则层评估（P2）" in output
    assert "代理人评分（P3）" in output
    assert "AI 客户行为诊断（P3）" in output


def test_render_judge_result_contains_dimension_labels():
    from peilian.judge import render_judge_result

    output = render_judge_result(_build_result())

    for label in ("话术专业度", "共情度", "逻辑结构", "异议处理"):
        assert label in output


def test_render_judge_result_contains_issue_details():
    from peilian.judge import render_judge_result

    output = render_judge_result(_build_result())

    assert "family_structure" in output
    assert "我家里 5 口人" in output


def test_render_judge_result_handles_zero_customer_issues():
    from peilian.judge import render_judge_result

    output = render_judge_result(_build_result(no_issues=True))

    assert "未发现客户行为异常" in output


def test_render_judge_result_p2_section_has_compact_summary():
    from peilian.judge import render_judge_result

    output = render_judge_result(_build_result())

    assert "必问点覆盖率" in output
    assert "合规红线扫描" in output
    assert "综合评估报告" in output
    assert output.count("评估报告") == 1
