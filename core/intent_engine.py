"""
GUNA-ASTRA Intent Engine
------------------------
Smart classifier that instantly determines:
  - CHAT       → simple conversation, no agents needed
  - SINGLE     → one agent can handle it
  - MULTI      → needs planning + multiple agents
  - BACKGROUND → run agents while user does something else (e.g. play music)
"""

import re
from dataclasses import dataclass
from typing import Optional

# ─────────────────────────────────────────────
#  Intent Categories
# ─────────────────────────────────────────────
CHAT    = "CHAT"
SINGLE  = "SINGLE"
MULTI   = "MULTI"
BACKGROUND = "BACKGROUND"

# ─────────────────────────────────────────────
#  Pattern banks
# ─────────────────────────────────────────────

CHAT_PATTERNS = [
    r"^(hey|hi|hello|sup|yo)\b",
    r"^(what'?s? (up|going on|happening))",
    r"^(how are you|how r u|how do you do)",
    r"^(what'?s? your name|who are you|what are you)",
    r"^(what'?s? my name|do you know me|remember me)",
    r"^(good (morning|afternoon|evening|night))",
    r"^(thanks|thank you|ty|thx)\b",
    r"^(ok|okay|cool|got it|sure|alright)\b",
    r"^(bye|goodbye|see you|cya)\b",
    r"^(lol|haha|hehe|nice|wow|great|awesome)\b",
    r"^tell me (a joke|something|about yourself)",
    r"^(what time|what date|what day)",
    r"^(i (am|am feeling|feel|like|hate|love|want to say))",
    r"^(help|what can you do|show commands)",
]

MEDIA_PATTERNS = [
    r"play\s+(.+?)\s*(on\s+(youtube|spotify|music))?",
    r"(open|launch|start)\s+(youtube|spotify|netflix|music|video)",
    r"(pause|stop|resume|next|previous|skip)\s+(music|song|video|playback)",
    r"(volume|mute|unmute)\b",
    r"(search|find|look up)\s+.+\s+on\s+(youtube|spotify)",
]

BROWSER_PATTERNS = [
    r"(open|go to|navigate to|visit)\s+(google|youtube|github|reddit|twitter|wikipedia|https?://\S+)",
    r"(search|google)\s+(for\s+)?(.+)",
    r"open\s+(chrome|firefox|browser|edge)",
]

SYSTEM_PATTERNS = [
    r"(open|launch|start|run)\s+\w+(\s+app)?",
    r"(close|kill|stop)\s+\w+",
    r"(screenshot|screen shot|capture screen)",
    r"(shutdown|restart|sleep|hibernate|lock)\s+(pc|computer|system|laptop)?",
    r"(create|make|new)\s+(folder|file|directory)\s+",
    r"(delete|remove)\s+(folder|file)\s+",
    r"(copy|move|rename)\s+.+",
    r"(type|write|input)\s+.+",
    r"(click|press|tap)\s+.+",
]

CODE_PATTERNS = [
    r"(write|create|build|make|generate|code)\s+(a\s+)?(python|script|program|function|class|app|tool)",
    r"(debug|fix|repair|solve)\s+(this\s+)?(code|error|bug|issue)",
    r"(explain|review|analyze)\s+(this\s+)?(code|script|function)",
]

RESEARCH_PATTERNS = [
    r"(research|find out|look up|tell me about|explain|summarize|what is|who is|how does)\s+.{5,}",
    r"(latest|recent|current|new(s)?)\s+(on|about|in)\s+.+",
    r"(difference between|compare|versus|vs)\s+.+",
]

MULTI_PATTERNS = [
    r"(and|then|also|after that|followed by)",  # chained tasks
    r"(create|build|make).+(and|then).+(test|send|upload|save|open)",
    r"(research|find).+(and|then).+(write|create|build|code)",
    r"(write|draft).+(and|then).+(send|email|upload)",
    r"(analyze|process).+(and|then).+(visualize|plot|chart|show)",
]

BACKGROUND_CUES = [
    r"(while|as|in the meantime|meanwhile|background|keep working|continue)",
    r"play.+(while|as).+",
    r"(still|continue).+(working|processing|running)",
]


@dataclass
class Intent:
    category: str           # CHAT / SINGLE / MULTI / BACKGROUND
    primary_agent: Optional[str] = None   # which agent handles it
    confidence: float = 1.0
    entities: dict = None   # extracted info (song name, url, etc.)
    raw_input: str = ""

    def __post_init__(self):
        if self.entities is None:
            self.entities = {}


def _match(patterns: list, text: str) -> bool:
    for p in patterns:
        if re.search(p, text, re.IGNORECASE):
            return True
    return False


def _extract_media_entity(text: str) -> dict:
    """Extract song/video title and platform from user input."""
    entities = {"platform": "youtube", "query": ""}

    # platform detection
    if re.search(r"\bspotify\b", text, re.I):
        entities["platform"] = "spotify"
    elif re.search(r"\byoutube\b", text, re.I):
        entities["platform"] = "youtube"

    # Extract song / query:
    # "play <X> on youtube" or "play <X>"
    m = re.search(
        r"play\s+(.+?)(?:\s+(?:on|in|via)\s+(?:youtube|spotify|music))?$",
        text, re.IGNORECASE
    )
    if m:
        query = m.group(1).strip()
        # Remove trailing filler words
        query = re.sub(r"\s+(on|in|via|using|with)\s*$", "", query, flags=re.I)
        entities["query"] = query

    return entities


def _extract_browser_entity(text: str) -> dict:
    entities = {}
    # Direct URL
    m = re.search(r"https?://\S+", text)
    if m:
        entities["url"] = m.group(0)
        return entities

    # "open X" or "go to X"
    m = re.search(r"(?:open|go to|visit|navigate to)\s+(\S+)", text, re.I)
    if m:
        site = m.group(1).strip(".,!?")
        if "." not in site:
            site = site + ".com"
        entities["url"] = "https://" + site
        return entities

    # "search for X"
    m = re.search(r"(?:search|google)\s+(?:for\s+)?(.+)", text, re.I)
    if m:
        q = m.group(1).strip()
        entities["url"] = f"https://www.google.com/search?q={q.replace(' ', '+')}"
    return entities


def classify(user_input: str) -> Intent:
    """
    Main classifier. Returns an Intent object.
    Order of priority:
      1. CHAT  (fast path — no agents)
      2. BACKGROUND cues (parallel work)
      3. MULTI (chained / complex)
      4. SINGLE agent detection
    """
    text = user_input.strip()

    # ── 1. Pure chat ────────────────────────────────
    if _match(CHAT_PATTERNS, text):
        return Intent(CHAT, raw_input=text, confidence=0.95)

    # ── 2. Background / parallel ────────────────────
    has_background = _match(BACKGROUND_CUES, text)

    # ── 3. Multi-step ───────────────────────────────
    if _match(MULTI_PATTERNS, text) and not has_background:
        return Intent(MULTI, raw_input=text, confidence=0.85)

    # ── 4. Media ────────────────────────────────────
    if _match(MEDIA_PATTERNS, text):
        entities = _extract_media_entity(text)
        category = BACKGROUND if has_background else SINGLE
        return Intent(category, primary_agent="SystemAgent",
                      entities=entities, raw_input=text, confidence=0.9)

    # ── 5. Browser ──────────────────────────────────
    if _match(BROWSER_PATTERNS, text):
        entities = _extract_browser_entity(text)
        return Intent(SINGLE, primary_agent="SystemAgent",
                      entities=entities, raw_input=text, confidence=0.88)

    # ── 6. System ───────────────────────────────────
    if _match(SYSTEM_PATTERNS, text):
        return Intent(SINGLE, primary_agent="SystemAgent",
                      raw_input=text, confidence=0.85)

    # ── 7. Code ─────────────────────────────────────
    if _match(CODE_PATTERNS, text):
        return Intent(SINGLE, primary_agent="CodingAgent",
                      raw_input=text, confidence=0.88)

    # ── 8. Research ─────────────────────────────────
    if _match(RESEARCH_PATTERNS, text):
        return Intent(SINGLE, primary_agent="ResearchAgent",
                      raw_input=text, confidence=0.82)

    # ── 9. Default: let LLM decide (MULTI path) ─────
    return Intent(MULTI, raw_input=text, confidence=0.6)
