# FlowOps Agent

FlowOps is a runnable reference implementation of an after-sales multi-agent
workflow. It demonstrates the engineering around an Agent system: a
Supervisor routes requests to bounded specialist agents, tools expose explicit
schemas, state transitions are auditable, and risky operations fail closed to
human support.

The project uses only the Python standard library and deterministic fixtures.
It is designed to run in a clean environment without API keys, Redis, MySQL,
or an MCP server. The tool registry and model adapter are replaceable seams
for production integrations.

## What it demonstrates

- Supervisor routing for order, logistics, refund, and knowledge intents
- Explicit tool contracts with required fields, type checks, and safe errors
- MCP-style tool metadata and a registry boundary
- Idempotent refund actions, one retry, timeout simulation, and fallback
- Human handoff for policy exceptions, missing data, and repeated failures
- Conversation history and SSE streaming responses
- Structured audit events with trace IDs and state transitions
- 180-case regression fixture and quality metrics

## Quick start

```bash
python -m venv .venv
.venv/Scripts/activate        # Windows
python -m pip install -e .

flowops demo
flowops evaluate examples/regression.jsonl
flowops serve --port 8090
```

On macOS/Linux, activate the environment with `source .venv/bin/activate`.

## CLI examples

```bash
flowops ask "Where is order A1001?"
flowops ask "Can I refund order A1001?"
flowops ask "The refund failed twice for A1002" 
```

The CLI prints a JSON response containing `answer`, `intent`, `status`,
`trace_id`, `tool_calls`, and `audit`.

## HTTP API

```bash
curl http://localhost:8090/health

curl -X POST http://localhost:8090/v1/chat \
  -H "Content-Type: application/json" \
  -d '{"message":"Where is order A1001?","history":[]}'

curl -N -X POST http://localhost:8090/v1/chat/stream \
  -H "Content-Type: application/json" \
  -d '{"message":"Can I refund order A1001?"}'
```

The stream emits `event: token` lines followed by one `event: done` payload.

## Workflow

```text
message -> intent classifier -> specialist agent -> tool registry
                                      |                  |
                                      +---- retry -------+
                                      |                  |
                         answer / human handoff <- audit log
```

Refunds are intentionally conservative: eligibility is checked first, the
operation is sent with an idempotency key, and a second failure ends automated
processing. The demo store exposes failure fixtures so the path can be tested.

## Regression evaluation

```bash
flowops evaluate examples/regression.jsonl
```

The evaluator reports intent accuracy, expected-tool accuracy, safe handoff
rate, and response keyword coverage. The included 180 rows are generated from
the deterministic fixture and are a regression baseline, not a production KPI.

## Testing

```bash
python -m unittest discover -s tests -v
```

## Production extension points

- Replace `RuleIntentClassifier` with an LLM classifier constrained to the
  `Intent` enum and JSON schema.
- Replace `ToolRegistry` calls with MCP transport while preserving contracts.
- Persist `AfterSalesStore` and `AuditLog` in MySQL / Redis.
- Add auth, PII redaction, rate limits, and tenant-level authorization.
- Instrument tool latency and model usage with OpenTelemetry or Langfuse.

## License

MIT

