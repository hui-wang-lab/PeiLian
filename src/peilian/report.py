"""P2 评估报告：EvaluationReport / ComplianceHit + render_report()。

来源：docs/phases/phase-2.md §3
- 两个 dataclass 都 frozen，便于跨调用安全传递与做缓存
- render_report() 输出符合 phase-2.md 「Demo 命令」一节预期格式
- 同一轮多条 rule 命中时，渲染按 turn 分组（demo 中「1 处违规」= 1 个轮次）

# P3: LLM judge could augment this report later (phase-2.md §8)
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterable

from peilian.rules import (
    MANDATORY_CATEGORY_LABELS,
    MANDATORY_QUESTION_RULES,
)


@dataclass(frozen=True)
class ComplianceHit:
    """单条合规红线命中。"""

    turn_index: int          # 在 messages 列表中的索引（含 system，从 0 起）
    agent_turn_number: int   # 代理人第几轮发言（从 1 起，人类可读）
    excerpt: str             # 命中片段（关键词 ±10 字符上下文）
    rule_id: str
    rule_label: str
    matched_keyword: str     # 命中的具体关键词或 pattern 匹配片段


@dataclass(frozen=True)
class EvaluationReport:
    """单次对话的规则层评估结果。"""

    total_categories: int                 # 必问点总类数（= len(MANDATORY_QUESTION_RULES)）
    covered_categories: tuple[str, ...]   # 已覆盖的类别 id（按 rules 中顺序）
    missed_categories: tuple[str, ...]    # 漏问的类别 id
    compliance_hits: tuple[ComplianceHit, ...]


# ---------------------------------------------------------------------------
# 渲染
# ---------------------------------------------------------------------------
_SEPARATOR = "═" * 39


def render_report(report: EvaluationReport) -> str:
    """把 EvaluationReport 渲染为人类可读的多段文本。"""
    lines: list[str] = []
    lines.append(_SEPARATOR)
    lines.append("评估报告")
    lines.append(_SEPARATOR)
    lines.append("")

    lines.extend(_render_mandatory_section(report))
    lines.append("")
    lines.extend(_render_compliance_section(report))

    lines.append("")
    lines.append(_SEPARATOR)
    return "\n".join(lines)


def _render_mandatory_section(report: EvaluationReport) -> list[str]:
    covered_n = len(report.covered_categories)
    total = report.total_categories
    rate = (covered_n / total * 100.0) if total else 0.0

    out = [f"【必问点覆盖率】{covered_n} / {total}  ({rate:.1f}%)"]

    covered_str = (
        ", ".join(_label_categories(report.covered_categories))
        if report.covered_categories
        else "（无）"
    )
    missed_str = (
        ", ".join(_label_categories(report.missed_categories))
        if report.missed_categories
        else "（无）"
    )
    out.append(f"  ✓ 已覆盖：{covered_str}")
    out.append(f"  ✗ 漏问：  {missed_str}")
    return out


def _render_compliance_section(report: EvaluationReport) -> list[str]:
    if not report.compliance_hits:
        return ["【合规红线扫描】未发现违规"]

    # 按 (turn_index, agent_turn_number) 分组，每个 turn 算 1 处违规
    groups: dict[tuple[int, int], list[ComplianceHit]] = {}
    for hit in report.compliance_hits:
        key = (hit.turn_index, hit.agent_turn_number)
        groups.setdefault(key, []).append(hit)

    out = [f"【合规红线扫描】发现 {len(groups)} 处违规"]

    # 保持出现顺序（dict 在 Python 3.7+ 保留插入顺序）
    for (_turn_idx, agent_turn_n), hits in groups.items():
        out.append(f"  ⚠ 第 {agent_turn_n} 轮 [代理人]")
        # 同一 turn 下的所有 hit 共享同一段 excerpt（取第一条即可）
        excerpt = hits[0].excerpt
        out.append(f"     原话：{excerpt}")
        out.append("     命中规则：")
        for hit in hits:
            out.append(
                f"       - {hit.rule_label}（关键词「{hit.matched_keyword}」）"
            )
    return out


def _label_categories(category_ids: Iterable[str]) -> list[str]:
    """把类别 id 翻成 'family_structure (家庭结构)' 形式，方便人读。

    若该 id 没有中文标签（不该出现），退化为原 id。
    """
    labeled: list[str] = []
    for cid in category_ids:
        zh = MANDATORY_CATEGORY_LABELS.get(cid)
        labeled.append(f"{cid} ({zh})" if zh else cid)
    return labeled
