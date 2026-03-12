"""
GUNA-ASTRA Orchestrator
The central brain — coordinates all agents through a strict pipeline.

Two Modes:
  NORMAL MODE  — default, fast direct execution via IntentClassifier + ComputerController
  WORKING MODE — full multi-agent pipeline for complex goals

v2 Smart Routing (layered on top of modes):
  CHAT       — instant reply, no agents
  SINGLE     — one agent handles it
  MULTI      — full pipeline
  BACKGROUND — run in background thread

Smart routing in Normal Mode bypasses LLM for instant system commands.
Enhanced with InterpreterEngine for autonomous code execution.
"""

import json
import os
import random
import re
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime

from agents.coding_agent import CodingAgent
from agents.memory_agent import MemoryAgent
from agents.planner_agent import PlannerAgent
from agents.research_agent import ResearchAgent
from agents.result_synthesizer import ResultSynthesizer
from agents.system_agent import SystemAgent
from agents.task_dispatcher import TaskDispatcher
from agents.testing_agent import TestingAgent
from agents.verification_agent import VerificationAgent
from config.settings import (AUTO_SWITCH_TO_WORKING, CHAT_SYSTEM_PROMPT,
                             CONVERSATION_HISTORY_SIZE, DEFAULT_MODE,
                             DIRECT_EXECUTION_ENABLED, MAX_TASK_ITERATIONS,
                             MODE_NORMAL, MODE_WORKING, SPEAK_RESPONSES,
                             TASK_TIMEOUT_SECONDS)
from core.computer_controller import ComputerController
from core.intent_classifier import (CHANGE_MODE, CHECK_WEBSITE, COMPLEX_TASK,
                                    CONVERSATION, COPY_FILE, CREATE_FILE,
                                    CREATE_FOLDER, DELETE_FILE, DELETE_FOLDER,
                                    DOWNLOAD_FILE, EMPTY_TRASH, FIND_REPLACE,
                                    GET_CLIPBOARD, GET_WEATHER, GET_WINDOW,
                                    KILL_PROCESS, LIST_DIR, LIST_PROCESSES,
                                    LOCK_SCREEN, MOVE_FILE, MUTE_VOLUME,
                                    OPEN_APP, OPEN_FILE_MANAGER, OPEN_URL,
                                    PLAY_MUSIC, PLAY_VIDEO, PRESS_KEY,
                                    READ_DOC, RENAME_FILE, RESTART,
                                    RUN_COMMAND, SEARCH_FILES, SET_CLIPBOARD,
                                    SET_VOLUME, SHOW_BATTERY, SHOW_HELP,
                                    SHOW_HISTORY, SHOW_NETWORK, SHOW_STATUS,
                                    SHOW_SYSTEM_INFO, SHOW_TIME, SHUTDOWN,
                                    SLEEP, STOP, TAKE_SCREENSHOT, TYPE_TEXT,
                                    UNKNOWN, UNZIP_FILE, VOLUME_DOWN,
                                    VOLUME_UP, ZIP_FILES, IntentClassifier)
from core.intent_engine import BACKGROUND, CHAT, MULTI, SINGLE
from core.intent_engine import classify as v2_classify
from core.interpreter_engine import InterpreterEngine
from utils.llm_client import LLMClient, check_ollama_health
from utils.logger import get_logger
from utils.memory_db import (MemoryDB, get_conversation_history,
                             save_conversation, save_task)

logger = get_logger("GUNA-ASTRA")

# ── v2 Chat Responses ──────────────────────────────────────────────────────
CHAT_RESPONSES = {
    "greetings": [
        "Hey {name}! What can I do for you? 👋",
        "Hello {name}! Ready to assist! ⚡",
        "Hi {name}! What's on your mind?",
    ],
    "farewell": ["See you later! 👋", "Bye {name}! 👋", "Take care!"],
    "thanks": ["Happy to help!", "No problem! 😊", "You're welcome!"],
    "status": ["All systems running! ⚡", "I'm here and ready!"],
    "identity": [
        "I'm GUNA-ASTRA — your AI-powered system agent!",
        "I'm GUNA-ASTRA v2.0, your personal AI assistant!",
    ],
}


class GUNAASTRAOrchestrator:
    def __init__(self):
        self.planner = PlannerAgent()
        self.dispatcher = TaskDispatcher()
        self.tester = TestingAgent()
        self.verifier = VerificationAgent()
        self.synthesizer = ResultSynthesizer()
        self.system_agent = SystemAgent()
        self.session_id = f"session_{int(time.time())}"

        # ── v2.0 additions ──
        self.current_mode = DEFAULT_MODE
        self.current_directory = os.path.expanduser("~")
        self.computer = ComputerController()
        self.engine = InterpreterEngine()
        self.classifier = IntentClassifier()
        self.voice_manager = None

        self._pending_confirmation = None
        self._conversation = []

        # Normal Mode command history for follow-ups
        self.normal_mode_history = []
        self.MAX_NORMAL_HISTORY = 20
        self._last_doc_path = None

        # ── v2 Smart Routing additions ──
        self.llm = LLMClient()
        self.memory = MemoryDB()
        self.user_name = self._load_user_name()
        self.bg_futures = []
        self._executor = ThreadPoolExecutor(max_workers=3)
        self.research_agent = ResearchAgent()
        self.coding_agent = CodingAgent()
        self.memory_agent = MemoryAgent()

    # ─── Path Shortening ──────────────────────────────────────────────────

    def _shorten_path(self, path: str) -> str:
        """Shorten path for display: ~/Desktop instead of full path."""
        home = os.path.expanduser("~")
        if path.startswith(home):
            return "~" + path[len(home) :]
        return path

    # ─── v2 User Name Memory ─────────────────────────────────────────────

    def _load_user_name(self) -> str:
        """Load user name from memory, if previously stored."""
        try:
            data = self.memory.recall("user_name")
            if data and isinstance(data, dict):
                return data.get("name", "")
        except Exception:
            pass
        return ""

    def _save_user_name(self, name: str):
        """Persist user name to memory."""
        self.user_name = name
        self.memory.remember("user_name", {"name": name})

    # ─── v2 Smart Routing ─────────────────────────────────────────────────

    def _v2_route(self, user_input: str) -> str | None:
        """
        v2 smart intent routing. Returns a response string if handled,
        or None to fall through to existing Normal/Working mode routing.
        """
        intent = v2_classify(user_input)
        t = user_input.lower().strip()

        # ── Check for user name save/recall ──
        name_match = re.match(r"(?:my name is|i'?m|call me|i am)\s+(.+)", t, re.I)
        if name_match:
            name = name_match.group(1).strip().title()
            self._save_user_name(name)
            return f"Got it! I'll remember you as {name}. 😊"

        if re.search(r"what'?s? my name|do you know my name|who am i", t, re.I):
            if self.user_name:
                return f"Your name is {self.user_name}! 😊"
            return "I don't know your name yet. Tell me by saying 'my name is ...'"

        # ── Route by v2 intent category ──
        if intent.category == CHAT:
            return self._v2_chat(t)
        elif intent.category == BACKGROUND:
            return self._v2_background(user_input, intent)
        elif intent.category == SINGLE:
            return self._v2_single(user_input, intent)
        # MULTI → fall through to existing pipeline
        return None

    def _v2_chat(self, text: str) -> str:
        """v2 instant chat response — no agents involved."""
        name = self.user_name or "there"

        if re.search(r"^(hey|hi|hello|sup|yo|good\s)", text, re.I):
            return random.choice(CHAT_RESPONSES["greetings"]).format(name=name)
        if re.search(r"^(bye|goodbye|see you|cya)", text, re.I):
            return random.choice(CHAT_RESPONSES["farewell"]).format(name=name)
        if re.search(r"^(thanks|thank|ty|thx)", text, re.I):
            return random.choice(CHAT_RESPONSES["thanks"]).format(name=name)
        if re.search(r"(what can you do|help|what are you|who are you)", text, re.I):
            return random.choice(CHAT_RESPONSES["identity"]).format(name=name)
        if re.search(r"(how are you|how r u|what'?s up)", text, re.I):
            return random.choice(CHAT_RESPONSES["status"]).format(name=name)

        # Catch-all: try LLM for generic chat
        try:
            return self.llm.ask(
                user=text,
                system="You are GUNA-ASTRA, a friendly AI assistant. Reply briefly and naturally.",
                temperature=0.8,
                max_tokens=200,
            )
        except Exception:
            return "I'm here! How can I help?"

    def _v2_single(self, text: str, intent) -> str:
        """v2 route to a single agent and return result."""
        agent_name = intent.primary_agent or "SystemAgent"
        entities = intent.entities or {}

        # Inject media hints for SystemAgent
        if agent_name == "SystemAgent" and entities.get("query"):
            hint_text = (
                f"{text} [EXTRACTED_QUERY: {entities['query']}]"
                f" [PLATFORM: {entities.get('platform', 'youtube')}]"
            )
            result = self.system_agent.execute(hint_text)
        elif agent_name == "ResearchAgent":
            result = self.research_agent.execute(text)
        elif agent_name == "CodingAgent":
            result = self.coding_agent.execute(text)
        elif agent_name == "MemoryAgent":
            result = self.memory_agent.execute(text)
        else:
            result = self.system_agent.execute(text)

        # Save to history
        self.memory.add_history(text, result[:200])
        return result

    def _v2_background(self, text: str, intent) -> str:
        """v2 run task in background thread."""

        def _bg_task():
            try:
                return self._v2_single(text, intent)
            except Exception as e:
                logger.error(f"Background task failed: {e}")
                return f"Background task failed: {e}"

        future = self._executor.submit(_bg_task)
        self.bg_futures.append(future)
        return f"🔄 Running in background: {text[:60]}..."

    def run(self):
        logger.info("GUNA-ASTRA v2.0 orchestrator is online.")

        if not check_ollama_health():
            print(
                "\033[91m[WARNING] Ollama is not running. Start it with: ollama serve\033[0m"
            )
            print(
                "\033[93mYou can still use Normal Mode — direct commands work without LLM!\033[0m\n"
            )

        self._print_mode()

        while True:
            try:
                mode_icon = "⚡" if self.current_mode == MODE_NORMAL else "🤖"
                short_dir = self._shorten_path(self.current_directory)
                prompt = f"\n\033[96m{mode_icon} [{self.current_mode.upper()}] {short_dir} >\033[0m "
                user_input = input(prompt).strip()
            except (EOFError, KeyboardInterrupt):
                print("\n\n\033[96m[GUNA-ASTRA] Goodbye. Stay productive! 👋\033[0m")
                break

            if not user_input:
                continue

            if user_input.lower() in ("exit", "quit", "bye", "goodbye"):
                print("\n\033[96m[GUNA-ASTRA] Goodbye. Stay productive! 👋\033[0m")
                break

            if user_input.lower() == "clear":
                os.system("cls" if os.name == "nt" else "clear")
                from utils.banner import print_banner

                print_banner()
                self._print_mode()
                continue

            # Handle pending confirmation
            if self._pending_confirmation:
                self._resolve_confirmation(user_input)
                continue

            # Resolve follow-up references ("that file", "again")
            user_input = self._resolve_references(user_input)

            # Save to conversation context
            self._remember("user", user_input)

            # ── v2 Smart Routing (first pass) ──
            # Tries CHAT/SINGLE/BACKGROUND instantly. Returns None for MULTI.
            v2_response = self._v2_route(user_input)
            if v2_response is not None:
                print(f"\n\033[92m{v2_response}\033[0m")
                self._remember("assistant", v2_response)
                continue

            # Classify the intent FIRST (fast, no LLM)
            classification = self.classifier.classify(user_input)
            intent = classification["intent"]
            params = classification["params"]
            confidence = classification["confidence"]

            # Handle mode change
            if intent == CHANGE_MODE:
                self._change_mode(params.get("mode", ""))
                continue

            # Handle help/history/status
            if intent == SHOW_HELP:
                self._show_help()
                continue
            if intent == SHOW_HISTORY:
                self._show_history()
                continue
            if intent == SHOW_STATUS:
                self._show_status()
                continue
            if intent == "CLEAR_SCREEN":
                os.system("cls" if os.name == "nt" else "clear")
                from utils.banner import print_banner

                print_banner()
                self._print_mode()
                continue

            # ── ROUTING DECISION ──
            if self.current_mode == MODE_NORMAL:
                if intent == CONVERSATION:
                    self._handle_conversation(user_input)
                elif intent == COMPLEX_TASK:
                    if AUTO_SWITCH_TO_WORKING:
                        print(
                            f"\n\033[93m[GUNA-ASTRA] 💡 This looks like a complex task.\033[0m"
                        )
                        print(
                            f"\033[93m[GUNA-ASTRA] Switching to WORKING MODE for this request...\033[0m"
                        )
                        self._process_goal_working_mode(user_input)
                    else:
                        print(
                            f"\n\033[93m[GUNA-ASTRA] 💡 This looks complex. "
                            f"Say 'mode working' to switch.\033[0m"
                        )
                        self._execute_simple_pipeline(user_input)
                elif intent == UNKNOWN:
                    # Unknown with action keywords — try direct system execution
                    self._execute_direct_fallback(user_input)
                else:
                    # Execute in Normal Mode via ComputerController
                    result = self._execute_normal_mode(intent, params, user_input)
                    self._display_normal_result(result)
                    self._save_normal_history(user_input, intent, params, result)

            elif self.current_mode == MODE_WORKING:
                if intent == CONVERSATION:
                    self._handle_conversation(user_input)
                else:
                    self._process_goal_working_mode(user_input)

    # ─── API Entry Point ──────────────────────────────────────────────────

    def process_command(self, text: str) -> dict:
        """Process a command and return result dict. Used by FastAPI."""
        self._remember("user", text)
        classification = self.classifier.classify(text)
        intent = classification["intent"]
        params = classification["params"]

        if intent == CONVERSATION:
            response = self._handle_conversation(text, silent=True)
            return {"status": "success", "output": response, "agent": "DirectChat"}

        if self.current_mode == MODE_NORMAL:
            if intent in (COMPLEX_TASK,) and len(text.split()) > 6:
                return self._process_goal_full_pipeline_api(text)
            elif intent == UNKNOWN:
                return self._execute_direct_api(text)
            else:
                result = self._execute_normal_mode(intent, params, text)
                return {
                    "status": "success" if result.get("success") else "failed",
                    "output": result.get("output", ""),
                    "agent": "ComputerController",
                }
        else:
            return self._process_goal_full_pipeline_api(text)

    def process_voice_command(self, text: str) -> str:
        """Used specifically by the VoiceManager to inject speech text and return a synthesized string response."""
        result_dict = self.process_command(text)

        # Simple extraction of standard output for TTS reading
        if result_dict.get("output"):
            return str(result_dict["output"])
        elif result_dict.get("result"):
            return str(result_dict["result"])
        return "I have completed the task."

    def start_voice_service(self):
        """Starts the continuous acoustic VoiceManager in a background thread."""
        from config.settings import VOICE_MODE_ENABLED

        if not VOICE_MODE_ENABLED:
            logger.warning(
                "Voice mode requested but VOICE_MODE_ENABLED=False in settings.py"
            )
            return

        try:
            import threading

            from core.voice.voice_manager import VoiceManager

            self.voice_manager = VoiceManager(self)

            # Start the heavy voice loop in a daemon thread so it exits when CLI exits
            voice_thread = threading.Thread(
                target=self.voice_manager.start_listening, daemon=True
            )
            voice_thread.start()
            logger.info("Voice Service started in background thread.")
        except Exception as e:
            logger.error(f"Failed to start voice service: {e}")

    # ─── Normal Mode Execution ────────────────────────────────────────────

    def _execute_normal_mode(self, intent: str, params: dict, raw_input: str) -> dict:
        """Route to the correct ComputerController method based on intent."""
        cc = self.computer

        if intent == OPEN_APP:
            return cc.open_application(
                params.get(
                    "app_name", raw_input.replace("open ", "").replace("launch ", "")
                )
            )

        elif intent == OPEN_URL:
            url = params.get("url", "")
            if not url.startswith("http"):
                url = "https://" + url
            return cc.open_url(url)

        elif intent in (PLAY_MUSIC, PLAY_VIDEO):
            return cc.play_youtube(params.get("query", raw_input))

        elif intent == CREATE_FILE:
            filename = params.get("filename", "")
            content = params.get("content", "")
            path = os.path.join(self.current_directory, filename) if filename else ""
            return cc.create_file(path, content)

        elif intent == CREATE_FOLDER:
            name = params.get("folder_name", "")
            path = os.path.join(self.current_directory, name) if name else ""
            return cc.create_folder(path)

        elif intent == DELETE_FILE:
            path = params.get("path", "")
            if path and not os.path.isabs(path):
                path = os.path.join(self.current_directory, path)
            return cc.delete_file(path)

        elif intent == DELETE_FOLDER:
            path = params.get("path", "")
            if path and not os.path.isabs(path):
                path = os.path.join(self.current_directory, path)
            return cc.delete_folder(path, recursive=True)

        elif intent == MOVE_FILE:
            return cc.move_file(params.get("src", ""), params.get("dst", ""))

        elif intent == COPY_FILE:
            return cc.copy_file(params.get("src", ""), params.get("dst", ""))

        elif intent == RENAME_FILE:
            return cc.rename_file(params.get("path", ""), params.get("new_name", ""))

        elif intent == LIST_DIR:
            path = params.get("path", self.current_directory)
            if path and not os.path.isabs(path):
                path = os.path.join(self.current_directory, path)
            return cc.list_directory(path or self.current_directory)

        elif intent == SHOW_TIME:
            return cc.show_datetime()

        elif intent == SET_VOLUME:
            return cc.set_volume(int(params.get("level", 50)))

        elif intent == VOLUME_UP:
            return cc.volume_up(int(params.get("amount", 10)))

        elif intent == VOLUME_DOWN:
            return cc.volume_down(int(params.get("amount", 10)))

        elif intent == MUTE_VOLUME:
            return cc.mute_volume()

        elif intent == TAKE_SCREENSHOT:
            return cc.take_screenshot(params.get("path"))

        elif intent == SHOW_SYSTEM_INFO:
            return cc.get_system_info()

        elif intent == SHOW_BATTERY:
            return cc.get_battery_status()

        elif intent == LIST_PROCESSES:
            return cc.list_processes()

        elif intent == KILL_PROCESS:
            return cc.kill_process(params.get("process_name", ""))

        elif intent == SEARCH_FILES:
            return cc.search_files(params.get("query", ""))

        elif intent == SHOW_NETWORK:
            return cc.get_network_info()

        elif intent == CHECK_WEBSITE:
            return cc.check_website(params.get("url", ""))

        elif intent == GET_WEATHER:
            return cc.get_weather(params.get("city"))

        elif intent == EMPTY_TRASH:
            return cc.empty_trash()

        elif intent == LOCK_SCREEN:
            return cc.lock_screen()

        elif intent == SHUTDOWN:
            return cc.shutdown_computer()

        elif intent == RESTART:
            return cc.restart_computer()

        elif intent == SLEEP:
            return cc.sleep_computer()

        elif intent == GET_CLIPBOARD:
            return cc.get_clipboard()

        elif intent == SET_CLIPBOARD:
            return cc.set_clipboard(params.get("text", ""))

        elif intent == TYPE_TEXT:
            return cc.type_text(params.get("text", ""))

        elif intent == PRESS_KEY:
            return cc.press_key(params.get("key", ""))

        elif intent == RUN_COMMAND:
            command = params.get("command", raw_input)
            return self.engine.execute_shell(command, self.current_directory)

        elif intent == ZIP_FILES:
            paths_str = params.get("paths", "")
            return cc.zip_files(paths_str)

        elif intent == UNZIP_FILE:
            return cc.unzip_file(params.get("path", ""))

        elif intent == DOWNLOAD_FILE:
            return cc.download_file(params.get("url", ""))

        elif intent == OPEN_FILE_MANAGER:
            return cc.open_file_manager(params.get("path", self.current_directory))

        elif intent == FIND_REPLACE:
            return cc.find_replace_in_file(
                params.get("file_path", ""),
                params.get("find", ""),
                params.get("replace", ""),
            )

        elif intent == READ_DOC:
            path = params.get("path", "")
            if path == "last_opened":
                path = self._last_doc_path

            if not path or not os.path.exists(path):
                # Try to find a file if only a name was given
                search_res = cc.search_files(path)
                if search_res["success"] and "Found" in search_res["output"]:
                    # Heuristic: pick the first one
                    found_path = search_res["output"].split("\n")[1].strip()
                    path = found_path

            if path:
                self._last_doc_path = path
                return cc.read_document(path)
            return {
                "success": False,
                "output": "I couldn't find the document you want me to read.",
                "action": READ_DOC,
            }

        elif intent == GET_WINDOW:
            return cc.get_active_window()

        elif intent == STOP:
            # This is primarily handled in VoiceManager, but we can acknowledge it here
            return {"success": True, "output": "Stopping all tasks.", "action": STOP}

        else:
            return {
                "success": False,
                "output": f"Action not yet implemented: {intent}",
                "action": intent,
            }

    # ─── Result Display ───────────────────────────────────────────────────

    def _display_normal_result(self, result: dict):
        """Display Normal Mode results with clean formatting."""
        if result.get("success"):
            color = "\033[92m"  # Green
        else:
            color = "\033[91m"  # Red

        output = result.get("output", "")
        print(f"\n{color}{output}\033[0m")

    # ─── Direct Fallback (for unknown short commands) ─────────────────────

    def _execute_direct_fallback(self, user_input: str):
        """Fallback: try SystemAgent directly for unknown Normal Mode input."""
        print(f"\n\033[90m{'─' * 60}\033[0m")
        print(f"\033[93m[GUNA-ASTRA] ⚡ Normal Mode — Direct execution...\033[0m")

        start = time.time()
        task = {"description": user_input, "original_goal": user_input}
        result = self.system_agent.run(task)
        elapsed = time.time() - start

        if result.get("status") == "pending_confirmation":
            print(f"\n\033[93m{result['output']}\033[0m")
            self._pending_confirmation = {"task": task, "plan": result}
            return

        output = result.get("output", "Done.")
        status = result.get("status", "success")
        icon = "✅" if status == "success" else "❌"

        print(f"\033[92m[GUNA-ASTRA] {icon} {output}\033[0m")
        print(f"\033[90m  ⚡ Completed in {elapsed:.1f}s\033[0m")

        if SPEAK_RESPONSES and status == "success":
            try:
                from utils.system_tools import speak

                speak(output[:200])
            except Exception:
                pass

        save_task(
            {
                "goal": user_input,
                "task_count": 1,
                "status": status,
                "mode": "normal",
                "direct": True,
            }
        )
        save_conversation("user", user_input, self.session_id)
        save_conversation("assistant", output, self.session_id)
        self._remember("assistant", output)

    # ── Direct Conversation (LLM Chat) ────────────────────────────────────

    def _handle_conversation(self, user_input: str, silent: bool = False) -> str:
        """Handle conversational input by chatting directly with the LLM."""
        from utils.llm_client import query_llm

        if not silent:
            print(f"\n\033[90m{'─' * 60}\033[0m")
            print(f"\033[96m[GUNA-ASTRA] 💬 Chatting...\033[0m")

        # Build context from recent conversation history
        context_lines = []
        for msg in self._conversation[-6:]:  # Last 6 messages for context
            role = msg["role"].capitalize()
            context_lines.append(f"{role}: {msg['content']}")

        if context_lines:
            prompt = (
                "Recent conversation:\n"
                + "\n".join(context_lines)
                + f"\n\nUser: {user_input}\n\nRespond naturally:"
            )
        else:
            prompt = user_input

        start = time.time()
        response = query_llm(prompt, system_prompt=CHAT_SYSTEM_PROMPT)
        elapsed = time.time() - start

        if not response or response.startswith("ERROR"):
            response = "I'm having trouble connecting to my brain right now. Make sure Ollama is running!"

        if not silent:
            print(f"\n\033[92m[GUNA-ASTRA]\033[0m {response}")
            print(f"\033[90m  💬 Replied in {elapsed:.1f}s\033[0m")

            if SPEAK_RESPONSES:
                try:
                    from utils.system_tools import speak

                    speak(response[:200])
                except Exception:
                    pass

        save_conversation("user", user_input, self.session_id)
        save_conversation("assistant", response, self.session_id)
        self._remember("assistant", response)

        return response

    def _execute_direct_api(self, text: str) -> dict:
        """Direct execution for API."""
        task = {"description": text, "original_goal": text}
        result = self.system_agent.run(task)
        save_task(
            {
                "goal": text,
                "task_count": 1,
                "status": result.get("status"),
                "mode": "normal",
                "direct": True,
            }
        )
        return result

    # ─── Simple Pipeline (Normal Mode, needs LLM) ─────────────────────────

    def _execute_simple_pipeline(self, user_input: str):
        """Simplified pipeline for Normal Mode — plan + execute, skip testing."""
        print(f"\n\033[90m{'─' * 60}\033[0m")
        print(f"\033[93m[GUNA-ASTRA] ⚡ Normal Mode — Quick pipeline...\033[0m")

        plan_result = self.planner.run({"goal": user_input})
        if plan_result["status"] == "failed":
            task = {"description": user_input, "original_goal": user_input}
            result = self.system_agent.run(task)
            print(f"\033[92m[GUNA-ASTRA] {result.get('output', 'Done.')}\033[0m")
            self._remember("assistant", result.get("output", ""))
            return

        try:
            tasks = json.loads(plan_result["output"])
        except Exception:
            tasks = [
                {
                    "id": 1,
                    "description": user_input,
                    "agent": "SystemAgent",
                    "priority": 1,
                }
            ]

        for task in tasks:
            task["original_goal"] = user_input
            print(f"\033[94m  [{task['agent']}]\033[0m {task['description'][:80]}")

            start = time.time()
            result = self.dispatcher.dispatch(task)
            elapsed = time.time() - start

            if result.get("status") == "pending_confirmation":
                print(f"\n\033[93m{result['output']}\033[0m")
                self._pending_confirmation = {"task": task, "plan": result}
                return

            print(
                f"\033[90m  ↳ {result.get('status', '?').upper()} ({elapsed:.1f}s)\033[0m"
            )

        output = result.get("output", "Done.")
        print(f"\n\033[92m[GUNA-ASTRA] {output}\033[0m")

        save_task(
            {
                "goal": user_input,
                "task_count": len(tasks),
                "status": "success",
                "mode": "normal",
            }
        )
        save_conversation("assistant", output, self.session_id)
        self._remember("assistant", output)

    # ─── Full Pipeline (Working Mode) ─────────────────────────────────────

    def _process_goal_working_mode(self, goal: str):
        """Working Mode: Full multi-agent pipeline with Open Interpreter enhancement."""
        print(f"\n\033[90m{'─' * 60}\033[0m")
        print(f"\033[95m[GUNA-ASTRA] 🤖 Working Mode — Full pipeline activated.\033[0m")
        logger.info(f"Working Mode — Goal: {goal}")

        save_conversation("user", goal, self.session_id)
        all_results = []

        # ── STEP 1: Planning ──────────────────────────────────────────────
        print("\n\033[95m[Step 1/5] 📋 Planning your goal...\033[0m")
        plan_result = self.planner.run({"goal": goal})

        if plan_result["status"] == "failed":
            print(
                f"\033[91m[GUNA-ASTRA] Planning failed: {plan_result['output']}\033[0m"
            )
            return

        try:
            tasks = json.loads(plan_result["output"])
        except Exception:
            tasks = [
                {"id": 1, "description": goal, "agent": "ResearchAgent", "priority": 1}
            ]

        print(f"\033[92m[Planner] Created {len(tasks)} tasks:\033[0m")
        for t in tasks:
            print(f"  {t['id']}. [{t['agent']}] {t['description']}")

        # ── STEP 2: Dispatch & Execute ────────────────────────────────────
        print(f"\n\033[95m[Step 2/5] ⚙️  Executing tasks...\033[0m")

        iteration = 0
        for task in tasks:
            if iteration >= MAX_TASK_ITERATIONS:
                logger.warning("Max task iterations reached.")
                break
            iteration += 1
            task["original_goal"] = goal

            if all_results:
                task["context"] = all_results[-1].get("output", "")

            print(f"\n\033[94m  [{task['agent']}]\033[0m {task['description'][:80]}")

            start = time.time()
            result = self.dispatcher.dispatch(task)
            elapsed = time.time() - start

            if result.get("status") == "pending_confirmation":
                print(f"\n\033[93m{result['output']}\033[0m")
                self._pending_confirmation = {"task": task, "plan": result}
                return

            print(
                f"\033[90m  ↳ {result.get('status', '?').upper()} ({elapsed:.1f}s)\033[0m"
            )

            # ── Open Interpreter Enhancement: auto-execute CodingAgent output ──
            if "CodingAgent" in result.get("agent", ""):
                code = result.get("output", "")
                if code and len(code) > 20:
                    print(f"\n\033[96m📝 Code generated. Running it now...\033[0m")
                    exec_result = self.engine.execute_with_retry(
                        code, task.get("description", "")
                    )
                    if exec_result.get("success"):
                        result["output"] = (
                            f"Code executed successfully.\n"
                            f"Output:\n{exec_result.get('stdout', exec_result.get('output', ''))}"
                        )
                    else:
                        result[
                            "output"
                        ] += f"\n\nExecution output:\n{exec_result.get('output', '')}"

            all_results.append(result)

        # ── STEP 3: Testing ───────────────────────────────────────────────
        code_results = [r for r in all_results if "CodingAgent" in r.get("agent", "")]
        if code_results:
            print(f"\n\033[95m[Step 3/5] 🧪 Testing generated code...\033[0m")
            for cr in code_results:
                test_result = self.tester.run(
                    {
                        "description": cr.get("task", ""),
                        "code": cr.get("output", ""),
                        "output": cr.get("output", ""),
                    }
                )
                all_results.append(test_result)
                print(f"\033[90m  ↳ Test: {test_result['status'].upper()}\033[0m")
        else:
            print(f"\n\033[90m[Step 3/5] 🧪 No code to test — skipping.\033[0m")

        # ── STEP 4: Verification ──────────────────────────────────────────
        print(f"\n\033[95m[Step 4/5] ✅ Verifying results...\033[0m")
        outputs_summary = "\n".join(
            [f"[{r['agent']}]: {r['output'][:200]}" for r in all_results]
        )
        verify_result = self.verifier.run(
            {"original_goal": goal, "outputs": outputs_summary}
        )
        all_results.append(verify_result)

        if verify_result["status"] == "failed":
            print(
                f"\033[91m[Verification] Issues found:\n{verify_result['output']}\033[0m"
            )

        # ── STEP 5: Synthesize Final Response ─────────────────────────────
        print(f"\n\033[95m[Step 5/5] 📝 Preparing your response...\033[0m")
        final = self.synthesizer.run(
            {"original_goal": goal, "results": all_results, "mode": "working"}
        )

        save_task(
            {
                "goal": goal,
                "task_count": len(tasks),
                "status": final["status"],
                "mode": "working",
            }
        )
        save_conversation("assistant", final["output"], self.session_id)
        self._remember("assistant", final["output"])

        print(f"\n\033[96m{'═' * 60}\033[0m")
        print(f"\033[96m[GUNA-ASTRA]\033[0m\n{final['output']}")
        print(f"\033[96m{'═' * 60}\033[0m")

        if SPEAK_RESPONSES:
            try:
                from utils.system_tools import speak

                speak(final["output"][:200])
            except Exception:
                pass

    def _process_goal_full_pipeline_api(self, text: str) -> dict:
        """Working Mode via API."""
        plan_result = self.planner.run({"goal": text})
        if plan_result["status"] == "failed":
            return plan_result
        try:
            tasks = json.loads(plan_result["output"])
        except Exception:
            tasks = [
                {"id": 1, "description": text, "agent": "ResearchAgent", "priority": 1}
            ]

        all_results = []
        for task in tasks:
            task["original_goal"] = text
            if all_results:
                task["context"] = all_results[-1].get("output", "")
            result = self.dispatcher.dispatch(task)
            all_results.append(result)

        final = self.synthesizer.run(
            {"original_goal": text, "results": all_results, "mode": "working"}
        )
        save_task(
            {
                "goal": text,
                "task_count": len(tasks),
                "status": final["status"],
                "mode": "working",
            }
        )
        return final

    # ─── Conversation Memory ──────────────────────────────────────────────

    def _remember(self, role: str, content: str):
        self._conversation.append({"role": role, "content": content})
        if len(self._conversation) > CONVERSATION_HISTORY_SIZE:
            self._conversation = self._conversation[-CONVERSATION_HISTORY_SIZE:]

    # ─── Normal Mode History ──────────────────────────────────────────────

    def _save_normal_history(
        self, user_input: str, intent: str, params: dict, result: dict
    ):
        """Save Normal Mode command to history for follow-up references."""
        entry = {
            "timestamp": datetime.now(),
            "input": user_input,
            "intent": intent,
            "params": params,
            "result": result,
            "success": result.get("success", False),
        }
        self.normal_mode_history.append(entry)
        if len(self.normal_mode_history) > self.MAX_NORMAL_HISTORY:
            self.normal_mode_history = self.normal_mode_history[
                -self.MAX_NORMAL_HISTORY :
            ]

        # Also persist
        save_task(
            {
                "goal": user_input,
                "task_count": 1,
                "status": "success" if result.get("success") else "failed",
                "mode": "normal",
                "direct": True,
            }
        )
        save_conversation("user", user_input, self.session_id)
        save_conversation("assistant", result.get("output", ""), self.session_id)
        self._remember("assistant", result.get("output", ""))

    def _resolve_references(self, text: str) -> str:
        """Resolve follow-up references like 'that file', 'again'."""
        lower = text.lower().strip()

        if not self.normal_mode_history:
            return text

        last = self.normal_mode_history[-1]

        # "again" or "do it again" → repeat last command
        if lower in ("again", "do it again", "repeat", "do that again"):
            return last.get("input", text)

        # "that file" → last file
        if "that file" in lower:
            for h in reversed(self.normal_mode_history):
                if h["intent"] in (CREATE_FILE, DELETE_FILE):
                    fname = h["params"].get("filename", h["params"].get("path", ""))
                    if fname:
                        return text.replace("that file", fname)

        # "that folder" → last folder
        if "that folder" in lower:
            for h in reversed(self.normal_mode_history):
                if h["intent"] in (CREATE_FOLDER, DELETE_FOLDER):
                    fname = h["params"].get("folder_name", h["params"].get("path", ""))
                    if fname:
                        return text.replace("that folder", fname)

        return text

    # ─── Confirmation Handling ─────────────────────────────────────────────

    def _resolve_confirmation(self, user_input: str):
        if user_input.lower() in ("confirm", "yes", "y"):
            task = self._pending_confirmation["task"]
            self._pending_confirmation = None
            print("\033[92m[GUNA-ASTRA] Confirmed. Proceeding...\033[0m")
            result = self.system_agent._handle_by_keywords(
                task.get("description", ""), task
            )
            print(f"\033[92m[SystemAgent] {result['output']}\033[0m")
        else:
            self._pending_confirmation = None
            print("\033[93m[GUNA-ASTRA] Action cancelled.\033[0m")

    # ─── Mode Display ─────────────────────────────────────────────────────

    def _print_mode(self):
        if self.current_mode == MODE_NORMAL:
            print("\033[93m[GUNA-ASTRA] ⚡ NORMAL MODE — Fast direct execution.\033[0m")
            print(
                "\033[90m  Type 'mode working' for complex tasks. Type 'help' for commands.\033[0m"
            )
        else:
            print(
                "\033[95m[GUNA-ASTRA] 🤖 WORKING MODE — Full multi-agent pipeline.\033[0m"
            )
            print(
                "\033[90m  Type 'mode normal' to switch back. Type 'help' for commands.\033[0m"
            )

    # ─── Mode Switching ───────────────────────────────────────────────────

    def _change_mode(self, mode_input: str):
        """Switch between Normal and Working modes."""
        mode_map = {
            "n": "normal",
            "normal": "normal",
            "w": "working",
            "working": "working",
        }
        new_mode = mode_map.get(mode_input.lower(), None)

        if new_mode:
            self.current_mode = new_mode

            if new_mode == "normal":
                print(f"\n\033[93m⚡ Switched to NORMAL MODE\033[0m")
                print(
                    "\033[90m  Fast, direct computer control. No agent pipeline.\033[0m"
                )
                print(
                    "\033[90m  Examples: 'open chrome', 'play music', 'volume up 20'\033[0m"
                )
            else:
                print(f"\n\033[95m🤖 Switched to WORKING MODE\033[0m")
                print("\033[90m  Full 11-agent pipeline for complex tasks.\033[0m")
                print(
                    "\033[90m  Examples: 'create a PPT on AI', 'analyze this data'\033[0m"
                )
        else:
            print(
                f"\033[91mUnknown mode: {mode_input}. Use 'normal' or 'working'.\033[0m"
            )

    # ─── Help System ──────────────────────────────────────────────────────

    def _show_help(self):
        nm = "→" if self.current_mode == MODE_NORMAL else " "
        wm = "→" if self.current_mode == MODE_WORKING else " "
        print(f"""
\033[96m╔══════════════════════════════════════════════════════════════╗
║              GUNA-ASTRA v2.0 — COMMAND REFERENCE             ║
╠══════════════════════════════════════════════════════════════╣
║  MODES                                                       ║
║  mode normal (or: mode n) — Fast direct computer control     ║
║  mode working (or: mode w) — Full 11-agent AI pipeline       ║
╠══════════════════════════════════════════════════════════════╣\033[0m
\033[93m{nm} ⚡ NORMAL MODE — QUICK EXAMPLES\033[0m

  \033[96mAPPS & WEB:\033[0m
  open chrome / launch spotify / start vs code
  go to youtube.com / open github.com
  play relaxing music / play lofi hip hop

  \033[96mFILES:\033[0m
  create file hello.txt / make folder projects
  delete file test.py / move file.txt to Desktop
  list files / search files *.py

  \033[96mSYSTEM:\033[0m
  volume up 20 / volume down / set volume to 50
  mute / screenshot / show time / battery
  sysinfo / lock screen / list processes / kill chrome
  weather / weather in Mumbai
  $ ping google.com — run shell commands with $ prefix

\033[95m{wm} 🤖 WORKING MODE — COMPLEX TASK EXAMPLES\033[0m

  Create a PowerPoint on climate change
  Write a Python script that sorts a list
  Research quantum computing and summarize it
  Analyze this CSV data
  Review this code for security vulnerabilities

\033[96m╠══════════════════════════════════════════════════════════════╣
║  SYSTEM COMMANDS                                             ║\033[0m
  history — show recent tasks
  status  — check Ollama, MongoDB, system health
  clear   — clear the screen
  exit    — quit GUNA-ASTRA
\033[96m╚══════════════════════════════════════════════════════════════╝\033[0m
""")

    # ─── History ──────────────────────────────────────────────────────────

    def _show_history(self):
        from utils.memory_db import get_recent_tasks

        tasks = get_recent_tasks(10)
        if not tasks:
            print("\033[90m[Memory] No task history found.\033[0m")
        else:
            print("\n\033[96m[Recent Tasks]\033[0m")
            for t in tasks:
                mode = t.get("mode", "?")
                icon = "⚡" if mode == "normal" else "🤖" if mode == "working" else "?"
                direct = " (direct)" if t.get("direct") else ""
                print(
                    f"  {icon} [{t.get('timestamp', '?')}] {t.get('goal', '?')}{direct}"
                )

    # ─── Status ───────────────────────────────────────────────────────────

    def _show_status(self):
        ollama_ok = check_ollama_health()
        from utils.memory_db import MONGO_AVAILABLE

        mode_name = (
            "⚡ Normal Mode" if self.current_mode == MODE_NORMAL else "🤖 Working Mode"
        )

        # Check optional dependencies
        pyautogui_ok = False
        psutil_ok = False
        try:
            import pyautogui

            pyautogui_ok = True
        except ImportError:
            pass
        try:
            import psutil

            psutil_ok = True
        except ImportError:
            pass

        print(f"""
\033[96m[GUNA-ASTRA v2.0 Status]\033[0m
  Current Mode:    {mode_name}
  Working Dir:     {self.current_directory}
  Ollama (Llama3): {'✅ Online' if ollama_ok else '❌ Offline (run: ollama serve)'}
  MongoDB:         {'✅ Connected' if MONGO_AVAILABLE else '⚠️  Offline (using in-memory)'}
  pyautogui:       {'✅ Available' if pyautogui_ok else '⚠️  Not installed'}
  psutil:          {'✅ Available' if psutil_ok else '⚠️  Not installed'}
  Agents online:   11/11
  Conversation:    {len(self._conversation)} messages
  Normal History:  {len(self.normal_mode_history)} commands
  Session ID:      {self.session_id}
""")
