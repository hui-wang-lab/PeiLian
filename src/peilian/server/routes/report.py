"""GET /api/sessions/{id}/report — 评估报告（含缓存）。"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException

from peilian.observer import match_mandatory_categories

from ..schemas import (
    AnnotationResponse,
    ComplianceHitResponse,
    MessageResponse,
    ReportResponse,
)
from ..session_store import get_session_store

router = APIRouter(prefix="/api/sessions", tags=["report"])


@router.get("/{session_id}/report", response_model=ReportResponse)
def get_report(session_id: str) -> ReportResponse:
    store = get_session_store()
    data = store.get(session_id)
    if data is None:
        raise HTTPException(status_code=404, detail="Session not found")

    with data.lock:
        if data.cached_report is not None:
            return data.cached_report

        try:
            from peilian.judge import build_judge_result

            judge_result = build_judge_result(data.dialogue.messages)
        except Exception as e:
            raise HTTPException(
                status_code=502, detail=f"LLM 评估调用失败：{type(e).__name__}"
            )

        from ..schemas import JudgeResultResponse

        judge_result_resp = JudgeResultResponse.from_dataclass(judge_result)

        compliance_hits = judge_result.evaluation_report.compliance_hits
        violation_turns = {
            (h.turn_index, h.agent_turn_number) for h in compliance_hits
        }
        compliance_score = max(0, 5 - len(violation_turns))

        messages_resp: list[MessageResponse] = []
        annotations: list[AnnotationResponse] = []
        agent_turn_number = 0

        for idx, msg in enumerate(data.dialogue.messages):
            role = msg.get("role", "")
            content = msg.get("content", "")
            if not isinstance(content, str):
                content = str(content)
            messages_resp.append(
                MessageResponse(turn_index=idx, role=role, content=content)
            )

            if role == "user":
                agent_turn_number += 1
                categories = list(match_mandatory_categories(content))
                turn_hits = [
                    ComplianceHitResponse.from_dataclass(h)
                    for h in compliance_hits
                    if h.turn_index == idx
                ]
                annotations.append(
                    AnnotationResponse(
                        turn_index=idx,
                        agent_turn_number=agent_turn_number,
                        categories=categories,
                        compliance_hits=turn_hits,
                    )
                )

        report = ReportResponse(
            compliance_score=compliance_score,
            judge_result=judge_result_resp,
            messages=messages_resp,
            annotations=annotations,
        )

        data.cached_report = report
        data.status = "completed"

    return report
