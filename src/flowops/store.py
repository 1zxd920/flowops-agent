from __future__ import annotations

from dataclasses import replace
from threading import RLock

from .models import Order


class StoreError(RuntimeError):
    pass


class AfterSalesStore:
    """Small in-memory store with deterministic fixtures and atomic updates."""

    def __init__(self, orders: list[Order] | None = None):
        self._lock = RLock()
        self.orders = {
            item.order_id: item for item in (orders or [
                Order("A1001", "C001", "Wireless keyboard", 199.0, "delivered", "SF1001", True, "not_requested"),
                Order("A1002", "C002", "USB-C dock", 399.0, "in_transit", "SF1002", True, "failed"),
                Order("A1003", "C003", "Desk lamp", 129.0, "paid", None, False, "not_requested"),
                Order("A1004", "C004", "Monitor arm", 289.0, "delivered", "SF1004", True, "completed"),
            ])
        }
        self._refund_attempts: dict[str, int] = {}
        self._idempotency_results: dict[str, dict] = {}

    def _get(self, order_id: str) -> Order:
        with self._lock:
            if order_id not in self.orders:
                raise StoreError(f"order_not_found:{order_id}")
            return replace(self.orders[order_id])

    def get_order(self, order_id: str) -> dict:
        order = self._get(order_id)
        return {
            "order_id": order.order_id,
            "customer_id": order.customer_id,
            "item": order.item,
            "amount": order.amount,
            "status": order.status,
            "tracking_no": order.tracking_no,
            "shipped": order.shipped,
            "refund_status": order.refund_status,
        }

    def get_logistics(self, order_id: str) -> dict:
        order = self._get(order_id)
        if not order.tracking_no:
            return {"order_id": order_id, "status": "not_shipped", "tracking_no": None}
        status = "delivered" if order.status == "delivered" else "in_transit"
        return {
            "order_id": order_id,
            "status": status,
            "tracking_no": order.tracking_no,
            "last_update": "2026-09-15 18:20",
        }

    def get_refund_status(self, order_id: str) -> dict:
        order = self._get(order_id)
        return {
            "order_id": order_id,
            "refund_status": order.refund_status,
            "amount": order.amount,
            "eligible": (
                order.refund_status == "not_requested"
                and not order.shipped
            ),
        }

    def retry_refund(self, order_id: str, idempotency_key: str) -> dict:
        if not idempotency_key or len(idempotency_key) > 96:
            raise StoreError("invalid_idempotency_key")
        with self._lock:
            if idempotency_key in self._idempotency_results:
                return dict(self._idempotency_results[idempotency_key])
            order = self._get(order_id)
            if order.refund_status == "completed":
                result = {"order_id": order_id, "status": "already_completed", "attempt": 0}
                self._idempotency_results[idempotency_key] = result
                return dict(result)
            attempts = self._refund_attempts.get(order_id, 0) + 1
            self._refund_attempts[order_id] = attempts
            # A1002 is the controlled failure fixture: both attempts fail.
            if order_id == "A1002":
                result = {"order_id": order_id, "status": "failed", "attempt": attempts, "error": "payment_provider_timeout"}
            else:
                order.refund_status = "completed"
                self.orders[order_id] = order
                result = {"order_id": order_id, "status": "completed", "attempt": attempts}
            self._idempotency_results[idempotency_key] = result
            return dict(result)

