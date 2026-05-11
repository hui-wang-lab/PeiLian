"""P4 Persona 工厂：从 YAML 配置生成 Persona + PersonaMeta，支持难度档缩放。"""

from __future__ import annotations

import re
import weakref
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

from peilian.persona import VALID_COLLOQUIAL_STYLES, Persona

# ---------------------------------------------------------------------------
# 常量与类型
# ---------------------------------------------------------------------------

VALID_DIFFICULTIES = {"easy", "medium", "hard"}
VALID_STAGES = {"untouched", "triggered", "hinted", "expressed"}
KEY_PATTERN = re.compile(r"^[a-z][a-z0-9_]*$")

_REQUIRED_FIELDS = {
    "name", "age", "occupation", "family", "income_level",
    "existing_coverage", "pain_points", "hidden_concerns",
    "persistence", "expressiveness", "initial_mood",
}

_DIFFICULTY_SCALING = {
    "easy":   {"persistence": 0.5, "expressiveness": 1.3},
    "medium": {"persistence": 1.0, "expressiveness": 1.0},
    "hard":   {"persistence": 1.3, "expressiveness": 0.7},
}


@dataclass(frozen=True)
class PersonaMeta:
    """工厂内部维护的结构化 hidden_concerns 索引。"""
    source_path: str
    difficulty: str
    name: str
    hidden_concerns: list[dict[str, Any]] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Persona → PersonaMeta 索引
#
# 用 WeakKeyDictionary 以 Persona 实例作为弱引用 key，避免：
#   1. dict[id(persona), ...] 在 persona 被 GC 后 id 复用导致拿到错误 meta；
#   2. 普通 dict 强引用 Persona 造成内存泄漏。
#
# Persona 是 frozen dataclass（普通对象，无 __slots__），可作 weakref target。
# ---------------------------------------------------------------------------
_META_BY_PERSONA: "weakref.WeakKeyDictionary[Persona, PersonaMeta]" = (
    weakref.WeakKeyDictionary()
)


# ---------------------------------------------------------------------------
# 公开纯函数：难度档缩放
# ---------------------------------------------------------------------------

def adjust_difficulty_values(
    persistence: float,
    expressiveness: float,
    difficulty: str,
) -> tuple[float, float]:
    """按档位线性缩放 persistence / expressiveness 并 clip 到 [0, 1]。"""
    if difficulty not in VALID_DIFFICULTIES:
        raise ValueError(f"Invalid difficulty: {difficulty!r}. Must be one of {VALID_DIFFICULTIES}")

    p_scale = _DIFFICULTY_SCALING[difficulty]["persistence"]
    e_scale = _DIFFICULTY_SCALING[difficulty]["expressiveness"]

    return (
        max(0.0, min(1.0, persistence * p_scale)),
        max(0.0, min(1.0, expressiveness * e_scale)),
    )


# ---------------------------------------------------------------------------
# 内部校验
# ---------------------------------------------------------------------------

def _validate_yaml_data(data: dict[str, Any]) -> None:
    """校验 YAML 数据的必填字段和类型约束。"""
    missing = _REQUIRED_FIELDS - set(data.keys())
    if missing:
        raise KeyError(f"Missing required fields: {missing}")

    if not (0.0 <= data["persistence"] <= 1.0):
        raise ValueError(
            f"persistence must be in [0, 1], got {data['persistence']}"
        )
    if not (0.0 <= data["expressiveness"] <= 1.0):
        raise ValueError(
            f"expressiveness must be in [0, 1], got {data['expressiveness']}"
        )

    # hidden_concerns 校验
    for i, hc in enumerate(data["hidden_concerns"]):
        key = hc.get("key")
        if key is None:
            raise KeyError(f"hidden_concerns[{i}] missing 'key'")
        if not KEY_PATTERN.match(key):
            raise ValueError(
                f"hidden_concerns[{i}].key {key!r} must match {KEY_PATTERN.pattern}"
            )

        keywords = hc.get("keywords")
        if keywords is None:
            raise KeyError(f"hidden_concerns[{i}] missing 'keywords'")
        if not isinstance(keywords, list) or len(keywords) == 0:
            raise ValueError(
                f"hidden_concerns[{i}].keywords must be a non-empty list"
            )

        stage = hc.get("initial_stage")
        if stage is None:
            raise KeyError(f"hidden_concerns[{i}] missing 'initial_stage'")
        if stage not in VALID_STAGES:
            raise ValueError(
                f"hidden_concerns[{i}].initial_stage {stage!r} must be one of {VALID_STAGES}"
            )

    # 单 persona 内 key 不重复
    keys = [hc["key"] for hc in data["hidden_concerns"]]
    if len(keys) != len(set(keys)):
        raise ValueError("Duplicate hidden_concern keys within the same persona")

    # colloquial_style 可选；存在时校验取值
    if "colloquial_style" in data:
        style = data["colloquial_style"]
        if style not in VALID_COLLOQUIAL_STYLES:
            raise ValueError(
                f"colloquial_style must be one of "
                f"{sorted(VALID_COLLOQUIAL_STYLES)}, got {style!r}"
            )


# ---------------------------------------------------------------------------
# 工厂函数
# ---------------------------------------------------------------------------

def load_persona_from_yaml(
    path: str,
    *,
    difficulty: str = "medium",
) -> Persona:
    """从单个 YAML 文件加载 Persona，按难度档线性缩放并 clip。"""
    abs_path = str(Path(path).resolve())

    with open(abs_path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)

    _validate_yaml_data(data)

    # 难度缩放
    persistence, expressiveness = adjust_difficulty_values(
        data["persistence"],
        data["expressiveness"],
        difficulty,
    )

    # 构建 hidden_concerns labels（保持 P1/P2/P3 兼容）
    hidden_concern_labels = tuple(hc["label"] for hc in data["hidden_concerns"])

    persona = Persona(
        name=data["name"],
        age=data["age"],
        occupation=data["occupation"],
        family=data["family"],
        income_level=data["income_level"],
        existing_coverage=tuple(data["existing_coverage"]),
        pain_points=tuple(data["pain_points"]),
        hidden_concerns=hidden_concern_labels,
        persistence=persistence,
        expressiveness=expressiveness,
        initial_mood=data["initial_mood"],
        colloquial_style=data.get("colloquial_style", "off"),
    )

    _META_BY_PERSONA[persona] = PersonaMeta(
        source_path=abs_path,
        difficulty=difficulty,
        name=data["name"],
        hidden_concerns=data["hidden_concerns"],
    )

    return persona


def load_personas_from_dir(
    dir_path: str = "personas",
    *,
    difficulty: str = "medium",
    include_user: bool = False,
) -> list[Persona]:
    """加载目录下所有 YAML，按难度档统一缩放。

    P5.1 起额外扫描 `<dir_path>/_user/`，以支持 UI 自定义 persona。
    Web 层需要自定义 persona 时显式传 `include_user=True`；
    默认仅加载内置目录，保留 P0–P5 / CLI 兼容行为。
    """
    dir_p = Path(dir_path)
    if not dir_p.is_dir():
        raise ValueError(f"Directory not found: {dir_path}")

    personas: list[Persona] = []
    for yaml_file in sorted(dir_p.glob("*.yaml")):
        persona = load_persona_from_yaml(str(yaml_file), difficulty=difficulty)
        personas.append(persona)

    if include_user:
        user_dir = dir_p / "_user"
        if user_dir.is_dir():
            for yaml_file in sorted(user_dir.glob("*.yaml")):
                persona = load_persona_from_yaml(
                    str(yaml_file), difficulty=difficulty
                )
                personas.append(persona)

    return personas


def get_persona_meta(persona: Persona) -> PersonaMeta:
    """按 Persona 实例查回工厂内部的结构化索引。

    使用 WeakKeyDictionary 直接以 Persona 实例为 key，确保：
    - 同一 yaml 不同难度加载得到的 Persona 是不同对象，不会串台；
    - persona 被 GC 后自动从注册表移除，不会因 id 复用拿到错误 meta。
    """
    meta = _META_BY_PERSONA.get(persona)
    if meta is not None:
        return meta

    raise ValueError(
        f"PersonaMeta not found for persona '{persona.name}'. "
        "Make sure the persona was loaded via load_persona_from_yaml."
    )
