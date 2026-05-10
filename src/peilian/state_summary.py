"""P4 State Summary：CustomerState → LLM 可读摘要（≤400 字、被动语态）。"""

from __future__ import annotations

from peilian.rules import MANDATORY_CATEGORY_LABELS, MANDATORY_QUESTION_RULES

# ---------------------------------------------------------------------------
# 常量
# ---------------------------------------------------------------------------

_MAX_LENGTH = 400

FORBIDDEN_PHRASES = (
    "可以披露",
    "现在可以说",
    "主动表达",
    "主动说出来",
    "现在可以表达",
    "可以主动",
    "请主动",
    "不妨主动",
)

# 隐藏关切阶段 → 被动语态描述
_STAGE_DESCRIPTIONS = {
    "untouched": "尚未被触及；不要主动提及",
    "triggered": "已被触及；如代理人再次问及，可简短回应",
    "hinted": "已被触及并暗示过；如代理人再次触及，可保持模糊，不要完整说出来",
    "expressed": "已表达过；如被追问，可适当补充细节",
}

# 信任度区间 → 描述
_TRUST_DESCRIPTIONS = [
    (0.3, "戒备心强"),
    (0.5, "偏低，保持戒备语气"),
    (0.7, "一般，适度开放"),
    (1.1, "较高，态度软化"),
]

# 耐心值区间 → 描述
_PATIENCE_DESCRIPTIONS = [
    (0.3, "快耗尽，注意节奏"),
    (0.6, "中等"),
    (1.1, "充足"),
]


def _describe_value(value: float, descriptions: list[tuple[float, str]]) -> str:
    for threshold, desc in descriptions:
        if value < threshold:
            return desc
    return descriptions[-1][1]


def render_state_summary(state, persona, persona_meta) -> str:
    """生成注入到 system prompt 的文本片段。

    长度约束：返回字符串 len() ≤ 400 字。
    超长时截断 untouched 的隐藏关切，末尾加省略提示。
    """

    # 字段标签映射
    field_labels = MANDATORY_CATEGORY_LABELS
    all_field_ids = set(MANDATORY_QUESTION_RULES.keys())
    disclosed = state.disclosed_fields
    undisclosed = all_field_ids - disclosed

    # 已披露字段
    if disclosed:
        disclosed_labels = [field_labels.get(f, f) for f in sorted(disclosed)]
        disclosed_str = "、".join(disclosed_labels)
    else:
        disclosed_str = "（无）"

    # 未披露字段
    if undisclosed:
        undisclosed_labels = [field_labels.get(f, f) for f in sorted(undisclosed)]
        undisclosed_str = "、".join(undisclosed_labels)
    else:
        undisclosed_str = "（无）"

    # 隐藏关切
    concern_lines = []
    for hc in persona_meta.hidden_concerns:
        key = hc["key"]
        label = hc["label"]
        stage = state.stage_of(key)
        desc = _STAGE_DESCRIPTIONS.get(stage, "状态未知")
        concern_lines.append(f"  - {label}：{desc}")

    # 信任度 / 耐心值
    trust_desc = _describe_value(state.trust, _TRUST_DESCRIPTIONS)
    patience_desc = _describe_value(state.patience, _PATIENCE_DESCRIPTIONS)

    # 组装
    parts = [
        "【本轮对话状态】",
        f"已被问到并披露：{disclosed_str}",
        f"尚未被问到（不要主动提）：{undisclosed_str}",
        "隐藏关切：",
    ]
    parts.extend(concern_lines)
    parts.append(f"当前信任度：{state.trust:.2f}（{trust_desc}）")
    parts.append(f"当前耐心值：{state.patience:.2f}（{patience_desc}）")

    summary = "\n".join(parts)

    # 注意：禁用词替换必须放在长度兜底之前。
    # 替换文本"（已过滤）"长度通常大于禁用词本身，若放在截断之后可能再次撑爆 _MAX_LENGTH。
    summary = _enforce_forbidden_phrases(summary)

    # 长度保护：截断 untouched 的隐藏关切
    if len(summary) > _MAX_LENGTH:
        # 只保留非 untouched 的隐藏关切
        active_concerns = []
        for hc in persona_meta.hidden_concerns:
            stage = state.stage_of(hc["key"])
            if stage != "untouched":
                active_concerns.append(
                    f"  - {hc['label']}：{_STAGE_DESCRIPTIONS.get(stage, '')}"
                )

        parts_trimmed = [
            "【本轮对话状态】",
            f"已被问到并披露：{disclosed_str}",
            f"尚未被问到（不要主动提）：{undisclosed_str}",
            "隐藏关切：",
        ]
        parts_trimmed.extend(active_concerns)
        parts_trimmed.append(f"当前信任度：{state.trust:.2f}（{trust_desc}）")
        parts_trimmed.append(f"当前耐心值：{state.patience:.2f}（{patience_desc}）")

        summary = _enforce_forbidden_phrases("\n".join(parts_trimmed))
        if len(summary) > _MAX_LENGTH:
            summary = summary[: _MAX_LENGTH - 4] + " ..."

    return summary


def _enforce_forbidden_phrases(text: str) -> str:
    """禁用词守护：替换为占位符。"""
    for phrase in FORBIDDEN_PHRASES:
        if phrase in text:
            text = text.replace(phrase, "（已过滤）")
    return text
