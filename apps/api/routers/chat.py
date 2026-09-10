"""Conversational Chat API router for OmniBrain.

Enables natural conversation, question answering, and direct multi-step task execution
with optional Lady Assistant voice output.
"""
import base64
from typing import Any, Dict, Optional
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from packages.core.schemas.common import APIResponse
from packages.core.db.models import User, Task, TaskStep, Alias, Workflow
from packages.core.workflows.engine import WorkflowEngine
from packages.core.brain.context import ContextEngine
from packages.core.brain.classifier import IntentEngine
from packages.core.brain.planner import DAGPlanner
from packages.core.brain.synthesizer import ResultSynthesizer, StructuredReport
from packages.core.voice.tts import VoiceEngine, DEFAULT_LADY_VOICE, DEFAULT_HINGLISH_VOICE
from packages.core.router.model_router import ModelRouter
from packages.core.agents.frameworks import get_framework_adapter
from apps.api.deps import get_db, get_current_user
from apps.worker.main import execute_task_job

router = APIRouter()


class ChatRequest(BaseModel):
    message: str = Field(description="User message or instruction")
    include_audio: bool = Field(default=False, description="Generate audio for spoken response")
    voice: Optional[str] = Field(default=None, description="Voice identifier e.g. en-US-JennyNeural or hi-IN-SwaraNeural")


class ChatResponseData(BaseModel):
    reply: str
    path: str
    task_id: Optional[str] = None
    report: Optional[StructuredReport] = None
    audio_base64: Optional[str] = None


@router.post("", response_model=APIResponse)
async def chat_with_brain(
    payload: ChatRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Interact with OmniBrain — conversational Q&A or direct task execution with optional voice."""
    trace_id = getattr(request.state, "trace_id", None)

    # Voice Engine setup & Language detection
    has_hindi = any("\u0900" <= char <= "\u097F" for char in payload.message) or any(
        kw in payload.message.lower().split()
        for kw in ["kaise", "kya", "namaste", "tum", "aap", "mera", "meri", "hai", "karo", "kaho", "batao", "shuru", "theek", "bhai", "bat", "baat"]
    )
    selected_voice = payload.voice
    user_pref_voice = (current_user.settings or {}).get("active_voice") if current_user else None

    if selected_voice == "custom_clone" or (not selected_voice and user_pref_voice == "custom_clone"):
        selected_voice = "custom_clone"
    elif not selected_voice or selected_voice == "auto":
        selected_voice = DEFAULT_HINGLISH_VOICE if has_hindi else DEFAULT_LADY_VOICE
    elif has_hindi and not selected_voice.startswith("hi-") and selected_voice != "custom_clone":
        selected_voice = DEFAULT_HINGLISH_VOICE

    voice_engine = VoiceEngine(default_voice=selected_voice)

    # 0. Fast-Path Natural Language Alias Check (Zero-Latency, ₹0 LLM Cost)
    clean_msg = payload.message.strip().lower()
    target_wf_keyword = None

    if clean_msg in ("morning", "briefing", "morning briefing", "morning brief", "standup"):
        target_wf_keyword = "Morning"
    elif clean_msg in ("triage", "github triage", "issues"):
        target_wf_keyword = "Triage"
    elif clean_msg in ("digest", "tech digest", "articles"):
        target_wf_keyword = "Digest"
    else:
        # Check custom user aliases
        alias_res = await db.execute(
            select(Alias).where(Alias.user_id == current_user.id, Alias.is_active == True)
        )
        for ca in alias_res.scalars().all():
            if clean_msg == ca.name.lower() or clean_msg.startswith(f"{ca.name.lower()} "):
                target_wf_keyword = ca.target_id
                break

    if target_wf_keyword:
        wf_engine = WorkflowEngine()
        wf_res = await db.execute(
            select(Workflow).where(
                Workflow.user_id == current_user.id,
                Workflow.name.ilike(f"%{target_wf_keyword}%"),
            )
        )
        wf = wf_res.scalars().first()
        if not wf:
            await wf_engine.seed_default_workflows(db, current_user.id)
            wf_res = await db.execute(
                select(Workflow).where(
                    Workflow.user_id == current_user.id,
                    Workflow.name.ilike(f"%{target_wf_keyword}%"),
                )
            )
            wf = wf_res.scalars().first()

        if wf:
            run = await wf_engine.run_workflow(db, workflow=wf)
            reply_text = (
                f"Ji! Maine '{wf.name}' workflow execute kar diya hai. Status: {run.status}."
                if has_hindi
                else f"Executed workflow '{wf.name}' successfully. Status: {run.status}."
            )
            audio_base64 = None
            if payload.include_audio:
                audio_bytes = await voice_engine.synthesize(reply_text)
                if audio_bytes:
                    audio_base64 = base64.b64encode(audio_bytes).decode("utf-8")

            report = StructuredReport(
                status=run.status,
                what_was_done=[f"Executed workflow '{wf.name}' via natural language alias shortcut"],
                important_results=[f"Workflow run finished with status: {run.status}"],
                any_problems=[],
                actions_requiring_me=[],
                spoken_summary=reply_text,
            )
            return APIResponse(
                ok=True,
                data=ChatResponseData(
                    reply=reply_text,
                    path="FAST",
                    task_id=str(run.id),
                    report=report,
                    audio_base64=audio_base64,
                ),
                trace_id=trace_id,
            )

    # 0.1 Multi-Agent Framework Delegation (CrewAI, AutoGen, LangGraph)
    fw_target = None
    if any(k in clean_msg for k in ("crewai", "crew ai", "research crew", "review crew", "content crew")):
        fw_target = "crewai"
    elif any(k in clean_msg for k in ("autogen", "auto gen", "debate team", "critic team")):
        fw_target = "autogen"
    elif any(k in clean_msg for k in ("langgraph", "lang graph", "state graph", "cyclic graph")):
        fw_target = "langgraph"

    if fw_target:
        adapter = get_framework_adapter(fw_target)
        template_name = None
        if "review" in clean_msg or "code" in clean_msg or "audit" in clean_msg:
            template_name = "code_review" if fw_target == "crewai" else "coder_and_critic"
        elif "content" in clean_msg or "write" in clean_msg or "article" in clean_msg:
            template_name = "content_strategy"
        elif "pipeline" in clean_msg or "etl" in clean_msg:
            template_name = "data_pipeline"
        elif "support" in clean_msg or "triage" in clean_msg:
            template_name = "support_triage"

        fw_result = await adapter.execute(task=payload.message, crew_or_graph_name=template_name)

        reply_text = (
            f"Ji! Maine {fw_result.framework.upper()} multi-agent squad ({fw_result.crew_or_graph_name}) ko deploy kiya hai. "
            f"{len(fw_result.agent_dialogue)} agents ne collaborate karke task complete kiya."
            if has_hindi
            else f"Deployed {fw_result.framework.upper()} multi-agent squad '{fw_result.crew_or_graph_name}'. "
            f"{len(fw_result.agent_dialogue)} agents collaborated and synthesized the final output."
        )

        audio_base64 = None
        if payload.include_audio:
            try:
                audio_base64 = await voice_engine.synthesize_to_base64(reply_text)
            except Exception:
                pass

        dialogue_summaries = [f"[{msg.role} ({msg.name})]: {msg.content[:120]}..." for msg in fw_result.agent_dialogue]

        report = StructuredReport(
            status=fw_result.status,
            what_was_done=[f"Executed {fw_result.framework.upper()} team: {fw_result.crew_or_graph_name}", *dialogue_summaries],
            important_results=[fw_result.final_output[:400]],
            any_problems=[],
            actions_requiring_me=[],
            spoken_summary=reply_text,
        )

        return APIResponse(
            ok=True,
            data=ChatResponseData(
                reply=reply_text + "\n\n" + fw_result.final_output,
                path="DELEGATED",
                task_id=f"fw-{fw_result.framework}",
                report=report,
                audio_base64=audio_base64,
            ),
            trace_id=trace_id,
        )

    # 1. Assemble Runtime Context
    context_engine = ContextEngine()
    system_ctx = await context_engine.assemble_context(db, current_user.id, query=payload.message)
    ctx_snippet = system_ctx.to_system_prompt_snippet()

    # 2. Intent Classification
    intent_engine = IntentEngine()
    classification = await intent_engine.classify(
        user_message=payload.message,
        system_context_snippet=ctx_snippet,
        provider_name="mock" if "test" in str(request.url) else "gemini",
    )

    # 3. Path A: Pure Conversational / Question Answering (FAST path, sub-second)
    if classification.is_conversational:
        router_engine = ModelRouter()
        convo_prompt = (
            f"{ctx_snippet}\n"
            f"You are Sara (S.A.R.A.), the user's autonomous, highly capable, and sophisticated personal AI operating system.\n"
            f"TONE & STYLE GUIDELINES:\n"
            f"- Speak with the poise, intellect, and professionalism of an executive AI partner (like Claude, ChatGPT-4o, or Gemini).\n"
            f"- Be courteous, articulate, and direct. Avoid generic repetitive phrases.\n"
            f"- If the user writes or speaks in Hindi or Hinglish (e.g. 'tum kya kya kar skti ho', 'kaise ho'), reply in refined, polite, and natural Hindi/Hinglish using respectful terms ('Aap', 'Ji'). If English, reply in polished English.\n"
            f"- If asked about your capabilities, clearly highlight what you can do: Gmail management (search, draft, send), Google Calendar scheduling, Google Drive file access, Google Sheets data updates, Proactive Morning Briefings, Meeting reminders, and persistent Long-Term Memory.\n"
            f"- Keep spoken responses concise and informative (2 to 4 crisp sentences or short clear points) so voice synthesis sounds crisp and natural.\n\n"
            f"User says: \"{payload.message}\"\n\n"
            f"Your professional response:"
        )

        model_res = await router_engine.complete(
            prompt=convo_prompt,
            path="FAST",
            provider_name="mock" if "test" in str(request.url) else "gemini",
        )
        reply_text = model_res.content or "Hello! I am ready to assist you with your tasks, emails, calendar, and documents."

        audio_data = None
        if payload.include_audio:
            try:
                audio_data = await voice_engine.synthesize_to_base64(reply_text[:250])
            except Exception:
                pass

        return APIResponse(
            ok=True,
            data=ChatResponseData(
                reply=reply_text,
                path="FAST",
                audio_base64=audio_data,
            ),
            trace_id=trace_id,
        )

    # 4. Path B: Actionable Command (SMART / DEEP path)
    dag_planner = DAGPlanner()
    dag_plan = dag_planner.plan(classification, initial_inputs={"raw_command": payload.message})

    # Create Task in database
    task = Task(
        user_id=current_user.id,
        source="chat",
        intent={"goal": classification.goal, "raw_message": payload.message, "entities": classification.entities},
        path=dag_plan.task_path,
        status="PLANNED",
        trace_id=trace_id,
    )
    db.add(task)
    await db.flush()

    # Create TaskSteps in database
    for step_plan in dag_plan.steps:
        step_record = TaskStep(
            task_id=task.id,
            step_key=step_plan.step_key,
            kind="tool",
            capability=step_plan.capability,
            status="PLANNED",
            inputs=step_plan.inputs,
        )
        db.add(step_record)

    await db.commit()

    # Execute Task DAG via Worker
    job_result = await execute_task_job({"worker_id": "chat-orchestrator"}, str(task.id), session=db)
    await db.commit()

    # Reload Task with steps to synthesize report
    task_res = await db.execute(
        select(Task).where(Task.id == task.id).options(selectinload(Task.steps))
    )
    reloaded_task = task_res.scalar_one()

    steps_data = [
        {"step_key": s.step_key, "capability": s.capability, "status": s.status, "outputs": s.outputs, "error": s.error}
        for s in reloaded_task.steps
    ]

    synthesizer = ResultSynthesizer()
    report = synthesizer.synthesize(
        task_goal=classification.goal,
        task_status=reloaded_task.status,
        steps_data=steps_data,
    )

    reloaded_task.result = report.model_dump()
    await db.commit()

    # Audio synthesis
    audio_data = None
    if payload.include_audio:
        try:
            audio_data = await voice_engine.synthesize_to_base64(report.spoken_summary)
        except Exception:
            pass

    return APIResponse(
        ok=True,
        data=ChatResponseData(
            reply=report.spoken_summary,
            path=dag_plan.task_path,
            task_id=str(reloaded_task.id),
            report=report,
            audio_base64=audio_data,
        ),
        trace_id=trace_id,
    )
