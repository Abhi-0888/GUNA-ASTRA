"""
MongoDB interface for GUNA-ASTRA.
Only the Memory Agent should call this directly.
"""

from datetime import datetime
from config.settings import MONGO_URI, MONGO_DB_NAME
from utils.logger import get_logger

logger = get_logger("MongoDB")

try:
    from pymongo import MongoClient
    from pymongo.errors import ConnectionFailure
    _client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=3000)
    _client.admin.command("ping")
    _db = _client[MONGO_DB_NAME]
    MONGO_AVAILABLE = True
    logger.info("MongoDB connected successfully.")
except Exception as e:
    _db = None
    MONGO_AVAILABLE = False
    logger.warning(f"MongoDB unavailable — using in-memory fallback. ({e})")

# In-memory fallback store
_memory_store = {
    "tasks": [],
    "logs": [],
    "conversations": [],
    "state": {}
}


def _col(name):
    if MONGO_AVAILABLE:
        return _db[name]
    return None


# ─── Task History ───────────────────────────────────────────────────────────

def save_task(task: dict):
    task["timestamp"] = datetime.utcnow().isoformat()
    if MONGO_AVAILABLE:
        _col("tasks").insert_one(task)
    else:
        _memory_store["tasks"].append(task)


def get_recent_tasks(limit: int = 10) -> list:
    if MONGO_AVAILABLE:
        return list(_col("tasks").find({}, {"_id": 0}).sort("timestamp", -1).limit(limit))
    return _memory_store["tasks"][-limit:]


# ─── Agent Logs ─────────────────────────────────────────────────────────────

def save_log(agent: str, message: str, level: str = "INFO"):
    entry = {
        "agent": agent,
        "message": message,
        "level": level,
        "timestamp": datetime.utcnow().isoformat()
    }
    if MONGO_AVAILABLE:
        _col("logs").insert_one(entry)
    else:
        _memory_store["logs"].append(entry)


# ─── Conversation Memory ─────────────────────────────────────────────────────

def save_conversation(role: str, content: str, session_id: str = "default"):
    entry = {
        "session_id": session_id,
        "role": role,
        "content": content,
        "timestamp": datetime.utcnow().isoformat()
    }
    if MONGO_AVAILABLE:
        _col("conversations").insert_one(entry)
    else:
        _memory_store["conversations"].append(entry)


def get_conversation_history(session_id: str = "default", limit: int = 20) -> list:
    if MONGO_AVAILABLE:
        return list(
            _col("conversations")
            .find({"session_id": session_id}, {"_id": 0})
            .sort("timestamp", 1)
            .limit(limit)
        )
    return [m for m in _memory_store["conversations"] if m.get("session_id") == session_id][-limit:]


# ─── System State ────────────────────────────────────────────────────────────

def set_state(key: str, value):
    if MONGO_AVAILABLE:
        _col("state").update_one({"key": key}, {"$set": {"value": value}}, upsert=True)
    else:
        _memory_store["state"][key] = value


def get_state(key: str):
    if MONGO_AVAILABLE:
        doc = _col("state").find_one({"key": key}, {"_id": 0})
        return doc["value"] if doc else None
    return _memory_store["state"].get(key)
