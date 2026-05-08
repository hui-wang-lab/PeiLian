"""P2 规则数据：必问点词库 + 合规红线词库。

来源：docs/phases/phase-2.md §1 / §2
- 写死在 Python 字面量，不引入 yaml/json（P4 起再考虑配置化）
- 关键词策略：方案 A，只放最高频核心词；假阴性由 P3 LLM judge 兜底
- 关键词在必问点类别间互斥（test_rules 守护）
"""

from __future__ import annotations

from dataclasses import dataclass


# ---------------------------------------------------------------------------
# 必问点（KYC 阶段代理人应覆盖的话题）
# ---------------------------------------------------------------------------
# 结构：dict[category_id, tuple[keyword, ...]]
# 命中规则：代理人发言中出现任一关键词，即视为该类别已覆盖
#
# 边界（phase-2.md §1 / Q1）：
# - income 仅作为「支付能力 / 现金流」的最小代理变量，不展开 FNA 子项
# - 资产负债 / 现金流结构 / 预算区间等更细粒度 FNA 不独立成类（留 P4）
# - 「保险态度 / 抗拒度」属销售过程观察项，不进 P2 必问点
MANDATORY_QUESTION_RULES: dict[str, tuple[str, ...]] = {
    "family_structure": (
        "几口人",
        "几个孩子",
        "家里有",
        "父母",
        "太太",
        "丈夫",
        "妻子",
        "老婆",
        "老公",
        "孩子多大",
        "家庭情况",
    ),
    "occupation": (
        "工作",
        "职业",
        "行业",
        "单位",
        "公司是做",
        "您是做什么的",
    ),
    "income": (
        "收入",
        "年收入",
        "月薪",
        "年薪",
        "家庭年收入",
        "赚",
    ),
    "existing_coverage": (
        "保险",
        "保单",
        "保障",
        "医疗险",
        "重疾",
        "意外险",
        "团险",
        "公司团",
    ),
    "future_planning": (
        "规划",
        "打算",
        "未来",
        "以后",
        "养老",
        "退休",
        "孩子教育",
        "子女教育",
    ),
    "health_status": (
        "身体",
        "健康",
        "体检",
        "手术",
        "住院",
        "家族病史",
        "慢病",
    ),
}


# 必问点类别的中文标签（render_report 用）
MANDATORY_CATEGORY_LABELS: dict[str, str] = {
    "family_structure": "家庭结构",
    "occupation": "职业行业",
    "income": "收入水平",
    "existing_coverage": "已有保障",
    "future_planning": "未来规划",
    "health_status": "健康情况",
}


# ---------------------------------------------------------------------------
# 合规红线（代理人发言中触碰即违规）
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class ComplianceRule:
    """单条合规红线规则。

    keywords：精确字符串，任一出现即命中
    patterns：正则字符串（可空），任一匹配即命中
    keywords 与 patterns 在同一规则下命中只算一次（observer 层去重）
    """

    rule_id: str
    label: str
    keywords: tuple[str, ...]
    patterns: tuple[str, ...] = ()


COMPLIANCE_RULES: tuple[ComplianceRule, ...] = (
    ComplianceRule(
        rule_id="guarantee_return",
        label="保证收益",
        keywords=(
            "保证收益",
            "稳赚不赔",
            "零风险",
            "肯定不亏",
            "保本保息",
        ),
        patterns=(
            r"保证.{0,3}收益",
            r"保本.{0,3}息",
        ),
    ),
    ComplianceRule(
        rule_id="mislead_vs_deposit",
        label="与存款/国债误导对比",
        keywords=(
            "比存款",
            "比银行",
            "跟存款一样",
            "比国债",
            "跟定期一样",
        ),
    ),
    ComplianceRule(
        rule_id="hide_exclusion",
        label="隐瞒免责条款",
        keywords=(
            "不用看免责",
            "免责不重要",
            "免责条款没事",
            "不会拒赔",
        ),
    ),
    ComplianceRule(
        rule_id="hide_health_disclosure",
        label="隐瞒 / 代填健康告知",
        keywords=(
            "健告随便填",
            "不用如实告知",
            "告知不重要",
            "不报也行",
            "不告知没事",
            "我帮您填",
            "这项填否",
            "这个不用写",
            "病史不用写",
            "我来处理健告",
        ),
    ),
    ComplianceRule(
        rule_id="promise_underwriting",
        label="承诺核保 / 理赔",
        keywords=(
            "核保肯定过",
            "肯定能买",
            "理赔包过",
            "保证赔付",
            "百分百赔",
        ),
    ),
    ComplianceRule(
        rule_id="misrepresent_as_financial_product",
        label="混淆保险与理财",
        keywords=(
            "就是理财",
            "当理财买",
            "和理财一样",
            "主要看收益",
        ),
        patterns=(
            r"保险.{0,6}理财",
            r"当.{0,3}理财.{0,3}买",
            r"保险.{0,6}理财.{0,6}产品",
        ),
    ),
)
