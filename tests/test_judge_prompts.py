"""测试 P3 judge prompt 的关键约束。"""

from __future__ import annotations


def test_agent_prompt_contains_dimensions_and_json_contract():
    from peilian.judge_prompts import AGENT_JUDGE_SYSTEM_PROMPT

    prompt = AGENT_JUDGE_SYSTEM_PROMPT

    for token in (
        "professionalism",
        "empathy",
        "structure",
        "objection_handling",
        "话术专业度",
        "共情度",
        "逻辑结构",
        "异议处理",
    ):
        assert token in prompt

    assert "JSON" in prompt
    assert "1-5" in prompt or "1–5" in prompt
    assert "overall_comment" in prompt


def test_agent_prompt_contains_score_anchors_per_dimension():
    from peilian.judge_prompts import AGENT_JUDGE_SYSTEM_PROMPT

    prompt = AGENT_JUDGE_SYSTEM_PROMPT
    assert "1 分" in prompt and "3 分" in prompt and "5 分" in prompt

    anchors = {
        "professionalism": ("反复说错", "动态调整"),
        "empathy": ("完全无视", "主动回应"),
        "structure": ("完全跳跃", "节奏清晰"),
        "objection_handling": ("没识别", "差异化"),
    }
    for dim, (low, high) in anchors.items():
        assert low in prompt, f"{dim} 缺 1 分锚点字样：{low}"
        assert high in prompt, f"{dim} 缺 5 分锚点字样：{high}"


def test_customer_prompt_contains_disclosure_and_consistency_rules():
    from peilian.judge_prompts import CUSTOMER_JUDGE_SYSTEM_PROMPT

    prompt = CUSTOMER_JUDGE_SYSTEM_PROMPT

    for token in (
        "premature_disclosure",
        "inconsistency",
        "family_structure",
        "income",
        "existing_coverage",
        "hidden_concerns",
        "截至该 assistant 回复前",
        "不判断与外部 persona 对象的矛盾",
    ):
        assert token in prompt


def test_render_messages_for_judge_includes_turn_indices():
    from peilian.judge_prompts import render_messages_for_judge

    messages = [
        {"role": "system", "content": "sys"},
        {"role": "user", "content": "您好"},
        {"role": "assistant", "content": "你好"},
    ]

    rendered = render_messages_for_judge(messages)

    assert "[0] system: sys" in rendered
    assert "[1] user: 您好" in rendered
    assert "[2] assistant: 你好" in rendered
