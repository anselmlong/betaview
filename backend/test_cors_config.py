import os
import unittest
from unittest.mock import patch
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.testclient import TestClient
from cors_config import cors_options


class CorsTests(unittest.TestCase):
    def test_exact_origin_preflight(self):
        with patch.dict(os.environ, {"CORS_ORIGINS": "https://climb.example"}):
            app = FastAPI()
            app.add_middleware(CORSMiddleware, **cors_options())
            client = TestClient(app)
            for origin, status in [("https://climb.example", 200),
                                   ("https://evil.example", 400),
                                   ("https://climb.example.evil.example", 400)]:
                response = client.options("/upload", headers={
                    "Origin": origin, "Access-Control-Request-Method": "POST",
                    "Access-Control-Request-Headers": "Content-Type"})
                self.assertEqual(response.status_code, status)
                self.assertNotIn("access-control-allow-credentials", response.headers)

    def test_reject_wildcards_and_urls_with_paths(self):
        for value in ["*", "https://*.example", "https://example/path"]:
            with patch.dict(os.environ, {"CORS_ORIGINS": value}):
                with self.assertRaises(ValueError):
                    cors_options()


if __name__ == "__main__":
    unittest.main()
