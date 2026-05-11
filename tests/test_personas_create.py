"""P5.1 /api/personas POST 路由测试：含 hidden_concerns 完整结构 + 错误分支。"""

from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from peilian.server.app import create_app


_PROJECT_ROOT = Path(__file__).resolve().parent.parent
_PERSONAS_USER_DIR = _PROJECT_ROOT / "personas" / "_user"


@pytest.fixture
def client(monkeypatch: pytest.MonkeyPatch) -> TestClient:
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    app = create_app()
    return TestClient(app)


@pytest.fixture(autouse=True)
def _cleanup_user_personas():
    before = set()
    if _PERSONAS_USER_DIR.is_dir():
        before = {p.name for p in _PERSONAS_USER_DIR.glob("*.yaml")}
    yield
    if _PERSONAS_USER_DIR.is_dir():
        for p in _PERSONAS_USER_DIR.glob("*.yaml"):
            if p.name not in before:
                p.unlink(missing_ok=True)


def _valid_payload(slug: str = "p5_1_test_persona", style: str = "mild") -> dict:
    return {
        "id": slug,
        "name": "测试客户",
        "age": 33,
        "occupation": "测试工程师",
        "family": "已婚",
        "income_level": "中等",
        "existing_coverage": ["社保"],
        "pain_points": ["对保险不熟悉"],
        "hidden_concerns": [
            {
                "key": "test_concern_a",
                "label": "测试关切 A",
                "keywords": ["test", "demo"],
                "initial_stage": "untouched",
            }
        ],
        "persistence": 0.6,
        "expressiveness": 0.5,
        "initial_mood": "礼貌但谨慎",
        "colloquial_style": style,
    }


def test_create_persona_full_flow(client: TestClient):
    resp = client.post("/api/personas", json=_valid_payload())
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["id"] == "p5_1_test_persona"
    assert body["is_builtin"] is False
    assert body["colloquial_style"] == "mild"

    target = _PERSONAS_USER_DIR / "p5_1_test_persona.yaml"
    assert target.exists()

    list_resp = client.get("/api/personas")
    ids = {p["id"] for p in list_resp.json()}
    assert "p5_1_test_persona" in ids


def test_create_persona_loadable_via_factory(client: TestClient):
    resp = client.post("/api/personas", json=_valid_payload("p5_1_factory_test"))
    assert resp.status_code == 201
    from peilian.persona_factory import get_persona_meta, load_persona_from_yaml

    persona = load_persona_from_yaml(
        str(_PERSONAS_USER_DIR / "p5_1_factory_test.yaml"),
        difficulty="medium",
    )
    meta = get_persona_meta(persona)
    assert persona.colloquial_style == "mild"
    assert len(meta.hidden_concerns) == 1


def test_create_persona_rejects_invalid_id(client: TestClient):
    payload = _valid_payload("Bad-ID")
    resp = client.post("/api/personas", json=payload)
    assert resp.status_code == 422


def test_create_persona_rejects_empty_hidden_concerns(client: TestClient):
    payload = _valid_payload("p5_1_no_hc")
    payload["hidden_concerns"] = []
    resp = client.post("/api/personas", json=payload)
    assert resp.status_code == 422


def test_create_persona_rejects_invalid_concern_key(client: TestClient):
    payload = _valid_payload("p5_1_bad_key")
    payload["hidden_concerns"][0]["key"] = "Bad-Key"
    resp = client.post("/api/personas", json=payload)
    assert resp.status_code == 422


def test_create_persona_rejects_invalid_stage(client: TestClient):
    payload = _valid_payload("p5_1_bad_stage")
    payload["hidden_concerns"][0]["initial_stage"] = "wrong"
    resp = client.post("/api/personas", json=payload)
    assert resp.status_code == 422


def test_create_persona_conflict_with_builtin(client: TestClient):
    payload = _valid_payload("price_sensitive_midcareer")
    resp = client.post("/api/personas", json=payload)
    assert resp.status_code == 409


def test_create_persona_rejects_invalid_colloquial(client: TestClient):
    payload = _valid_payload("p5_1_bad_style")
    payload["colloquial_style"] = "bogus"
    resp = client.post("/api/personas", json=payload)
    assert resp.status_code == 422
