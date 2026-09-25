"""User-facing personal assistant utilities for desktop tasks.

This layer intentionally keeps actions narrow and explicit: the user must approve
sensitive actions such as opening apps, typing text, or writing files outside the
safe workspace. It is designed to sit atop OmniBrain's host-agent automation and
helps turn natural-language requests into safe operating instructions.
"""

from __future__ import annotations

import os
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, Optional


@dataclass
class PersonalCommand:
    """Structured representation of a command the assistant may execute."""

    verb: str
    target: str = ""
    text: str = ""
    path: Optional[str] = None
    requires_approval: bool = True
    risk: str = "low"
    metadata: Dict[str, Any] = field(default_factory=dict)


class PersonalAssistant:
    """Small rule-based assistant for personal desktop command routing.

    It intentionally favors predictable, explicit command parsing over broad
    unrestricted automation. The user can allow or deny sensitive actions.
    """

    DEFAULT_ALLOWED_ROOTS = (
        Path.home() / "Documents",
        Path.home() / "Desktop",
        Path.home() / "Downloads",
    )
    ALLOWED_APPS = {
        "word": "word",
        "microsoft word": "word",
        "notepad": "notepad",
        "text editor": "notepad",
        "explorer": "explorer",
        "file explorer": "explorer",
        "chrome": "chrome",
        "google chrome": "chrome",
        "edge": "edge",
        "microsoft edge": "edge",
        "calculator": "calculator",
        "paint": "paint",
        "terminal": "terminal",
        "cmd": "terminal",
    }

    def __init__(self, permission_policy: str = "ask") -> None:
        self.permission_policy = permission_policy.lower()
        self.allowed_roots = self._resolve_allowed_roots()

    def _resolve_allowed_roots(self) -> tuple[Path, ...]:
        raw_value = os.environ.get(
            "OMNIBRAIN_HOST_ALLOWED_ROOTS",
            "~/Desktop;~/Documents;~/Downloads",
        )
        roots = []
        for entry in raw_value.split(";"):
            entry = entry.strip()
            if not entry:
                continue
            roots.append(Path(entry).expanduser().resolve())
        if not roots:
            roots = list(self.DEFAULT_ALLOWED_ROOTS)
        return tuple(dict.fromkeys(roots))

    def _safe_path(self, candidate: str) -> Path:
        path = Path(candidate).expanduser().resolve()
        if not any(path == root or root in path.parents for root in self.allowed_roots):
            raise ValueError(f"Path is outside the allowed workspace: {candidate}")
        return path

    def _looks_like_question(self, text: str) -> bool:
        lowered = text.lower().strip()
        return "?" in lowered or any(
            phrase in lowered
            for phrase in (
                "what is",
                "who is",
                "why",
                "how can",
                "can you",
                "please explain",
                "what do you think",
            )
        )

    def _answer_general_question(self, text: str) -> str:
        lowered = text.lower()
        if "ai" in lowered:
            return (
                "AI is software that can understand instructions, reason through tasks, and help you do work "
                "more quickly. I can help you open apps, draft documents, manage files, and keep actions safe."
            )
        if "word" in lowered or "essay" in lowered:
            return "I can help draft and organize a document. For example, try: 'Open Word' or 'Write an essay about AI into My Document'."
        return (
            "I can help with desktop tasks, writing, file work, and quick planning. Try commands like 'Open Notepad', "
            "'Write an essay about AI into My Document', or 'List my documents'."
        )

    def parse(self, user_text: str) -> PersonalCommand:
        text = (user_text or "").strip()
        lowered = text.lower()

        if not text:
            raise ValueError("Please provide a command for your assistant.")

        if self._looks_like_question(text):
            return PersonalCommand(
                verb="answer",
                target="conversation",
                text=self._answer_general_question(text),
                requires_approval=False,
                risk="low",
            )

        if any(word in lowered for word in ("open", "launch", "start", "run", "kholo", "chalao", "start kar")):
            app_name = self._extract_app_name(text)
            return PersonalCommand(
                verb="open_app",
                target=app_name or "default-app",
                requires_approval=self.permission_policy in {"ask", "confirm"},
                risk="medium",
                metadata={"app": app_name or "default-app"},
            )

        if any(word in lowered for word in ("write", "type", "compose", "draft", "likho", "type karo", "likhna")):
            if re.search(r"(?i)([A-Za-z]:\\|[A-Za-z]:/|\\\\|/Windows/|/Program Files/|/System32/)", text):
                raise ValueError("Path is outside the allowed workspace. Please pick a file inside Documents, Desktop, or Downloads.")

            target = self._extract_filename(text) or "document.txt"
            content = text
            content = re.sub(r"^(write|type|compose|draft|likho|likhna)\s+", "", content, flags=re.I)
            content = re.sub(
                r"\s+(?:into|in|to)\s+(?:my\s+)?(?:document|doc|note|file|essay|report)(?:\s+.*)?$",
                "",
                content,
                flags=re.I,
            )
            content = re.sub(r"\s+(?:in|into|to)\s+['\"]?[A-Za-z0-9_ .-]+['\"]?$", "", content, flags=re.I)
            if not content or content.strip() == "":
                content = "Draft content"
            safe_target = self._safe_path(Path.home() / "Documents" / target)
            return PersonalCommand(
                verb="write_text",
                target=target,
                text=content.strip(),
                path=str(safe_target),
                requires_approval=self.permission_policy in {"ask", "confirm"},
                risk="medium",
            )

        if any(word in lowered for word in ("read", "open file", "show", "padh", "read file", "dekho", "read karo")):
            target = self._extract_filename(text) or "document.txt"
            safe_target = self._safe_path(Path.home() / "Documents" / target)
            return PersonalCommand(
                verb="read_file",
                target=target,
                path=str(safe_target),
                requires_approval=self.permission_policy in {"ask", "confirm"},
                risk="low",
            )

        if any(word in lowered for word in ("list", "show files", "directory", "folder", "list my docs", "my documents", "files")):
            folder = "Documents"
            safe_folder = self._safe_path(Path.home() / folder)
            return PersonalCommand(
                verb="list_folder",
                target=folder,
                path=str(safe_folder),
                requires_approval=False,
                risk="low",
            )

        raise ValueError(f"I don't yet understand this command: {text}")

    def _extract_app_name(self, text: str) -> str:
        matches = re.findall(r"(?:open|launch|start|run|kholo|chalao)\s+(?:the\s+)?([a-zA-Z0-9_ .-]+)", text, flags=re.I)
        if not matches:
            return "notepad"
        app = matches[0].strip().lower()
        for key, canonical in self.ALLOWED_APPS.items():
            if app == key or app.startswith(key):
                return canonical
        if "word" in app:
            return "word"
        if "notepad" in app:
            return "notepad"
        return app

    def _extract_filename(self, text: str) -> str:
        lowered = text.lower()
        if "my document" in lowered or "my doc" in lowered:
            return "My Document.txt"
        if "my notes" in lowered:
            return "My Notes.txt"

        match = re.search(r"(?:file|document|note|essay|report|memo)\s+(?:named\s+)?['\"]?([A-Za-z0-9_ .-]+)['\"]?", text, flags=re.I)
        if match:
            filename = match.group(1).strip()
            if filename and not filename.endswith((".txt", ".md", ".docx")):
                return filename + ".txt"
            return filename

        if "into" in lowered or "to" in lowered:
            for label in ("document", "note", "essay", "report"):
                idx = lowered.rfind(label)
                if idx != -1:
                    return f"{label.title()} Draft.txt"
        return "document.txt"

    def run(self, user_text: str) -> Dict[str, Any]:
        command = self.parse(user_text)

        if command.verb == "answer":
            return {
                "status": "ready",
                "command": "answer",
                "target": command.target,
                "text": command.text,
                "risk": command.risk,
            }

        if self.permission_policy == "deny":
            return {
                "status": "denied",
                "command": command.verb,
                "target": command.target,
                "message": "This action was denied by policy.",
            }

        if command.requires_approval and self.permission_policy in {"ask", "confirm"}:
            return {
                "status": "approval_required",
                "command": command.verb,
                "target": command.target,
                "message": "I need your approval before I perform this action.",
            }

        return {
            "status": "ready",
            "command": command.verb,
            "target": command.target,
            "path": command.path,
            "text": command.text,
            "risk": command.risk,
            "metadata": command.metadata,
        }
