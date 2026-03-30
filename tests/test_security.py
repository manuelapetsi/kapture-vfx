import unittest

from app.security import is_allowed_websocket_origin


class SecurityTests(unittest.TestCase):
    def test_same_host_origin_is_allowed(self):
        self.assertTrue(
            is_allowed_websocket_origin(
                origin="http://127.0.0.1:8000",
                host="127.0.0.1:8000",
            )
        )

    def test_cross_site_origin_is_rejected(self):
        self.assertFalse(
            is_allowed_websocket_origin(
                origin="https://evil.example",
                host="127.0.0.1:8000",
                allowed_origins=[],
            )
        )

    def test_explicit_allowlist_origin_is_honored(self):
        self.assertTrue(
            is_allowed_websocket_origin(
                origin="https://preview.example.com",
                host="127.0.0.1:8000",
                allowed_origins=["https://preview.example.com"],
            )
        )
