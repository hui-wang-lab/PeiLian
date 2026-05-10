"""测试 customer system prompt 渲染。

P1 阶段：确保被动反应核心约束关键字不被无意删除（重构防护）。
"""

from __future__ import annotations


def test_render_returns_non_empty_string():
    from peilian.persona import SAMPLE_PERSONA
    from peilian.prompts import render_customer_system_prompt
    from peilian.scenario import SAMPLE_SCENARIO

    output = render_customer_system_prompt(SAMPLE_PERSONA, SAMPLE_SCENARIO)
    assert isinstance(output, str)
    assert len(output) > 0


def test_render_contains_persona_basic_fields():
    from peilian.persona import SAMPLE_PERSONA
    from peilian.prompts import render_customer_system_prompt
    from peilian.scenario import SAMPLE_SCENARIO

    output = render_customer_system_prompt(SAMPLE_PERSONA, SAMPLE_SCENARIO)
    assert SAMPLE_PERSONA.name in output
    assert str(SAMPLE_PERSONA.age) in output
    assert SAMPLE_PERSONA.family in output


def test_render_contains_passive_response_keywords():
    """渲染输出至少命中 3/4 被动反应核心关键词。"""
    from peilian.persona import SAMPLE_PERSONA
    from peilian.prompts import render_customer_system_prompt
    from peilian.scenario import SAMPLE_SCENARIO

    output = render_customer_system_prompt(SAMPLE_PERSONA, SAMPLE_SCENARIO)
    keywords = ["不主动", "代理人不问", "不替代理人推进", "不主动结束对话"]
    hits = [kw for kw in keywords if kw in output]
    assert len(hits) >= 3, (
        f"被动反应核心关键词命中 {len(hits)}/4：命中={hits}"
    )


def test_render_contains_hidden_concerns_constraint():
    """hidden_concerns 三段强约束必须显式体现。"""
    from peilian.persona import SAMPLE_PERSONA
    from peilian.prompts import render_customer_system_prompt
    from peilian.scenario import SAMPLE_SCENARIO

    output = render_customer_system_prompt(SAMPLE_PERSONA, SAMPLE_SCENARIO)
    assert "禁止一次性完整暴露" in output
    assert ("内心顾虑" in output) or ("隐藏关切" in output)


def test_render_contains_scenario_context():
    from peilian.persona import SAMPLE_PERSONA
    from peilian.prompts import render_customer_system_prompt
    from peilian.scenario import SAMPLE_SCENARIO

    output = render_customer_system_prompt(SAMPLE_PERSONA, SAMPLE_SCENARIO)
    assert "办公室" in output


def test_render_warns_against_revealing_existing_coverage_unprompted():
    """开场或泛问时不主动透露已有保障/单位医疗险（针对人工验收发现的越界）。"""
    from peilian.persona import SAMPLE_PERSONA
    from peilian.prompts import render_customer_system_prompt
    from peilian.scenario import SAMPLE_SCENARIO

    output = render_customer_system_prompt(SAMPLE_PERSONA, SAMPLE_SCENARIO)
    coverage_terms = ["已有保障", "单位医疗", "公司团险", "基础医疗险"]
    hits = [t for t in coverage_terms if t in output]
    assert len(hits) >= 2, (
        f"prompt 应显式提及不主动透露已有保障/单位医疗险类关键字（至少 2 个变体）；"
        f"命中={hits}"
    )


def test_render_addresses_vague_questions():
    """对代理人泛泛话术（如「了解保障情况」），客户应模糊回应或要求具体。"""
    from peilian.persona import SAMPLE_PERSONA
    from peilian.prompts import render_customer_system_prompt
    from peilian.scenario import SAMPLE_SCENARIO

    output = render_customer_system_prompt(SAMPLE_PERSONA, SAMPLE_SCENARIO)
    assert "保障情况" in output, (
        "prompt 应针对「了解保障情况」这种泛泛话术给出指引"
    )
    assert (
        ("模糊" in output)
        or ("具体一点" in output)
        or ("具体哪方面" in output)
    ), "prompt 应教客户在面对泛泛话术时的应对方式（模糊回应或要求对方具体）"


def test_render_has_opening_turn_guidance():
    """prompt 必须有针对开场/首次回应的特别约束。"""
    from peilian.persona import SAMPLE_PERSONA
    from peilian.prompts import render_customer_system_prompt
    from peilian.scenario import SAMPLE_SCENARIO

    output = render_customer_system_prompt(SAMPLE_PERSONA, SAMPLE_SCENARIO)
    opening_markers = ["开场", "第一", "首次", "首轮"]
    hits = [m for m in opening_markers if m in output]
    assert hits, (
        f"prompt 应包含针对开场/首次回应的特别约束；"
        f"未命中任何候选关键字={opening_markers}"
    )


def test_render_forbids_stage_directions():
    """客户回复只能是口语，不应含动作/神态旁白。"""
    from peilian.persona import SAMPLE_PERSONA
    from peilian.prompts import render_customer_system_prompt
    from peilian.scenario import SAMPLE_SCENARIO

    output = render_customer_system_prompt(SAMPLE_PERSONA, SAMPLE_SCENARIO)
    required_terms = ["只输出客户说出口的话", "不要写动作", "神态", "括号"]
    missing = [term for term in required_terms if term not in output]
    assert not missing, f"prompt 缺少去舞台提示约束：{missing}"
