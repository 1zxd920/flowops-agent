from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Any, Callable

from .models import ToolCall
from .store import AfterSalesStore, StoreError


class ToolContractError(ValueError):
    pass


@dataclass(slots=True)
class ToolSpec:
    name: str
    description: str
    required: tuple[str, ...]
    handler: Callable[..., dict]

    def schema(self) -> dict:
        return {
            "name": self.name,
            "description": self.description,
            "inputSchema": {
                "type": "object",
                "required": list(self.required),
                "additionalProperties": False,
            },
        }


class ToolRegistry:
    """MCP-style registry: metadata and invocation are kept behind one boundary."""

    def __init__(self, store: AfterSalesStore):
        self.store = store
        self.specs = {
            "get_order": ToolSpec("get_order", "Read order status and amount.", ("order_id",), store.get_order),
            "get_logistics": ToolSpec("get_logistics", "Read shipment tracking status.", ("order_id",), store.get_logistics),
            "get_refund_status": ToolSpec("get_refund_status", "Check refund state and basic eligibility.", ("order_id",), store.get_refund_status),
            "retry_refund": ToolSpec("retry_refund", "Retry a refund once with an idempotency key.", ("order_id", "idempotency_key"), store.retry_refund),
        }

    def list_tools(self) -> list[dict]:
        return [spec.schema() for spec in self.specs.values()]

    def call(self, name: str, arguments: dict[str, Any]) -> ToolCall:
        started = time.perf_counter()
        spec = self.specs.get(name)
        try:
            if not spec:
                raise ToolContractError(f"unknown_tool:{name}")
            if set(arguments) - set(spec.required):
                unknown = sorted(set(arguments) - set(spec.required))
                raise ToolContractError(f"unexpected_arguments:{unknown}")
            missing = [field for field in spec.required if not arguments.get(field)]
            if missing:
                raise ToolContractError(f"missing_arguments:{missing}")
            if not all(isinstance(value, str) for value in arguments.values()):
                raise ToolContractError("arguments_must_be_strings")
            result = spec.handler(**arguments)
            return ToolCall(name, arguments, True, result, round((time.perf_counter() - started) * 1000, 3))
        except (ToolContractError, StoreError) as exc:
            return ToolCall(name, arguments, False, {"error": str(exc)}, round((time.perf_counter() - started) * 1000, 3))

