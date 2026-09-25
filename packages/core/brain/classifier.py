"""Intent Engine and Task Classifier for OmniBrain.

Classifies incoming user messages into FAST, SMART, or DEEP execution paths,
and identifies whether a command requires tool execution or conversational response.
"""
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

from packages.core.router.model_router import ModelRouter


class TaskClassification(BaseModel):
    is_conversational: bool = Field(
        description="True if greeting, query, or general chit-chat; False if actionable command"
    )
    path: str = Field(
        default="FAST",
        description="FAST (single query/instant), SMART (multi-tool DAG), or DEEP (complex planning)"
    )
    goal: str = Field(description="Normalized concise summary of user intent")
    entities: Dict[str, Any] = Field(
        default_factory=dict,
        description="Extracted entities. For host.mouse_control include 'action' (click, move, drag, scroll) and 'x', 'y'. For host.keyboard_control include 'action' (press, hotkey, write), 'keys' (list of strings like ['alt', 'f4']) or 'text'."
    )
    required_capabilities: List[str] = Field(
        default_factory=list,
        description="List of required tool actions like gmail.search, calendar.list_events, sheets.read_rows"
    )
    estimated_risk: str = Field(
        default="LOW",
        description="LOW (read only), MEDIUM (draft/create), HIGH (send/delete/share)"
    )


CLASSIFIER_SYSTEM_PROMPT = """You are the Intent and Task Classifier for OmniBrain, an AI Operating System.
Analyze user messages and classify them into:
1. is_conversational: True if the user is saying hello, asking who you are, asking questions, seeking news, facts, research, advice, or explanations (e.g. "aaj ki latest news batao", "what is quantum computing", "how are you"). SARA handles questions and news with real-time research directly in conversation.
ONLY set is_conversational=False when the user wants to execute a concrete action or change something on tools/host (e.g. send email, book meeting, edit spreadsheet, open an app, control mouse/keyboard).
2. path:
   - FAST: simple questions, information lookup, or single read action (latency <1s).
   - SMART: 2-4 coordinated tool steps (e.g. read email, summarize, save to drive or sheet).
   - DEEP: complex multi-stage tasks requiring subagents and extensive reasoning.
3. required_capabilities: choose from [gmail.read, gmail.search, gmail.draft, gmail.send, drive.list, drive.read, drive.create, drive.share, calendar.list_events, calendar.create_event, sheets.read_rows, sheets.append_rows, sheets.update_cell, web.search, host.open_app, host.mouse_control, host.keyboard_control, host.file_op, host.run_script, host.read_screen].
4. estimated_risk: LOW for reading/searching, MEDIUM for creating drafts/typing, HIGH for sending emails, running scripts, or deleting items.

CRITICAL EXAMPLES:
- "HEY SARA MUJE AAJ KI LATEST NEWS BATAO" -> is_conversational=True, path="FAST", goal="Get today's latest news", required_capabilities=[]
- "aaj ki breaking news kya hai" -> is_conversational=True, path="FAST", goal="Get breaking news", required_capabilities=[]
- "ISRO ka mission kya hai" -> is_conversational=True, path="FAST", goal="Explain ISRO upcoming missions", required_capabilities=[]
- "Google par search karke batao" -> is_conversational=True, path="FAST", goal="Search internet for user question", required_capabilities=[]
- "minimize all windows" -> is_conversational=False, required_capabilities=["host.keyboard_control"], entities={"action": "hotkey", "keys": ["win", "m"]}
- "close window" -> is_conversational=False, required_capabilities=["host.keyboard_control"], entities={"action": "hotkey", "keys": ["alt", "f4"]}
- "open calculator" -> is_conversational=False, required_capabilities=["host.open_app"], entities={"app": "calc"}
- "open notepad" -> is_conversational=False, required_capabilities=["host.open_app"], entities={"app": "notepad"}
- "type in notepad: Hello" -> is_conversational=False, path="SMART", required_capabilities=["host.open_app", "host.type_text"], entities={"app": "notepad", "text": "Hello"}
"""


class IntentEngine:
    """Classifies user intents and decides execution paths using LLM."""

    def __init__(self, model_router: Optional[ModelRouter] = None):
        self.router = model_router or ModelRouter()

    async def classify(
        self,
        user_message: str,
        system_context_snippet: str = "",
        provider_name: str = "gemini",
    ) -> TaskClassification:
        """Classify message intent and extract parameters."""
        """Classify message intent and extract parameters with sub-millisecond fast-path."""
        lower_msg = user_message.lower().strip()
        hindi_chat_phrases = [
            "namaste", "namaskar", "kaise", "kaisa", "kaisi", "haal", "hal",
            "kaun ho", "kaun hai", "who are you", "kya kar", "kya haal",
            "theek", "shukriya", "dhanyawad", "batao", "bolo", "kaho", "shuru",
            "slow", "kyu", "q hai", "kyon", "tez", "fast", "aawaz", "voice",
            "नमस्ते", "नमस्कार", "कैसी", "कैसे", "कौन", "हाल", "क्या", "हाय", "हेलो", "शुक्रिया", "धन्यवाद"
        ]
        is_chat = any(w in lower_msg for w in ["hello", "hi", "hey", "who are you", "what can you do", "help"] + hindi_chat_phrases)

        req_caps = []
        if any(w in lower_msg for w in ["mail", "inbox", "email", "ईमेल", "मेल"]):
            req_caps.append("gmail.search")
        if any(w in lower_msg for w in ["meeting", "calendar", "schedule", "कैलेंडर", "मीटिंग"]):
            req_caps.append("calendar.list_events")
        if any(w in lower_msg for w in ["sheet", "spreadsheet", "शीट"]):
            req_caps.append("sheets.read_rows")
        if any(w in lower_msg for w in ["drive", "file", "doc", "ड्राइव", "फाइल", "folder"]):
            req_caps.append("drive.list")

        # Action verbs indicating tool execution intent
        action_intent_words = [
            "send", "draft", "create", "delete", "remove", "schedule", "update", "append",
            "search inbox", "check mail", "read mail", "check calendar", "bhejo", "banao",
            "likho", "karo", "hatao", "dhundo", "open", "type", "run", "kholo", "chalao", "start", "minimize", "close", "band"
        ]
        has_action_intent = bool(req_caps) or any(w in lower_msg for w in action_intent_words)

        prompt = (
            f"{system_context_snippet}\n"
            f"User Message: \"{user_message}\"\n\n"
            f"Classify this message into a valid TaskClassification JSON object."
        )

        try:
            response = await self.router.complete(
                prompt=prompt,
                path="FAST",
                system_prompt=CLASSIFIER_SYSTEM_PROMPT,
                schema=TaskClassification,
                provider_name=provider_name,
            )
            if response.structured_data:
                return TaskClassification(**response.structured_data)
        except Exception:
            pass

        # Robust deterministic fallback if model is offline/unreachable
        lower_msg = user_message.lower()
        hindi_chat_phrases = [
            "namaste", "namaskar", "kaise", "kaisa", "kaisi", "haal", "hal",
            "kaun ho", "kaun hai", "who are you", "kya kar", "kya haal",
            "theek", "shukriya", "dhanyawad", "batao", "bolo", "kaho", "shuru",
            "नमस्ते", "नमस्कार", "कैसी", "कैसे", "कौन", "हाल", "क्या", "हाय", "हेलो", "शुक्रिया", "धन्यवाद"
        ]
        is_chat = any(w in lower_msg for w in ["hello", "hi", "hey", "who are you", "what can you do", "help"] + hindi_chat_phrases)
        
        req_caps = []
        desktop_apps = {
            "notepad": "notepad",
            "calculator": "calculator",
            "calc": "calculator",
            "paint": "paint",
            "explorer": "explorer",
        }
        requested_app = next((name for name in desktop_apps if name in lower_msg), None)
        if any(w in lower_msg for w in ["mail", "inbox", "email", "ईमेल", "मेल"]):
            req_caps.append("gmail.search")
        if any(w in lower_msg for w in ["meeting", "calendar", "schedule", "कैलेंडर", "मीटिंग"]):
            req_caps.append("calendar.list_events")
        if any(w in lower_msg for w in ["sheet", "spreadsheet", "शीट"]):
            req_caps.append("sheets.read_rows")
        if any(w in lower_msg for w in ["drive", "file", "doc", "ड्राइव", "फाइल"]):
            req_caps.append("drive.list")
        if requested_app or any(w in lower_msg for w in ["excel", "word", "chrome", "app", "window"]):
            req_caps.append("host.open_app")
        if any(w in lower_msg for w in ["type", "write", "likho", "टाइप", "लिखो"]):
            req_caps.extend(["host.type_text", "host.read_screen"])

        # Action verbs indicating tool execution intent
        action_intent_words = [
            "send", "draft", "create", "delete", "remove", "schedule", "update", "append",
            "search inbox", "check mail", "read mail", "check calendar", "bhejo", "banao",
            "likho", "karo", "hatao", "dhundo", "open", "type", "write", "run", "minimize", "close", "band", "start"
        ]
        question_words = [
            "?", "kya", "kaise", "kyun", "kyu", "kaisa", "kaisi", "who", "what",
            "why", "how", "explain", "batao", "samjhao", "tell me", "define",
            "meaning", "fayde", "nuksan", "think", "news", "khabar", "taaza",
            "latest", "update", "research"
        ]
        is_question = any(qw in lower_msg for qw in question_words)
        has_action_intent = any(w in lower_msg for w in action_intent_words)
        
        # Any question or statement without explicit action verbs is conversational (deep thinking)
        is_conversational = (not req_caps) and (is_chat or is_question or (not has_action_intent))

        entities = {"query": user_message}
        if requested_app:
            entities["app"] = requested_app

        return TaskClassification(
            is_conversational=is_conversational,
            path="SMART" if len(req_caps) > 1 else "FAST",
            goal=user_message[:100],
            entities=entities,
            required_capabilities=[] if is_conversational else req_caps,
            estimated_risk="HIGH" if any(w in lower_msg for w in ["send", "delete"]) else "LOW",
        )

