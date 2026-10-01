"""Travel Buddy — GreenNode AgentBase sample (backend).

Endpoints:
  POST /invocations      — SDK entrypoint: chat (cần 2 headers user/session)
  GET  /health           — SDK health check (tự động)
  GET  /                 — serve frontend (src/frontend)
  GET  /api/info         — thông tin cấu hình (cho UI)
  GET  /api/memory       — browse memory records per actor (memory panel)
  GET  /api/history      — events lịch sử hội thoại per actor+session
  GET  /api/actors       — danh sách actor + sessions đã tồn tại

Chạy local:  uvicorn không cần — `python main.py` (SDK tự chạy server port 8080).
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import threading
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from starlette.requests import Request
from starlette.responses import JSONResponse, StreamingResponse
from starlette.staticfiles import StaticFiles

from greennode_agentbase import (
    GreenNodeAgentBaseApp,
    RequestContext,
    PingStatus,
)

import agent as agent_mod
import memory_tools
from memory_tools import run_coro
from mcp_client import mcp_request

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s | %(message)s",
)
logger = logging.getLogger("travel-buddy")

app = GreenNodeAgentBaseApp()

MEMORY_ID = os.environ.get("AGENTBASE_MEMORY_ID", "")
MCP_TAVILY_URL = os.environ.get("MCP_TAVILY_URL", "")
LLM_MODEL = os.environ.get("LLM_MODEL", "")
LLM_API_KEY = os.environ.get("LLM_API_KEY", "")
# AGENT_API_KEY (optional): đặt trong production để chặn người lạ xài LLM của bạn
AGENT_API_KEY = os.environ.get("AGENT_API_KEY", "").strip()
# DEBUG_OPS=1: bật op whoami (lộ identity runtime — chỉ dùng lúc setup policy)
DEBUG_OPS = os.environ.get("DEBUG_OPS", "0").strip() in ("1", "true", "yes")

FRONTEND_DIR = Path(__file__).resolve().parent.parent / "frontend"
TZ_VN = ZoneInfo("Asia/Ho_Chi_Minh")


def _now() -> str:
    return datetime.now(TZ_VN).isoformat()


# ── API-key middleware: bảo vệ /invocations + /api/* (trừ /api/info) ──
class ApiKeyMiddleware:
    """Pure-ASGI middleware. Không đặt AGENT_API_KEY → mở (local dev)."""

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] == "http" and AGENT_API_KEY:
            path = scope.get("path", "")
            protected = path == "/invocations" or (
                path.startswith("/api/") and path != "/api/info"
            )
            if protected:
                headers = {
                    k.decode("latin-1").lower(): v.decode("latin-1")
                    for k, v in scope.get("headers", [])
                }
                if headers.get("x-api-key") != AGENT_API_KEY:
                    resp = JSONResponse(
                        {"status": "error", "error": "Unauthorized — thiếu/sai header X-API-Key"},
                        status_code=401,
                    )
                    await resp(scope, receive, send)
                    return
        await self.app(scope, receive, send)


def _get_user_id(context) -> str:
    """user_id từ header (SDK 1.0.1 chưa expose context.user_id → đọc từ request)."""
    uid = getattr(context, "user_id", None)
    if uid:
        return uid
    req = getattr(context, "request", None)
    if req is not None:
        try:
            return req.headers.get("X-GreenNode-AgentBase-User-Id", "") or ""
        except Exception:
            return ""
    return ""


@app.entrypoint
def handler(payload: dict, context: RequestContext) -> dict:
    """Chat entrypoint — BẮT BUỘC có 2 headers user/session (memory integration)."""
    if payload.get("op") == "whoami":
        if not DEBUG_OPS:
            return {
                "status": "error",
                "error": "whoami bị tắt. Set DEBUG_OPS=1 (chỉ dùng lúc setup policy) rồi restart runtime.",
            }
        return {"status": "success", "agent": "travel-buddy", **agent_mod.whoami()}

    user_id = _get_user_id(context)
    if not user_id or not context.session_id:
        return {
            "status": "error",
            "error": (
                "Thiếu headers bắt buộc: X-GreenNode-AgentBase-User-Id và "
                "X-GreenNode-AgentBase-Session-Id (để tách bộ nhớ theo user/session)."
            ),
        }

    message = payload.get("message") or payload.get("input") or "Hello"
    try:
        result = run_coro(agent_mod.get_agent().ainvoke(
            {"messages": [{"role": "user", "content": message}]},
            config={"configurable": {"thread_id": context.session_id, "actor_id": user_id}},
        ))
    except Exception as e:  # lỗi MCP/policy/LLM → trả message rõ ràng
        return {"status": "error", "error": f"{type(e).__name__}: {e}", "timestamp": _now()}

    ai_message = result["messages"][-1]
    # Thu thập hoạt động memory trong turn này (cho UI callout "✨ agent vừa nhớ")
    memories_used: list[str] = []
    for m in result["messages"]:
        if type(m).__name__ != "ToolMessage":
            continue
        content = str(getattr(m, "content", ""))
        if content.startswith("Đã nhớ: "):
            memories_used.append(content[len("Đã nhớ: "):])
        elif "score:" in content and content.lstrip().startswith("- "):
            # output của tool recall → trích các dòng fact
            for line in content.splitlines():
                line = line.strip()
                if line.startswith("- ") and " (score:" in line:
                    memories_used.append(line[2:].split(" (score:")[0])
    reply = str(ai_message.content or "")
    if reply:
        memory_tools.add_chat_events_sync(user_id, context.session_id, message, reply)
    return {
        "status": "success",
        "agent": "travel-buddy",
        "response": ai_message.content,
        "memories_used": memories_used,
        "timestamp": _now(),
    }


@app.ping
def health_check() -> PingStatus:
    return PingStatus.HEALTHY


# ---------- REST helpers cho frontend (same-origin, không CORS) ----------

async def _api_info(request: Request) -> JSONResponse:
    return JSONResponse(
        {
            "agent": "travel-buddy",
            "memory_id": MEMORY_ID,
            "mcp_url": MCP_TAVILY_URL,
            "llm_model": LLM_MODEL,
            "gateway": MCP_TAVILY_URL.split("/tavily")[0] if "/tavily" in MCP_TAVILY_URL else "",
            "auth_required": bool(AGENT_API_KEY),
            "streaming": True,
        }
    )


async def _api_memory(request: Request) -> JSONResponse:
    """GET /api/memory?actor=<user> — browse records theo từng strategy."""
    actor = request.query_params.get("actor", "")
    if not actor:
        return JSONResponse({"error": "thiếu ?actor=<userId>"}, status_code=400)
    groups = []
    for sid, sname in (
        (memory_tools.MEMORY_STRATEGY_PREF_ID, "user-preferences"),
        (memory_tools.MEMORY_STRATEGY_FACTS_ID, "trip-facts"),
    ):
        if not sid:
            continue
        try:
            records = memory_tools.browse_group_sync(actor, sid)
        except Exception as e:
            records = []
            groups.append({"strategy_id": sid, "strategy": sname, "error": str(e)[:200], "records": []})
            continue
        groups.append({"strategy_id": sid, "strategy": sname, "records": records})
    return JSONResponse({"actor": actor, "groups": groups})


async def _api_history(request: Request) -> JSONResponse:
    """GET /api/history?actor=<user>&session=<session> — events hội thoại."""
    actor = request.query_params.get("actor", "")
    session = request.query_params.get("session", "")
    if not actor or not session:
        return JSONResponse({"error": "thiếu ?actor= và &session="}, status_code=400)
    try:
        raw = memory_tools.list_events_sync(actor, session)
        def _f(r, k, d=""):
            if isinstance(r, dict):
                v = r.get(k, d)
            else:
                v = getattr(r, k, d)
            return v if v is not None else d

        # Chỉ lấy conversational events (checkpoint binary của langgraph bị lọc bỏ)
        events = []
        for ev in raw:
            payload = _f(ev, "payload", None)
            if payload is None or _f(payload, "type", "") != "conversational":
                continue
            events.append(
                {
                    "role": _f(payload, "role", "user") or "user",
                    "message": _f(payload, "message", ""),
                    "createdAt": str(_f(ev, "event_timestamp") or _f(ev, "eventTimestamp") or _f(ev, "created_at")),
                }
            )
        events.reverse()  # API trả mới nhất trước → reverse
        return JSONResponse({"actor": actor, "session": session, "events": events})
    except Exception as e:
        return JSONResponse({"actor": actor, "session": session, "events": [], "error": str(e)[:200]})


async def _api_actors(request: Request) -> JSONResponse:
    """GET /api/actors — danh sách user đã có memory (gợi ý cho switcher)."""
    try:
        return JSONResponse({"actors": memory_tools.list_actors_sync()})
    except Exception as e:
        return JSONResponse({"actors": [], "error": str(e)[:200]})


# ── /api/chat/stream: SSE stream token từ LLM (fallback tự động ở frontend) ──
async def _chat_stream(request: Request) -> StreamingResponse:
    """POST /api/chat/stream — body {"message":...} + headers user/session.

    SSE events: {"type":"token","text":...} · {"type":"done","response":...,
    "memories_used":[...]} · {"type":"error","error":...}
    """
    if AGENT_API_KEY and request.headers.get("X-API-Key") != AGENT_API_KEY:
        return JSONResponse({"status": "error", "error": "Unauthorized"}, status_code=401)
    user_id = request.headers.get("X-GreenNode-AgentBase-User-Id", "")
    session_id = request.headers.get("X-GreenNode-AgentBase-Session-Id", "")
    if not user_id or not session_id:
        return JSONResponse(
            {"status": "error", "error": "Thiếu headers X-GreenNode-AgentBase-User-Id / -Session-Id"},
            status_code=400,
        )
    try:
        body = await request.json()
    except Exception:
        body = {}
    message = body.get("message") or body.get("input") or "Hello"

    # Kiến trúc: agent chạy trên PERSISTENT LOOP (giống /invocations — SDK MemoryClient
    # cache theo event loop), event được relay sang SSE generator qua queue thread-safe.
    uv_loop = asyncio.get_running_loop()
    out_q: asyncio.Queue = asyncio.Queue()

    async def _produce():
        """Chạy TRÊN persistent loop: stream events + thu reply + lưu history."""
        reply = ""
        memories_used: list[str] = []
        agent = agent_mod.get_agent()
        try:
            async for ev in agent.astream_events(
                {"messages": [{"role": "user", "content": message}]},
                config={"configurable": {"thread_id": session_id, "actor_id": user_id}},
            ):
                if ev["event"] == "on_chat_model_stream":
                    token = ev["data"].get("chunk").content or ""
                    if isinstance(token, str) and token:
                        reply += token
                        uv_loop.call_soon_threadsafe(out_q.put_nowait, ("token", token))
                elif ev["event"] == "on_tool_end" and ev["name"] in ("remember", "recall"):
                    out = str(ev["data"].get("output") or "")
                    if out.startswith("Đã nhớ: "):
                        memories_used.append(out[len("Đã nhớ: "):])
                    else:
                        for line in out.splitlines():
                            line = line.strip()
                            if line.startswith("- ") and " (score:" in line:
                                memories_used.append(line[2:].split(" (score:")[0])
            if reply:
                try:
                    await memory_tools.add_chat_events(user_id, session_id, message, reply)
                except Exception:
                    logger.warning("lưu history sau stream thất bại (bỏ qua)")
            uv_loop.call_soon_threadsafe(out_q.put_nowait, ("done", (reply, memories_used)))
        except Exception as e:
            logger.exception("stream error")
            uv_loop.call_soon_threadsafe(out_q.put_nowait, ("error", f"{type(e).__name__}: {e}"))

    threading.Thread(
        target=lambda: memory_tools.run_coro(_produce()),
        daemon=True,
        name=f"sse-{session_id[:20]}",
    ).start()

    async def gen():
        reply = ""
        memories_used: list[str] = []
        try:
            while True:
                kind, payload = await out_q.get()
                if kind == "token":
                    yield f"data: {json.dumps({'type': 'token', 'text': payload}, ensure_ascii=False)}\n\n"
                elif kind == "done":
                    reply, memories_used = payload
                    break
                else:  # error
                    yield f"data: {json.dumps({'type': 'error', 'error': payload}, ensure_ascii=False)}\n\n"
                    return
            yield f"data: {json.dumps({'type': 'done', 'response': reply, 'memories_used': memories_used}, ensure_ascii=False)}\n\n"
        except Exception as e:  # client đóng kết nối giữa chừng
            logger.info("SSE client ngắt (session=%s): %s", session_id, e)

    return StreamingResponse(gen(), media_type="text/event-stream", headers={"Cache-Control": "no-store", "X-Accel-Buffering": "no"})


# ── /ready: health check sâu (memory + gateway + LLM) cho ops ──
async def _ready(request: Request) -> JSONResponse:
    checks: dict = {}
    try:
        memory_tools.list_actors_sync()
        checks["memory"] = {"ok": True}
    except Exception as e:
        checks["memory"] = {"ok": False, "error": str(e)[:150]}
    try:
        tools = agent_mod.get_mcp_tools()
        checks["gateway"] = {"ok": bool(tools), "tools": len(tools)}
    except Exception as e:
        checks["gateway"] = {"ok": False, "error": str(e)[:150]}
    checks["llm"] = {"ok": bool(LLM_API_KEY), "model": LLM_MODEL}
    ok = all(c.get("ok") for c in checks.values())
    return JSONResponse({"status": "ok" if ok else "degraded", "checks": checks}, status_code=200 if ok else 503)


app.add_route("/ready", _ready, methods=["GET"])
app.add_route("/api/chat/stream", _chat_stream, methods=["POST"])
app.add_route("/api/info", _api_info, methods=["GET"])
app.add_route("/api/memory", _api_memory, methods=["GET"])
app.add_route("/api/history", _api_history, methods=["GET"])
app.add_route("/api/actors", _api_actors, methods=["GET"])
app.add_middleware(ApiKeyMiddleware)
# Static frontend — mount CUỐI cùng để không che các route trên
app.mount("/", StaticFiles(directory=str(FRONTEND_DIR), html=True), name="ui")


if __name__ == "__main__":
    app.run(port=8080, host="0.0.0.0")