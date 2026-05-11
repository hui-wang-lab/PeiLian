"""P5.1 场景路由：GET /api/scenarios + POST /api/scenarios。

POST 落地到 `scenarios/_user/{id}.yaml`；id 必须匹配 `^[a-z0-9_]{1,32}$`。
"""

from __future__ import annotations

import re
from pathlib import Path

import yaml
from fastapi import APIRouter, HTTPException

from peilian.scenario_factory import (
    ID_PATTERN,
    list_scenarios,
    load_scenario_from_yaml,
)

from ..schemas import CreateScenarioRequest, ScenarioSummary

router = APIRouter(prefix="/api/scenarios", tags=["scenarios"])

_SCENARIOS_DIR = (
    Path(__file__).resolve().parent.parent.parent.parent.parent / "scenarios"
)
_USER_DIR = _SCENARIOS_DIR / "_user"


@router.get("", response_model=list[ScenarioSummary])
def list_all_scenarios() -> list[ScenarioSummary]:
    items = list_scenarios(_SCENARIOS_DIR)
    return [
        ScenarioSummary(
            id=meta.id,
            name=meta.name,
            context=scenario.context,
            constraints=scenario.constraints,
            tags=list(meta.tags),
            is_builtin=meta.is_builtin,
        )
        for scenario, meta in items
    ]


@router.post("", response_model=ScenarioSummary, status_code=201)
def create_scenario(req: CreateScenarioRequest) -> ScenarioSummary:
    slug = req.id.strip()
    if not ID_PATTERN.match(slug):
        raise HTTPException(
            status_code=422,
            detail=f"id 必须匹配 {ID_PATTERN.pattern}（小写字母/数字/下划线，长度 ≤ 32）",
        )
    if not req.name.strip():
        raise HTTPException(status_code=422, detail="name 不能为空")
    if not req.context.strip():
        raise HTTPException(status_code=422, detail="context 不能为空")
    if not req.constraints.strip():
        raise HTTPException(status_code=422, detail="constraints 不能为空")

    existing_ids = {meta.id for _s, meta in list_scenarios(_SCENARIOS_DIR)}
    if slug in existing_ids:
        raise HTTPException(
            status_code=409, detail=f"scenario '{slug}' 已存在（与内置或已有自定义冲突）"
        )

    _USER_DIR.mkdir(parents=True, exist_ok=True)
    target = (_USER_DIR / f"{slug}.yaml").resolve()
    if not _is_within(target, _USER_DIR.resolve()):
        raise HTTPException(status_code=400, detail="非法文件路径")

    payload = {
        "id": slug,
        "name": req.name.strip(),
        "context": req.context.strip(),
        "constraints": req.constraints.strip(),
        "tags": [t.strip() for t in req.tags if t.strip()],
    }

    try:
        with open(target, "x", encoding="utf-8") as f:
            yaml.safe_dump(payload, f, allow_unicode=True, sort_keys=False)
    except FileExistsError:
        raise HTTPException(
            status_code=409,
            detail=f"scenario '{slug}' 已存在（与已有自定义冲突）",
        )

    try:
        scenario, meta = load_scenario_from_yaml(str(target), is_builtin=False)
    except Exception as e:
        target.unlink(missing_ok=True)
        raise HTTPException(status_code=422, detail=f"scenario schema 校验失败：{e}")
    return ScenarioSummary(
        id=meta.id,
        name=meta.name,
        context=scenario.context,
        constraints=scenario.constraints,
        tags=list(meta.tags),
        is_builtin=False,
    )


def _is_within(child: Path, parent: Path) -> bool:
    try:
        child.relative_to(parent)
        return True
    except ValueError:
        return False
