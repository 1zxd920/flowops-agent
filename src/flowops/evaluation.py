from __future__ import annotations

import json
from pathlib import Path
from statistics import mean

from .agent import FlowOpsAgent
from .models import RegressionCase


def load_cases(path: str | Path) -> list[RegressionCase]:
    with Path(path).open("r", encoding="utf-8") as stream:
        return [RegressionCase(**json.loads(line)) for line in stream if line.strip()]


def evaluate(agent: FlowOpsAgent, cases: list[RegressionCase]) -> dict[str, float]:
    intent, tool, status, coverage, handoff = [], [], [], [], []
    for case in cases:
        result = agent.run(case.message)
        intent.append(result.intent.value == case.expected_intent)
        names = [call.name for call in result.tool_calls]
        tool.append(case.expected_tool is None or case.expected_tool in names)
        status.append(result.status.value == case.expected_status)
        answer = result.answer.lower()
        coverage.append(sum(word.lower() in answer for word in case.expected_keywords) / max(1, len(case.expected_keywords)))
        handoff.append(result.status.value == "human_handoff" if case.expected_status == "human_handoff" else True)
    avg = lambda values: round(mean(values), 4) if values else 0.0
    return {
        "cases": float(len(cases)),
        "intent_accuracy": avg(intent),
        "expected_tool_accuracy": avg(tool),
        "status_accuracy": avg(status),
        "keyword_coverage": avg(coverage),
        "safe_handoff_accuracy": avg(handoff),
    }

