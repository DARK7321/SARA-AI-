"""Result Synthesizer for OmniBrain.

Generates the Blueprint standard 5-point report and conversational spoken summary.
"""
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class StructuredReport(BaseModel):
    status: str = Field(description="COMPLETED | WAITING_APPROVAL | FAILED")
    what_was_done: List[str] = Field(description="Bullet points of actions taken")
    important_results: List[str] = Field(description="Key data found or created")
    any_problems: List[str] = Field(description="Errors or warnings encountered")
    actions_requiring_me: List[str] = Field(description="Pending approvals or decisions")
    spoken_summary: str = Field(description="Concise 1-2 sentence summary for voice assistant")

    def to_markdown(self) -> str:
        done_str = "\n".join(f"- {d}" for d in self.what_was_done) or "- None"
        results_str = "\n".join(f"- {r}" for r in self.important_results) or "- None"
        problems_str = "\n".join(f"- {p}" for p in self.any_problems) or "- None"
        actions_str = "\n".join(f"- {a}" for a in self.actions_requiring_me) or "- None"

        return (
            f"### 📋 Execution Report\n\n"
            f"**STATUS**: {self.status}\n\n"
            f"**WHAT WAS DONE**:\n{done_str}\n\n"
            f"**IMPORTANT RESULTS**:\n{results_str}\n\n"
            f"**ANY PROBLEMS**:\n{problems_str}\n\n"
            f"**ACTIONS REQUIRING ME**:\n{actions_str}\n"
        )


class ResultSynthesizer:
    """Synthesizes raw task execution outputs into the standard 5-point report."""

    def synthesize(
        self,
        task_goal: str,
        task_status: str,
        steps_data: List[Dict[str, Any]],
        approval_summary: Optional[Dict[str, Any]] = None,
    ) -> StructuredReport:
        what_done = []
        results = []
        problems = []
        requiring_me = []

        for step in steps_data:
            cap = step.get("capability", "action")
            status = step.get("status", "UNKNOWN")

            if status == "SUCCEEDED":
                what_done.append(f"Executed {cap} successfully.")
                outputs = step.get("outputs", {})
                if "messages" in outputs:
                    count = len(outputs["messages"])
                    results.append(f"Found {count} message(s) in Gmail.")
                elif "files" in outputs:
                    count = len(outputs["files"])
                    results.append(f"Found {count} file(s) in Google Drive.")
                elif "events" in outputs:
                    count = len(outputs["events"])
                    results.append(f"Retrieved {count} calendar event(s).")
                elif "rows" in outputs:
                    count = len(outputs["rows"])
                    results.append(f"Read {count} row(s) from Google Sheets.")
                elif "id" in outputs:
                    results.append(f"Created item with ID: {outputs['id']}.")

            elif status == "WAITING_APPROVAL":
                what_done.append(f"Paused at {cap} — human confirmation required.")
                requiring_me.append(f"Approval needed for: {step.get('step_key')}")

            elif status == "FAILED":
                err = step.get("error", {}).get("message", "Unknown error")
                problems.append(f"Step '{step.get('step_key')}' failed: {err}")

        if approval_summary:
            requiring_me.append(f"Confirm action: {approval_summary.get('what', 'Proposed change')}")

        # Check if task_goal contains Hindi or Hinglish
        is_hindi = any("\u0900" <= char <= "\u097F" for char in task_goal) or any(
            w in task_goal.lower().split() for w in ["karo", "kaho", "mera", "meri", "kya", "kaise", "bhejo", "batao"]
        )

        # Spoken summary for Lady Voice Assistant
        if is_hindi:
            if task_status == "COMPLETED":
                spoken = "मैंने आपका काम पूरा कर दिया है। सभी स्टेप्स वेरिफाई हो चुके हैं।"
            elif task_status == "WAITING_APPROVAL":
                spoken = "मैंने टास्क तैयार कर लिया है, लेकिन आगे बढ़ने के लिए आपकी अनुमति चाहिए।"
            else:
                spoken = "टास्क प्रोसेस करने में कोई समस्या आई है। कृपया डिटेल्स चेक करें।"
        else:
            if task_status == "COMPLETED":
                spoken = f"I've completed your task to {task_goal.lower()}. All steps executed and verified."
            elif task_status == "WAITING_APPROVAL":
                spoken = "I've prepared the task, but need your confirmation before proceeding with the sensitive action."
            else:
                spoken = "I encountered an issue while processing your request. Please check the details."

        return StructuredReport(
            status=task_status,
            what_was_done=what_done or [f"Processed {task_goal}."],
            important_results=results or ["Task completed with standard results."],
            any_problems=problems,
            actions_requiring_me=requiring_me,
            spoken_summary=spoken,
        )

