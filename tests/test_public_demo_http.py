"""HTTP regressions for public input and private runtime artifacts."""

from __future__ import annotations

import http.client
import json
import threading
import unittest
from unittest.mock import patch

from demo.live import server


class PublicDemoHttpTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.http = server.ThreadingHTTPServer(("127.0.0.1", 0), server.Handler)
        cls.thread = threading.Thread(target=cls.http.serve_forever, daemon=True)
        cls.thread.start()

    @classmethod
    def tearDownClass(cls) -> None:
        cls.http.shutdown()
        cls.http.server_close()
        cls.thread.join(timeout=5)

    def request(self, path: str, method: str = "GET", body: object = None) -> tuple[int, bytes]:
        connection = http.client.HTTPConnection(*self.http.server_address, timeout=10)
        encoded = None if body is None else json.dumps(body).encode()
        connection.request(method, path, body=encoded, headers={"Content-Type": "application/json"})
        response = connection.getresponse()
        result = response.status, response.read()
        connection.close()
        return result

    def test_home_and_health_are_available(self) -> None:
        status, body = self.request("/")
        self.assertEqual(status, 200)
        self.assertIn(b"<!DOCTYPE html>", body)
        for path in ("/health", "/api/health"):
            status, body = self.request(path)
            self.assertEqual(status, 200)
            self.assertGreater(json.loads(body)["agents"], 0)

    def test_source_and_runtime_are_private_for_get_and_head(self) -> None:
        for method in ("GET", "HEAD"):
            for path in ("/server.py", "/Dockerfile", "/.brain-web/", "/%2e%2e/server.py"):
                self.assertEqual(self.request(path, method)[0], 404, (method, path))

    def test_public_assets_are_served(self) -> None:
        for path in ("/styles.css", "/app.js"):
            status, body = self.request(path)
            self.assertEqual(status, 200)
            self.assertGreater(len(body), 100)

    def test_malformed_input_is_rejected_before_graph(self) -> None:
        invalid = [
            [],
            {"intent": 12},
            {"intent": "oi", "context": []},
            {"intent": "oi", "context": {"revenue_brl_year": "mil"}},
            {"intent": "oi", "context": {"founder_led": "false"}},
        ]
        with patch.object(server, "run_intent") as execute:
            for body in invalid:
                self.assertEqual(self.request("/api/intent", "POST", body)[0], 400)
            execute.assert_not_called()

    def test_oversized_body_and_route_suffix_are_rejected(self) -> None:
        self.assertEqual(self.request("/api/intent", "POST", {"intent": "x" * 17000})[0], 413)
        self.assertEqual(self.request("/api/intent-other", "POST", {"intent": "oi"})[0], 404)
        self.assertEqual(self.request("/api/health-other")[0], 404)

    def test_internal_exception_is_not_published(self) -> None:
        with patch.object(server, "run_intent", side_effect=RuntimeError("private-runtime-path")):
            status, body = self.request("/api/intent", "POST", {"intent": "oi"})
        self.assertEqual(status, 500)
        self.assertNotIn(b"private-runtime-path", body)

    def test_real_offline_intent_remains_in_shadow(self) -> None:
        status, body = self.request(
            "/api/intent",
            "POST",
            {
                "intent": "qualifique este lead",
                "context": {
                    "company": "Empresa sintética",
                    "revenue_brl_year": 3000000,
                    "founder_led": True,
                    "sells_well": True,
                    "lacks_process": True,
                },
            },
        )
        self.assertEqual(status, 200, body)
        result = json.loads(body)
        self.assertEqual(result["mode"], "SHADOW")
        self.assertEqual(result["guild"], "G08")
        self.assertTrue(result["workers"])
