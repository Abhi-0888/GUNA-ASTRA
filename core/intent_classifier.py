"""
GUNA-ASTRA Intent Classifier
Fast, pure-Python intent classification — NO LLM calls.
Classifies user input in < 5ms using exact matches, regex patterns, and fuzzy fallback.
"""

import re

# ── Intent Categories ──────────────────────────────────────────────────────────

OPEN_APP = "OPEN_APP"
OPEN_URL = "OPEN_URL"
PLAY_MUSIC = "PLAY_MUSIC"
PLAY_VIDEO = "PLAY_VIDEO"
CREATE_FILE = "CREATE_FILE"
CREATE_FOLDER = "CREATE_FOLDER"
DELETE_FILE = "DELETE_FILE"
DELETE_FOLDER = "DELETE_FOLDER"
MOVE_FILE = "MOVE_FILE"
COPY_FILE = "COPY_FILE"
RENAME_FILE = "RENAME_FILE"
LIST_DIR = "LIST_DIR"
SHOW_TIME = "SHOW_TIME"
SET_VOLUME = "SET_VOLUME"
VOLUME_UP = "VOLUME_UP"
VOLUME_DOWN = "VOLUME_DOWN"
MUTE_VOLUME = "MUTE_VOLUME"
TAKE_SCREENSHOT = "TAKE_SCREENSHOT"
SHOW_SYSTEM_INFO = "SHOW_SYSTEM_INFO"
SHOW_BATTERY = "SHOW_BATTERY"
LIST_PROCESSES = "LIST_PROCESSES"
KILL_PROCESS = "KILL_PROCESS"
SEARCH_FILES = "SEARCH_FILES"
SHOW_NETWORK = "SHOW_NETWORK"
CHECK_WEBSITE = "CHECK_WEBSITE"
GET_WEATHER = "GET_WEATHER"
EMPTY_TRASH = "EMPTY_TRASH"
LOCK_SCREEN = "LOCK_SCREEN"
SHUTDOWN = "SHUTDOWN"
RESTART = "RESTART"
SLEEP = "SLEEP"
GET_CLIPBOARD = "GET_CLIPBOARD"
SET_CLIPBOARD = "SET_CLIPBOARD"
TYPE_TEXT = "TYPE_TEXT"
PRESS_KEY = "PRESS_KEY"
RUN_COMMAND = "RUN_COMMAND"
ZIP_FILES = "ZIP_FILES"
UNZIP_FILE = "UNZIP_FILE"
DOWNLOAD_FILE = "DOWNLOAD_FILE"
OPEN_FILE_MANAGER = "OPEN_FILE_MANAGER"
FIND_REPLACE = "FIND_REPLACE"
SHOW_HELP = "SHOW_HELP"
SHOW_HISTORY = "SHOW_HISTORY"
SHOW_STATUS = "SHOW_STATUS"
CHANGE_MODE = "CHANGE_MODE"
STOP = "STOP"
READ_DOC = "READ_DOC"
GET_WINDOW = "GET_WINDOW"
COMPLEX_TASK = "COMPLEX_TASK"
CONVERSATION = "CONVERSATION"
UNKNOWN = "UNKNOWN"


# ── Exact Matches (confidence 1.0) ────────────────────────────────────────────

EXACT_MATCHES = {
    # Time / Date
    "time": SHOW_TIME,
    "date": SHOW_TIME,
    "what time is it": SHOW_TIME,
    "what's the time": SHOW_TIME,
    "whats the time": SHOW_TIME,
    "show time": SHOW_TIME,
    "current time": SHOW_TIME,
    "show date": SHOW_TIME,
    "what time": SHOW_TIME,
    "what date": SHOW_TIME,
    "date and time": SHOW_TIME,
    # Screenshot
    "screenshot": TAKE_SCREENSHOT,
    "take screenshot": TAKE_SCREENSHOT,
    "take a screenshot": TAKE_SCREENSHOT,
    "screen capture": TAKE_SCREENSHOT,
    "capture screen": TAKE_SCREENSHOT,
    # Battery
    "battery": SHOW_BATTERY,
    "battery status": SHOW_BATTERY,
    "battery level": SHOW_BATTERY,
    "power status": SHOW_BATTERY,
    "charge level": SHOW_BATTERY,
    "show battery": SHOW_BATTERY,
    "check battery": SHOW_BATTERY,
    # System info
    "sysinfo": SHOW_SYSTEM_INFO,
    "system info": SHOW_SYSTEM_INFO,
    "computer info": SHOW_SYSTEM_INFO,
    "pc info": SHOW_SYSTEM_INFO,
    "hardware info": SHOW_SYSTEM_INFO,
    "show system info": SHOW_SYSTEM_INFO,
    # Network
    "network info": SHOW_NETWORK,
    "show network": SHOW_NETWORK,
    "my ip": SHOW_NETWORK,
    "ip address": SHOW_NETWORK,
    "what is my ip": SHOW_NETWORK,
    "show ip": SHOW_NETWORK,
    # Processes
    "list processes": LIST_PROCESSES,
    "show processes": LIST_PROCESSES,
    "running processes": LIST_PROCESSES,
    "task list": LIST_PROCESSES,
    # Clipboard
    "clipboard": GET_CLIPBOARD,
    "get clipboard": GET_CLIPBOARD,
    "show clipboard": GET_CLIPBOARD,
    "read clipboard": GET_CLIPBOARD,
    "paste clipboard": GET_CLIPBOARD,
    # Volume
    "mute": MUTE_VOLUME,
    "unmute": MUTE_VOLUME,
    "volume up": VOLUME_UP,
    "volume down": VOLUME_DOWN,
    # Power
    "lock screen": LOCK_SCREEN,
    "lock pc": LOCK_SCREEN,
    "lock computer": LOCK_SCREEN,
    "lock": LOCK_SCREEN,
    # File listing
    "list files": LIST_DIR,
    "ls": LIST_DIR,
    "dir": LIST_DIR,
    "show files": LIST_DIR,
    # Trash
    "empty trash": EMPTY_TRASH,
    "empty recycle bin": EMPTY_TRASH,
    "clear trash": EMPTY_TRASH,
    "clear recycle bin": EMPTY_TRASH,
    # Weather
    "weather": GET_WEATHER,
    "show weather": GET_WEATHER,
    "whats the weather": GET_WEATHER,
    "what's the weather": GET_WEATHER,
    # Help / History / Status
    "help": SHOW_HELP,
    "show help": SHOW_HELP,
    "commands": SHOW_HELP,
    "history": SHOW_HISTORY,
    "show history": SHOW_HISTORY,
    "task history": SHOW_HISTORY,
    "status": SHOW_STATUS,
    "show status": SHOW_STATUS,
    "system status": SHOW_STATUS,
    # File manager
    "file manager": OPEN_FILE_MANAGER,
    "open file manager": OPEN_FILE_MANAGER,
    "open explorer": OPEN_FILE_MANAGER,
    "file explorer": OPEN_FILE_MANAGER,
    # Stop
    "stop": STOP,
    "halt": STOP,
    "cancel": STOP,
    "quiet": STOP,
    "shut up": STOP,
    "stop talking": STOP,
    "stop reading": STOP,
    # Screen / Window
    "what's on my screen": GET_WINDOW,
    "whats on my screen": GET_WINDOW,
    "active window": GET_WINDOW,
    "what am i looking at": GET_WINDOW,
    "what window is open": GET_WINDOW,
    # Clear
    "clear": "CLEAR_SCREEN",
}


# ── Regex Patterns (confidence 0.9) ───────────────────────────────────────────

# Each entry: (compiled_regex, intent, param_extractor_func_or_None)
# param_extractor returns a dict of params from the match object


def _extract_app_name(m):
    return {"app_name": m.group(1).strip()}


def _extract_query(m):
    return {"query": m.group(1).strip() if m.group(1) else ""}


def _extract_filename(m):
    raw = m.group(1).strip()
    # Split off " with " content
    parts = re.split(r"\s+with\s+", raw, maxsplit=1)
    result = {"filename": parts[0].strip()}
    if len(parts) > 1:
        result["content"] = parts[1].strip()
    return result


def _extract_folder_name(m):
    return {"folder_name": m.group(1).strip()}


def _extract_level(m):
    return {"level": int(m.group(1))}


def _extract_amount(m):
    amt = m.group(1) if m.lastindex and m.group(1) else "10"
    return {"amount": int(amt) if amt else 10}


def _extract_url(m):
    return {"url": m.group(1).strip()}


def _extract_process(m):
    return {"process_name": m.group(1).strip()}


def _extract_path(m):
    return {"path": m.group(1).strip()}


def _extract_city(m):
    city = m.group(1).strip() if m.lastindex and m.group(1) else None
    return {"city": city}


def _extract_command(m):
    return {"command": m.group(1).strip()}


def _extract_mode(m):
    raw = m.group(1).strip().lower()
    mode_map = {"n": "normal", "w": "working", "normal": "normal", "working": "working"}
    return {"mode": mode_map.get(raw, raw)}


def _extract_clipboard_text(m):
    return {"text": m.group(1).strip()}


def _extract_download(m):
    return {"url": m.group(1).strip()}


REGEX_PATTERNS = []


def _add(pattern, intent, extractor=None):
    REGEX_PATTERNS.append((re.compile(pattern, re.IGNORECASE), intent, extractor))


# ── Mode change
_add(r"^mode\s+(normal|working|n|w)$", CHANGE_MODE, _extract_mode)
_add(r"^switch\s+to\s+(normal|working)\s+mode$", CHANGE_MODE, _extract_mode)

# ── Play music / YouTube
_add(r"^play\s+(.+?)\s+on\s+(?:youtube|yt)$", PLAY_MUSIC, _extract_query)
_add(r"^play\s+(.+?)\s+(?:music|song|video)$", PLAY_MUSIC, _extract_query)
_add(r"^(?:play|listen to|put on|start playing)\s+(.+)$", PLAY_MUSIC, _extract_query)

# ── Open URL (must be before OPEN_APP to catch URLs)
_add(
    r"^(?:open|go to|browse to|visit|navigate to)\s+((?:https?://)?[\w.-]+\.\w{2,}(?:/\S*)?)$",
    OPEN_URL,
    _extract_url,
)
_add(
    r"^([\w.-]+\.(?:com|org|net|io|ai|dev|edu|gov|co|me|app))(?:\s|$)",
    OPEN_URL,
    _extract_url,
)

# ── Open application
_add(r"^open\s+(.+)$", OPEN_APP, _extract_app_name)
_add(r"^launch\s+(.+)$", OPEN_APP, _extract_app_name)
_add(r"^start\s+(.+)$", OPEN_APP, _extract_app_name)

# ── Create file
_add(
    r"^(?:create|make|touch)\s+(?:a\s+)?(?:new\s+)?file\s+(?:called\s+|named\s+)?(.+)$",
    CREATE_FILE,
    _extract_filename,
)
_add(r"^touch\s+(.+)$", CREATE_FILE, _extract_filename)
_add(
    r"^(?:create|make)\s+(.+\.(?:txt|py|js|html|css|md|json|csv|xml|yaml|yml|ini|cfg|log|sh|bat|ps1))$",
    CREATE_FILE,
    _extract_filename,
)

# ── Create folder
_add(
    r"^(?:create|make)\s+(?:a\s+)?(?:new\s+)?(?:folder|directory|dir)\s+(?:called\s+|named\s+)?(.+)$",
    CREATE_FOLDER,
    _extract_folder_name,
)
_add(r"^mkdir\s+(.+)$", CREATE_FOLDER, _extract_folder_name)

# ── Delete file
_add(r"^(?:delete|remove|rm)\s+(?:the\s+)?file\s+(.+)$", DELETE_FILE, _extract_path)
_add(r"^(?:delete|remove|rm)\s+(.+\.[\w]+)$", DELETE_FILE, _extract_path)

# ── Delete folder
_add(
    r"^(?:delete|remove|rm)\s+(?:the\s+)?(?:folder|directory|dir)\s+(.+)$",
    DELETE_FOLDER,
    _extract_path,
)
_add(r"^rmdir\s+(.+)$", DELETE_FOLDER, _extract_path)

# ── Move / Copy / Rename
_add(
    r"^move\s+(.+?)\s+to\s+(.+)$",
    MOVE_FILE,
    lambda m: {"src": m.group(1).strip(), "dst": m.group(2).strip()},
)
_add(
    r"^copy\s+(.+?)\s+to\s+(.+)$",
    COPY_FILE,
    lambda m: {"src": m.group(1).strip(), "dst": m.group(2).strip()},
)
_add(
    r"^rename\s+(.+?)\s+to\s+(.+)$",
    RENAME_FILE,
    lambda m: {"path": m.group(1).strip(), "new_name": m.group(2).strip()},
)

# ── List directory
_add(
    r"^(?:list|ls|dir|show)\s+(?:files|contents|directory)\s*(?:in\s+|of\s+)?(.+)?$",
    LIST_DIR,
    _extract_path,
)
_add(r"^(?:list|ls|dir)\s+(.+)$", LIST_DIR, _extract_path)

# ── Volume
_add(r"^(?:set\s+)?volume\s+(?:to\s+)?(\d+)\s*%?$", SET_VOLUME, _extract_level)
_add(r"^volume\s+(\d+)$", SET_VOLUME, _extract_level)
_add(r"^volume\s+up(?:\s+(\d+))?$", VOLUME_UP, _extract_amount)
_add(
    r"^(?:turn|make)\s+(?:it\s+)?(?:louder|sound\s+up)(?:\s+(\d+))?$",
    VOLUME_UP,
    _extract_amount,
)
_add(r"^increase\s+volume(?:\s+(?:by\s+)?(\d+))?$", VOLUME_UP, _extract_amount)
_add(r"^volume\s+down(?:\s+(\d+))?$", VOLUME_DOWN, _extract_amount)
_add(
    r"^(?:turn|make)\s+(?:it\s+)?(?:quieter|lower|sound\s+down)(?:\s+(\d+))?$",
    VOLUME_DOWN,
    _extract_amount,
)
_add(r"^decrease\s+volume(?:\s+(?:by\s+)?(\d+))?$", VOLUME_DOWN, _extract_amount)
_add(r"^(?:mute|unmute)\s*(?:volume|sound|audio)?$", MUTE_VOLUME, None)

# ── Time / Date
_add(r"^(?:what'?s?\s+the\s+)?(?:current\s+)?(?:time|date|datetime)$", SHOW_TIME, None)
_add(r"^what\s+time", SHOW_TIME, None)
_add(r"^show\s+(?:the\s+)?(?:time|date|clock)$", SHOW_TIME, None)

# ── Screenshot
_add(
    r"^(?:take|capture)\s+(?:a\s+)?(?:screenshot|screen\s*shot|screen\s*capture)$",
    TAKE_SCREENSHOT,
    None,
)

# ── System info
_add(
    r"^(?:show|get)\s+(?:system|pc|computer|cpu|ram|hardware)\s+info",
    SHOW_SYSTEM_INFO,
    None,
)

# ── Battery
_add(r"^(?:show|get|check)\s+(?:the\s+)?battery", SHOW_BATTERY, None)

# ── Kill process
_add(
    r"^(?:kill|close|terminate|stop|end|force quit)\s+(?:process\s+)?(.+)$",
    KILL_PROCESS,
    _extract_process,
)

# ── Search files
_add(
    r"^(?:search|find)\s+(?:files?\s+)?(?:named\s+|called\s+|for\s+)?(.+)$",
    SEARCH_FILES,
    _extract_query,
)

# ── Network
_add(r"^(?:show|get)\s+(?:network|ip|internet)\s*(?:info)?$", SHOW_NETWORK, None)
_add(r"^(?:network|wifi|internet)\s+(?:info|status)$", SHOW_NETWORK, None)

# ── Check website / Ping
_add(
    r"^(?:ping|check)\s+(?:if\s+)?(.+?\.\w{2,})(?:\s+is\s+online)?$",
    CHECK_WEBSITE,
    _extract_url,
)
_add(
    r"^(?:is)\s+(.+?\.\w{2,})\s+(?:online|up|running|working)$",
    CHECK_WEBSITE,
    _extract_url,
)

# ── Weather
_add(r"^weather\s+(?:in|for|at)\s+(.+)$", GET_WEATHER, _extract_city)
_add(r"^(?:what'?s?\s+the\s+)?weather(?:\s+in\s+(.+))?$", GET_WEATHER, _extract_city)
_add(
    r"^(?:show|get|check)\s+(?:the\s+)?weather(?:\s+(?:in|for)\s+(.+))?$",
    GET_WEATHER,
    _extract_city,
)
_add(r"^temperature(?:\s+in\s+(.+))?$", GET_WEATHER, _extract_city)

# ── Lock / Shutdown / Restart / Sleep
_add(r"^lock\s+(?:the\s+)?(?:screen|pc|computer)$", LOCK_SCREEN, None)
_add(r"^(?:shutdown|shut\s+down)\s*(?:the\s+)?(?:computer|pc|system)?$", SHUTDOWN, None)
_add(r"^restart\s*(?:the\s+)?(?:computer|pc|system)?$", RESTART, None)
_add(r"^(?:sleep|hibernate)\s*(?:the\s+)?(?:computer|pc|system)?$", SLEEP, None)

# ── Clipboard
_add(
    r"^(?:copy|set)\s+(?:to\s+)?clipboard\s*[:\-]?\s*(.+)$",
    SET_CLIPBOARD,
    _extract_clipboard_text,
)
_add(r"^(?:copy)\s+(.+)\s+to\s+clipboard$", SET_CLIPBOARD, _extract_clipboard_text)

# ── Type / Keys
_add(r"^type\s+(.+)$", TYPE_TEXT, lambda m: {"text": m.group(1).strip()})
_add(r"^press\s+(.+)$", PRESS_KEY, lambda m: {"key": m.group(1).strip()})

# ── Shell command ($ prefix)
_add(r"^\$\s*(.+)$", RUN_COMMAND, _extract_command)
_add(r"^run\s+(?:command\s+)?[`'\"](.+)[`'\"]$", RUN_COMMAND, _extract_command)
_add(r"^(?:execute|run)\s+(.+\.(?:bat|sh|cmd|ps1))$", RUN_COMMAND, _extract_command)

# ── Zip / Unzip
_add(r"^(?:zip|compress)\s+(.+)$", ZIP_FILES, lambda m: {"paths": m.group(1).strip()})
_add(r"^(?:unzip|extract)\s+(.+)$", UNZIP_FILE, _extract_path)

# ── Download
_add(r"^download\s+(https?://\S+)$", DOWNLOAD_FILE, _extract_download)
_add(
    r"^download\s+(?:file\s+)?(?:from\s+)?(https?://\S+)$",
    DOWNLOAD_FILE,
    _extract_download,
)

# ── File manager
_add(
    r"^open\s+(?:file\s+)?(?:manager|explorer|finder)(?:\s+(?:at|in)\s+(.+))?$",
    OPEN_FILE_MANAGER,
    _extract_path,
)

# ── Find and replace
_add(
    r"^(?:find|replace)\s+(.+?)\s+with\s+(.+?)\s+in\s+(.+)$",
    FIND_REPLACE,
    lambda m: {
        "find": m.group(1).strip(),
        "replace": m.group(2).strip(),
        "file_path": m.group(3).strip(),
    },
)

# ── Stop
_add(
    r"^(?:stop|halt|cancel|quiet|enough|shut\s+up)(?:\s+talking|\s+reading|\s+working)?$",
    STOP,
    None,
)

# ── Read document
_add(
    r"^(?:read|open\s+and\s+read|extract\s+text\s+from)\s+(?:the\s+)?(?:file|doc|document|pdf|docx)?\s*(.+)$",
    READ_DOC,
    _extract_path,
)
_add(r"^read\s+it(?:\s+to\s+me)?$", READ_DOC, lambda m: {"path": "last_opened"})

# ── Active window
_add(
    r"^(?:what|which)\s+(?:window|app|application)\s+is\s+(?:open|active|focused)$",
    GET_WINDOW,
    None,
)
_add(r"^(?:what|whats|what's)\s+on\s+(?:my\s+)?screen$", GET_WINDOW, None)
_add(r"^what\s+am\s+i\s+looking\s+at$", GET_WINDOW, None)

# ── Empty trash
_add(r"^(?:empty|clear)\s+(?:the\s+)?(?:recycle\s*bin|trash)$", EMPTY_TRASH, None)


# ── Complex Task Indicators ───────────────────────────────────────────────────

COMPLEX_KEYWORDS = [
    "research",
    "analyze",
    "create a presentation",
    "write a report",
    "generate a",
    "build a",
    "develop",
    "summarize this",
    "explain in detail",
    "compare",
    "create a python program",
    "write code",
    "write a script",
    "make a spreadsheet",
    "create a powerpoint",
    "make a ppt",
    "draft an email",
    "send an email",
    "write an email",
    "security review",
    "vulnerability",
    "audit",
    "analyze this data",
    "dataset",
    "write a program",
    "build a website",
    "create a project",
    "complete my assignment",
    "implement",
    "debug",
    "fix the bug",
    "generate a report",
    "create a document",
    "write an essay",
]

_COMPLEX_PATTERNS = [
    re.compile(
        r"create\s+(?:a\s+)?(?:powerpoint|ppt|presentation|document|report|project)",
        re.IGNORECASE,
    ),
    re.compile(
        r"write\s+(?:a\s+)?(?:program|application|app|script|code|essay|report)",
        re.IGNORECASE,
    ),
    re.compile(r"build\s+(?:a\s+)?(?:website|app|tool|system|project)", re.IGNORECASE),
    re.compile(r"analyze\s+(?:the\s+)?(?:data|dataset|csv|file)", re.IGNORECASE),
    re.compile(r"research\s+(?:about|on|the)\s+", re.IGNORECASE),
    re.compile(r"generate\s+(?:a\s+)?(?:report|analysis|document|code)", re.IGNORECASE),
    re.compile(r"develop\s+", re.IGNORECASE),
    re.compile(r"implement\s+", re.IGNORECASE),
    re.compile(r"debug\s+", re.IGNORECASE),
    re.compile(r"fix\s+(?:the\s+)?(?:bug|error|issue|code)", re.IGNORECASE),
    re.compile(r"complete\s+(?:my\s+)?(?:assignment|homework|project)", re.IGNORECASE),
]


# ── Conversational Patterns ───────────────────────────────────────────────────

CONVERSATION_EXACT = {
    # Greetings
    "hi",
    "hello",
    "hey",
    "yo",
    "sup",
    "howdy",
    "hola",
    "namaste",
    "good morning",
    "good afternoon",
    "good evening",
    "good night",
    "morning",
    "evening",
    # How are you
    "how are you",
    "how are you doing",
    "how's it going",
    "hows it going",
    "how do you do",
    "what's up",
    "whats up",
    "how are you today",
    "how you doing",
    # Identity / meta
    "who are you",
    "what are you",
    "what's your name",
    "whats your name",
    "what can you do",
    "what do you do",
    "are you an ai",
    "are you real",
    "are you a bot",
    # Casual
    "tell me a joke",
    "joke",
    "tell me something",
    "tell me something interesting",
    "i'm bored",
    "im bored",
    "thank you",
    "thanks",
    "thank you so much",
    "thanks a lot",
    "ok",
    "okay",
    "cool",
    "nice",
    "great",
    "awesome",
    "perfect",
    "bye",
    "goodbye",
    "see you",
    "see ya",
    "later",
    "yes",
    "no",
    "yeah",
    "nah",
    "yep",
    "nope",
}

_CONVERSATION_PATTERNS = [
    # Questions about concepts / knowledge
    re.compile(r"^what\s+(?:is|are|was|were)\s+.+", re.IGNORECASE),
    re.compile(r"^who\s+(?:is|are|was|were)\s+.+", re.IGNORECASE),
    re.compile(r"^where\s+(?:is|are|was|were)\s+.+", re.IGNORECASE),
    re.compile(r"^when\s+(?:is|are|was|were|did)\s+.+", re.IGNORECASE),
    re.compile(
        r"^why\s+(?:is|are|do|does|did|was|were|can|should)\s+.+", re.IGNORECASE
    ),
    re.compile(
        r"^how\s+(?:does|do|did|can|is|are|to|much|many|long|far|old)\s+.+",
        re.IGNORECASE,
    ),
    re.compile(
        r"^(?:can|could|would|will|shall)\s+you\s+(?:tell|explain|describe|help)\s+.+",
        re.IGNORECASE,
    ),
    re.compile(
        r"^(?:tell|explain|describe|teach)\s+(?:me\s+)?(?:about|what|how|why)\s+.+",
        re.IGNORECASE,
    ),
    re.compile(r"^(?:do you|can you|have you|are you|will you)\s+.+", re.IGNORECASE),
    # Opinions / feelings
    re.compile(r"^(?:what\s+do\s+you\s+think)\s+.+", re.IGNORECASE),
    re.compile(
        r"^(?:i\s+(?:think|feel|want|need|like|love|hate|wish))\s+.+", re.IGNORECASE
    ),
    # Greetings with extras
    re.compile(r"^(?:hi|hello|hey|yo)\s+.+", re.IGNORECASE),
    # Suggestions
    re.compile(
        r"^(?:suggest|recommend)\s+(?:me\s+)?(?:a|some|the)\s+.+", re.IGNORECASE
    ),
    re.compile(r"^(?:give me|tell me)\s+(?:a|some|the|an)\s+.+", re.IGNORECASE),
    # Definitions
    re.compile(r"^(?:define|meaning of|definition of)\s+.+", re.IGNORECASE),
]


# ── Classifier ─────────────────────────────────────────────────────────────────


class IntentClassifier:
    """Fast, pure-Python intent classifier. No LLM calls."""

    def classify(self, text: str) -> dict:
        """
        Classify user input.
        Returns: {"intent": str, "params": dict, "confidence": float}
        """
        if not text:
            return {"intent": UNKNOWN, "params": {}, "confidence": 0.0}

        clean = text.strip()
        lower = clean.lower()

        # ── STEP 1: Exact match — system commands (confidence 1.0) ──
        if lower in EXACT_MATCHES:
            intent = EXACT_MATCHES[lower]
            return {"intent": intent, "params": {}, "confidence": 1.0}

        # ── STEP 2: Regex pattern matching — system commands (confidence 0.9) ──
        for pattern, intent, extractor in REGEX_PATTERNS:
            m = pattern.match(clean)
            if m:
                params = extractor(m) if extractor else {}
                return {"intent": intent, "params": params, "confidence": 0.9}

        # ── STEP 3: Complex task detection (confidence 0.85) ──
        for kw in COMPLEX_KEYWORDS:
            if kw in lower:
                return {"intent": COMPLEX_TASK, "params": {}, "confidence": 0.85}

        for pat in _COMPLEX_PATTERNS:
            if pat.search(clean):
                return {"intent": COMPLEX_TASK, "params": {}, "confidence": 0.85}

        # ── STEP 4: Conversation detection (confidence 0.9) ──
        if lower in CONVERSATION_EXACT:
            return {"intent": CONVERSATION, "params": {}, "confidence": 0.9}

        for pat in _CONVERSATION_PATTERNS:
            if pat.match(clean):
                return {"intent": CONVERSATION, "params": {}, "confidence": 0.85}

        # ── STEP 5: Fuzzy fallback ──
        word_count = len(clean.split())

        # Long inputs without complex keywords → conversation (chat with LLM)
        if word_count >= 8:
            return {"intent": CONVERSATION, "params": {}, "confidence": 0.7}

        # Short inputs with action keywords → try system execution
        action_words = [
            "open",
            "run",
            "start",
            "create",
            "make",
            "show",
            "get",
            "set",
            "delete",
            "move",
            "copy",
            "play",
        ]
        if any(lower.startswith(w) for w in action_words):
            return {"intent": UNKNOWN, "params": {}, "confidence": 0.5}

        # Default: treat as conversation (chat) rather than unknown
        return {"intent": CONVERSATION, "params": {}, "confidence": 0.5}
