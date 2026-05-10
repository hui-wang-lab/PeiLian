"""P2 状态观察器：evaluate(messages) -> EvaluationReport。

来源：docs/phases/phase-2.md §4 / CLAUDE.md §2.2

架构铁律（不可违反）：
- 观察器只**消费** messages，不修改、不注入、不 hook 进对话流
- 不调度对话分支，不参与客户回复生成
- 模块层 import 只允许 peilian.rules / peilian.report；
  禁止出现 peilian.dialogue / openai（test_observer 守护）

# P3: LLM judge could augment this report later (phase-2.md §8)
"""

from __future__ import annotations

import re
from typing import Any

from peilian.report import ComplianceHit, EvaluationReport
from peilian.rules import (
    COMPLIANCE_RULES,
    MANDATORY_QUESTION_RULES,
)


_EXCERPT_CONTEXT_CHARS = 10


def evaluate(messages: list[dict[str, Any]]) -> EvaluationReport:
    """对一段对话历史做规则层评估（纯函数）。

    - 只读 messages，不修改入参
    - 只扫 role == "user"（代理人发言）
    - 同一条 user 消息中，同一条红线只记 1 次（去重）
    - 多次调用同一份 messages 结果一致
    """
    covered: set[str] = set()
    hits: list[ComplianceHit] = []

    agent_turn_n = 0
    for turn_index, msg in enumerate(messages):
        if msg.get("role") != "user":
            continue
        agent_turn_n += 1
        content = msg.get("content") or ""
        if not isinstance(content, str):
            continue

        _scan_mandatory(content, covered)
        _scan_compliance(content, turn_index, agent_turn_n, hits)

    covered_in_order = tuple(
        cid for cid in MANDATORY_QUESTION_RULES if cid in covered
    )
    missed_in_order = tuple(
        cid for cid in MANDATORY_QUESTION_RULES if cid not in covered
    )

    return EvaluationReport(
        total_categories=len(MANDATORY_QUESTION_RULES),
        covered_categories=covered_in_order,
        missed_categories=missed_in_order,
        compliance_hits=tuple(hits),
    )


# ---------------------------------------------------------------------------
# 内部扫描器
# ---------------------------------------------------------------------------
# ---------------------------------------------------------------------------
# 公开纯函数：P2 内部使用 + P4 复用
# ---------------------------------------------------------------------------
def match_mandatory_categories(text: str) -> frozenset[str]:
    """扫描文本，返回命中的必问点类别 ID 集合（纯函数）。

    基于 MANDATORY_QUESTION_RULES 的关键词子串匹配。
    P2 的 _scan_mandatory 内部调用此函数，P4 的 CustomerState 也复用此函数。
    """
    covered: set[str] = set()
    for category, keywords in MANDATORY_QUESTION_RULES.items():
        for kw in keywords:
            if kw in text:
                covered.add(category)
                break
    return frozenset(covered)


def _scan_mandatory(content: str, covered: set[str]) -> None:
    for category in match_mandatory_categories(content):
        covered.add(category)


def _scan_compliance(
    content: str,
    turn_index: int,
    agent_turn_n: int,
    hits: list[ComplianceHit],
) -> None:
    """对一条代理人发言扫描所有红线规则。每条规则在同一 content 内只记一次。"""
    for rule in COMPLIANCE_RULES:
        match_info = _first_rule_match(content, rule.keywords, rule.patterns)
        if match_info is None:
            continue
        matched_keyword, start, end = match_info
        excerpt = _make_excerpt(content, start, end)
        hits.append(
            ComplianceHit(
                turn_index=turn_index,
                agent_turn_number=agent_turn_n,
                excerpt=excerpt,
                rule_id=rule.rule_id,
                rule_label=rule.label,
                matched_keyword=matched_keyword,
            )
        )


def _first_rule_match(
    content: str,
    keywords: tuple[str, ...],
    patterns: tuple[str, ...],
) -> tuple[str, int, int] | None:
    """优先 keyword 命中（精确字符串），其次 pattern 命中。

    返回 (matched_text, start, end) 或 None。
    """
    earliest: tuple[str, int, int] | None = None
    for kw in keywords:
        idx = content.find(kw)
        if idx < 0:
            continue
        candidate = (kw, idx, idx + len(kw))
        if earliest is None or candidate[1] < earliest[1]:
            earliest = candidate
    if earliest is not None:
        return earliest

    for pat in patterns:
        m = re.search(pat, content)
        if m:
            return (m.group(0), m.start(), m.end())
    return None


def _make_excerpt(content: str, start: int, end: int) -> str:
    """取关键词上下文 ±N 字符，前后用省略号标识截断。"""
    left = max(0, start - _EXCERPT_CONTEXT_CHARS)
    right = min(len(content), end + _EXCERPT_CONTEXT_CHARS)
    snippet = content[left:right]
    if left > 0:
        snippet = "…" + snippet
    if right < len(content):
        snippet = snippet + "…"
    return snippet
