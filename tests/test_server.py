"""P5 API 端点测试 + e2e 集成测试（TestClient + mock LLM）。"""

from __future__ import annotations

import json
from typing import Any
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from peilian.server.app import create_app


@pytest.fixture
def client(monkeypatch: pytest.MonkeyPatch) -> TestClient:
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    app = create_app()
    return TestClient(app)


def _mock_llm_response(text: str = "您好，很高兴认识你。") -> MagicMock:
    choice = MagicMock()
    choice.message.content = text
    resp = MagicMock()
    resp.choices = [choice]
    return resp


def _mock_judge_response() -> dict[str, Any]:
    return {
        "scores": [
            {"dimension": "professionalism", "label": "专业度", "score": 3, "reasoning": "一般"},
            {"dimension": "empathy", "label": "共情度", "score": 4, "reasoning": "较好"},
            {"dimension": "structure", "label": "逻辑结构", "score": 3, "reasoning": "一般"},
            {"dimension": "objection_handling", "label": "异议处理", "score": 2, "reasoning": "偏弱"},
        ],
        "overall_comment": "综合评语",
    }


def _mock_customer_judge_response() -> dict[str, Any]:
    return {
        "premature_disclosure_issues": [],
        "inconsistency_issues": [],
        "overall_comment": "客户行为正常",
    }


# ---------------------------------------------------------------------------
# 单端点测试
# ---------------------------------------------------------------------------

class TestPersonas:
    def test_list_personas(self, client: TestClient) -> None:
        resp = client.get("/api/personas")
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)
        if len(data) > 0:
            assert "id" in data[0]
            assert "name" in data[0]

    def test_personas_no_pollution(self, client: TestClient) -> None:
        """GET /api/personas 不应注册 persona 到 weakref 表。"""
        from peilian.persona_factory import _META_BY_PERSONA
        before = len(_META_BY_PERSONA)
        client.get("/api/personas")
        after = len(_META_BY_PERSONA)
        assert before == after


class TestStaticFiles:
    def test_static_pages_and_assets(self, client: TestClient) -> None:
        paths = [
            "/",
            "/chat.html",
            "/report.html",
            "/css/style.css",
            "/js/chat.js",
            "/js/report.js",
            "/vendor/echarts.min.js",
        ]
        for path in paths:
            resp = client.get(path)
            assert resp.status_code == 200, path


class TestSessions:
    @patch("peilian.dialogue.OpenAI")
    def test_create_session(self, mock_openai: MagicMock, client: TestClient) -> None:
        mock_openai.return_value.chat.completions.create.return_value = _mock_llm_response()
        resp = client.post(
            "/api/sessions",
            json={"persona_id": "price_sensitive_midcareer", "difficulty": "medium"},
        )
        assert resp.status_code == 201
        data = resp.json()
        assert "session_id" in data
        assert data["persona_name"] != ""
        assert data["status"] == "active"

    def test_create_session_not_found_persona(self, client: TestClient) -> None:
        resp = client.post(
            "/api/sessions",
            json={"persona_id": "nonexistent", "difficulty": "medium"},
        )
        assert resp.status_code == 404

    @patch("peilian.dialogue.OpenAI")
    def test_get_session(self, mock_openai: MagicMock, client: TestClient) -> None:
        mock_openai.return_value.chat.completions.create.return_value = _mock_llm_response()
        create_resp = client.post(
            "/api/sessions",
            json={"persona_id": "price_sensitive_midcareer", "difficulty": "medium"},
        )
        session_id = create_resp.json()["session_id"]

        get_resp = client.get(f"/api/sessions/{session_id}")
        assert get_resp.status_code == 200
        assert get_resp.json()["session_id"] == session_id

    def test_get_session_not_found(self, client: TestClient) -> None:
        resp = client.get("/api/sessions/nonexistent")
        assert resp.status_code == 404

    @patch("peilian.dialogue.OpenAI")
    def test_delete_session(self, mock_openai: MagicMock, client: TestClient) -> None:
        mock_openai.return_value.chat.completions.create.return_value = _mock_llm_response()
        create_resp = client.post(
            "/api/sessions",
            json={"persona_id": "price_sensitive_midcareer", "difficulty": "medium"},
        )
        session_id = create_resp.json()["session_id"]

        del_resp = client.delete(f"/api/sessions/{session_id}")
        assert del_resp.status_code == 204

        get_resp = client.get(f"/api/sessions/{session_id}")
        assert get_resp.status_code == 404


class TestChat:
    @patch("peilian.dialogue.OpenAI")
    def test_chat(self, mock_openai: MagicMock, client: TestClient) -> None:
        mock_openai.return_value.chat.completions.create.return_value = _mock_llm_response(
            "我最近确实在考虑保险。"
        )
        create_resp = client.post(
            "/api/sessions",
            json={"persona_id": "price_sensitive_midcareer", "difficulty": "medium"},
        )
        session_id = create_resp.json()["session_id"]

        chat_resp = client.post(
            f"/api/sessions/{session_id}/chat",
            json={"message": "您好，想了解下您的家庭情况。"},
        )
        assert chat_resp.status_code == 200
        data = chat_resp.json()
        assert "response" in data
        assert data["turn_count"] >= 1

    def test_chat_session_not_found(self, client: TestClient) -> None:
        resp = client.post(
            "/api/sessions/nonexistent/chat",
            json={"message": "test"},
        )
        assert resp.status_code == 404


class TestReport:
    @patch("peilian.dialogue.OpenAI")
    def test_report_cache(self, mock_openai: MagicMock, client: TestClient) -> None:
        """第二次 GET report 应命中缓存，不触发额外 LLM 调用。"""
        mock_openai.return_value.chat.completions.create.return_value = _mock_llm_response()

        create_resp = client.post(
            "/api/sessions",
            json={"persona_id": "price_sensitive_midcareer", "difficulty": "medium"},
        )
        session_id = create_resp.json()["session_id"]

        client.post(
            f"/api/sessions/{session_id}/chat",
            json={"message": "您好"},
        )

        with patch(
            "peilian.judge.judge_agent"
        ) as mock_ja, patch(
            "peilian.judge.judge_customer"
        ) as mock_jc:
            from peilian.judge import AgentJudgeReport, CustomerJudgeReport, DimensionScore

            mock_ja.return_value = AgentJudgeReport(
                scores=tuple(
                    DimensionScore(dimension=d, label=d, score=3, reasoning="test")
                    for d in ("professionalism", "empathy", "structure", "objection_handling")
                ),
                overall_comment="test",
                raw_response="{}",
            )
            mock_jc.return_value = CustomerJudgeReport(
                premature_disclosure_issues=(),
                inconsistency_issues=(),
                overall_comment="test",
                raw_response="{}",
            )

            report_resp1 = client.get(f"/api/sessions/{session_id}/report")
            assert report_resp1.status_code == 200
            call_count_after_first = mock_ja.call_count

            report_resp2 = client.get(f"/api/sessions/{session_id}/report")
            assert report_resp2.status_code == 200
            assert mock_ja.call_count == call_count_after_first

    def test_report_session_not_found(self, client: TestClient) -> None:
        resp = client.get("/api/sessions/nonexistent/report")
        assert resp.status_code == 404

    @patch("peilian.dialogue.OpenAI")
    def test_chat_rejected_after_report_completed(
        self, mock_openai: MagicMock, client: TestClient
    ) -> None:
        mock_openai.return_value.chat.completions.create.return_value = _mock_llm_response()
        create_resp = client.post(
            "/api/sessions",
            json={"persona_id": "price_sensitive_midcareer", "difficulty": "medium"},
        )
        session_id = create_resp.json()["session_id"]
        client.post(f"/api/sessions/{session_id}/chat", json={"message": "您好"})

        from peilian.judge import AgentJudgeReport, CustomerJudgeReport, DimensionScore

        with patch("peilian.judge.judge_agent") as mock_ja, patch(
            "peilian.judge.judge_customer"
        ) as mock_jc:
            mock_ja.return_value = AgentJudgeReport(
                scores=tuple(
                    DimensionScore(dimension=d, label=d, score=3, reasoning="test")
                    for d in ("professionalism", "empathy", "structure", "objection_handling")
                ),
                overall_comment="test",
                raw_response="{}",
            )
            mock_jc.return_value = CustomerJudgeReport(
                premature_disclosure_issues=(),
                inconsistency_issues=(),
                overall_comment="test",
                raw_response="{}",
            )
            assert client.get(f"/api/sessions/{session_id}/report").status_code == 200

        chat_resp = client.post(
            f"/api/sessions/{session_id}/chat",
            json={"message": "报告之后继续说一句"},
        )
        assert chat_resp.status_code == 422


# ---------------------------------------------------------------------------
# e2e 集成测试
# ---------------------------------------------------------------------------

class TestE2E:
    @patch("peilian.dialogue.OpenAI")
    def test_full_flow(self, mock_openai: MagicMock, client: TestClient) -> None:
        """创建会话 → 发 3 条消息 → 取报告 全链路。"""
        mock_openai.return_value.chat.completions.create.return_value = _mock_llm_response(
            "好的，我听听看。"
        )

        from peilian.judge import AgentJudgeReport, CustomerJudgeReport, DimensionScore

        with patch("peilian.judge.judge_agent") as mock_ja, patch(
            "peilian.judge.judge_customer"
        ) as mock_jc:
            mock_ja.return_value = AgentJudgeReport(
                scores=tuple(
                    DimensionScore(dimension=d, label=d, score=4, reasoning="e2e test")
                    for d in ("professionalism", "empathy", "structure", "objection_handling")
                ),
                overall_comment="e2e overall",
                raw_response="{}",
            )
            mock_jc.return_value = CustomerJudgeReport(
                premature_disclosure_issues=(),
                inconsistency_issues=(),
                overall_comment="客户行为正常",
                raw_response="{}",
            )

            # 1. 创建会话
            create_resp = client.post(
                "/api/sessions",
                json={"persona_id": "price_sensitive_midcareer", "difficulty": "medium"},
            )
            assert create_resp.status_code == 201
            session_id = create_resp.json()["session_id"]

            # 2. 发 3 条消息
            messages = [
                "您好，想了解下您家里几口人？",
                "您目前有购买什么保险吗？",
                "保证收益，稳赚不赔！",
            ]
            for msg in messages:
                chat_resp = client.post(
                    f"/api/sessions/{session_id}/chat",
                    json={"message": msg},
                )
                assert chat_resp.status_code == 200

            # 3. 取报告
            report_resp = client.get(f"/api/sessions/{session_id}/report")
            assert report_resp.status_code == 200
            report = report_resp.json()

            # 校验 compliance_score
            assert "compliance_score" in report
            assert isinstance(report["compliance_score"], int)
            assert 0 <= report["compliance_score"] <= 5

            # 校验 judge_result 结构
            jr = report["judge_result"]
            assert "evaluation_report" in jr
            assert "agent_report" in jr
            assert "customer_report" in jr

            # 校验 agent_report scores 按 dimension 查找
            scores = jr["agent_report"]["scores"]
            assert len(scores) == 4
            dim_set = {s["dimension"] for s in scores}
            assert "professionalism" in dim_set
            assert "objection_handling" in dim_set

            # 校验 messages 与 annotations
            assert len(report["messages"]) > 0
            assert len(report["annotations"]) > 0

            # 校验 annotations 包含 agent_turn_number
            ann = report["annotations"][0]
            assert "turn_index" in ann
            assert "agent_turn_number" in ann
            assert "categories" in ann
            assert "compliance_hits" in ann

            # 校验 customer_report 存在
            cr = jr["customer_report"]
            assert "premature_disclosure_issues" in cr
            assert "inconsistency_issues" in cr
            assert "overall_comment" in cr

            # 校验 status 变为 completed
            session_resp = client.get(f"/api/sessions/{session_id}")
            assert session_resp.json()["status"] == "completed"
