"""P3 LLM-as-Judge 评估层。

架构边界：
- judge_agent / judge_customer 只消费 messages，不依赖 P2 EvaluationReport
- build_judge_result 顺序执行 P2 evaluate + P3 judge_agent + P3 judge_customer
- P3 只做诊断，不参与客户回复生成
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

from peilian.judge_prompts import (
    AGENT_JUDGE_SYSTEM_PROMPT,
    CUSTOMER_JUDGE_SYSTEM_PROMPT,
    render_messages_for_judge,
)
from peilian.observer import evaluate
from peilian.report import ComplianceHit, EvaluationReport
from peilian.rules import MANDATORY_CATEGORY_LABELS


AGENT_DIMENSIONS = (
    "professionalism",
    "empathy",
    "structure",
    "objection_handling",
)

_SEPARATOR = "═" * 39


class JudgeParseError(ValueError):
    """LLM judge 输出无法解析为约定 schema。"""

    def __init__(self, message: str, raw_response: str) -> None:
        super().__init__(message)
        self.raw_response = raw_response


@dataclass(frozen=True)
class DimensionScore:
    dimension: str
    label: str
    score: int
    reasoning: str


@dataclass(frozen=True)
class AgentJudgeReport:
    scores: tuple[DimensionScore, ...]
    overall_comment: str
    raw_response: str


@dataclass(frozen=True)
class Issue:
    turn_index: int
    agent_turn_number: int
    related_turn_indices: tuple[int, ...]
    excerpt: str
    violation_type: str
    protected_field: str
    reasoning: str


@dataclass(frozen=True)
class CustomerJudgeReport:
    premature_disclosure_issues: tuple[Issue, ...]
    inconsistency_issues: tuple[Issue, ...]
    overall_comment: str
    raw_response: str


@dataclass(frozen=True)
class JudgeResult:
    evaluation_report: EvaluationReport
    agent_report: AgentJudgeReport
    customer_report: CustomerJudgeReport


def judge_agent(
    messages: list[dict[str, Any]],
    *,
    client: Any | None = None,
    model: str | None = None,
) -> AgentJudgeReport:
    """用 LLM 评价代理人表现。"""
    client, model_name = _resolve_client_and_model(client, model)
    raw = _call_judge(
        client=client,
        model=model_name,
        system_prompt=AGENT_JUDGE_SYSTEM_PROMPT,
        messages=messages,
    )
    return parse_agent_report(raw)


def judge_customer(
    messages: list[dict[str, Any]],
    *,
    client: Any | None = None,
    model: str | None = None,
) -> CustomerJudgeReport:
    """用 LLM 诊断 AI 客户自身的越界泄露与一致性问题。"""
    client, model_name = _resolve_client_and_model(client, model)
    raw = _call_judge(
        client=client,
        model=model_name,
        system_prompt=CUSTOMER_JUDGE_SYSTEM_PROMPT,
        messages=messages,
    )
    return parse_customer_report(raw)


def build_judge_result(
    messages: list[dict[str, Any]],
    *,
    client: Any | None = None,
    model: str | None = None,
) -> JudgeResult:
    """顺序执行 evaluate + judge_agent + judge_customer 并合并。"""
    evaluation_report = evaluate(messages)
    agent_report = judge_agent(messages, client=client, model=model)
    customer_report = judge_customer(messages, client=client, model=model)
    return JudgeResult(
        evaluation_report=evaluation_report,
        agent_report=agent_report,
        customer_report=customer_report,
    )


def parse_agent_report(raw_response: str) -> AgentJudgeReport:
    data = _loads_object(raw_response)
    scores_raw = _require(data, "scores", list, raw_response)
    if len(scores_raw) != len(AGENT_DIMENSIONS):
        raise JudgeParseError("scores must contain exactly 4 dimensions", raw_response)

    scores: list[DimensionScore] = []
    seen: set[str] = set()
    for idx, item in enumerate(scores_raw):
        if not isinstance(item, dict):
            raise JudgeParseError(f"scores[{idx}] must be an object", raw_response)
        dimension = _require(item, "dimension", str, raw_response)
        if dimension not in AGENT_DIMENSIONS:
            raise JudgeParseError(f"unknown dimension: {dimension}", raw_response)
        if dimension in seen:
            raise JudgeParseError(f"duplicate dimension: {dimension}", raw_response)
        seen.add(dimension)

        score = _require(item, "score", int, raw_response)
        if score < 1 or score > 5:
            raise JudgeParseError("score must be an integer from 1 to 5", raw_response)

        scores.append(
            DimensionScore(
                dimension=dimension,
                label=_require(item, "label", str, raw_response),
                score=score,
                reasoning=_require(item, "reasoning", str, raw_response),
            )
        )

    missing = [dim for dim in AGENT_DIMENSIONS if dim not in seen]
    if missing:
        raise JudgeParseError(f"missing dimension: {missing[0]}", raw_response)

    scores_by_dimension = {score.dimension: score for score in scores}
    ordered_scores = tuple(scores_by_dimension[dim] for dim in AGENT_DIMENSIONS)
    return AgentJudgeReport(
        scores=ordered_scores,
        overall_comment=_require(data, "overall_comment", str, raw_response),
        raw_response=raw_response,
    )


def parse_customer_report(raw_response: str) -> CustomerJudgeReport:
    data = _loads_object(raw_response)
    premature = _parse_issues(
        _require(data, "premature_disclosure_issues", list, raw_response),
        raw_response,
        expected_violation_type="premature_disclosure",
    )
    inconsistent = _parse_issues(
        _require(data, "inconsistency_issues", list, raw_response),
        raw_response,
        expected_violation_type="inconsistency",
    )
    return CustomerJudgeReport(
        premature_disclosure_issues=premature,
        inconsistency_issues=inconsistent,
        overall_comment=_require(data, "overall_comment", str, raw_response),
        raw_response=raw_response,
    )


def render_judge_result(result: JudgeResult) -> str:
    """把 P2 + P3 综合结果渲染为人类可读文本。"""
    lines: list[str] = []
    lines.append(_SEPARATOR)
    lines.append("综合评估报告")
    lines.append(_SEPARATOR)
    lines.append("")

    lines.append("【一、规则层评估（P2）】")
    lines.extend(_render_p2_summary(result.evaluation_report))
    lines.append("")

    lines.append("【二、代理人评分（P3）】")
    for score in result.agent_report.scores:
        lines.append(
            f"  {score.score}/5  {score.label:<8}  {score.reasoning}"
        )
    lines.append(f"  综合评语：{result.agent_report.overall_comment}")
    lines.append("")

    lines.append("【三、AI 客户行为诊断（P3）】")
    customer_lines = _render_customer_report(result.customer_report)
    lines.extend(customer_lines)
    lines.append("")
    lines.append(_SEPARATOR)
    return "\n".join(lines)


def _resolve_client_and_model(client: Any | None, model: str | None) -> tuple[Any, str]:
    try:
        from peilian.config import load_settings

        settings = load_settings()
        configured_model = settings.model
    except ModuleNotFoundError:
        if client is None:
            raise
        settings = None
        configured_model = None
    model_name = model or configured_model or "gpt-4o-mini"
    if client is not None:
        return client, model_name

    if settings is None or not settings.api_key:
        raise RuntimeError(
            "未检测到 OPENAI_API_KEY；请在 .env 中配置 OPENAI_API_KEY / "
            "OPENAI_BASE_URL / OPENAI_MODEL 后重试。"
        )
    from openai import OpenAI

    return OpenAI(api_key=settings.api_key, base_url=settings.base_url), model_name


def _call_judge(
    *,
    client: Any,
    model: str,
    system_prompt: str,
    messages: list[dict[str, Any]],
) -> str:
    rendered_dialogue = render_messages_for_judge(messages)
    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": rendered_dialogue},
        ],
        temperature=0,
        response_format={"type": "json_object"},
    )
    return response.choices[0].message.content or ""


def _loads_object(raw_response: str) -> dict[str, Any]:
    try:
        data = json.loads(raw_response)
    except json.JSONDecodeError as e:
        raise JudgeParseError(f"invalid JSON: {e}", raw_response) from e
    if not isinstance(data, dict):
        raise JudgeParseError("JSON root must be an object", raw_response)
    return data


def _require(
    data: dict[str, Any],
    field: str,
    expected_type: type,
    raw_response: str,
) -> Any:
    if field not in data:
        raise JudgeParseError(f"missing field: {field}", raw_response)
    value = data[field]
    if not isinstance(value, expected_type):
        raise JudgeParseError(
            f"field {field} must be {expected_type.__name__}",
            raw_response,
        )
    return value


def _parse_issues(
    items: list[Any],
    raw_response: str,
    *,
    expected_violation_type: str,
) -> tuple[Issue, ...]:
    parsed: list[Issue] = []
    for idx, item in enumerate(items):
        if not isinstance(item, dict):
            raise JudgeParseError(f"issues[{idx}] must be an object", raw_response)

        violation_type = _require(item, "violation_type", str, raw_response)
        if violation_type != expected_violation_type:
            raise JudgeParseError(
                f"violation_type must be {expected_violation_type}",
                raw_response,
            )

        related = _require(item, "related_turn_indices", list, raw_response)
        if not all(isinstance(x, int) for x in related):
            raise JudgeParseError("related_turn_indices must contain integers", raw_response)

        parsed.append(
            Issue(
                turn_index=_require(item, "turn_index", int, raw_response),
                agent_turn_number=_require(item, "agent_turn_number", int, raw_response),
                related_turn_indices=tuple(related),
                excerpt=_require(item, "excerpt", str, raw_response),
                violation_type=violation_type,
                protected_field=_require(item, "protected_field", str, raw_response),
                reasoning=_require(item, "reasoning", str, raw_response),
            )
        )
    return tuple(parsed)


def _render_p2_summary(report: EvaluationReport) -> list[str]:
    """把 P2 EvaluationReport 渲染成不带外层装饰的紧凑摘要。

    与 peilian.report.render_report 不同，这里不输出 ═══ 分隔线与
    「评估报告」二级标题，便于嵌入 P3 综合报告的「【一、…】」段下。
    """
    out: list[str] = []
    covered_n = len(report.covered_categories)
    total = report.total_categories
    rate = (covered_n / total * 100.0) if total else 0.0
    out.append(f"  必问点覆盖率：{covered_n} / {total}  ({rate:.1f}%)")

    covered_str = (
        ", ".join(_label_category(cid) for cid in report.covered_categories)
        if report.covered_categories
        else "（无）"
    )
    missed_str = (
        ", ".join(_label_category(cid) for cid in report.missed_categories)
        if report.missed_categories
        else "（无）"
    )
    out.append(f"    ✓ 已覆盖：{covered_str}")
    out.append(f"    ✗ 漏问：  {missed_str}")

    if not report.compliance_hits:
        out.append("  合规红线扫描：未发现违规")
        return out

    groups: dict[tuple[int, int], list[ComplianceHit]] = {}
    for hit in report.compliance_hits:
        key = (hit.turn_index, hit.agent_turn_number)
        groups.setdefault(key, []).append(hit)

    out.append(f"  合规红线扫描：发现 {len(groups)} 处违规")
    for (_idx, agent_n), hits in groups.items():
        out.append(f"    ⚠ 第 {agent_n} 轮 [代理人]")
        out.append(f"       原话：{hits[0].excerpt}")
        out.append("       命中规则：")
        for hit in hits:
            out.append(
                f"         - {hit.rule_label}（关键词「{hit.matched_keyword}」）"
            )
    return out


def _label_category(cid: str) -> str:
    zh = MANDATORY_CATEGORY_LABELS.get(cid)
    return f"{cid} ({zh})" if zh else cid


def _render_customer_report(report: CustomerJudgeReport) -> list[str]:
    issue_count = (
        len(report.premature_disclosure_issues)
        + len(report.inconsistency_issues)
    )
    if issue_count == 0:
        return ["  未发现客户行为异常", f"  综合评语：{report.overall_comment}"]

    out: list[str] = []
    out.append(f"  越界泄露：发现 {len(report.premature_disclosure_issues)} 处")
    for issue in report.premature_disclosure_issues:
        out.extend(_render_issue(issue))
    out.append(f"  一致性问题：发现 {len(report.inconsistency_issues)} 处")
    for issue in report.inconsistency_issues:
        out.extend(_render_issue(issue))
    out.append(f"  综合评语：{report.overall_comment}")
    return out


def _render_issue(issue: Issue) -> list[str]:
    related = (
        f"；相关轮次：{', '.join(str(i) for i in issue.related_turn_indices)}"
        if issue.related_turn_indices
        else ""
    )
    return [
        f"    - 第 {issue.turn_index} 位消息 [{issue.protected_field}]{related}",
        f"      原话：{issue.excerpt}",
        f"      理由：{issue.reasoning}",
    ]
