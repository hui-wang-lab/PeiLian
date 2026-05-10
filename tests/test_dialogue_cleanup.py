from __future__ import annotations


def test_strip_stage_directions_removes_leading_chinese_parentheses():
    from peilian.dialogue import strip_stage_directions

    assert strip_stage_directions("（微微皱眉）这个我得再想想。") == "这个我得再想想。"


def test_strip_stage_directions_removes_multiple_leading_directions():
    from peilian.dialogue import strip_stage_directions

    text = "（抬眼看了看）（靠在椅背上，略带审视地看了看对方）您先说说看。"
    assert strip_stage_directions(text) == "您先说说看。"


def test_strip_stage_directions_removes_leading_ascii_parentheses():
    from peilian.dialogue import strip_stage_directions

    assert strip_stage_directions("(稍作停顿)我先听听看。") == "我先听听看。"


def test_strip_stage_directions_keeps_non_leading_parentheses():
    from peilian.dialogue import strip_stage_directions

    text = "我想了解下重疾险（尤其是保费）大概怎么配置。"
    assert strip_stage_directions(text) == text
