"""A2A protocol (agent card + JSON-RPC message/send) — unit tests, không cần mạng."""
import uuid

import pytest


# ── agent card (discovery: GET /.well-known/agent-card.json) ──
def test_a2a_card_shape():
    import main

    card = main._a2a_card()
    assert card["name"] == "travel-buddy"
    assert card["protocolVersion"] == "0.3.0"
    assert card["preferredTransport"] == "JSONRPC"
    assert card["url"].endswith("/a2a")
    caps = card["capabilities"]
    assert isinstance(caps["streaming"], bool) is True
    assert card["defaultInputModes"] == ["text/plain"]
    assert card["defaultOutputModes"] == ["text/plain"]


def test_a2a_card_skills():
    import main

    card = main._a2a_card()
    ids = [s["id"] for s in card["skills"]]
    assert "travel-planning" in ids and "personalization" in ids
    for s in card["skills"]:
        assert s["name"] and s["description"] and s.get("tags")


# ── _a2a_text: trích text từ message.parts ──
def test_a2a_text_kind_text():
    import main

    params = {"message": {"parts": [
        {"kind": "text", "text": "xin chào "},
        {"kind": "text", "text": "đà lạt"},
    ]}}
    assert main._a2a_text(params) == "xin chào đà lạt"


def test_a2a_text_legacy_part():
    import main

    params = {"message": {"parts": [{"text": "legacy"}]}}
    assert main._a2a_text(params) == "legacy"


def test_a2a_text_ignores_non_text():
    import main

    params = {"message": {"parts": [
        {"kind": "file", "file": {"bytes": "AA=="}},
        {"kind": "text", "text": "ok"},
    ]}}
    assert main._a2a_text(params) == "ok"


def test_a2a_text_empty():
    import main

    assert main._a2a_text({}) == ""
    assert main._a2a_text(None) == ""
    assert main._a2a_text({"message": {}}) == ""
    assert main._a2a_text({"message": {"parts": []}}) == ""


# ── _a2a_ctx: contextId của message ──
def test_a2a_ctx_passthrough():
    import main

    body = {"params": {"message": {"contextId": "ctx-123"}}}
    assert main._a2a_ctx(body) == "ctx-123"


def test_a2a_ctx_generated():
    import main

    ctx = main._a2a_ctx({})
    assert ctx.startswith("a2a-") and len(ctx) > len("a2a-")


# ── _a2a_msg_result: envelope JSON-RPC kết quả ──
def test_a2a_msg_result_envelope():
    import main

    out = main._a2a_msg_result("req-1", "ctx-9", "Đà Lạt đẹp lắm")
    assert out["jsonrpc"] == "2.0"
    assert out["id"] == "req-1"
    msg = out["result"]
    assert msg["kind"] == "message"
    assert msg["contextId"] == "ctx-9"
    assert msg["role"] == "agent"
    assert msg["parts"] == [{"kind": "text", "text": "Đà Lạt đẹp lắm"}]
    assert msg["messageId"]


# ── LangFuse v4 helpers: tracing tắt khi thiếu env (chạy bình thường) ──
def test_lf_helpers_off_without_env(monkeypatch):
    import main

    for k in ("LANGFUSE_PUBLIC_KEY", "LANGFUSE_SECRET_KEY", "LANGFUSE_HOST"):
        monkeypatch.delenv(k, raising=False)
    assert main._lf_tracing() is False
    with main._lf_scope("t", "u", "s", ["x"]):
        pass  # nullcontext → không raise
    assert main._lf_callback() is None
