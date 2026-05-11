"""GET /api/personas — 内置 + _user/ 双源；POST /api/personas — 新建落地到 _user/。"""

from __future__ import annotations

import re
from pathlib import Path

import yaml
from fastapi import APIRouter, HTTPException

from peilian.persona import VALID_COLLOQUIAL_STYLES
from peilian.persona_factory import KEY_PATTERN, VALID_STAGES, load_persona_from_yaml

from ..schemas import CreatePersonaRequest, PersonaSummary

router = APIRouter(prefix="/api/personas", tags=["personas"])

_PERSONAS_DIR = (
    Path(__file__).resolve().parent.parent.parent.parent.parent / "personas"
)
_USER_DIR = _PERSONAS_DIR / "_user"

ID_PATTERN = re.compile(r"^[a-z0-9_]{1,32}$")


def _load_summary_from_yaml(yaml_file: Path, *, is_builtin: bool) -> PersonaSummary:
    with open(yaml_file, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}
    return PersonaSummary(
        id=yaml_file.stem,
        name=data.get("name", yaml_file.stem),
        age=data.get("age", 0),
        occupation=data.get("occupation", ""),
        family=data.get("family", ""),
        income_level=data.get("income_level", ""),
        hidden_concerns_labels=[
            hc.get("label", hc.get("key", ""))
            for hc in data.get("hidden_concerns", [])
            if isinstance(hc, dict)
        ],
        colloquial_style=data.get("colloquial_style", "off"),
        is_builtin=is_builtin,
    )


@router.get("", response_model=list[PersonaSummary])
def list_personas() -> list[PersonaSummary]:
    """列出 personas/ + personas/_user/ 下所有 yaml 的元数据；按 id 去重内置优先。"""
    result: list[PersonaSummary] = []
    seen: set[str] = set()

    if _PERSONAS_DIR.is_dir():
        for yaml_file in sorted(_PERSONAS_DIR.glob("*.yaml")):
            try:
                summary = _load_summary_from_yaml(yaml_file, is_builtin=True)
            except (yaml.YAMLError, OSError):
                continue
            if summary.id in seen:
                continue
            seen.add(summary.id)
            result.append(summary)

    if _USER_DIR.is_dir():
        for yaml_file in sorted(_USER_DIR.glob("*.yaml")):
            try:
                summary = _load_summary_from_yaml(yaml_file, is_builtin=False)
            except (yaml.YAMLError, OSError):
                continue
            if summary.id in seen:
                continue
            seen.add(summary.id)
            result.append(summary)

    return result


@router.post("", response_model=PersonaSummary, status_code=201)
def create_persona(req: CreatePersonaRequest) -> PersonaSummary:
    slug = req.id.strip()
    if not ID_PATTERN.match(slug):
        raise HTTPException(
            status_code=422,
            detail=f"id 必须匹配 {ID_PATTERN.pattern}（小写字母/数字/下划线，长度 ≤ 32）",
        )

    if not req.name.strip():
        raise HTTPException(status_code=422, detail="name 不能为空")
    if not req.occupation.strip():
        raise HTTPException(status_code=422, detail="occupation 不能为空")
    if not req.family.strip():
        raise HTTPException(status_code=422, detail="family 不能为空")
    if not req.income_level.strip():
        raise HTTPException(status_code=422, detail="income_level 不能为空")
    if not req.initial_mood.strip():
        raise HTTPException(status_code=422, detail="initial_mood 不能为空")
    if req.age < 0 or req.age > 120:
        raise HTTPException(status_code=422, detail="age 应在 0–120 之间")
    if not 0.0 <= req.persistence <= 1.0:
        raise HTTPException(status_code=422, detail="persistence 须在 [0, 1]")
    if not 0.0 <= req.expressiveness <= 1.0:
        raise HTTPException(status_code=422, detail="expressiveness 须在 [0, 1]")
    if req.colloquial_style not in VALID_COLLOQUIAL_STYLES:
        raise HTTPException(
            status_code=422,
            detail=f"colloquial_style 必须是 {sorted(VALID_COLLOQUIAL_STYLES)} 之一",
        )

    if not req.hidden_concerns:
        raise HTTPException(
            status_code=422, detail="至少需要配置 1 条 hidden_concern"
        )

    seen_keys: set[str] = set()
    for i, hc in enumerate(req.hidden_concerns):
        if not KEY_PATTERN.match(hc.key):
            raise HTTPException(
                status_code=422,
                detail=f"hidden_concerns[{i}].key {hc.key!r} 须匹配 {KEY_PATTERN.pattern}",
            )
        if hc.key in seen_keys:
            raise HTTPException(
                status_code=422,
                detail=f"hidden_concerns[{i}].key {hc.key!r} 在同一 persona 中重复",
            )
        seen_keys.add(hc.key)
        if not hc.label.strip():
            raise HTTPException(
                status_code=422, detail=f"hidden_concerns[{i}].label 不能为空"
            )
        if not hc.keywords:
            raise HTTPException(
                status_code=422,
                detail=f"hidden_concerns[{i}].keywords 不能为空列表",
            )
        if hc.initial_stage not in VALID_STAGES:
            raise HTTPException(
                status_code=422,
                detail=f"hidden_concerns[{i}].initial_stage 必须是 {sorted(VALID_STAGES)} 之一",
            )

    existing_ids = {p.id for p in list_personas()}
    if slug in existing_ids:
        raise HTTPException(
            status_code=409,
            detail=f"persona '{slug}' 已存在（与内置或已有自定义冲突）",
        )

    _USER_DIR.mkdir(parents=True, exist_ok=True)
    target = (_USER_DIR / f"{slug}.yaml").resolve()
    try:
        target.relative_to(_USER_DIR.resolve())
    except ValueError:
        raise HTTPException(status_code=400, detail="非法文件路径")

    payload = {
        "name": req.name.strip(),
        "age": req.age,
        "occupation": req.occupation.strip(),
        "family": req.family.strip(),
        "income_level": req.income_level.strip(),
        "existing_coverage": [s for s in req.existing_coverage if s.strip()],
        "pain_points": [s for s in req.pain_points if s.strip()],
        "hidden_concerns": [
            {
                "key": hc.key,
                "label": hc.label.strip(),
                "keywords": [k for k in hc.keywords if k.strip()],
                "initial_stage": hc.initial_stage,
            }
            for hc in req.hidden_concerns
        ],
        "persistence": req.persistence,
        "expressiveness": req.expressiveness,
        "initial_mood": req.initial_mood.strip(),
        "colloquial_style": req.colloquial_style,
    }

    try:
        with open(target, "x", encoding="utf-8") as f:
            yaml.safe_dump(payload, f, allow_unicode=True, sort_keys=False)
    except FileExistsError:
        raise HTTPException(
            status_code=409,
            detail=f"persona '{slug}' 已存在（与已有自定义冲突）",
        )

    try:
        load_persona_from_yaml(str(target), difficulty="medium")
    except Exception as e:
        target.unlink(missing_ok=True)
        raise HTTPException(
            status_code=422, detail=f"persona schema 校验失败：{e}"
        )

    return _load_summary_from_yaml(target, is_builtin=False)
