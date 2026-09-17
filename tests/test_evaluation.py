import unittest

from flowops.agent import FlowOpsAgent
from flowops.evaluation import evaluate
from flowops.models import RegressionCase


class EvaluationTests(unittest.TestCase):
    def test_evaluation_report(self):
        report = evaluate(FlowOpsAgent(), [
            RegressionCase("Where is order A1001?", "logistics", "get_logistics", "completed", ["delivered"]),
            RegressionCase("The refund failed twice for A1002", "refund", "retry_refund", "human_handoff", ["two attempts"]),
        ])
        self.assertEqual(1.0, report["intent_accuracy"])
        self.assertEqual(1.0, report["status_accuracy"])


if __name__ == "__main__":
    unittest.main()

