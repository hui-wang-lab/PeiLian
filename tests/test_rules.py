"""测试 P2 规则数据：必问点词库 + 合规红线词库。

P2 阶段：规则写死在 `peilian.rules`，不引入 yaml/json。
本文件只校验词库结构与契约，不调用 evaluator。
"""

from __future__ import annotations


EXPECTED_MANDATORY_CATEGORIES = {
    "family_structure",
    "occupation",
    "income",
    "existing_coverage",
    "future_planning",
    "health_status",
}

EXPECTED_COMPLIANCE_RULE_IDS = {
    "guarantee_return",
    "mislead_vs_deposit",
    "hide_exclusion",
    "hide_health_disclosure",
    "promise_underwriting",
    "misrepresent_as_financial_product",
}

# phase-2.md §6: guarantee_return 与 misrepresent_as_financial_product 至少含 patterns
EXPECTED_RULES_WITH_PATTERNS = {
    "guarantee_return",
    "misrepresent_as_financial_product",
}


def test_mandatory_categories_match_spec():
    """必问点含且仅含 6 个预期类别 id。"""
    from peilian.rules import MANDATORY_QUESTION_RULES

    assert set(MANDATORY_QUESTION_RULES.keys()) == EXPECTED_MANDATORY_CATEGORIES


def test_each_mandatory_category_has_enough_keywords():
    """每个必问点类别 keywords 非空且长度 >= 3。"""
    from peilian.rules import MANDATORY_QUESTION_RULES

    for category, keywords in MANDATORY_QUESTION_RULES.items():
        assert len(keywords) >= 3, (
            f"必问点类别 {category} 关键词数量={len(keywords)} 少于 3"
        )
        for kw in keywords:
            assert isinstance(kw, str) and kw, (
                f"必问点 {category} 含空关键词或非字符串：{kw!r}"
            )


def test_compliance_rules_match_spec():
    """合规红线含且仅含 6 个预期 rule_id（含 misrepresent_as_financial_product）。"""
    from peilian.rules import COMPLIANCE_RULES

    rule_ids = {rule.rule_id for rule in COMPLIANCE_RULES}
    assert rule_ids == EXPECTED_COMPLIANCE_RULE_IDS


def test_compliance_rules_have_keywords_and_some_have_patterns():
    """每条红线规则 keywords 非空；guarantee_return 与
    misrepresent_as_financial_product 至少含 patterns。"""
    from peilian.rules import COMPLIANCE_RULES

    rules_by_id = {rule.rule_id: rule for rule in COMPLIANCE_RULES}

    for rule in COMPLIANCE_RULES:
        assert rule.keywords, f"红线 {rule.rule_id} keywords 不能为空"
        assert isinstance(rule.label, str) and rule.label, (
            f"红线 {rule.rule_id} 标签为空"
        )

    for rule_id in EXPECTED_RULES_WITH_PATTERNS:
        assert rules_by_id[rule_id].patterns, (
            f"红线 {rule_id} 应至少含 1 条 patterns（phase-2.md §6 要求）"
        )


def test_mandatory_keywords_do_not_overlap_across_categories():
    """关键词在必问点类别间互斥（避免一句话同时算两个类别已覆盖）。"""
    from peilian.rules import MANDATORY_QUESTION_RULES

    seen: dict[str, str] = {}
    for category, keywords in MANDATORY_QUESTION_RULES.items():
        for kw in keywords:
            if kw in seen:
                raise AssertionError(
                    f"关键词 {kw!r} 同时出现在 {seen[kw]} 与 {category}"
                )
            seen[kw] = category
