"""P5 内存会话存储。

两层锁：SessionStore._lock (RLock) 保护 dict 本身；
SessionData.lock (Lock) per-session 串行化 dialogue 调用。
"""

from __future__ import annotations

import threading
from dataclasses import dataclass, field
from datetime import datetime
from typing import TYPE_CHECKING, Any
from uuid import uuid4

if TYPE_CHECKING:
    from peilian.config import Settings
    from peilian.dialogue import Dialogue
    from peilian.persona import Persona
    from peilian.persona_factory import PersonaMeta
    from peilian.scenario import Scenario

    from .schemas import ReportResponse


@dataclass
class SessionData:
    dialogue: Dialogue
    persona: Persona
    persona_meta: PersonaMeta
    difficulty: str
    created_at: datetime
    scenario_id: str = "office_first_meet"
    status: str = "active"
    cached_report: ReportResponse | None = None
    lock: threading.Lock = field(default_factory=threading.Lock)


class SessionStore:
    """内存会话存储。单进程单用户场景，不做分布式。"""

    def __init__(self) -> None:
        self._sessions: dict[str, SessionData] = {}
        self._lock = threading.RLock()

    def create(
        self,
        persona: Persona,
        persona_meta: PersonaMeta,
        difficulty: str,
        settings: Settings,
        *,
        scenario: Scenario | None = None,
        scenario_id: str = "office_first_meet",
    ) -> str:
        from peilian.dialogue import Dialogue
        from peilian.scenario import SAMPLE_SCENARIO

        active_scenario = scenario if scenario is not None else SAMPLE_SCENARIO

        session_id = uuid4().hex[:8]
        dialogue = Dialogue(
            persona, active_scenario, settings, persona_meta=persona_meta
        )
        data = SessionData(
            dialogue=dialogue,
            persona=persona,
            persona_meta=persona_meta,
            difficulty=difficulty,
            created_at=datetime.now(),
            scenario_id=scenario_id,
        )
        with self._lock:
            self._sessions[session_id] = data
        return session_id

    def get(self, session_id: str) -> SessionData | None:
        with self._lock:
            return self._sessions.get(session_id)

    def delete(self, session_id: str) -> bool:
        with self._lock:
            return self._sessions.pop(session_id, None) is not None

    def all_ids(self) -> list[str]:
        with self._lock:
            return list(self._sessions.keys())


def get_session_store() -> SessionStore:
    """全局单例工厂。"""
    if not hasattr(get_session_store, "_instance"):
        get_session_store._instance = SessionStore()  # type: ignore[attr-defined]
    return get_session_store._instance  # type: ignore[attr-defined]
