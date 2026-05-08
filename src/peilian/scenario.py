from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Scenario:
    context: str
    constraints: str


SAMPLE_SCENARIO = Scenario(
    context=(
        "你和这位代理人是初次见面，地点在你的办公室。"
        "你对保险了解不深，但同事最近买了一份重疾险，让你有点好奇，"
        "所以你愿意听听看。"
    ),
    constraints=(
        "你只能预留约 20 分钟，因此希望代理人讲重点。"
        "你对保费比较敏感，不希望负担过重；"
        "也不愿意做太详细的健康告知。"
    ),
)
