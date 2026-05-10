"""测试 P2 状态观察器：evaluate(messages) 纯函数。

P2 阶段：
- 只扫 role == 'user'（代理人发言）
- 纯函数，多次调用结果一致
- 与 dialogue.py 物理隔离（本测试文件不 import dialogue / openai）
"""

from __future__ import annotations

import pytest


# 6 类必问点，按 phase-2.md §1 关键词构造的代理人发言（精确命中）
PERFECT_AGENT_TURNS = [
    "您家里几口人，几个孩子？",       # family_structure: 几口人 / 几个孩子
    "请问您是做什么的？",             # occupation: 您是做什么的
    "您家庭年收入大概多少？",         # income: 收入 / 年收入
    "您之前买过什么保险吗？",         # existing_coverage: 保险
    "您对未来有什么规划吗？",         # future_planning: 规划 / 未来
    "您身体怎么样，做过手术吗？",     # health_status: 身体 / 手术
]


def _wrap_as_messages(agent_turns: list[str]) -> list[dict[str, str]]:
    """把代理人发言列表包成完整的 messages 结构（含 system + 客户应答占位）。"""
    messages: list[dict[str, str]] = [{"role": "system", "content": ""}]
    for utt in agent_turns:
        messages.append({"role": "user", "content": utt})
        messages.append({"role": "assistant", "content": "嗯。"})
    return messages


def test_empty_messages_returns_all_missed():
    """空对话：必问点全漏、无红线命中。"""
    from peilian.observer import evaluate

    report = evaluate([])
    assert report.total_categories == 6
    assert report.covered_categories == ()
    assert len(report.missed_categories) == 6
    assert report.compliance_hits == ()


def test_perfect_dialog_covers_all_categories_no_hits():
    """完美对话：6 类必问点全覆盖，无红线。"""
    from peilian.observer import evaluate

    messages = _wrap_as_messages(PERFECT_AGENT_TURNS)
    report = evaluate(messages)

    assert set(report.covered_categories) == {
        "family_structure",
        "occupation",
        "income",
        "existing_coverage",
        "future_planning",
        "health_status",
    }
    assert report.missed_categories == ()
    assert report.compliance_hits == ()


def test_missing_one_category_is_identified():
    """漏问 future_planning：missed 恰好为该类。"""
    from peilian.observer import evaluate

    turns_without_planning = [
        utt for utt in PERFECT_AGENT_TURNS
        if "规划" not in utt and "未来" not in utt
    ]
    assert len(turns_without_planning) == 5  # 守护：构造正确

    messages = _wrap_as_messages(turns_without_planning)
    report = evaluate(messages)

    assert report.missed_categories == ("future_planning",)
    assert "family_structure" in report.covered_categories


def test_single_compliance_violation_is_located():
    """触发 1 条红线：hits 长度=1，rule_id 正确。"""
    from peilian.observer import evaluate

    messages = [
        {"role": "system", "content": ""},
        {"role": "user", "content": "您放心，这个不会拒赔的。"},
        {"role": "assistant", "content": "好的。"},
    ]
    report = evaluate(messages)

    assert len(report.compliance_hits) == 1
    hit = report.compliance_hits[0]
    assert hit.rule_id == "hide_exclusion"
    assert "不会拒赔" in hit.excerpt or "不会拒赔" == hit.matched_keyword


def test_one_sentence_triggers_two_rules():
    """一句多命中：「保证收益 4.5%，比存款利息高得多」→ 命中 2 条规则。"""
    from peilian.observer import evaluate

    messages = [
        {"role": "system", "content": ""},
        {
            "role": "user",
            "content": "这款产品保证收益 4.5%，比存款利息高得多。",
        },
        {"role": "assistant", "content": "真的吗？"},
    ]
    report = evaluate(messages)

    assert len(report.compliance_hits) == 2
    rule_ids = {hit.rule_id for hit in report.compliance_hits}
    assert rule_ids == {"guarantee_return", "mislead_vs_deposit"}


def test_sample_conversation_p2_end_to_end():
    """SAMPLE_CONVERSATION_P2 端到端：missed 恰好是 income/future_planning，红线命中 2 条。"""
    from peilian.conversations import SAMPLE_CONVERSATION_P2
    from peilian.observer import evaluate

    report = evaluate(SAMPLE_CONVERSATION_P2)

    assert set(report.missed_categories) == {"income", "future_planning"}
    assert len(report.compliance_hits) == 2
    rule_ids = {hit.rule_id for hit in report.compliance_hits}
    assert rule_ids == {"guarantee_return", "mislead_vs_deposit"}


def test_evaluate_is_pure_function():
    """同一份 messages 多次调用结果一致；不修改入参。"""
    from peilian.observer import evaluate

    messages = _wrap_as_messages(PERFECT_AGENT_TURNS)
    snapshot = [dict(m) for m in messages]

    report1 = evaluate(messages)
    report2 = evaluate(messages)

    assert report1 == report2
    assert messages == snapshot, "evaluate 不能修改入参 messages"


def test_observer_is_isolated_from_dialogue_layer():
    """架构隔离：observer 模块不 import Dialogue / openai。"""
    import peilian.observer as observer_mod

    source_path = observer_mod.__file__
    assert source_path is not None
    with open(source_path, "r", encoding="utf-8") as f:
        source = f.read()

    # 不能直接依赖 dialogue 层或 LLM SDK
    assert "from peilian.dialogue" not in source
    assert "import peilian.dialogue" not in source
    assert "import openai" not in source
    assert "from openai" not in source


# ---------------------------------------------------------------------------
# P4 兼容守护：match_mandatory_categories 与 _scan_mandatory 等价
# ---------------------------------------------------------------------------
# phase-4.md §6 / 实施任务 #2 要求：将 _scan_mandatory 核心提取为公开纯函数
# match_mandatory_categories 后，对既有 P2 关键词应返回与 _scan_mandatory 等价的
# category 集合。本组测试防止 observer 重构悄悄改 P2 行为。

def test_match_mandatory_categories_equivalent_to_scan_mandatory():
    """match_mandatory_categories 与 _scan_mandatory 在等价输入上结果一致。"""
    from peilian.observer import _scan_mandatory, match_mandatory_categories

    samples = [
        "",
        "您家里几口人，几个孩子？",
        "请问您是做什么的？",
        "您家庭年收入大概多少？",
        "您之前买过什么保险吗？",
        "您对未来有什么规划吗？",
        "您身体怎么样，做过手术吗？",
        "您家里几口人？年收入多少？身体怎么样？",
        "今天天气不错。",
        "保险保险保险",
    ]
    for text in samples:
        covered: set[str] = set()
        _scan_mandatory(text, covered)
        assert frozenset(covered) == match_mandatory_categories(text), (
            f"对文本 {text!r}，_scan_mandatory 与 match_mandatory_categories 结果不一致"
        )


def test_match_mandatory_categories_returns_frozenset():
    """返回 frozenset（保证可作为 frozen dataclass 字段值）。"""
    from peilian.observer import match_mandatory_categories

    result = match_mandatory_categories("您家里几口人？")
    assert isinstance(result, frozenset)
    assert "family_structure" in result


def test_match_mandatory_categories_does_not_mutate_input():
    """纯函数，不影响外部状态。"""
    from peilian.observer import match_mandatory_categories

    text = "您家里几口人？"
    snapshot = text
    _ = match_mandatory_categories(text)
    assert text == snapshot
