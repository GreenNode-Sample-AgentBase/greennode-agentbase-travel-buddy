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
import os
from datetime import datetime
from pathlib import Path

from starlette.requests import Request
from starlette.responses import JSONResponse
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

app = GreenNodeAgentBaseApp()

MEMORY_ID = os.environ.get("AGENTBASE_MEMORY_ID", "")
MCP_TAVILY_URL = os.environ.get("MCP_TAVILY_URL", "")
LLM_MODEL = os.environ.get("LLM_MODEL", "")

FRONTEND_DIR = Path(__file__).resolve().parent.parent / "frontend"


def _now() -> str:
    return datetime.now().isoformat()


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


app.add_route("/api/info", _api_info, methods=["GET"])
app.add_route("/api/memory", _api_memory, methods=["GET"])
app.add_route("/api/history", _api_history, methods=["GET"])
app.add_route("/api/actors", _api_actors, methods=["GET"])
# Static frontend — mount CUỐI cùng để không che các route trên
app.mount("/", StaticFiles(directory=str(FRONTEND_DIR), html=True), name="ui")


if __name__ == "__main__":
    app.run(port=8080, host="0.0.0.0")