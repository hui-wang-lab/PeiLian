"""测试 Persona dataclass 与 SAMPLE_PERSONA 常量。

P1 阶段：测试不依赖真实 LLM，只覆盖 persona 加载与字段范围。
"""

from __future__ import annotations

import pytest


def test_sample_persona_can_be_imported():
    from peilian.persona import SAMPLE_PERSONA

    assert SAMPLE_PERSONA is not None


def test_persona_is_frozen():
    from peilian.persona import SAMPLE_PERSONA

    with pytest.raises(Exception):
        SAMPLE_PERSONA.name = "李先生"  # type: ignore[misc]


def test_persistence_in_range():
    from peilian.persona import SAMPLE_PERSONA

    assert 0.0 <= SAMPLE_PERSONA.persistence <= 1.0


def test_expressiveness_in_range():
    from peilian.persona import SAMPLE_PERSONA

    assert 0.0 <= SAMPLE_PERSONA.expressiveness <= 1.0


def test_collection_fields_are_tuples():
    from peilian.persona import SAMPLE_PERSONA

    assert isinstance(SAMPLE_PERSONA.existing_coverage, tuple)
    assert isinstance(SAMPLE_PERSONA.pain_points, tuple)
    assert isinstance(SAMPLE_PERSONA.hidden_concerns, tuple)


def test_invalid_persistence_raises():
    from peilian.persona import Persona

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
            persistence=2.0,
            expressiveness=0.5,
            initial_mood="x",
        )


def test_invalid_expressiveness_raises():
    from peilian.persona import Persona

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
            expressiveness=-0.1,
            initial_mood="x",
        )
