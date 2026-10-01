"""Đặt env dummy TRƯỚC khi import module backend (agent.py raise nếu thiếu key)."""
import os
import sys
from pathlib import Path

os.environ.setdefault("LLM_API_KEY", "test-key")
os.environ.setdefault("LLM_MODEL", "test-model")
os.environ.setdefault("AGENTBASE_MEMORY_ID", "memory-test")
os.environ.setdefault("MEMORY_STRATEGY_PREF_ID", "ltms-pref-test")
os.environ.setdefault("MEMORY_STRATEGY_FACTS_ID", "ltms-facts-test")
os.environ.setdefault("MCP_TAVILY_URL", "https://gw.example/tavily")
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src" / "backend"))
