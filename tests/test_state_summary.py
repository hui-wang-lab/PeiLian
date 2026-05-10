"""P4 State Summary 测试：摘要长度 / 被动措辞 / 含未披露字段清单 / 隐藏关切阶段。"""

import pytest

from peilian.persona import Persona
from peilian.persona_factory import PersonaMeta
from peilian.state_summary import render_state_summary
from peilian.customer_state import CustomerState


def _make_persona_and_state():
    persona = Persona(
        name="测试",
        age=30,
        occupation="IT",
        family="已婚",
        income_level="中产",
        existing_coverage=("社保",),
        pain_points=("忙",),
        hidden_concerns=("担心保费", "不想体检"),
        persistence=0.5,
        expressiveness=0.5,
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
                "keywords": ["价格", "保费", "预算"],
                "initial_stage": "untouched",
            },
            {
                "key": "health_reluctance",
                "label": "不想体检",
                "keywords": ["健康告知", "体检"],
                "initial_stage": "untouched",
            },
        ],
    )
    state = CustomerState.initial(persona, meta)
    return persona, meta, state


FORBIDDEN_PHRASES = [
    "可以披露",
    "现在可以说",
    "主动表达",
    "主动说出来",
    "现在可以表达",
    "可以主动",
    "请主动",
    "不妨主动",
]


def test_summary_length_under_400():
    """摘要长度 ≤ 400 字。"""
    persona, meta, state = _make_persona_and_state()
    summary = render_state_summary(state, persona, meta)
    assert len(summary) <= 400


def test_summary_contains_undisclosed_fields():
    """摘要含未披露字段清单（初始状态应含全部 6 个 P2 中文标签）。"""
    persona, meta, state = _make_persona_and_state()
    summary = render_state_summary(state, persona, meta)

    # 初始状态全部未披露
    assert "尚未被问到" in summary
    assert "家庭结构" in summary
    assert "职业行业" in summary
    assert "收入水平" in summary
    assert "已有保障" in summary
    assert "未来规划" in summary
    assert "健康情况" in summary


def test_summary_contains_hidden_concern_stages():
    """摘要含隐藏关切当前阶段。"""
    persona, meta, state = _make_persona_and_state()
    summary = render_state_summary(state, persona, meta)

    assert "担心保费" in summary
    assert "不想体检" in summary
    # 初始状态应为 untouched 描述
    assert "尚未被触及" in summary or "不要主动提及" in summary


def test_summary_contains_trust_and_patience():
    """摘要含信任度 / 耐心值数值。"""
    persona, meta, state = _make_persona_and_state()
    summary = render_state_summary(state, persona, meta)

    assert "信任度" in summary
    assert "耐心值" in summary
    # 应包含数值
    assert "0.40" in summary  # trust
    assert "1.00" in summary  # patience


def test_initial_summary_no_disclosed_fields():
    """初始状态摘要不含已披露信息。"""
    persona, meta, state = _make_persona_and_state()
    summary = render_state_summary(state, persona, meta)

    # 初始时没有已披露字段
    assert "已被问到并披露" in summary
    # 披露部分应为"无"或空
    assert "（无）" in summary or "无" in summary


def test_summary_forbidden_phrases_absent():
    """摘要不出现禁用词。"""
    persona, meta, state = _make_persona_and_state()
    summary = render_state_summary(state, persona, meta)

    for phrase in FORBIDDEN_PHRASES:
        assert phrase not in summary, f"摘要中出现禁用词: {phrase}"
