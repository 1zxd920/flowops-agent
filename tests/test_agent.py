import unittest

from flowops.agent import FlowOpsAgent
from flowops.models import WorkflowStatus


class AgentTests(unittest.TestCase):
    def setUp(self):
        self.agent = FlowOpsAgent()

    def test_logistics_route(self):
        result = self.agent.run("Where is order A1001?")
        self.assertEqual("logistics", result.intent.value)
        self.assertEqual(WorkflowStatus.COMPLETED, result.status)
        self.assertEqual("get_logistics", result.tool_calls[0].name)

    def test_missing_order_id_clarifies(self):
        result = self.agent.run("Can I get a refund?")
        self.assertEqual(WorkflowStatus.NEEDS_CLARIFICATION, result.status)
        self.assertEqual([], result.tool_calls)

    def test_failed_refund_handoffs_after_two_attempts(self):
        result = self.agent.run("The refund failed twice for A1002")
        self.assertEqual(WorkflowStatus.HUMAN_HANDOFF, result.status)
        self.assertEqual(3, len(result.tool_calls))
        self.assertEqual("retry_refund", result.tool_calls[-1].name)
        self.assertIn("two attempts", result.answer)

    def test_knowledge_policy_does_not_call_tools(self):
        result = self.agent.run("What is the refund policy?")
        self.assertEqual("knowledge", result.intent.value)
        self.assertEqual([], result.tool_calls)
        self.assertIn("seven calendar days", result.answer)


if __name__ == "__main__":
    unittest.main()

