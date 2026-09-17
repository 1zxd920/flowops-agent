from __future__ import annotations

from dataclasses import asdict, dataclass, field
from enum import Enum
from typing import Any


class Intent(str, Enum):
    ORDER = "order"
    LOGISTICS = "logistics"
    REFUND = "refund"
    KNOWLEDGE = "knowledge"
    UNKNOWN = "unknown"


class WorkflowStatus(str, Enum):
    COMPLETED = "completed"
    NEEDS_CLARIFICATION = "needs_clarification"
    HUMAN_HANDOFF = "human_handoff"
    FAILED = "failed"


@dataclass(slots=True)
class Order:
    order_id: str
    customer_id: str
    item: str
    amount: float
    status: str
    tracking_no: str | None
    shipped: bool
    refund_status: str


@dataclass(slots=True)
class ToolCall:
    name: str
    arguments: dict[str, Any]
    ok: bool
    result: dict[str, Any]
    latency_ms: float

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class AuditEvent:
    trace_id: str
    stage: str
    state: str
    message: str
    data: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class WorkflowResult:
    answer: str
    intent: Intent
    status: WorkflowStatus
    trace_id: str
    tool_calls: list[ToolCall] = field(default_factory=list)
    audit: list[AuditEvent] = field(default_factory=list)
    state: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "answer": self.answer,
            "intent": self.intent.value,
            "status": self.status.value,
            "trace_id": self.trace_id,
            "tool_calls": [call.to_dict() for call in self.tool_calls],
            "audit": [event.to_dict() for event in self.audit],
            "state": self.state,
        }


@dataclass(slots=True)
class RegressionCase:
    message: str
    expected_intent: str
    expected_tool: str | None
    expected_status: str
    expected_keywords: list[str]

