import json
import os
import unittest
from unittest.mock import patch

from tools.openrouter_agent import complete, resolve_model


class _Response:
    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def read(self):
        return json.dumps({"choices": [{"message": {"content": "ok"}}]}).encode()


class OpenRouterAgentTests(unittest.TestCase):
    def test_paid_model_override_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "free OpenRouter model"):
            resolve_model("research", "some/model")

    def test_defaults_route_agents_to_free_router(self):
        captured = {}

        def fake_urlopen(request, timeout):
            captured["request"] = request
            return _Response()

        with patch.dict(os.environ, {"OPENROUTER_API_KEY": "test-key"}, clear=False), patch(
            "tools.openrouter_agent.urlopen", fake_urlopen
        ):
            result = complete("hello", agent="review")

        body = json.loads(captured["request"].data)
        self.assertEqual(result["choices"][0]["message"]["content"], "ok")
        self.assertEqual(body["model"], "stealth/union-alpha")
        self.assertEqual(body["messages"], [{"role": "user", "content": "hello"}])
        self.assertEqual(captured["request"].headers["Authorization"], "Bearer test-key")

    def test_system_message_and_model_override_are_forwarded(self):
        captured = {}

        def fake_urlopen(request, timeout):
            captured["body"] = json.loads(request.data)
            return _Response()

        with patch.dict(os.environ, {"OPENROUTER_API_KEY": "test-key"}, clear=False), patch(
            "tools.openrouter_agent.urlopen", fake_urlopen
        ):
            complete("hello", system="be concise", model="some/model:free")

        self.assertEqual(captured["body"]["model"], "some/model:free")
        self.assertEqual(captured["body"]["messages"][0], {"role": "system", "content": "be concise"})


if __name__ == "__main__":
    unittest.main()
