"""GET /api/personas — yaml.safe_load 直读，不污染注册表。"""

from __future__ import annotations

from pathlib import Path

import yaml
from fastapi import APIRouter

from ..schemas import PersonaSummary

router = APIRouter(prefix="/api/personas", tags=["personas"])

_PERSONAS_DIR = Path(__file__).resolve().parent.parent.parent.parent.parent / "personas"


@router.get("", response_model=list[PersonaSummary])
def list_personas() -> list[PersonaSummary]:
    """列出 personas/ 目录下所有 yaml 的元数据。"""
    result: list[PersonaSummary] = []
    personas_dir = _PERSONAS_DIR
    if not personas_dir.is_dir():
        return result

    for yaml_file in sorted(personas_dir.glob("*.yaml")):
        with open(yaml_file, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
        result.append(
            PersonaSummary(
                id=yaml_file.stem,
                name=data.get("name", yaml_file.stem),
                age=data.get("age", 0),
                occupation=data.get("occupation", ""),
                family=data.get("family", ""),
                income_level=data.get("income_level", ""),
                hidden_concerns_labels=[
                    hc.get("label", hc.get("key", ""))
                    for hc in data.get("hidden_concerns", [])
                ],
            )
        )
    return result
