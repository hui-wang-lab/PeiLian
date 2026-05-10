"""P4 CustomerState 测试：状态迁移 / 进度释放 / 重复问幂等 / 边界条件。"""

import pytest

from peilian.customer_state import CustomerState, update_state
from peilian.persona import Persona
from peilian.persona_factory import PersonaMeta


def _make_persona(persistence=0.5, expressiveness=0.5):
    """辅助函数：创建最小 Persona + PersonaMeta 用于测试。"""
    persona = Persona(
        name="测试",
        age=30,
        occupation="IT",
        family="已婚",
        income_level="中产",
        existing_coverage=("社保",),
        pain_points=("忙",),
        hidden_concerns=("担心保费", "不想体检"),
        persistence=persistence,
        expressiveness=expressiveness,
        initial_mood="正常",
    )
    meta = PersonaMeta(
        source_path="test.yaml",
        difficulty="medium",
        name="测试",
        hidden_concerns=[
            {
                "key": "price_sensitive",
                "label": "担心保费",
                "keywords": ["价格", "保费", "预算", "贵"],
                "initial_stage": "untouched",
            },
            {
                "key": "health_reluctance",
                "label": "不想体检",
                "keywords": ["健康告知", "体检", "病史"],
                "initial_stage": "untouched",
            },
        ],
    )
    return persona, meta


def test_initial_state_all_undisclosed():
    """初始状态：所有字段未披露，所有隐藏关切 untouched。"""
    persona, meta = _make_persona(persistence=0.5)
    state = CustomerState.initial(persona, meta)

    assert state.disclosed_fields == frozenset()
    assert state.asked_fields_this_turn == frozenset()
    assert state.turn_count == 0
    assert state.patience == pytest.approx(1.0)
    # trust = clip(0.6 - 0.4 * 0.5, 0.1, 0.9) = clip(0.4, 0.1, 0.9) = 0.4
    assert state.trust == pytest.approx(0.4)

    for hc in meta.hidden_concerns:
        assert state.stage_of(hc["key"]) == "untouched"


def test_agent_specific_ask_populates_asked_and_disclosed():
    """代理人点名 occupation → asked_fields_this_turn 含 occupation，disclosed_fields 含 occupation。"""
    persona, meta = _make_persona()
    state = CustomerState.initial(persona, meta)

    # "工作" is in occupation keywords
    agent_msg = "您是在哪个单位工作？做什么工作？"
    # "工作" in response triggers occupation
    customer_resp = "我在一家互联网公司工作，负责产品。"

    new_state = update_state(
        state, agent_msg, customer_resp, persona=persona, persona_meta=meta
    )

    assert "occupation" in new_state.asked_fields_this_turn
    assert "occupation" in new_state.disclosed_fields


def test_specific_ask_not_blocked_by_coarse_p2_keywords():
    """P4 具体点名词即使未命中 P2 粗词库，也应进入 asked_fields_this_turn。"""
    persona, meta = _make_persona()
    state = CustomerState.initial(persona, meta)

    new_state = update_state(
        state,
        "您结婚了吗？有孩子吗？",
        "已婚，有一个孩子。",
        persona=persona,
        persona_meta=meta,
    )

    assert "family_structure" in new_state.asked_fields_this_turn
    assert "family_structure" in new_state.disclosed_fields


def test_natural_short_answers_count_as_disclosed_after_specific_ask():
    """客户自然短答不复述 P2 关键词时，也应在被点名后记为已披露。"""
    persona, meta = _make_persona()
    state = CustomerState.initial(persona, meta)

    state = update_state(
        state,
        "您家里几口人？",
        "三口，孩子 5 岁。",
        persona=persona,
        persona_meta=meta,
    )
    assert "family_structure" in state.disclosed_fields

    state = update_state(
        state,
        "您年收入大概多少？",
        "30 万左右。",
        persona=persona,
        persona_meta=meta,
    )
    assert "income" in state.disclosed_fields


def test_vague_question_yields_empty_asked_fields():
    """泛泛提问 → asked_fields_this_turn 为空集。"""
    persona, meta = _make_persona()
    state = CustomerState.initial(persona, meta)

    agent_msg = "想了解你的情况"
    customer_resp = "哦，好的。"

    new_state = update_state(
        state, agent_msg, customer_resp, persona=persona, persona_meta=meta
    )

    assert new_state.asked_fields_this_turn == frozenset()


def test_customer_volunteering_unasked_field_not_disclosed():
    """客户主动报未问字段 → disclosed_fields 不增加。"""
    persona, meta = _make_persona()
    state = CustomerState.initial(persona, meta)

    agent_msg = "你好，今天天气不错"
    customer_resp = "我年收入50万，有社保。"  # 命中 income 和 existing_coverage

    new_state = update_state(
        state, agent_msg, customer_resp, persona=persona, persona_meta=meta
    )

    # 没被问过，所以不标记为 disclosed
    assert "income" not in new_state.disclosed_fields
    assert "existing_coverage" not in new_state.disclosed_fields


def test_hidden_concern_linear_progression():
    """隐藏关切迁移：untouched→triggered→hinted→expressed。"""
    persona, meta = _make_persona()
    state = CustomerState.initial(persona, meta)

    # 轮1: agent 触及关键词 → untouched → triggered
    state1 = update_state(
        state,
        "你觉得保费价格怎么样？预算够吗？",
        "嗯……还在考虑。",
        persona=persona,
        persona_meta=meta,
    )
    assert state1.stage_of("price_sensitive") == "triggered"

    # 轮2: customer 含模糊表达词 → triggered → hinted
    state2 = update_state(
        state1,
        "保费这块你有什么顾虑吗？",
        "有点担心保费太贵影响生活。",
        persona=persona,
        persona_meta=meta,
    )
    assert state2.stage_of("price_sensitive") == "hinted"

    # 轮3: customer 含明确表达词 → hinted → expressed
    state3 = update_state(
        state2,
        "具体说说你的担心？",
        "我担心保费太贵，房贷压力已经很大了。",
        persona=persona,
        persona_meta=meta,
    )
    assert state3.stage_of("price_sensitive") == "expressed"


def test_hidden_concern_max_one_step_per_turn():
    """隐藏关切单轮最多推进一档。"""
    persona, meta = _make_persona()
    state = CustomerState.initial(persona, meta)

    # 单轮中同时满足 agent 触发 + customer 明确表达
    # 应只推进一档：untouched → triggered
    new_state = update_state(
        state,
        "你觉得保费贵吗？预算怎么样？",
        "我担心保费太贵，房贷压力很大。",
        persona=persona,
        persona_meta=meta,
    )

    # 只前进一档，不跳级
    assert new_state.stage_of("price_sensitive") == "triggered"


def test_patience_decay_on_empty_asks():
    """耐心值衰减：连续 3 轮无进展 → patience ≈ 0.91（首轮不扣减，需 4 次迭代得 3 次扣减）。"""
    persona, meta = _make_persona()
    state = CustomerState.initial(persona, meta)

    for _ in range(4):
        state = update_state(
            state,
            "今天天气不错",
            "是的。",
            persona=persona,
            persona_meta=meta,
        )

    # turn_count=0 时不扣减；turn_count=1,2,3 各扣 0.03 → 1.0 - 3×0.03 = 0.91
    assert state.patience == pytest.approx(0.91, abs=0.01)


def test_compliance_violation_reduces_trust():
    """合规红线词出现在 agent_message → trust -0.10。"""
    persona, meta = _make_persona()
    state = CustomerState.initial(persona, meta)
    initial_trust = state.trust

    # Use a message that triggers compliance but NOT mandatory categories
    # "不用看免责" triggers hide_exclusion rule
    new_state = update_state(
        state,
        "这个不错，不用看免责条款。",
        "真的吗？",
        persona=persona,
        persona_meta=meta,
    )

    assert new_state.trust == pytest.approx(initial_trust - 0.10, abs=0.01)


def test_disclosed_fields_idempotent():
    """同一字段重复问到 → 幂等。"""
    persona, meta = _make_persona()
    state = CustomerState.initial(persona, meta)

    # 第一次问 family - "家里有" is a keyword
    state1 = update_state(
        state,
        "您家里几口人？",
        "我们家里有三口人。",
        persona=persona,
        persona_meta=meta,
    )
    assert "family_structure" in state1.disclosed_fields

    # 第二次问 family（已披露）
    state2 = update_state(
        state1,
        "孩子多大了？家里有几口人？",
        "孩子5岁了，家里还是三口之家。",
        persona=persona,
        persona_meta=meta,
    )
    # disclosed_fields 不重复计数（frozenset 天然幂等）
    assert "family_structure" in state2.disclosed_fields
    # patience 仍按规则变化（1.0 + 0.01 被 clip 到 1.0）
    assert state2.patience == pytest.approx(1.0, abs=0.01)


def test_frozen_dataclass():
    """CustomerState 是 frozen dataclass。"""
    from dataclasses import FrozenInstanceError

    persona, meta = _make_persona()
    state = CustomerState.initial(persona, meta)
    with pytest.raises(FrozenInstanceError):
        state.trust = 0.5  # Direct attribute assignment raises on frozen
