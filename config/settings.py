import os

# GUNA-ASTRA Configuration
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, "data")

# Ollama settings
OLLAMA_BASE_URL = "http://localhost:11434"
OLLAMA_MODEL = "llama3"
OLLAMA_TIMEOUT = 120  # seconds

# MongoDB settings
MONGO_URI = "mongodb://localhost:27017"
MONGO_DB_NAME = "guna_astra"

# Safety settings
MAX_TASK_ITERATIONS = 10
TASK_TIMEOUT_SECONDS = 60
DANGEROUS_ACTIONS = [
    "delete_file", "format_drive",
    "install_software", "shutdown"
]

# Logging
LOG_DIR = os.path.join(BASE_DIR, "logs")
LOG_LEVEL = "INFO"

# Agent settings
AGENT_MAX_RETRIES = 3

# Smart routing — skip LLM pipeline for simple system commands
DIRECT_EXECUTION_ENABLED = True
CONVERSATION_HISTORY_SIZE = 20

# Text-to-speech (GUNA-ASTRA speaks responses aloud)
SPEAK_RESPONSES = False

# API Server (for background service mode)
API_HOST = "127.0.0.1"
API_PORT = 7777

# ── Voice Configuration ──────────────────────────────────────────────────────────
VOICE_MODE_ENABLED = False
# Speaker Verification (Resemblyzer)
SPEAKER_VERIFICATION_THRESHOLD = 0.70
USER_VOICE_EMBEDDING_PATH = os.path.join(DATA_DIR, "user_embedding.npy")
# Speech-to-Text (Whisper)
STT_MODEL_SIZE = "small"
# Text-to-Speech
TTS_ENGINE = "sapi5"  # native windows TTS for Hindi/English mix initially
TTS_VOICE_RATE = 150

# ── Modes ──────────────────────────────────────────────────────────────────────
MODE_NORMAL = "normal"       # Quick tasks, direct execution
MODE_WORKING = "working"     # Full multi-agent pipeline
DEFAULT_MODE = MODE_NORMAL   # System starts in Normal Mode
AUTO_SWITCH_TO_WORKING = True  # Auto-switch when complex task detected

# Code execution settings (InterpreterEngine)
CODE_EXECUTION_MAX_RETRIES = 3
PYTHON_TIMEOUT = 60              # seconds
SHELL_TIMEOUT = 30               # seconds
JS_TIMEOUT = 30                  # seconds
DOWNLOAD_TIMEOUT = 120           # seconds
STREAM_BUFFER_SIZE = 1024        # bytes for real-time output

# Normal mode settings
NORMAL_MODE_MAX_RESPONSE_MS = 500  # Target response time

# Computer control settings
SCREENSHOT_DIR = os.path.join(os.path.expanduser("~"), "Desktop")
VOLUME_DEFAULT_STEP = 10         # % to change volume by default

# Chat personality for direct conversations (no agent pipeline)
CHAT_SYSTEM_PROMPT = (
    "You are GUNA-ASTRA, a brilliant personal AI assistant. "
    "You are friendly, witty, and concise. "
    "Answer the user's question directly in 2-4 sentences. "
    "If the user asks you to do something complex (write code, create files, "
    "research topics in depth), tell them to say 'mode working' for full power. "
    "Keep responses short and natural — like a smart friend chatting."
)
