"""Generate a deterministic 180-case regression set from the fixture scenarios."""

import json
from pathlib import Path


CASES = [
    {"message": "Where is order A1001?", "expected_intent": "logistics", "expected_tool": "get_logistics", "expected_status": "completed", "expected_keywords": ["A1001", "delivered"]},
    {"message": "What did I buy in order A1003?", "expected_intent": "order", "expected_tool": "get_order", "expected_status": "completed", "expected_keywords": ["A1003", "Desk lamp"]},
    {"message": "Can I refund order A1001?", "expected_intent": "refund", "expected_tool": "get_refund_status", "expected_status": "human_handoff", "expected_keywords": ["human", "specialist"]},
    {"message": "The refund failed twice for A1002", "expected_intent": "refund", "expected_tool": "retry_refund", "expected_status": "human_handoff", "expected_keywords": ["two attempts", "human"]},
    {"message": "What is the refund policy?", "expected_intent": "knowledge", "expected_tool": None, "expected_status": "completed", "expected_keywords": ["seven calendar days", "no shipment"]},
    {"message": "I need help", "expected_intent": "unknown", "expected_tool": None, "expected_status": "needs_clarification", "expected_keywords": ["order", "logistics"]},
    {"message": "Where is order A1002?", "expected_intent": "logistics", "expected_tool": "get_logistics", "expected_status": "completed", "expected_keywords": ["A1002", "in_transit"]},
    {"message": "Check refund status for order A1004", "expected_intent": "refund", "expected_tool": "get_refund_status", "expected_status": "completed", "expected_keywords": ["completed"]},
]


def main() -> None:
    target = Path(__file__).with_name("regression.jsonl")
    rows = [CASES[index % len(CASES)] for index in range(180)]
    with target.open("w", encoding="utf-8") as stream:
        for row in rows:
            stream.write(json.dumps(row, ensure_ascii=False) + "\n")


if __name__ == "__main__":
    main()

