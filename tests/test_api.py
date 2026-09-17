import json
import threading
import unittest
from http.client import HTTPConnection
from http.server import ThreadingHTTPServer

from flowops.api import FlowOpsHandler


class ApiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server = ThreadingHTTPServer(("127.0.0.1", 0), FlowOpsHandler)
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()
        cls.port = cls.server.server_address[1]

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()

    def test_health(self):
        connection = HTTPConnection("127.0.0.1", self.port)
        connection.request("GET", "/health")
        response = connection.getresponse()
        body = json.loads(response.read())
        self.assertEqual(200, response.status)
        self.assertEqual("ok", body["status"])

    def test_chat(self):
        connection = HTTPConnection("127.0.0.1", self.port)
        data = json.dumps({"message": "Where is order A1001?"})
        connection.request("POST", "/v1/chat", data, {"Content-Type": "application/json"})
        response = connection.getresponse()
        body = json.loads(response.read())
        self.assertEqual(200, response.status)
        self.assertEqual("logistics", body["intent"])


if __name__ == "__main__":
    unittest.main()

