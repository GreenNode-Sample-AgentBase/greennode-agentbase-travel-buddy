"""Memory headers: thiếu X-GreenNode-AgentBase-User-Id / -Session-Id → 400, KHÔNG fallback default.

Docs AgentBase: "If your agent uses memory, validate that these headers are present and
return an error if missing. Do not fall back to default values."
"""
import pytest
from starlette.testclient import TestClient

USER = "X-GreenNode-AgentBase-User-Id"
SESSION = "X-GreenNode-AgentBase-Session-Id"


@pytest.fixture()
def client(monkeypatch):
    import main

    monkeypatch.setattr(main, "AGENT_API_KEY", "")

    # Nếu code lỡ chạy tới agent khi thiếu header → fail rõ ràng
    def _boom(*a, **k):
        raise AssertionError("agent KHÔNG được chạy khi thiếu headers")

    monkeypatch.setattr(main.agent_mod, "get_agent", _boom)
    return TestClient(main.app, raise_server_exceptions=False)


def test_missing_identity_helper():
    import main

    assert main._missing_identity("", "s")
    assert main._missing_identity("u", "")
    assert main._missing_identity(None, None)
    assert main._missing_identity("  ", "s")
    assert not main._missing_identity("u", "s")


@pytest.mark.parametrize(
    "headers",
    [{}, {USER: "alice"}, {SESSION: "s-1"}],
    ids=["none", "only-user", "only-session"],
)
def test_invocations_missing_headers_400(client, headers):
    r = client.post("/invocations", json={"message": "hi"}, headers=headers)
    assert r.status_code == 400
    assert "X-GreenNode-AgentBase-User-Id" in r.text


@pytest.mark.parametrize(
    "headers",
    [{}, {USER: "alice"}, {SESSION: "s-1"}],
    ids=["none", "only-user", "only-session"],
)
def test_stream_missing_headers_400(client, headers):
    r = client.post("/api/chat/stream", json={"message": "hi"}, headers=headers)
    assert r.status_code == 400
    assert r.json()["status"] == "error"


def test_a2a_requires_user_header_no_shared_actor(client):
    body = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "message/send",
        "params": {"message": {"parts": [{"kind": "text", "text": "hello"}]}},
    }
    r = client.post("/a2a", json=body)
    assert r.status_code == 400
    assert r.json()["error"]["code"] == -32602


def test_a2a_uses_header_user_as_actor(client, monkeypatch):
    import main

    seen = {}

    async def _fake_turn(user, ctx, text):
        seen.update(user=user, ctx=ctx)
        return "ok", []

    monkeypatch.setattr(main, "_a2a_turn", _fake_turn)
    body = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "message/send",
        "params": {"message": {"contextId": "c-1", "parts": [{"kind": "text", "text": "hello"}]}},
    }
    r = client.post("/a2a", json=body, headers={USER: "alice"})
    assert r.status_code == 200
    assert seen == {"user": "alice", "ctx": "c-1"}


def test_a2a_ctx_prefers_context_id_then_header():
    import main

    body = {"params": {"message": {"contextId": "ctx-x"}}}
    assert main._a2a_ctx(body, "hdr") == "ctx-x"
    assert main._a2a_ctx({}, "hdr") == "hdr"
    assert main._a2a_ctx({}, "").startswith("a2a-")
