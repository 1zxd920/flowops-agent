import unittest

from flowops.store import AfterSalesStore
from flowops.tools import ToolRegistry


class ToolTests(unittest.TestCase):
    def setUp(self):
        self.tools = ToolRegistry(AfterSalesStore())

    def test_missing_argument_is_safe(self):
        call = self.tools.call("get_order", {})
        self.assertFalse(call.ok)
        self.assertIn("missing_arguments", call.result["error"])

    def test_unknown_argument_is_rejected(self):
        call = self.tools.call("get_order", {"order_id": "A1001", "admin": "true"})
        self.assertFalse(call.ok)
        self.assertIn("unexpected_arguments", call.result["error"])

    def test_idempotency_returns_same_result(self):
        first = self.tools.call("retry_refund", {"order_id": "A1001", "idempotency_key": "k1"})
        second = self.tools.call("retry_refund", {"order_id": "A1001", "idempotency_key": "k1"})
        self.assertEqual(first.result, second.result)


if __name__ == "__main__":
    unittest.main()

