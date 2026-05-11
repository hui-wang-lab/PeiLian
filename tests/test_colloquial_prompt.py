"""P5.1 口语化片段渲染测试。"""

from __future__ import annotations

from dataclasses import replace

import pytest

from peilian.persona import SAMPLE_PERSONA, Persona
from peilian.prompts import _render_colloquial_block, render_customer_system_prompt
from peilian.scenario import SAMPLE_SCENARIO


def test_colloquial_block_off_is_empty():
    assert _render_colloquial_block("off") == ""


def test_colloquial_block_mild_has_marker():
    block = _render_colloquial_block("mild")
    assert "mild" in block
    assert "微信" in block or "语气词" in block


def test_colloquial_block_heavy_contains_homophone_mention():
    block = _render_colloquial_block("heavy")
    assert "heavy" in block
    assert "同音字" in block


def test_unknown_style_falls_back_to_empty():
    assert _render_colloquial_block("nonsense") == ""


def test_off_prompt_byte_identical_to_pre_p5_1():
    """off 风格下，新增字段不应在最终 prompt 中留下任何痕迹（向后兼容）。"""
    persona = replace(SAMPLE_PERSONA, colloquial_style="off")
    output = render_customer_system_prompt(persona, SAMPLE_SCENARIO)
    assert "口语化风格" not in output
    assert "mild" not in output
    assert "heavy" not in output


def test_mild_prompt_contains_colloquial_block():
    persona = replace(SAMPLE_PERSONA, colloquial_style="mild")
    output = render_customer_system_prompt(persona, SAMPLE_SCENARIO)
    assert "【口语化风格 — mild】" in output


def test_heavy_prompt_contains_colloquial_block():
    persona = replace(SAMPLE_PERSONA, colloquial_style="heavy")
    output = render_customer_system_prompt(persona, SAMPLE_SCENARIO)
    assert "【口语化风格 — heavy】" in output


def test_persona_rejects_invalid_colloquial_style():
    with pytest.raises(ValueError):
        Persona(
            name="测试",
            age=30,
            occupation="x",
            family="x",
            income_level="x",
            existing_coverage=(),
            pain_points=(),
            hidden_concerns=(),
            persistence=0.5,
            expressiveness=0.5,
            initial_mood="x",
            colloquial_style="bogus",
        )


def test_passive_response_constraints_preserved_in_all_styles():
    """所有口语化档下，被动反应红线必须保留。"""
    for style in ("off", "mild", "heavy"):
        persona = replace(SAMPLE_PERSONA, colloquial_style=style)
        output = render_customer_system_prompt(persona, SAMPLE_SCENARIO)
        assert "不主动" in output
        assert "禁止使用括号描述动作" in output
