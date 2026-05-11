"""P5.1 Scenario 工厂：从 YAML 配置加载 Scenario。

与 persona_factory 的差异：
- Scenario 是简单 dataclass，不需要弱引用注册表
- 不做难度缩放
- 支持内置 + _user/ 两源合并扫描，按 id 去重（内置优先）
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

from peilian.scenario import Scenario

# ---------------------------------------------------------------------------
# 常量
# ---------------------------------------------------------------------------

ID_PATTERN = re.compile(r"^[a-z0-9_]{1,32}$")
_REQUIRED_FIELDS = {"id", "name", "context", "constraints"}


@dataclass(frozen=True)
class ScenarioMeta:
    """加载后保留的元数据（源文件路径、tags、name）。"""

    id: str
    name: str
    source_path: str
    tags: tuple[str, ...] = ()
    is_builtin: bool = True


# ---------------------------------------------------------------------------
# 内部校验
# ---------------------------------------------------------------------------


def _validate_yaml_data(data: dict[str, Any]) -> None:
    if not isinstance(data, dict):
        raise ValueError("scenario yaml root must be a mapping")

    missing = _REQUIRED_FIELDS - set(data.keys())
    if missing:
        raise KeyError(f"Missing required fields: {sorted(missing)}")

    scenario_id = data["id"]
    if not isinstance(scenario_id, str) or not ID_PATTERN.match(scenario_id):
        raise ValueError(
            f"scenario id {scenario_id!r} must match {ID_PATTERN.pattern}"
        )

    for key in ("name", "context", "constraints"):
        value = data[key]
        if not isinstance(value, str) or not value.strip():
            raise ValueError(f"scenario.{key} must be a non-empty string")

    tags = data.get("tags", [])
    if tags is not None and not isinstance(tags, list):
        raise ValueError("scenario.tags must be a list of strings (or omitted)")
    if isinstance(tags, list):
        for i, t in enumerate(tags):
            if not isinstance(t, str):
                raise ValueError(f"scenario.tags[{i}] must be a string")


# ---------------------------------------------------------------------------
# 工厂函数
# ---------------------------------------------------------------------------


def load_scenario_from_yaml(
    path: str,
    *,
    is_builtin: bool = True,
) -> tuple[Scenario, ScenarioMeta]:
    """从单个 YAML 加载 Scenario + 元数据。"""
    abs_path = Path(path).resolve()
    with open(abs_path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)

    _validate_yaml_data(data)

    scenario = Scenario(
        context=data["context"].strip(),
        constraints=data["constraints"].strip(),
    )
    tags = tuple(data.get("tags") or ())
    meta = ScenarioMeta(
        id=data["id"],
        name=data["name"].strip(),
        source_path=str(abs_path),
        tags=tags,
        is_builtin=is_builtin,
    )
    return scenario, meta


def list_scenarios(
    base_dir: str | Path = "scenarios",
) -> list[tuple[Scenario, ScenarioMeta]]:
    """扫描内置 + _user/ 两源，按 id 去重（内置优先）。"""
    base = Path(base_dir)
    if not base.is_dir():
        return []

    seen_ids: set[str] = set()
    result: list[tuple[Scenario, ScenarioMeta]] = []

    for yaml_file in sorted(base.glob("*.yaml")):
        try:
            scenario, meta = load_scenario_from_yaml(str(yaml_file), is_builtin=True)
        except (KeyError, ValueError, yaml.YAMLError):
            continue
        if meta.id in seen_ids:
            continue
        seen_ids.add(meta.id)
        result.append((scenario, meta))

    user_dir = base / "_user"
    if user_dir.is_dir():
        for yaml_file in sorted(user_dir.glob("*.yaml")):
            try:
                scenario, meta = load_scenario_from_yaml(
                    str(yaml_file), is_builtin=False
                )
            except (KeyError, ValueError, yaml.YAMLError):
                continue
            if meta.id in seen_ids:
                continue
            seen_ids.add(meta.id)
            result.append((scenario, meta))

    return result


def find_scenario_by_id(
    scenario_id: str,
    base_dir: str | Path = "scenarios",
) -> tuple[Scenario, ScenarioMeta] | None:
    """按 id 查找 Scenario，内置优先。"""
    for scenario, meta in list_scenarios(base_dir):
        if meta.id == scenario_id:
            return scenario, meta
    return None
