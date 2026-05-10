"""P5 Pydantic v2 请求/响应模型。

独立于 P0-P4 dataclass，提供 from_dataclass 转换，隔离 OpenAPI schema 差异。
"""

from __future__ import annotations

from pydantic import BaseModel


# ---------------------------------------------------------------------------
# 请求模型
# ---------------------------------------------------------------------------

class CreateSessionRequest(BaseModel):
    persona_id: str
    difficulty: str = "medium"


class ChatRequest(BaseModel):
    message: str


# ---------------------------------------------------------------------------
# 响应模型
# ---------------------------------------------------------------------------

class PersonaSummary(BaseModel):
    id: str
    name: str
    age: int
    occupation: str
    family: str
    income_level: str
    hidden_concerns_labels: list[str]


class SessionResponse(BaseModel):
    session_id: str
    persona_name: str
    difficulty: str
    turn_count: int
    status: str


class ChatResponse(BaseModel):
    response: str
    turn_count: int


class ComplianceHitResponse(BaseModel):
    turn_index: int
    agent_turn_number: int
    excerpt: str
    rule_id: str
    rule_label: str
    matched_keyword: str

    @classmethod
    def from_dataclass(cls, hit: object) -> ComplianceHitResponse:
        return cls(
            turn_index=hit.turn_index,
            agent_turn_number=hit.agent_turn_number,
            excerpt=hit.excerpt,
            rule_id=hit.rule_id,
            rule_label=hit.rule_label,
            matched_keyword=hit.matched_keyword,
        )


class DimensionScoreResponse(BaseModel):
    dimension: str
    label: str
    score: int
    reasoning: str

    @classmethod
    def from_dataclass(cls, ds: object) -> DimensionScoreResponse:
        return cls(
            dimension=ds.dimension,
            label=ds.label,
            score=ds.score,
            reasoning=ds.reasoning,
        )


class AgentJudgeReportResponse(BaseModel):
    scores: list[DimensionScoreResponse]
    overall_comment: str

    @classmethod
    def from_dataclass(cls, report: object) -> AgentJudgeReportResponse:
        return cls(
            scores=[DimensionScoreResponse.from_dataclass(s) for s in report.scores],
            overall_comment=report.overall_comment,
        )


class IssueResponse(BaseModel):
    turn_index: int
    agent_turn_number: int
    related_turn_indices: list[int]
    excerpt: str
    violation_type: str
    protected_field: str
    reasoning: str

    @classmethod
    def from_dataclass(cls, issue: object) -> IssueResponse:
        return cls(
            turn_index=issue.turn_index,
            agent_turn_number=issue.agent_turn_number,
            related_turn_indices=list(issue.related_turn_indices),
            excerpt=issue.excerpt,
            violation_type=issue.violation_type,
            protected_field=issue.protected_field,
            reasoning=issue.reasoning,
        )


class CustomerJudgeReportResponse(BaseModel):
    premature_disclosure_issues: list[IssueResponse]
    inconsistency_issues: list[IssueResponse]
    overall_comment: str

    @classmethod
    def from_dataclass(cls, report: object) -> CustomerJudgeReportResponse:
        return cls(
            premature_disclosure_issues=[
                IssueResponse.from_dataclass(i) for i in report.premature_disclosure_issues
            ],
            inconsistency_issues=[
                IssueResponse.from_dataclass(i) for i in report.inconsistency_issues
            ],
            overall_comment=report.overall_comment,
        )


class EvaluationReportResponse(BaseModel):
    total_categories: int
    covered_categories: list[str]
    missed_categories: list[str]
    compliance_hits: list[ComplianceHitResponse]

    @classmethod
    def from_dataclass(cls, report: object) -> EvaluationReportResponse:
        return cls(
            total_categories=report.total_categories,
            covered_categories=list(report.covered_categories),
            missed_categories=list(report.missed_categories),
            compliance_hits=[
                ComplianceHitResponse.from_dataclass(h) for h in report.compliance_hits
            ],
        )


class JudgeResultResponse(BaseModel):
    evaluation_report: EvaluationReportResponse
    agent_report: AgentJudgeReportResponse
    customer_report: CustomerJudgeReportResponse

    @classmethod
    def from_dataclass(cls, result: object) -> JudgeResultResponse:
        return cls(
            evaluation_report=EvaluationReportResponse.from_dataclass(
                result.evaluation_report
            ),
            agent_report=AgentJudgeReportResponse.from_dataclass(result.agent_report),
            customer_report=CustomerJudgeReportResponse.from_dataclass(
                result.customer_report
            ),
        )


class MessageResponse(BaseModel):
    turn_index: int
    role: str
    content: str


class AnnotationResponse(BaseModel):
    turn_index: int
    agent_turn_number: int
    categories: list[str]
    compliance_hits: list[ComplianceHitResponse]


class ReportResponse(BaseModel):
    compliance_score: int
    judge_result: JudgeResultResponse
    messages: list[MessageResponse]
    annotations: list[AnnotationResponse]
