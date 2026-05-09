"""测试 P3 judge JSON parsing。"""

from __future__ import annotations

import json

import pytest


def _agent_payload() -> str:
    return json.dumps(
        {
            "scores": [
                {
                    "dimension": "professionalism",
                    "label": "话术专业度",
                    "score": 3,
                    "reasoning": "术语基本准确。",
                },
                {
                    "dimension": "empathy",
                    "label": "共情度",
                    "score": 4,
                    "reasoning": "能回应客户情绪。",
                },
                {
                    "dimension": "structure",
                    "label": "逻辑结构",
                    "score": 2,
                    "reasoning": "KYC 未完成即讲产品。",
                },
                {
                    "dimension": "objection_handling",
                    "label": "异议处理",
                    "score": 3,
                    "reasoning": "识别价格异议但回应模板化。",
                },
            ],
            "overall_comment": "节奏需要更稳。",
        },
        ensure_ascii=False,
    )


def _customer_payload() -> str:
    return json.dumps(
        {
            "premature_disclosure_issues": [
                {
                    "turn_index": 2,
                    "agent_turn_number": 1,
                    "related_turn_indices": [],
                    "excerpt": "我家里 5 口人",
                    "violation_type": "premature_disclosure",
                    "protected_field": "family_structure",
                    "reasoning": "代理人尚未触发家庭结构。",
                }
            ],
            "inconsistency_issues": [
                {
                    "turn_index": 6,
                    "agent_turn_number": 0,
                    "related_turn_indices": [2],
                    "excerpt": "太太是医生 / 太太在律所",
                    "violation_type": "inconsistency",
                    "protected_field": "spouse_occupation",
                    "reasoning": "太太职业前后矛盾。",
                }
            ],
            "overall_comment": "客户演绎有越界和矛盾。",
        },
        ensure_ascii=False,
    )


def test_parse_agent_report_success():
    from peilian.judge import parse_agent_report

    report = parse_agent_report(_agent_payload())

    assert len(report.scores) == 4
    assert report.scores[0].dimension == "professionalism"
    assert report.scores[0].score == 3
    assert report.raw_response == _agent_payload()


def test_parse_customer_report_success():
    from peilian.judge import parse_customer_report

    report = parse_customer_report(_customer_payload())

    assert len(report.premature_disclosure_issues) == 1
    assert len(report.inconsistency_issues) == 1
    assert report.premature_disclosure_issues[0].protected_field == "family_structure"


def test_parse_agent_report_rejects_invalid_json():
    from peilian.judge import JudgeParseError, parse_agent_report

    with pytest.raises(JudgeParseError, match="JSON"):
        parse_agent_report("{")


def test_parse_agent_report_rejects_missing_field():
    from peilian.judge import JudgeParseError, parse_agent_report

    payload = json.loads(_agent_payload())
    del payload["scores"][0]["reasoning"]

    with pytest.raises(JudgeParseError, match="reasoning"):
        parse_agent_report(json.dumps(payload, ensure_ascii=False))


def test_parse_agent_report_rejects_score_out_of_range():
    from peilian.judge import JudgeParseError, parse_agent_report

    payload = json.loads(_agent_payload())
    payload["scores"][0]["score"] = 7

    with pytest.raises(JudgeParseError, match="score"):
        parse_agent_report(json.dumps(payload, ensure_ascii=False))


def test_parse_agent_report_rejects_unknown_dimension():
    from peilian.judge import JudgeParseError, parse_agent_report

    payload = json.loads(_agent_payload())
    payload["scores"][0]["dimension"] = "professionalisma"

    with pytest.raises(JudgeParseError, match="dimension"):
        parse_agent_report(json.dumps(payload, ensure_ascii=False))
