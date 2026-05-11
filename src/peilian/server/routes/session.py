"""会话 CRUD：POST /api/sessions, GET /api/sessions/{id}, DELETE /api/sessions/{id}。"""

from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, HTTPException, Response

from peilian.config import load_settings
from peilian.persona_factory import get_persona_meta, load_persona_from_yaml
from peilian.scenario_factory import find_scenario_by_id

from ..schemas import CreateSessionRequest, SessionResponse
from ..session_store import SessionData, get_session_store

router = APIRouter(prefix="/api/sessions", tags=["sessions"])

_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent.parent
_PERSONAS_DIR = _PROJECT_ROOT / "personas"
_SCENARIOS_DIR = _PROJECT_ROOT / "scenarios"


def _find_persona_yaml(persona_id: str) -> Path | None:
    """内置目录优先，然后 _user/。"""
    builtin = _PERSONAS_DIR / f"{persona_id}.yaml"
    if builtin.exists():
        return builtin
    user = _PERSONAS_DIR / "_user" / f"{persona_id}.yaml"
    if user.exists():
        return user
    return None


@router.post("", response_model=SessionResponse, status_code=201)
def create_session(req: CreateSessionRequest) -> SessionResponse:
    settings = load_settings()
    if not settings.has_llm_credentials:
        raise HTTPException(
            status_code=502,
            detail="未检测到 OPENAI_API_KEY；请在 .env 中配置后重试。",
        )

    yaml_path = _find_persona_yaml(req.persona_id)
    if yaml_path is None:
        raise HTTPException(
            status_code=404, detail=f"Persona '{req.persona_id}' not found"
        )

    try:
        persona = load_persona_from_yaml(str(yaml_path), difficulty=req.difficulty)
        persona_meta = get_persona_meta(persona)
    except Exception as e:
        raise HTTPException(status_code=422, detail=str(e))

    found = find_scenario_by_id(req.scenario_id, base_dir=_SCENARIOS_DIR)
    if found is None:
        raise HTTPException(
            status_code=404, detail=f"Scenario '{req.scenario_id}' not found"
        )
    scenario, _meta = found

    store = get_session_store()
    session_id = store.create(
        persona,
        persona_meta,
        req.difficulty,
        settings,
        scenario=scenario,
        scenario_id=req.scenario_id,
    )

    return SessionResponse(
        session_id=session_id,
        persona_name=persona.name,
        difficulty=req.difficulty,
        turn_count=0,
        status="active",
    )


@router.get("/{session_id}", response_model=SessionResponse)
def get_session(session_id: str) -> SessionResponse:
    store = get_session_store()
    data = store.get(session_id)
    if data is None:
        raise HTTPException(status_code=404, detail="Session not found")

    agent_turns = sum(
        1 for m in data.dialogue.messages if m.get("role") == "user"
    )
    return SessionResponse(
        session_id=session_id,
        persona_name=data.persona.name,
        difficulty=data.difficulty,
        turn_count=agent_turns,
        status=data.status,
    )


@router.delete("/{session_id}", status_code=204)
def delete_session(session_id: str) -> Response:
    store = get_session_store()
    if not store.delete(session_id):
        raise HTTPException(status_code=404, detail="Session not found")
    return Response(status_code=204)
