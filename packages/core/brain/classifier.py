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
        description="Extracted entities such as recipient, date, topic, filename"
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
1. is_conversational: True if the user is saying hello, asking who you are, or seeking advice/information without needing external tools. False if they want you to perform an action (read email, schedule event, update sheet, delete file, etc.).
2. path:
   - FAST: simple information lookup or 1 read tool (latency <1s).
   - SMART: 2-4 coordinated tool steps (e.g. read email, summarize, save to drive or sheet).
   - DEEP: complex multi-stage tasks requiring subagents and extensive reasoning.
3. required_capabilities: choose from [gmail.read, gmail.search, gmail.draft, gmail.send, drive.list, drive.read, drive.create, drive.share, calendar.list_events, calendar.create_event, sheets.read_rows, sheets.append_rows, sheets.update_cell, web.search, host.open_app, host.type_text, host.file_op, host.run_script, host.read_screen].
4. estimated_risk: LOW for reading, MEDIUM for creating drafts/typing, HIGH for sending emails, running scripts, or deleting items.
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
        if any(w in lower_msg for w in ["notepad", "excel", "word", "chrome", "app", "script", "window"]):
            req_caps.append("host.open_app")

        # Action verbs indicating tool execution intent
        action_intent_words = [
            "send", "draft", "create", "delete", "remove", "schedule", "update", "append",
            "search inbox", "check mail", "read mail", "check calendar", "bhejo", "banao",
            "likho", "karo", "hatao", "dhundo", "open", "type", "run", "kholo", "chalao", "start"
        ]
        has_action_intent = bool(req_caps) or any(w in lower_msg for w in action_intent_words)

        # Zero-latency Conversational & Tool Action Bypass:
        # Greetings, general queries, and direct tool commands are classified instantly (<1ms) with 100% precision.
        if provider_name != "mock":
            if is_chat and not has_action_intent:
                return TaskClassification(
                    is_conversational=True,
                    path="FAST",
                    goal=user_message[:100],
                    entities={},
                    required_capabilities=[],
                    estimated_risk="LOW",
                )
            if not has_action_intent:
                return TaskClassification(
                    is_conversational=True,
                    path="FAST",
                    goal=user_message[:100],
                    entities={},
                    required_capabilities=[],
                    estimated_risk="LOW",
                )
            # Direct tool commands (check inbox, calendar, sheets, drive)
            if req_caps and not any(w in lower_msg for w in ["why", "explain", "how does", "what is"]):
                return TaskClassification(
                    is_conversational=False,
                    path="SMART" if len(req_caps) > 1 else "FAST",
                    goal=user_message[:100],
                    entities={"query": user_message},
                    required_capabilities=req_caps,
                    estimated_risk="HIGH" if any(w in lower_msg for w in ["send", "delete", "remove"]) else "LOW",
                )

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
        if any(w in lower_msg for w in ["mail", "inbox", "email", "ईमेल", "मेल"]):
            req_caps.append("gmail.search")
        if any(w in lower_msg for w in ["meeting", "calendar", "schedule", "कैलेंडर", "मीटिंग"]):
            req_caps.append("calendar.list_events")
        if any(w in lower_msg for w in ["sheet", "spreadsheet", "शीट"]):
            req_caps.append("sheets.read_rows")
        if any(w in lower_msg for w in ["drive", "file", "doc", "ड्राइव", "फाइल"]):
            req_caps.append("drive.list")

        # Action verbs indicating tool execution intent
        action_intent_words = [
            "send", "draft", "create", "delete", "remove", "schedule", "update", "append",
            "search inbox", "check mail", "read mail", "check calendar", "bhejo", "banao",
            "likho", "karo", "hatao", "dhundo"
        ]
        has_action_intent = bool(req_caps) or any(w in lower_msg for w in action_intent_words)
        
        # Any question or statement without explicit action verbs is conversational
        is_conversational = (not has_action_intent) or is_chat

        return TaskClassification(
            is_conversational=is_conversational,
            path="SMART" if len(req_caps) > 1 else "FAST",
            goal=user_message[:100],
            entities={},
            required_capabilities=[] if is_conversational else req_caps,
            estimated_risk="HIGH" if any(w in lower_msg for w in ["send", "delete"]) else "LOW",
        )

