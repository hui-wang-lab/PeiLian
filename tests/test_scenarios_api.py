"""P5.1 /api/scenarios 路由测试：GET 列表 + POST 新建（含 422/409）。"""

from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from peilian.server.app import create_app


_PROJECT_ROOT = Path(__file__).resolve().parent.parent
_SCENARIOS_USER_DIR = _PROJECT_ROOT / "scenarios" / "_user"


@pytest.fixture
def client(monkeypatch: pytest.MonkeyPatch) -> TestClient:
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    app = create_app()
    return TestClient(app)


@pytest.fixture(autouse=True)
def _cleanup_user_scenarios():
    """测试后清理 scenarios/_user 下本测试创建的 yaml（不动 .gitkeep）。"""
    before = set()
    if _SCENARIOS_USER_DIR.is_dir():
        before = {p.name for p in _SCENARIOS_USER_DIR.glob("*.yaml")}
    yield
    if _SCENARIOS_USER_DIR.is_dir():
        for p in _SCENARIOS_USER_DIR.glob("*.yaml"):
            if p.name not in before:
                p.unlink(missing_ok=True)


def test_list_scenarios_returns_builtins(client: TestClient):
    resp = client.get("/api/scenarios")
    assert resp.status_code == 200
    data = resp.json()
    ids = {s["id"] for s in data}
    assert "office_first_meet" in ids
    for s in data:
        assert "context" in s
        assert "constraints" in s
        assert s["is_builtin"] is True or s["is_builtin"] is False


def test_create_scenario_writes_file_and_appears_in_list(client: TestClient):
    payload = {
        "id": "p5_1_test_scene",
        "name": "测试场景",
        "context": "你和这位代理人在一个测试环境中相见。",
        "constraints": "对话时间紧张，不能离题。",
        "tags": ["测试"],
    }
    resp = client.post("/api/scenarios", json=payload)
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["id"] == "p5_1_test_scene"
    assert body["is_builtin"] is False
    target = _SCENARIOS_USER_DIR / "p5_1_test_scene.yaml"
    assert target.exists()

    list_resp = client.get("/api/scenarios")
    ids = {s["id"] for s in list_resp.json()}
    assert "p5_1_test_scene" in ids


def test_create_scenario_rejects_invalid_id(client: TestClient):
    payload = {
        "id": "Bad-ID",
        "name": "x",
        "context": "x",
        "constraints": "x",
    }
    resp = client.post("/api/scenarios", json=payload)
    assert resp.status_code == 422


def test_create_scenario_rejects_empty_fields(client: TestClient):
    payload = {
        "id": "p5_1_empty",
        "name": "",
        "context": "x",
        "constraints": "x",
    }
    resp = client.post("/api/scenarios", json=payload)
    assert resp.status_code == 422


def test_create_scenario_conflict_with_builtin(client: TestClient):
    payload = {
        "id": "office_first_meet",
        "name": "撞名",
        "context": "x",
        "constraints": "x",
    }
    resp = client.post("/api/scenarios", json=payload)
    assert resp.status_code == 409
