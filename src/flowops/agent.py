from __future__ import annotations

import re
import uuid
from dataclasses import dataclass

from .models import AuditEvent, Intent, ToolCall, WorkflowResult, WorkflowStatus
from .store import AfterSalesStore
from .tools import ToolRegistry


ORDER_PATTERN = re.compile(r"\bA\d{4}\b", re.IGNORECASE)


@dataclass(slots=True)
class RuleIntentClassifier:
    def classify(self, message: str) -> Intent:
        text = message.lower()
        if any(word in text for word in ("政策", "规则", "知识", "policy")):
            return Intent.KNOWLEDGE
        if any(word in text for word in ("退款", "退货", "refund", "退钱")):
            return Intent.REFUND
        if any(word in text for word in ("物流", "快递", "配送", "tracking", "where is", "到哪")):
            return Intent.LOGISTICS
        if any(word in text for word in ("订单", "order", "买了什么", "订单状态")):
            return Intent.ORDER
        if any(word in text for word in ("how", "多久", "什么")):
            return Intent.KNOWLEDGE
        return Intent.UNKNOWN


class FlowOpsAgent:
    def __init__(
        self,
        store: AfterSalesStore | None = None,
        classifier: RuleIntentClassifier | None = None,
        tools: ToolRegistry | None = None,
        max_steps: int = 6,
    ):
        self.store = store or AfterSalesStore()
        self.tools = tools or ToolRegistry(self.store)
        self.classifier = classifier or RuleIntentClassifier()
        self.max_steps = max_steps

    def _event(self, trace_id: str, stage: str, state: str, message: str, **data) -> AuditEvent:
        return AuditEvent(trace_id, stage, state, message, data)

    def _order_id(self, message: str) -> str | None:
        match = ORDER_PATTERN.search(message.upper())
        return match.group(0) if match else None

    def _tool(self, calls: list[ToolCall], audit: list[AuditEvent], trace: str,
              name: str, arguments: dict[str, str]) -> ToolCall:
        call = self.tools.call(name, arguments)
        calls.append(call)
        audit.append(self._event(trace, "tool", "tool_ok" if call.ok else "tool_error", name, arguments=arguments, result=call.result))
        return call

    def _refund(self, message: str, order_id: str, trace: str, calls: list[ToolCall], audit: list[AuditEvent]) -> tuple[str, WorkflowStatus]:
        status_call = self._tool(calls, audit, trace, "get_refund_status", {"order_id": order_id})
        if not status_call.ok:
            return "I could not read the refund status. A human specialist will review this case.", WorkflowStatus.HUMAN_HANDOFF
        status = status_call.result
        if status["refund_status"] == "completed":
            return f"Order {order_id} already has a completed refund for ¥{status['amount']:.2f}.", WorkflowStatus.COMPLETED
        explicit_retry = any(word in message.lower() for word in ("失败", "failed", "retry", "重试"))
        if not status["eligible"] and not explicit_retry:
            return "This order is outside the automatic refund path. I will transfer it to a human specialist.", WorkflowStatus.HUMAN_HANDOFF
        if not explicit_retry:
            return f"Order {order_id} needs a refund review. I can check the transaction and retry once if the provider reports a failure.", WorkflowStatus.COMPLETED
        key = f"refund:{order_id}:attempt"
        first = self._tool(calls, audit, trace, "retry_refund", {"order_id": order_id, "idempotency_key": key})
        if first.ok and first.result.get("status") == "completed":
            return f"The refund for {order_id} completed successfully on attempt {first.result['attempt']}.", WorkflowStatus.COMPLETED
        second = self._tool(calls, audit, trace, "retry_refund", {"order_id": order_id, "idempotency_key": f"{key}:second"})
        if second.ok and second.result.get("status") == "completed":
            return f"The refund for {order_id} completed successfully on the second attempt.", WorkflowStatus.COMPLETED
        return "The provider did not confirm the refund after two attempts. Automated processing is stopped and the case is transferred to a human specialist.", WorkflowStatus.HUMAN_HANDOFF

    def run(self, message: str, history: list[str] | None = None) -> WorkflowResult:
        trace = uuid.uuid4().hex[:16]
        calls: list[ToolCall] = []
        audit: list[AuditEvent] = []
        state: dict[str, object] = {"step": 0, "history_size": len(history or [])}
        text = message.strip()
        if not text:
            audit.append(self._event(trace, "validate", "needs_clarification", "empty_message"))
            return WorkflowResult("Please describe the order, logistics, or refund issue you need help with.", Intent.UNKNOWN, WorkflowStatus.NEEDS_CLARIFICATION, trace, calls, audit, state)
        intent = self.classifier.classify(text)
        order_id = self._order_id(text)
        state.update({"intent": intent.value, "order_id": order_id})
        audit.append(self._event(trace, "classify", "routed", "intent_classified", intent=intent.value, order_id=order_id))
        if intent in {Intent.ORDER, Intent.LOGISTICS, Intent.REFUND} and not order_id:
            audit.append(self._event(trace, "validate", "needs_clarification", "order_id_required"))
            return WorkflowResult("Please provide the order number, for example A1001.", intent, WorkflowStatus.NEEDS_CLARIFICATION, trace, calls, audit, state)
        if intent == Intent.ORDER:
            call = self._tool(calls, audit, trace, "get_order", {"order_id": order_id})
            if not call.ok:
                answer, status = "I could not find that order. A human specialist can verify it.", WorkflowStatus.HUMAN_HANDOFF
            else:
                result = call.result
                answer = f"Order {order_id}: {result['item']}, status {result['status']}, amount ¥{result['amount']:.2f}."
                status = WorkflowStatus.COMPLETED
        elif intent == Intent.LOGISTICS:
            call = self._tool(calls, audit, trace, "get_logistics", {"order_id": order_id})
            if not call.ok:
                answer, status = "I could not read the shipment status. A human specialist can verify it.", WorkflowStatus.HUMAN_HANDOFF
            else:
                result = call.result
                tracking = f" Tracking number: {result['tracking_no']}." if result.get("tracking_no") else ""
                answer = f"Order {order_id} logistics status: {result['status']}.{tracking}"
                status = WorkflowStatus.COMPLETED
        elif intent == Intent.REFUND:
            answer, status = self._refund(text, order_id, trace, calls, audit)
        elif intent == Intent.KNOWLEDGE:
            answer, status = ("Automatic refunds require confirmed payment, no shipment, and a request within seven calendar days. Other cases need manual review.", WorkflowStatus.COMPLETED)
        else:
            answer, status = ("I can help with order status, logistics, refunds, or after-sales policy. Which one do you need?", WorkflowStatus.NEEDS_CLARIFICATION)
        state["step"] = min(self.max_steps, len(calls) + 1)
        state["tool_call_count"] = len(calls)
        audit.append(self._event(trace, "complete", status.value, "workflow_finished", tool_call_count=len(calls)))
        return WorkflowResult(answer, intent, status, trace, calls, audit, state)
