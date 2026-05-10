"""P4 CustomerState：frozen dataclass + update_state 纯函数。"""

from __future__ import annotations

import re
from dataclasses import dataclass

from peilian.observer import match_mandatory_categories
from peilian.rules import COMPLIANCE_RULES, MANDATORY_QUESTION_RULES

# ---------------------------------------------------------------------------
# 常量：P4 具体点名关键词映射
# 用于区分"泛泛提问"与"具体点名"
# ---------------------------------------------------------------------------

_SPECIFIC_ASK_KEYWORDS: dict[str, tuple[str, ...]] = {
    "family_structure": (
        "几口人", "几个孩子", "家里有几口", "孩子多大", "结婚了吗",
        "有孩子吗", "父母和", "配偶", "家里几口", "太太", "爱人",
    ),
    "occupation": (
        "做什么的", "什么工作", "什么行业", "在哪上班", "什么职位",
        "负责什么", "在哪个单位", "做什么工作", "从事什么",
    ),
    "income": (
        "收入多少", "年收入", "月薪", "大概赚", "收入水平",
        "家庭收入", "月收入", "薪资",
    ),
    "existing_coverage": (
        "买过什么保险", "有没有保单", "有商业保险吗", "买过重疾险吗",
        "有没有医疗险", "团险有吗", "已有保障", "有保险吗", "买了什么保险",
    ),
    "future_planning": (
        "养老打算", "孩子教育规划", "以后打算", "退休计划",
        "未来有什么规划", "准备怎么", "以后有什么打算",
    ),
    "health_status": (
        "身体怎么样", "健康状况", "做过体检吗", "住过院吗",
        "有病史吗", "动过手术吗", "身体如何", "健康方面",
    ),
}

# 模糊表达词：triggered → hinted
_VAGUE_EXPRESSION_WORDS = (
    "有点", "担心", "还在想", "考虑", "顾虑", "纠结", "犹豫",
    "不太好说", "看情况", "再说吧", "再看看",
)

# 明确表达词：hinted → expressed
_EXPLICIT_EXPRESSION_WORDS = (
    "我担心", "我怕", "我就是", "我最在意", "我主要",
    "其实我", "说实话我", "坦白说", "我顾虑", "我害怕",
)


@dataclass(frozen=True)
class CustomerState:
    """运行时客户状态（不可变）。"""

    disclosed_fields: frozenset[str] = frozenset()
    asked_fields_this_turn: frozenset[str] = frozenset()
    hidden_concern_stage: frozenset[tuple[str, str]] = frozenset()
    trust: float = 0.5
    patience: float = 1.0
    turn_count: int = 0

    @classmethod
    def initial(cls, persona, persona_meta) -> "CustomerState":
        """从 persona + 工厂索引构造初始状态。

        trust = clip(0.6 - 0.4 * persistence, 0.1, 0.9)
        patience = 1.0
        """
        trust = max(0.1, min(0.9, 0.6 - 0.4 * persona.persistence))

        hidden_concerns = frozenset(
            (hc["key"], hc["initial_stage"])
            for hc in persona_meta.hidden_concerns
        )

        return cls(
            disclosed_fields=frozenset(),
            asked_fields_this_turn=frozenset(),
            hidden_concern_stage=hidden_concerns,
            trust=trust,
            patience=1.0,
            turn_count=0,
        )

    def stage_of(self, concern_key: str) -> str:
        """便捷读取某 hidden_concern 的当前 stage。"""
        for key, stage in self.hidden_concern_stage:
            if key == concern_key:
                return stage
        return "untouched"


def _clip(value: float, lo: float = 0.0, hi: float = 1.0) -> float:
    return max(lo, min(hi, value))


def filter_specific_asked_fields(
    agent_message: str,
    coarse_fields: frozenset[str] | None = None,
) -> frozenset[str]:
    """从代理人的发言中识别「具体点名」的字段。

    泛泛提问（如「想了解你的情况」）不匹配任何具体关键词 → 空集。
    具体点名（如「您家里几口人？」）匹配 → 保留该 category。

    P4 的具体点名词表比 P2 粗粒度词库更细，匹配直接面向 agent_message
    原文而非 coarse_fields 子集——「结婚了吗」「有病史吗」等明确提问即使
    未命中 P2 粗词也应被视为具体点名。coarse_fields 保留为调用方可选的
    粗粒度提示，但函数内部不依赖其截断。
    """
    asked: set[str] = set()
    for category, specific_keywords in _SPECIFIC_ASK_KEYWORDS.items():
        for kw in specific_keywords:
            if kw in agent_message:
                asked.add(category)
                break
    return frozenset(asked)


def _detect_fields_in_text(text: str) -> frozenset[str]:
    """检测文本中提及的字段（基于关键词匹配）。"""
    return match_mandatory_categories(text)


_EVASIVE_ANSWER_WORDS = (
    "不想说",
    "不方便",
    "先不说",
    "暂时不说",
    "以后再说",
    "回头再说",
    "不好说",
    "不太好说",
    "你具体指什么",
    "具体哪方面",
)


_FIELD_ANSWER_KEYWORDS: dict[str, tuple[str, ...]] = {
    "family_structure": (
        "口",
        "孩子",
        "小孩",
        "儿子",
        "女儿",
        "已婚",
        "未婚",
        "结婚",
        "太太",
        "爱人",
        "父母",
        "一家",
        "三口",
        "两口",
    ),
    "occupation": (
        "公司",
        "单位",
        "上班",
        "工作",
        "行业",
        "负责",
        "做",
        "老板",
        "经理",
        "财务",
        "销售",
        "产品",
    ),
    "income": (
        "收入",
        "月薪",
        "年薪",
        "工资",
        "薪资",
        "万",
        "千",
        "元",
        "左右",
    ),
    "existing_coverage": (
        "社保",
        "保险",
        "保单",
        "保障",
        "医疗险",
        "重疾",
        "意外险",
        "团险",
        "买过",
        "没买",
        "没有",
    ),
    "future_planning": (
        "养老",
        "退休",
        "孩子教育",
        "教育",
        "规划",
        "打算",
        "以后",
        "未来",
        "还没想",
        "再看看",
    ),
    "health_status": (
        "身体",
        "健康",
        "体检",
        "病",
        "病史",
        "住院",
        "手术",
        "慢病",
        "没住过",
        "没有",
    ),
}


def _looks_like_field_answer(field: str, text: str) -> bool:
    """判断客户回复是否像是在回答某个已点名字段。

    客户常用短答不一定复述 P2 关键词，例如"三口，孩子 5 岁"或"30 万左右"。
    这里只在字段已经被代理人具体点名后使用，避免主动泄露被误记。
    """
    normalized = text.strip()
    if not normalized:
        return False

    if any(word in normalized for word in _EVASIVE_ANSWER_WORDS):
        return False

    if field in _detect_fields_in_text(normalized):
        return True

    if any(word in normalized for word in _FIELD_ANSWER_KEYWORDS.get(field, ())):
        return True

    if field == "income" and re.search(r"\d+(\.\d+)?\s*(万|千|元|k|K|w|W)", normalized):
        return True

    if field == "family_structure" and re.search(r"[一二两三四五六七八九十\d]\s*(口|个)", normalized):
        return True

    return False


def _has_compliance_violation(text: str) -> bool:
    """检测文本是否出现合规红线词。"""
    for rule in COMPLIANCE_RULES:
        for kw in rule.keywords:
            if kw in text:
                return True
        for pat in rule.patterns:
            if re.search(pat, text):
                return True
    return False


def update_state(
    state: CustomerState,
    agent_message: str,
    customer_response: str,
    *,
    persona,
    persona_meta,
) -> CustomerState:
    """根据代理人本轮发言 + 客户回复，返回新的 CustomerState（纯函数）。"""

    # Step 1: 确定本轮具体点名的字段
    coarse = match_mandatory_categories(agent_message)
    asked = filter_specific_asked_fields(agent_message, coarse)

    # Step 2: 已披露字段增量 = 本轮被具体点名且客户自然作答的字段
    answered_fields = frozenset(
        field for field in asked if _looks_like_field_answer(field, customer_response)
    )
    new_disclosed = state.disclosed_fields | answered_fields

    # Step 3: hidden_concern 迁移（单轮最多一档）
    new_concerns = set(state.hidden_concern_stage)

    for hc in persona_meta.hidden_concerns:
        key = hc["key"]
        current_stage = state.stage_of(key)
        keywords = hc["keywords"]

        # 检查 agent_message 是否触及该关切关键词
        agent_triggered = any(kw in agent_message for kw in keywords)

        if current_stage == "untouched":
            # untouched → triggered：需要 agent_message 触及关键词
            if agent_triggered:
                new_concerns.discard((key, "untouched"))
                new_concerns.add((key, "triggered"))
        elif current_stage == "triggered":
            # triggered → hinted：需要 customer_response 含模糊表达词
            if any(vw in customer_response for vw in _VAGUE_EXPRESSION_WORDS):
                new_concerns.discard((key, "triggered"))
                new_concerns.add((key, "hinted"))
        elif current_stage == "hinted":
            # hinted → expressed：需要 customer_response 含明确表达词
            if any(ew in customer_response for ew in _EXPLICIT_EXPRESSION_WORDS):
                new_concerns.discard((key, "hinted"))
                new_concerns.add((key, "expressed"))

    # Step 4: 信任度调整
    new_trust = state.trust
    mandatory_hits = match_mandatory_categories(agent_message)
    if mandatory_hits:
        new_trust += 0.02
    if _has_compliance_violation(agent_message):
        new_trust -= 0.10
    new_trust = _clip(new_trust, 0.0, 1.0)

    # Step 5: 耐心值调整（turn_count=0 时不扣减，首轮无提问不视为无效）
    new_patience = state.patience
    if not asked and state.turn_count > 0:
        new_patience -= 0.03
    elif asked:
        new_patience += 0.01
    new_patience = _clip(new_patience, 0.0, 1.0)

    # Step 6: turn_count + 1
    return CustomerState(
        disclosed_fields=new_disclosed,
        asked_fields_this_turn=asked,
        hidden_concern_stage=frozenset(new_concerns),
        trust=new_trust,
        patience=new_patience,
        turn_count=state.turn_count + 1,
    )
