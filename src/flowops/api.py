from __future__ import annotations

import json
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from .agent import FlowOpsAgent


class FlowOpsHandler(BaseHTTPRequestHandler):
    agent = FlowOpsAgent()

    def _json(self, status: int, payload: dict) -> None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _body(self) -> dict:
        length = int(self.headers.get("Content-Length", "0"))
        return json.loads(self.rfile.read(length) or b"{}")

    def do_GET(self) -> None:  # noqa: N802
        if self.path == "/health":
            self._json(HTTPStatus.OK, {"status": "ok", "tools": len(self.agent.tools.specs)})
        elif self.path == "/v1/tools":
            self._json(HTTPStatus.OK, {"tools": self.agent.tools.list_tools()})
        else:
            self._json(HTTPStatus.NOT_FOUND, {"error": "not_found"})

    def do_POST(self) -> None:  # noqa: N802
        try:
            payload = self._body()
            if self.path == "/v1/chat":
                message = str(payload.get("message", ""))
                result = self.agent.run(message, list(payload.get("history", [])))
                self._json(HTTPStatus.OK, result.to_dict())
                return
            if self.path == "/v1/chat/stream":
                message = str(payload.get("message", ""))
                result = self.agent.run(message, list(payload.get("history", [])))
                self.send_response(HTTPStatus.OK)
                self.send_header("Content-Type", "text/event-stream; charset=utf-8")
                self.send_header("Cache-Control", "no-cache")
                self.end_headers()
                words = result.answer.split(" ")
                for word in words:
                    self.wfile.write(f"event: token\ndata: {json.dumps(word + ' ', ensure_ascii=False)}\n\n".encode("utf-8"))
                self.wfile.write(f"event: done\ndata: {json.dumps(result.to_dict(), ensure_ascii=False)}\n\n".encode("utf-8"))
                return
            self._json(HTTPStatus.NOT_FOUND, {"error": "not_found"})
        except (ValueError, json.JSONDecodeError) as exc:
            self._json(HTTPStatus.BAD_REQUEST, {"error": str(exc)})

    def log_message(self, format: str, *args) -> None:
        return


def serve(host: str, port: int) -> None:
    server = ThreadingHTTPServer((host, port), FlowOpsHandler)
    print(f"FlowOps listening on http://{host}:{port}")
    server.serve_forever()

