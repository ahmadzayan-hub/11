"""Unit tests for the FastAPI adapter in server/app.py.

These tests run the API in-process against a temporary configuration and
memory file, so they never touch the repository's real data files.
"""

import json
import tempfile
import unittest
from pathlib import Path

try:
    from fastapi.testclient import TestClient
    from server.app import create_app
    FASTAPI_AVAILABLE = True
except ImportError:  # pragma: no cover - CLI-only environments
    FASTAPI_AVAILABLE = False


@unittest.skipUnless(FASTAPI_AVAILABLE, "fastapi is not installed")
class ApiTestCase(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp_dir.cleanup)
        root = Path(self.temp_dir.name)
        self.memory_path = root / "memory.json"
        config_path = root / "config.json"
        config_path.write_text(
            json.dumps(
                {
                    "agent_name": "Web Test Agent",
                    "version": "9.9.9",
                    "preferences": {"tone": "concise"},
                    "memory_file": str(self.memory_path),
                    "maximum_history_items": 50,
                }
            ),
            encoding="utf-8",
        )
        self.client = TestClient(create_app(config_path), raise_server_exceptions=False)

    def open_session(self):
        response = self.client.post("/api/sessions")
        self.assertEqual(response.status_code, 201)
        return response.json()

    def test_health_reports_agent_identity(self):
        response = self.client.get("/api/health")
        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body["status"], "ok")
        self.assertEqual(body["agent_name"], "Web Test Agent")

    def test_create_session_returns_full_snapshot(self):
        state = self.open_session()
        self.assertIn("session_id", state)
        self.assertEqual(state["agent_name"], "Web Test Agent")
        self.assertFalse(state["ended"])
        self.assertEqual(state["transcript"], [])
        self.assertEqual(state["preferences"]["tone"], "concise")
        self.assertTrue(any(c["command"] == "/help" for c in state["commands"]))

    def test_unknown_session_returns_404(self):
        response = self.client.get("/api/sessions/does-not-exist")
        self.assertEqual(response.status_code, 404)

    def test_send_message_appends_user_and_agent_entries(self):
        state = self.open_session()
        response = self.client.post(
            f"/api/sessions/{state['session_id']}/messages",
            json={"text": "Hello there"},
        )
        self.assertEqual(response.status_code, 200)
        body = response.json()
        roles = [entry["role"] for entry in body["state"]["transcript"]]
        self.assertEqual(roles, ["user", "agent"])
        self.assertIn("Hello there", body["state"]["transcript"][0]["text"])
        self.assertEqual(body["reply"]["role"], "agent")

    def test_blank_message_is_rejected(self):
        state = self.open_session()
        response = self.client.post(
            f"/api/sessions/{state['session_id']}/messages",
            json={"text": "   "},
        )
        self.assertEqual(response.status_code, 422)

    def test_slash_exit_message_ends_the_session(self):
        state = self.open_session()
        sid = state["session_id"]
        response = self.client.post(
            f"/api/sessions/{sid}/messages", json={"text": "/exit"}
        )
        self.assertTrue(response.json()["state"]["ended"])
        follow_up = self.client.post(
            f"/api/sessions/{sid}/messages", json={"text": "still there?"}
        )
        self.assertEqual(follow_up.status_code, 409)

    def test_memory_add_and_delete_round_trip(self):
        state = self.open_session()
        sid = state["session_id"]
        added = self.client.post(
            f"/api/sessions/{sid}/memory",
            json={"information": "The tram opens at 6am"},
        )
        self.assertEqual(added.status_code, 201)
        memory = added.json()["state"]["memory"]
        self.assertIn("The tram opens at 6am", memory.values())
        self.assertEqual(
            json.loads(self.memory_path.read_text(encoding="utf-8")), memory
        )

        key = next(iter(memory))
        deleted = self.client.delete(f"/api/sessions/{sid}/memory/{key}")
        self.assertEqual(deleted.status_code, 200)
        self.assertEqual(deleted.json()["state"]["memory"], {})

    def test_delete_unknown_memory_returns_404(self):
        state = self.open_session()
        response = self.client.delete(
            f"/api/sessions/{state['session_id']}/memory/memory_9"
        )
        self.assertEqual(response.status_code, 404)

    def test_clear_memory_removes_everything(self):
        state = self.open_session()
        sid = state["session_id"]
        self.client.post(
            f"/api/sessions/{sid}/memory", json={"information": "One"}
        )
        self.client.post(
            f"/api/sessions/{sid}/memory", json={"information": "Two"}
        )
        response = self.client.delete(f"/api/sessions/{sid}/memory")
        self.assertEqual(response.json()["state"]["memory"], {})

    def test_update_preference_applies_to_responses(self):
        state = self.open_session()
        sid = state["session_id"]
        response = self.client.put(
            f"/api/sessions/{sid}/preferences",
            json={"key": "tone", "value": "formal"},
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["state"]["preferences"]["tone"], "formal")

    def test_boolean_preference_values_become_booleans(self):
        state = self.open_session()
        response = self.client.put(
            f"/api/sessions/{state['session_id']}/preferences",
            json={"key": "save_history", "value": "false"},
        )
        self.assertIs(response.json()["state"]["preferences"]["save_history"], False)

    def test_invalid_preference_key_is_rejected(self):
        state = self.open_session()
        response = self.client.put(
            f"/api/sessions/{state['session_id']}/preferences",
            json={"key": "bad key!", "value": "x"},
        )
        self.assertEqual(response.status_code, 422)

    def test_clear_history_empties_history_only(self):
        state = self.open_session()
        sid = state["session_id"]
        self.client.post(f"/api/sessions/{sid}/messages", json={"text": "Hello"})
        self.client.post(
            f"/api/sessions/{sid}/memory", json={"information": "Keep me"}
        )
        response = self.client.delete(f"/api/sessions/{sid}/history")
        body = response.json()
        self.assertEqual(body["state"]["history"], [])
        self.assertIn("Keep me", body["state"]["memory"].values())

    def test_end_session_marks_session_ended(self):
        state = self.open_session()
        response = self.client.delete(f"/api/sessions/{state['session_id']}")
        self.assertTrue(response.json()["ended"])

    def test_multiline_memory_is_rejected(self):
        state = self.open_session()
        response = self.client.post(
            f"/api/sessions/{state['session_id']}/memory",
            json={"information": "line one\nline two"},
        )
        self.assertEqual(response.status_code, 422)


if __name__ == "__main__":
    unittest.main()
