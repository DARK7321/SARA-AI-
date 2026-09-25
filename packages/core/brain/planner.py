"""DAG Planner for OmniBrain.

Decomposes user intents into Directed Acyclic Graphs (DAGs) of executable task steps.
"""
from typing import Any, Dict, List, Optional
from uuid import UUID, uuid4
from pydantic import BaseModel, Field

from packages.connectors._sdk.contract import SideEffectType
from packages.core.brain.classifier import TaskClassification
from packages.core.db.models import Task, TaskStep


class StepPlan(BaseModel):
    step_key: str
    tool_id: str
    capability: str
    inputs: Dict[str, Any] = Field(default_factory=dict)
    depends_on: List[str] = Field(default_factory=list)
    side_effect: SideEffectType = SideEffectType.READ


class DAGPlan(BaseModel):
    task_path: str
    goal: str
    steps: List[StepPlan]


CAPABILITY_CONNECTOR_MAP = {
    "gmail.read": ("connector-gmail", SideEffectType.READ),
    "gmail.search": ("connector-gmail", SideEffectType.READ),
    "gmail.draft": ("connector-gmail", SideEffectType.WRITE),
    "gmail.send": ("connector-gmail", SideEffectType.EXTERNAL_SEND),
    "gmail.label": ("connector-gmail", SideEffectType.WRITE),
    "drive.list": ("connector-gdrive", SideEffectType.READ),
    "drive.read": ("connector-gdrive", SideEffectType.READ),
    "drive.create": ("connector-gdrive", SideEffectType.WRITE),
    "drive.share": ("connector-gdrive", SideEffectType.WRITE),
    "calendar.list_events": ("connector-gcal", SideEffectType.READ),
    "calendar.create_event": ("connector-gcal", SideEffectType.WRITE),
    "sheets.read_rows": ("connector-gsheets", SideEffectType.READ),
    "sheets.append_rows": ("connector-gsheets", SideEffectType.WRITE),
    "sheets.update_cell": ("connector-gsheets", SideEffectType.WRITE),
    "web.search": ("connector-websearch", SideEffectType.READ),
    "host.open_app": ("connector-host-agent", SideEffectType.WRITE),
    "host.type_text": ("connector-host-agent", SideEffectType.WRITE),
    "host.mouse_control": ("connector-host-agent", SideEffectType.WRITE),
    "host.keyboard_control": ("connector-host-agent", SideEffectType.WRITE),
    "host.file_op": ("connector-host-agent", SideEffectType.DESTRUCTIVE),
    "host.run_script": ("connector-host-agent", SideEffectType.EXTERNAL_SEND),
    "host.read_screen": ("connector-host-agent", SideEffectType.READ),
}


class DAGPlanner:
    """Generates execution plans with dependency graphs and side-effect tags."""

    def plan(
        self,
        classification: TaskClassification,
        initial_inputs: Optional[Dict[str, Any]] = None,
    ) -> DAGPlan:
        """Create a dependency DAG based on classified capabilities."""
        steps: List[StepPlan] = []
        inputs = initial_inputs or {}

        previous_step_key: Optional[str] = None

        for idx, cap in enumerate(classification.required_capabilities):
            step_key = f"step_{idx + 1}_{cap.replace('.', '_')}"
            tool_id, side_effect = CAPABILITY_CONNECTOR_MAP.get(
                cap, ("connector-fake", SideEffectType.WRITE)
            )

            step_inputs = dict(inputs)
            if cap == "gmail.search":
                q = classification.entities.get("query", "")
                if not q:
                    raw_goal = (classification.goal or "").lower()
                    conversational_words = {
                        "check", "read", "email", "gmail", "mail", "last", "lasrt", "latest", "inbox",
                        "karo", "meri", "mera", "mujhe", "muje", "dekho", "batao", "konsi", "kon",
                        "aai", "thi", "hai", "kya", "shuru", "please", "can", "you"
                    }
                    meaningful = [w for w in raw_goal.split() if w not in conversational_words]
                    q = " ".join(meaningful) if len(meaningful) >= 2 else ""
                step_inputs["query"] = q
                step_inputs.setdefault("max_results", 5)
            elif cap == "web.search":
                q = classification.entities.get("query", "")
                if not q:
                    raw_cmd = (inputs.get("raw_command") or "").strip()
                    raw_goal = (classification.goal or "").strip()
                    target = raw_cmd or raw_goal
                    conversational_words = {
                        "hey", "hi", "sara", "s.a.r.a.", "muje", "mujhe", "batao", "bataiye",
                        "kya", "hai", "please", "can", "you", "tell", "me", "karo", "do",
                        "search", "dhundo", "khojo"
                    }
                    meaningful = [w for w in target.split() if w.lower() not in conversational_words]
                    q = " ".join(meaningful) if meaningful else target
                step_inputs["query"] = q or "latest news headlines"
                step_inputs.setdefault("max_results", 4)
            elif cap == "calendar.list_events":
                step_inputs.setdefault("max_results", 5)
            elif cap == "sheets.read_rows":
                step_inputs.setdefault("spreadsheet_id", "sheet_101")
                step_inputs.setdefault("range", "Sheet1!A1:C10")
            elif cap == "drive.list":
                step_inputs.setdefault("query", classification.goal)
            elif cap == "host.open_app":
                # Try entities first, then scan goal text for known app names
                app = classification.entities.get("app")
                if not app:
                    goal_lower = classification.goal.lower()
                    for known in ["calculator", "calc", "notepad", "chrome", "edge", "paint", "explorer", "excel", "word"]:
                        if known in goal_lower:
                            app = "calc" if known in ("calculator", "calc") else known
                            break
                step_inputs["app"] = app or "notepad"
            elif cap == "host.mouse_control":
                step_inputs.setdefault("action", classification.entities.get("action", "move"))
                for k in ["x", "y", "scroll_amount"]:
                    if k in classification.entities: step_inputs[k] = classification.entities[k]
            elif cap == "host.type_text":
                step_inputs["app"] = classification.entities.get("app") or step_inputs.get("app", "notepad")
                step_inputs["text"] = classification.entities.get("text") or step_inputs.get("text") or classification.goal
                step_inputs["press_enter"] = False
            elif cap == "host.keyboard_control":
                action = classification.entities.get("action") or step_inputs.get("action", "press")
                keys = classification.entities.get("keys") or step_inputs.get("keys")
                goal_lower = classification.goal.lower()
                if not keys:
                    if any(w in goal_lower for w in ["minimize", "minimise", "desktop"]):
                        action = "hotkey"
                        keys = ["win", "m"]
                    elif any(w in goal_lower for w in ["close window", "band karo"]):
                        action = "hotkey"
                        keys = ["alt", "f4"]
                    elif any(w in goal_lower for w in ["close tab", "close tabs"]):
                        action = "hotkey"
                        keys = ["ctrl", "shift", "w"]
                step_inputs["action"] = action
                if keys:
                    step_inputs["keys"] = keys
                if "text" in classification.entities:
                    step_inputs["text"] = classification.entities["text"]

            step_plan = StepPlan(
                step_key=step_key,
                tool_id=tool_id,
                capability=cap,
                inputs=step_inputs,
                depends_on=[previous_step_key] if previous_step_key else [],
                side_effect=side_effect,
            )
            steps.append(step_plan)
            previous_step_key = step_key

        # If no specific capability identified, create fallback general action step
        if not steps:
            steps.append(
                StepPlan(
                    step_key="step_1_general_action",
                    tool_id="connector-fake",
                    capability="fake.read",
                    inputs={"goal": classification.goal, **inputs},
                    depends_on=[],
                    side_effect=SideEffectType.READ,
                )
            )

        return DAGPlan(
            task_path=classification.path,
            goal=classification.goal,
            steps=steps,
        )



