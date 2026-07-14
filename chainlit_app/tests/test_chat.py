from __future__ import annotations

import importlib.util
import sys
import types
import unittest
from pathlib import Path


class _FakeUserSession:
    def __init__(self) -> None:
        self.values: dict[str, object] = {}

    def get(self, key: str) -> object | None:
        return self.values.get(key)

    def set(self, key: str, value: object) -> None:
        self.values[key] = value


class _FakeMessage:
    def __init__(self, content: str) -> None:
        self.content = content

    async def send(self) -> None:
        return None


class _FakeHTTPError(Exception):
    pass


class _FakeHTTPStatusError(_FakeHTTPError):
    def __init__(self, response: object) -> None:
        self.response = response
        super().__init__("status error")


class _FakeResponse:
    def __init__(self, status_code: int, payload: dict[str, object]) -> None:
        self.status_code = status_code
        self._payload = payload

    def json(self) -> dict[str, object]:
        return self._payload

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            raise _FakeHTTPStatusError(self)


def _load_chat_module():
    fake_chainlit = types.SimpleNamespace(
        user_session=_FakeUserSession(),
        Message=_FakeMessage,
        on_chat_start=lambda func: func,
        on_message=lambda func: func,
    )
    sys.modules["chainlit"] = fake_chainlit
    sys.modules["httpx"] = types.SimpleNamespace(
        AsyncClient=object,
        HTTPError=_FakeHTTPError,
        HTTPStatusError=_FakeHTTPStatusError,
    )
    module_path = Path(__file__).resolve().parents[1] / "app" / "chat.py"
    module_name = f"chainlit_chat_under_test_{id(fake_chainlit)}"
    spec = importlib.util.spec_from_file_location(module_name, module_path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


class ChainlitChatTests(unittest.IsolatedAsyncioTestCase):
    def test_render_answer_with_chicago_notes(self) -> None:
        chat = _load_chat_module()

        rendered = chat.render_answer_with_citations(
            "The table shows 5 ml.",
            [
                {
                    "number": 1,
                    "document_title": "who-guidance.pdf",
                    "page_number": 7,
                    "section_path": "Dose table",
                }
            ],
        )

        self.assertEqual(rendered, "The table shows 5 ml.¹\n\n1. who-guidance.pdf, p. 7, Dose table.")

    async def test_backend_chat_client_posts_to_fastapi_chat(self) -> None:
        chat = _load_chat_module()
        seen: dict[str, object] = {}

        class FakeAsyncClient:
            def __init__(self, timeout: float) -> None:
                seen["timeout"] = timeout

            async def __aenter__(self):
                return self

            async def __aexit__(self, *_args):
                return None

            async def post(self, url: str, json: dict[str, str], headers: dict[str, str]) -> _FakeResponse:
                seen["url"] = url
                seen["json"] = json
                seen["headers"] = headers
                return _FakeResponse(
                    200,
                    {
                        "session_id": "00000000-0000-0000-0000-000000000001",
                        "answer": "Answer",
                        "citations": [{"number": 1}],
                    },
                )

        chat.httpx.AsyncClient = FakeAsyncClient
        client = chat.BackendChatClient(
            base_url="http://backend:6100/",
            auth_token="token",
            timeout_seconds=3,
        )

        response = await client.ask("question", "00000000-0000-0000-0000-000000000002")

        self.assertEqual(seen["url"], "http://backend:6100/api/v1/chat")
        self.assertEqual(
            seen["json"],
            {
                "message": "question",
                "session_id": "00000000-0000-0000-0000-000000000002",
            },
        )
        self.assertEqual(seen["headers"], {"Accept": "application/json", "Authorization": "Bearer token"})
        self.assertEqual(response.answer, "Answer")
        self.assertEqual(response.session_id, "00000000-0000-0000-0000-000000000001")
        self.assertEqual(response.citations, [{"number": 1}])


if __name__ == "__main__":
    unittest.main()
