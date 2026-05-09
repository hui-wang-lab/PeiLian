"""测试 P3 judge API：mock LLM client，不调用真实 LLM。"""

from __future__ import annotations

import json

import pytest


def _agent_json() -> str:
    return json.dumps(
        {
            "scores": [
                {"dimension": "professionalism", "label": "话术专业度", "score": 3, "reasoning": "术语基本准确。"},
                {"dimension": "empathy", "label": "共情度", "score": 4, "reasoning": "回应了情绪。"},
                {"dimension": "structure", "label": "逻辑结构", "score": 2, "reasoning": "流程跳跃。"},
                {"dimension": "objection_handling", "label": "异议处理", "score": 3, "reasoning": "回应偏模板。"},
            ],
            "overall_comment": "节奏需调整。",
        },
        ensure_ascii=False,
    )


def _customer_json() -> str:
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
                    "reasoning": "尚未问家庭结构。",
                }
            ],
            "inconsistency_issues": [
                {
                    "turn_index": 6,
                    "agent_turn_number": 0,
                    "related_turn_indices": [2],
                    "excerpt": "医生 / 律所合伙人",
                    "violation_type": "inconsistency",
                    "protected_field": "spouse_occupation",
                    "reasoning": "太太职业前后矛盾。",
                }
            ],
            "overall_comment": "客户行为有异常。",
        },
        ensure_ascii=False,
    )


class _Message:
    def __init__(self, content: str) -> None:
        self.content = content


class _Choice:
    def __init__(self, content: str) -> None:
        self.message = _Message(content)


class _Response:
    def __init__(self, content: str) -> None:
        self.choices = [_Choice(content)]


class _Completions:
    def __init__(self, responses: list[str]) -> None:
        self._responses = responses
        self.calls: list[dict[str, object]] = []

    def create(self, **kwargs):
        self.calls.append(kwargs)
        return _Response(self._responses.pop(0))


class _Chat:
    def __init__(self, responses: list[str]) -> None:
        self.completions = _Completions(responses)


class _FakeClient:
    def __init__(self, responses: list[str]) -> None:
        self.chat = _Chat(responses)


def test_judge_agent_uses_mock_client_and_json_response_format():
    from peilian.conversations import SAMPLE_CONVERSATION_P3
    from peilian.judge import judge_agent

    client = _FakeClient([_agent_json()])
    report = judge_agent(SAMPLE_CONVERSATION_P3, client=client, model="judge-model")

    assert report.scores[0].dimension == "professionalism"
    call = client.chat.completions.calls[0]
    assert call["model"] == "judge-model"
    assert call["temperature"] == 0
    assert call["response_format"] == {"type": "json_object"}


def test_judge_customer_uses_mock_client():
    from peilian.conversations import SAMPLE_CONVERSATION_P3
    from peilian.judge import judge_customer

    client = _FakeClient([_customer_json()])
    report = judge_customer(SAMPLE_CONVERSATION_P3, client=client, model="judge-model")

    assert report.premature_disclosure_issues[0].turn_index == 2
    assert report.inconsistency_issues[0].turn_index == 6


def test_build_judge_result_combines_p2_and_p3_in_order():
    from peilian.conversations import SAMPLE_CONVERSATION_P3
    from peilian.judge import build_judge_result

    client = _FakeClient([_agent_json(), _customer_json()])
    result = build_judge_result(SAMPLE_CONVERSATION_P3, client=client, model="judge-model")

    assert set(result.evaluation_report.covered_categories) == {
        "occupation",
        "health_status",
    }
    assert len(result.agent_report.scores) == 4
    assert len(result.customer_report.premature_disclosure_issues) == 1


def test_judge_agent_does_not_mutate_messages():
    from peilian.conversations import SAMPLE_CONVERSATION_P3
    from peilian.judge import judge_agent

    messages = [dict(m) for m in SAMPLE_CONVERSATION_P3]
    snapshot = [dict(m) for m in messages]

    judge_agent(messages, client=_FakeClient([_agent_json()]))

    assert messages == snapshot


def test_llm_errors_bubble_up():
    from peilian.conversations import SAMPLE_CONVERSATION_P3
    from peilian.judge import judge_agent

    class BrokenCompletions:
        def create(self, **kwargs):
            raise RuntimeError("boom")

    class BrokenClient:
        chat = type("Chat", (), {"completions": BrokenCompletions()})()

    with pytest.raises(RuntimeError, match="boom"):
        judge_agent(SAMPLE_CONVERSATION_P3, client=BrokenClient())


def test_judge_module_is_isolated_from_generation_layer():
    import peilian.judge as judge_mod

    source_path = judge_mod.__file__
    assert source_path is not None
    with open(source_path, "r", encoding="utf-8") as f:
        source = f.read()

    assert "peilian.dialogue" not in source
    assert "peilian.persona" not in source
    assert "peilian.scenario" not in source
    assert "peilian.prompts" not in source
