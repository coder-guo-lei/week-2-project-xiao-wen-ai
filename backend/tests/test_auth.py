"""
认证 API 测试：register / login / me

运行方式（在 backend 目录下）：
    python -m unittest tests.test_auth -v
"""

import os
import tempfile
import unittest
import uuid
from unittest.mock import patch


class AuthAPITestCase(unittest.TestCase):
    """使用临时 SQLite，避免污染开发库 xiaowen.db。"""

    @classmethod
    def setUpClass(cls):
        fd, cls.db_path = tempfile.mkstemp(suffix=".db")
        os.close(fd)
        cls.db_patch = patch("models.user.DB_PATH", cls.db_path)
        cls.db_patch.start()

        from models.user import init_db

        init_db()

        from app import app

        cls.app = app
        cls.client = app.test_client()

    @classmethod
    def tearDownClass(cls):
        cls.db_patch.stop()
        if os.path.isfile(cls.db_path):
            os.unlink(cls.db_path)

    def _register(self, username=None, password="test1234", display_name=""):
        username = username or f"user_{uuid.uuid4().hex[:8]}"
        payload = {"username": username, "password": password}
        if display_name:
            payload["displayName"] = display_name
        return self.client.post("/api/auth/register", json=payload), username

    def test_register_success(self):
        resp, username = self._register(display_name="测试用户")
        self.assertEqual(resp.status_code, 201)
        data = resp.get_json()
        self.assertIn("token", data)
        self.assertEqual(data["user"]["username"], username)
        self.assertEqual(data["user"]["displayName"], "测试用户")

    def test_register_duplicate_username(self):
        resp1, username = self._register()
        self.assertEqual(resp1.status_code, 201)
        resp2, _ = self._register(username=username)
        self.assertEqual(resp2.status_code, 409)
        self.assertIn("error", resp2.get_json())

    def test_register_invalid_username(self):
        resp = self.client.post(
            "/api/auth/register",
            json={"username": "ab", "password": "test1234"},
        )
        self.assertEqual(resp.status_code, 400)

    def test_register_short_password(self):
        resp = self.client.post(
            "/api/auth/register",
            json={"username": "validuser", "password": "123"},
        )
        self.assertEqual(resp.status_code, 400)

    def test_login_success(self):
        password = "secret5678"
        resp_reg, username = self._register(password=password)
        self.assertEqual(resp_reg.status_code, 201)

        resp = self.client.post(
            "/api/auth/login",
            json={"username": username, "password": password},
        )
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertIn("token", data)
        self.assertEqual(data["user"]["username"], username)

    def test_login_wrong_password(self):
        resp_reg, username = self._register(password="correctpass")
        self.assertEqual(resp_reg.status_code, 201)

        resp = self.client.post(
            "/api/auth/login",
            json={"username": username, "password": "wrongpass"},
        )
        self.assertEqual(resp.status_code, 401)

    def test_me_requires_token(self):
        resp = self.client.get("/api/auth/me")
        self.assertEqual(resp.status_code, 401)

    def test_me_with_valid_token(self):
        resp_reg, username = self._register()
        token = resp_reg.get_json()["token"]

        resp = self.client.get(
            "/api/auth/me",
            headers={"Authorization": f"Bearer {token}"},
        )
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertEqual(data["user"]["username"], username)


if __name__ == "__main__":
    unittest.main()
