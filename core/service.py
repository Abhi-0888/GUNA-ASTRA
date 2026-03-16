"""
GUNA-ASTRA FastAPI Service
Provides an HTTP API for sending commands when running as a background service.
Endpoints:
  POST /command   — execute a command
  GET  /status    — system health
  GET  /history   — recent tasks
  GET  /mode      — current mode
  POST /mode      — switch mode
"""

import threading
import time
from typing import Optional

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from config.settings import DEFAULT_MODE, MODE_NORMAL, MODE_WORKING
from utils.llm_client import check_ollama_health
from utils.logger import get_logger
from utils.memory_db import MONGO_AVAILABLE, get_recent_tasks

logger = get_logger("API")

app = FastAPI(
    title="GUNA-ASTRA API",
    description="Local Autonomous Multi-Agent AI System — HTTP Interface",
    version="2.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Shared state ─────────────────────────────────────────────────────────────
_orchestrator = None
_lock = threading.Lock()


def set_orchestrator(orchestrator):
    """Called by main.py to inject the orchestrator instance."""
    global _orchestrator
    _orchestrator = orchestrator


# ── Request/Response Models ──────────────────────────────────────────────────


class CommandRequest(BaseModel):
    text: str
    mode: Optional[str] = None  # "normal" or "working", defaults to current mode


class CommandResponse(BaseModel):
    status: str
    output: str
    mode: str
    elapsed: float


class ModeRequest(BaseModel):
    mode: str  # "normal" or "working"


# ── Endpoints ────────────────────────────────────────────────────────────────


@app.get("/")
def root():
    return {
        "system": "GUNA-ASTRA",
        "version": "2.0",
        "status": "online",
        "mode": _orchestrator.current_mode if _orchestrator else "unknown",
        "docs": "/docs",
    }


@app.post("/command", response_model=CommandResponse)
def execute_command(req: CommandRequest):
    """Execute a command through GUNA-ASTRA."""
    if not _orchestrator:
        return CommandResponse(
            status="error",
            output="Orchestrator not initialized.",
            mode="unknown",
            elapsed=0.0,
        )

    with _lock:
        start = time.time()

        # Temporarily override mode if specified
        original_mode = _orchestrator.current_mode
        if req.mode and req.mode in (MODE_NORMAL, MODE_WORKING):
            _orchestrator.current_mode = req.mode

        try:
            result = _orchestrator.process_command(req.text)
        finally:
            if req.mode:
                _orchestrator.current_mode = original_mode

        elapsed = time.time() - start

        return CommandResponse(
            status=result.get("status", "success"),
            output=result.get("output", "Done."),
            mode=_orchestrator.current_mode,
            elapsed=round(elapsed, 2),
        )


@app.get("/status")
def system_status():
    """Get system health status."""
    return {
        "system": "GUNA-ASTRA",
        "mode": _orchestrator.current_mode if _orchestrator else "unknown",
        "ollama": "online" if check_ollama_health() else "offline",
        "mongodb": "connected" if MONGO_AVAILABLE else "in-memory fallback",
        "agents": 11,
        "conversation_length": len(_orchestrator._conversation) if _orchestrator else 0,
    }


@app.get("/history")
def task_history(limit: int = 10):
    """Get recent task history."""
    tasks = get_recent_tasks(limit)
    return {"tasks": tasks}


@app.get("/mode")
def get_mode():
    """Get current operation mode."""
    return {
        "mode": _orchestrator.current_mode if _orchestrator else DEFAULT_MODE,
        "description": (
            "Normal Mode — fast direct execution"
            if (_orchestrator and _orchestrator.current_mode == MODE_NORMAL)
            else "Working Mode — full multi-agent pipeline"
        ),
    }


@app.post("/mode")
def set_mode(req: ModeRequest):
    """Switch operation mode."""
    if req.mode not in (MODE_NORMAL, MODE_WORKING):
        return {"error": f"Invalid mode '{req.mode}'. Use 'normal' or 'working'."}
    if _orchestrator:
        _orchestrator.current_mode = req.mode
    return get_mode()
