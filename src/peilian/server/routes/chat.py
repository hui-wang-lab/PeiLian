"""POST /api/sessions/{id}/chat — 同步对话。"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException

from ..schemas import ChatRequest, ChatResponse
from ..session_store import get_session_store

router = APIRouter(prefix="/api/sessions", tags=["chat"])


@router.post("/{session_id}/chat", response_model=ChatResponse)
def chat(session_id: str, req: ChatRequest) -> ChatResponse:
    store = get_session_store()
    data = store.get(session_id)
    if data is None:
        raise HTTPException(status_code=404, detail="Session not found")

    with data.lock:
        if data.status == "completed":
            raise HTTPException(status_code=422, detail="Session already completed")

        try:
            answer = data.dialogue.send_user(req.message)
        except Exception as e:
            raise HTTPException(
                status_code=502, detail=f"LLM 调用失败：{type(e).__name__}"
            )
        data.cached_report = None

        agent_turns = sum(
            1 for m in data.dialogue.messages if m.get("role") == "user"
        )
    return ChatResponse(response=answer, turn_count=agent_turns)
