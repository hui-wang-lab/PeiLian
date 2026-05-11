"""P5.1 e2e：自定义 scenario_id 创建 session → 对话 → 报告 全链路。"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from peilian.server.app import create_app


@pytest.fixture
def client(monkeypatch: pytest.MonkeyPatch) -> TestClient:
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    app = create_app()
    return TestClient(app)


def _mock_llm_response(text: str = "好的，我听听看。") -> MagicMock:
    choice = MagicMock()
    choice.message.content = text
    resp = MagicMock()
    resp.choices = [choice]
    return resp


@patch("peilian.dialogue.OpenAI")
def test_create_session_default_scenario_works(
    mock_openai: MagicMock, client: TestClient
) -> None:
    """不传 scenario_id 时默认 office_first_meet。"""
    mock_openai.return_value.chat.completions.create.return_value = _mock_llm_response()
    resp = client.post(
        "/api/sessions",
        json={"persona_id": "price_sensitive_midcareer", "difficulty": "medium"},
    )
    assert resp.status_code == 201


@patch("peilian.dialogue.OpenAI")
def test_create_session_with_explicit_scenario(
    mock_openai: MagicMock, client: TestClient
) -> None:
    mock_openai.return_value.chat.completions.create.return_value = _mock_llm_response()
    resp = client.post(
        "/api/sessions",
        json={
            "persona_id": "price_sensitive_midcareer",
            "difficulty": "medium",
            "scenario_id": "coffee_followup",
        },
    )
    assert resp.status_code == 201


def test_create_session_unknown_scenario(client: TestClient) -> None:
    resp = client.post(
        "/api/sessions",
        json={
            "persona_id": "price_sensitive_midcareer",
            "difficulty": "medium",
            "scenario_id": "not_a_real_scenario",
        },
    )
    assert resp.status_code == 404


@patch("peilian.dialogue.OpenAI")
def test_e2e_chat_uses_custom_scenario_context(
    mock_openai: MagicMock, client: TestClient
) -> None:
    """会话使用的 scenario context 应来自所选 scenario_id 而非 SAMPLE_SCENARIO 写死。"""
    mock_openai.return_value.chat.completions.create.return_value = _mock_llm_response()

    create_resp = client.post(
        "/api/sessions",
        json={
            "persona_id": "price_sensitive_midcareer",
            "difficulty": "medium",
            "scenario_id": "phone_intro",
        },
    )
    assert create_resp.status_code == 201
    session_id = create_resp.json()["session_id"]

    client.post(
        f"/api/sessions/{session_id}/chat",
        json={"message": "您好，请问方便聊几分钟保险吗？"},
    )

    from peilian.server.session_store import get_session_store

    store = get_session_store()
    data = store.get(session_id)
    assert data is not None
    sys_msg = data.dialogue.messages[0]
    assert sys_msg["role"] == "system"
    assert "电话" in sys_msg["content"]
    assert data.scenario_id == "phone_intro"


@patch("peilian.dialogue.OpenAI")
def test_create_session_with_mild_persona_injects_colloquial_block(
    mock_openai: MagicMock, client: TestClient
) -> None:
    """内置 price_sensitive_midcareer 现在是 mild，system prompt 应包含口语化片段。"""
    mock_openai.return_value.chat.completions.create.return_value = _mock_llm_response()

    create_resp = client.post(
        "/api/sessions",
        json={"persona_id": "price_sensitive_midcareer", "difficulty": "medium"},
    )
    session_id = create_resp.json()["session_id"]

    from peilian.server.session_store import get_session_store

    store = get_session_store()
    data = store.get(session_id)
    sys_content = data.dialogue.messages[0]["content"]
    assert "【口语化风格 — mild】" in sys_content
