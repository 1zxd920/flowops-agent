from __future__ import annotations

import argparse
import json

from .agent import FlowOpsAgent
from .api import serve
from .evaluation import evaluate, load_cases


def main() -> None:
    parser = argparse.ArgumentParser(prog="flowops")
    commands = parser.add_subparsers(dest="command", required=True)
    ask = commands.add_parser("ask")
    ask.add_argument("message")
    evaluate_cmd = commands.add_parser("evaluate")
    evaluate_cmd.add_argument("dataset")
    commands.add_parser("demo")
    server = commands.add_parser("serve")
    server.add_argument("--host", default="127.0.0.1")
    server.add_argument("--port", type=int, default=8090)
    args = parser.parse_args()
    agent = FlowOpsAgent()
    if args.command == "ask":
        print(json.dumps(agent.run(args.message).to_dict(), ensure_ascii=False, indent=2))
    elif args.command == "evaluate":
        print(json.dumps(evaluate(agent, load_cases(args.dataset)), indent=2))
    elif args.command == "demo":
        for message in ["Where is order A1001?", "Can I refund order A1001?", "The refund failed twice for A1002"]:
            print(json.dumps(agent.run(message).to_dict(), ensure_ascii=False, indent=2))
    elif args.command == "serve":
        serve(args.host, args.port)

