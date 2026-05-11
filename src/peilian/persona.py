from __future__ import annotations

from dataclasses import dataclass

VALID_COLLOQUIAL_STYLES = frozenset({"off", "mild", "heavy"})


@dataclass(frozen=True)
class Persona:
    name: str
    age: int
    occupation: str
    family: str
    income_level: str
    existing_coverage: tuple[str, ...]
    pain_points: tuple[str, ...]
    hidden_concerns: tuple[str, ...]
    persistence: float
    expressiveness: float
    initial_mood: str
    colloquial_style: str = "off"

    def __post_init__(self) -> None:
        if not 0.0 <= self.persistence <= 1.0:
            raise ValueError(
                f"persistence must be in [0, 1], got {self.persistence!r}"
            )
        if not 0.0 <= self.expressiveness <= 1.0:
            raise ValueError(
                f"expressiveness must be in [0, 1], got {self.expressiveness!r}"
            )
        if self.colloquial_style not in VALID_COLLOQUIAL_STYLES:
            raise ValueError(
                f"colloquial_style must be one of "
                f"{sorted(VALID_COLLOQUIAL_STYLES)}, "
                f"got {self.colloquial_style!r}"
            )


SAMPLE_PERSONA = Persona(
    name="王先生",
    age=35,
    occupation="IT 公司中层",
    family="已婚，一个 5 岁孩子",
    income_level="中产",
    existing_coverage=("百万医疗险（公司团险）",),
    pain_points=(
        "对保险了解不深",
        "时间紧、希望直接说重点",
    ),
    hidden_concerns=(
        "担心保费太贵影响房贷",
        "不希望做太详细的健康告知",
    ),
    persistence=0.7,
    expressiveness=0.5,
    initial_mood="略微戒备但礼貌",
    colloquial_style="off",
)
