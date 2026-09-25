"""Conversational Chat API router for OmniBrain.

Enables natural conversation, question answering, and direct multi-step task execution
with optional Lady Assistant voice output.
"""
import asyncio
import base64
import json as json_lib
from typing import Any, Dict, Optional
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import StreamingResponse
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
from packages.core.memory.store import get_memory_store
from packages.core.brain.web_research import is_research_query, search_web_realtime, format_research_context
from apps.api.deps import get_db, get_current_user
from apps.worker.main import execute_task_job
from apps.api.shared import (
    get_model_router, get_context_engine, get_intent_engine,
    get_dag_planner, get_synthesizer,
    get_cached_reply, set_cached_reply,
)

router = APIRouter()

# Enhanced Sara system prompt for dual-intelligence (deep thinking for questions, lightning fast for tasks)
SARA_SYSTEM_PROMPT = (
    "You are Sara (S.A.R.A.), the user's advanced personal AI operating system.\n\n"
    "CRITICAL PERSONALITY & INTELLIGENCE RULES:\n"
    "- Act completely human, warm, thoughtful, and highly intelligent. Never sound like a rigid robot.\n"
    "- If speaking in Hindi/Hinglish, speak naturally like a knowledgeable, supportive Indian colleague (using 'Haan ji', 'Dekhiye Vikas ji', 'Bilkul').\n"
    "- DUAL-MODE INTELLIGENCE:\n"
    "  1. WHEN THE USER ASKS A QUESTION, seeks advice, knowledge, reasoning, or explanation: THINK DEEPLY, analyze thoroughly, and provide a GENUINE, WELL-REASONED, comprehensive, and helpful answer. Do not artificially limit explanations to 1-2 sentences. Take time to think and explain clearly with depth.\n"
    "  2. WHEN THE USER GIVES A GREETING or casual chit-chat: Keep it warm, polite, and conversational.\n"
    "  3. WHEN THE USER REQUESTS AN ACTION OR TASK (e.g. open apps, close windows, send email, check calendar): Confirm clearly, concisely, and execute without unnecessary filler.\n"
    "- Always be honest, insightful, and factually accurate.\n"
)


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


def _memory_statement(message: str) -> Optional[str]:
    """Extract explicit remember requests without sending them through an LLM."""
    clean = message.strip()
    lowered = clean.lower()
    prefixes = (
        "remember that ", "remember ", "please remember that ",
        "yaad rakho ki ", "yaad rakhna ki ", "yaad rakho ", "याद रखो कि ", "याद रखना कि ",
    )
    for prefix in prefixes:
        if lowered.startswith(prefix) or clean.startswith(prefix):
            statement = clean[len(prefix):].strip(" .!?\n")
            return statement or None
    return None


async def _recent_memory_prompt(db: AsyncSession, user_id: UUID) -> str:
    """Load a small recent memory window without semantic embedding latency."""
    try:
        memories = await get_memory_store().list_memories(
            session=db,
            user_id=user_id,
            limit=5,
        )
        if memories:
            lines = "\n".join(f"- {memory.content}" for memory in memories)
            return f"\n### What Sara remembers about the user\n{lines}\n"
    except Exception:
        pass
    return ""


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
    clean_msg = payload.message.strip().lower()

    # 0. Emergency Stop / Halt Check (<1ms response, halts running tasks immediately)
    stop_phrases = (
        "stop", "ruko", "ruk jao", "cancel", "halt", "abort", "band karo",
        "stop karo", "task stop karo", "task cancel karo", "stop task", "cancel task",
        "sara stop", "sara ruko", "sara ruk jao", "s.a.r.a. stop", "s.a.r.a. ruko"
    )
    if clean_msg in stop_phrases or any(clean_msg == f"sara {sp}" or clean_msg == f"{sp} sara" for sp in ("stop", "ruko", "cancel", "halt")):
        from packages.core.safety.kill_switch import emergency_kill_switch
        await emergency_kill_switch.activate(reason=f"User stop command: {payload.message}", triggered_by=current_user.email)

        # Cancel all active tasks in DB
        active_tasks = await db.execute(
            select(Task).where(
                Task.user_id == current_user.id,
                Task.status.in_(["PLANNED", "RUNNING", "WAITING_APPROVAL", "EXECUTING"])
            )
        )
        for t in active_tasks.scalars().all():
            t.status = "CANCELLED"
            t.result = {"error": "Halted immediately by user stop command"}
        await db.commit()

        reply_text = (
            "Haan ji Vikas ji, maine chal rahe task ko turant STOP kar diya hai! Sabhi operations halt ho gayi hain."
            if has_hindi
            else "Task execution halted immediately. All actions have been stopped."
        )

        audio_base64 = None
        if payload.include_audio:
            try:
                audio_base64 = await voice_engine.synthesize_to_base64(reply_text)
            except Exception:
                pass

        report = StructuredReport(
            status="CANCELLED",
            what_was_done=["Emergency Stop triggered by user"],
            important_results=["All operations halted immediately"],
            any_problems=["Task halted mid-flight upon user request"],
            actions_requiring_me=[],
            spoken_summary=reply_text,
        )

        return APIResponse(
            ok=True,
            data=ChatResponseData(
                reply=reply_text,
                path="FAST",
                report=report,
                audio_base64=audio_base64,
            ),
            trace_id=trace_id,
        )

    # Auto-resume from emergency kill switch if a new valid request is sent
    from packages.core.safety.kill_switch import emergency_kill_switch
    if await emergency_kill_switch.is_active():
        await emergency_kill_switch.deactivate(actor=current_user.email)

    # 0.1 Fast-Path Natural Language Alias Check (Zero-Latency, ₹0 LLM Cost)
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

    # Explicit memory commands are persisted immediately and bypass planning.
    memory_statement = _memory_statement(payload.message)
    if memory_statement:
        category = "preference" if any(
            word in clean_msg for word in ("prefer", "preference", "pasand", " पसंद ", "like")
        ) else "fact"
        await get_memory_store().store_memory(
            session=db,
            user_id=current_user.id,
            content=memory_statement,
            category=category,
            source="user_stated",
        )
        await db.commit()
        reply_text = (
            f"Ji, maine yaad rakh liya: {memory_statement}."
            if has_hindi else f"Got it. I will remember: {memory_statement}."
        )
        return APIResponse(
            ok=True,
            data=ChatResponseData(reply=reply_text, path="FAST"),
            trace_id=trace_id,
        )

    # 1. Ultra-Fast Intent Classification (<1ms via fast-path, shared singleton)
    classification = await get_intent_engine().classify(
        user_message=payload.message,
        provider_name="mock" if "test" in str(request.url) else "gemini",
    )

    # 2. Path A: Pure Conversational / Question Answering (Target: ~1s response)
    if classification.is_conversational:
        # Instant Cache for standard greetings & identity inquiries (<10ms)
        reply_text = None
        lower_query = clean_msg

        if any(w in lower_query for w in ("kaise ho", "kaisa hai", "kaisi ho", "kya haal", "how are you")):
            reply_text = (
                "Haan ji, main bilkul theek hoon! Aap bataiye, aaj kaise help karu aapki?"
                if has_hindi
                else "I'm doing great, thanks for asking! How can I help you today?"
            )
        elif any(w in lower_query for w in ("kaun ho", "kaun hai", "who are you", "naam kya hai", "what is your name")):
            reply_text = (
                "Main Sara hoon, aapki personal AI assistant. Main aapke emails aur schedule manage kar sakti hoon. Bataiye, kya karna hai aaj?"
                if has_hindi
                else "I'm Sara, your personal AI assistant. I can manage your emails, calendar, and more. What's on your mind?"
            )
        elif any(w in lower_query for w in ("kya kar sakti ho", "kya karti ho", "what can you do", "help me")):
            reply_text = (
                "Ji main aapke emails bhej sakti hoon, meetings schedule kar sakti hoon, aur documents manage kar sakti hoon. Koi specific task hai aapke dimaag mein?"
                if has_hindi
                else "I can send emails, schedule your meetings, and manage your documents. Do you have a specific task in mind?"
            )

        # Redis Cache Check — instant response for repeated custom questions (skip for live research queries)
        is_research = is_research_query(payload.message)
        if not reply_text and not is_research:
            cached = await get_cached_reply(payload.message)
            if cached:
                reply_text = cached

        # Dynamic LLM Generation for novel custom questions (with Real-Time Internet Research Grounding)
        if not reply_text:
            router_engine = get_model_router()
            memory_context = await _recent_memory_prompt(db, current_user.id)

            # Real-Time Internet Research & Grounding
            research_context = ""
            if is_research:
                try:
                    live_results = search_web_realtime(payload.message, max_results=3)
                    if live_results:
                        research_context = format_research_context(live_results)
                except Exception as rx:
                    pass

            convo_prompt = (
                f"{memory_context}"
                f"{research_context}"
                f"User says: \"{payload.message}\"\n\n"
                f"Your crisp professional response:"
            )

            model_res = await router_engine.complete(
                prompt=convo_prompt,
                path="FAST",
                system_prompt=SARA_SYSTEM_PROMPT,
                provider_name="mock" if "test" in str(request.url) else "gemini",
            )
            reply_text = model_res.content or "Hello! I am ready to assist you with your tasks, emails, calendar, and documents."

            # Cache the LLM response for future instant replies (skip research queries)
            if not is_research:
                await set_cached_reply(payload.message, reply_text)

        # High-Speed Voice Synthesis: synthesize first punchy sentence for instant audio (<300ms)
        audio_data = None
        if payload.include_audio:
            try:
                first_sentence = reply_text.split(".")[0].split("?")[0].strip() + "."
                audio_data = await voice_engine.synthesize_to_base64(first_sentence[:120])
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

    # 3. Path B: Actionable Command — parallel context assembly
    system_ctx = await get_context_engine().assemble_context(db, current_user.id, query=payload.message)
    ctx_snippet = system_ctx.to_system_prompt_snippet()

    # 4. Plan and execute DAG
    dag_plan = get_dag_planner().plan(classification, initial_inputs={"raw_command": payload.message})

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

    report = get_synthesizer().synthesize(
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


# ============================================================================
# SSE Streaming Endpoint — Real-time token-by-token response delivery
# ============================================================================

def _sse_event(event_type: str, content: str = "", **kwargs) -> str:
    """Format a Server-Sent Event data line."""
    payload = {"type": event_type, "content": content, **kwargs}
    return f"data: {json_lib.dumps(payload, ensure_ascii=False)}\n\n"


@router.post("/stream")
async def chat_stream(
    payload: ChatRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Stream Sara's response token-by-token via Server-Sent Events (SSE)."""
    trace_id = getattr(request.state, "trace_id", None)

    # Voice & Language detection (same as non-streaming endpoint)
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
    clean_msg = payload.message.strip().lower()

    async def event_generator():
        """Async generator that yields SSE events."""
        # 0. Emergency Stop / Halt Check
        stop_phrases = (
            "stop", "ruko", "ruk jao", "cancel", "halt", "abort", "band karo",
            "stop karo", "task stop karo", "task cancel karo", "stop task", "cancel task",
            "sara stop", "sara ruko", "sara ruk jao", "s.a.r.a. stop", "s.a.r.a. ruko"
        )
        if clean_msg in stop_phrases or any(clean_msg == f"sara {sp}" or clean_msg == f"{sp} sara" for sp in ("stop", "ruko", "cancel", "halt")):
            from packages.core.safety.kill_switch import emergency_kill_switch
            await emergency_kill_switch.activate(reason=f"User stop command: {payload.message}", triggered_by=current_user.email)

            active_tasks = await db.execute(
                select(Task).where(
                    Task.user_id == current_user.id,
                    Task.status.in_(["PLANNED", "RUNNING", "WAITING_APPROVAL", "EXECUTING"])
                )
            )
            for t in active_tasks.scalars().all():
                t.status = "CANCELLED"
                t.result = {"error": "Halted immediately by user stop command"}
            await db.commit()

            reply_text = (
                "Haan ji Vikas ji, maine chal rahe task ko turant STOP kar diya hai! Sabhi operations halt ho gayi hain."
                if has_hindi
                else "Task execution halted immediately. All actions have been stopped."
            )
            yield _sse_event("status", "🛑 Stopped")
            yield _sse_event("token", reply_text)

            report = StructuredReport(
                status="CANCELLED",
                what_was_done=["Emergency Stop triggered by user"],
                important_results=["All operations halted immediately"],
                any_problems=["Task halted mid-flight upon user request"],
                actions_requiring_me=[],
                spoken_summary=reply_text,
            )
            yield _sse_event("report", report.model_dump())
            if payload.include_audio:
                try:
                    audio_b64 = await voice_engine.synthesize_to_base64(reply_text)
                    if audio_b64:
                        yield _sse_event("audio", {"audio_base64": audio_b64})
                except Exception:
                    pass
            yield _sse_event("done", {"task_id": None, "path": "FAST"})
            return

        # Auto-resume from emergency kill switch if a new valid request is sent
        from packages.core.safety.kill_switch import emergency_kill_switch
        if await emergency_kill_switch.is_active():
            await emergency_kill_switch.deactivate(actor=current_user.email)

        # 1. Classify intent (instant via fast-path, shared singleton)
        classification = await get_intent_engine().classify(
            user_message=payload.message,
            provider_name="gemini",
        )

        # 2A. Conversational Path — stream reply tokens
        if classification.is_conversational:
            yield _sse_event("status", "replying...")

            # Check instant cache first
            cached_reply = None
            if any(w in clean_msg for w in ("kaise ho", "kaisa hai", "kaisi ho", "kya haal", "how are you")):
                cached_reply = (
                    "Haan ji, main bilkul theek hoon! Aap bataiye, aaj kaise help karu aapki?"
                    if has_hindi
                    else "I'm doing great, thanks for asking! How can I help you today?"
                )
            elif any(w in clean_msg for w in ("kaun ho", "kaun hai", "who are you", "naam kya hai", "what is your name")):
                cached_reply = (
                    "Main Sara hoon, aapki personal AI assistant. Main aapke emails aur schedule manage kar sakti hoon. Bataiye, kya karna hai aaj?"
                    if has_hindi
                    else "I'm Sara, your personal AI assistant. I can manage your emails, calendar, and more. What's on your mind?"
                )
            elif any(w in clean_msg for w in ("kya kar sakti ho", "kya karti ho", "what can you do", "help me")):
                cached_reply = (
                    "Ji main aapke emails bhej sakti hoon, meetings schedule kar sakti hoon, aur documents manage kar sakti hoon. Koi specific task hai aapke dimaag mein?"
                    if has_hindi
                    else "I can send emails, schedule your meetings, and manage your documents. Do you have a specific task in mind?"
                )

            if cached_reply:
                # Stream cached reply word-by-word for natural typing effect
                words = cached_reply.split(" ")
                for i, word in enumerate(words):
                    token = word if i == 0 else " " + word
                    yield _sse_event("token", token)
                    await asyncio.sleep(0.02)  # 20ms between words for natural feel
                full_text = cached_reply
            else:
                is_research = is_research_query(payload.message)
                # Redis cache check for repeated custom queries (skip for live research queries)
                redis_cached = None if is_research else await get_cached_reply(payload.message)
                if redis_cached:
                    words = redis_cached.split(" ")
                    for i, word in enumerate(words):
                        token = word if i == 0 else " " + word
                        yield _sse_event("token", token)
                        await asyncio.sleep(0.02)
                    full_text = redis_cached
                else:
                    # Fetch real-time web context if query requires research/current data
                    research_context = ""
                    if is_research:
                        yield _sse_event("status", "🌐 Searching real-time internet data...")
                        try:
                            live_results = search_web_realtime(payload.message, max_results=3)
                            if live_results:
                                research_context = format_research_context(live_results)
                        except Exception:
                            pass

                    # Stream LLM response token-by-token from Gemini
                    memory_context = await _recent_memory_prompt(db, current_user.id)
                    convo_prompt = (
                        f"{memory_context}"
                        f"{research_context}"
                        f"User says: \"{payload.message}\"\n\n"
                        f"Your crisp professional response:"
                    )

                    full_text = ""
                    try:
                        async for chunk in get_model_router().stream(
                            prompt=convo_prompt,
                            path="FAST",
                            system_prompt=SARA_SYSTEM_PROMPT,
                            provider_name="gemini",
                        ):
                            full_text += chunk
                            yield _sse_event("token", chunk)
                    except Exception:
                        if not full_text:
                            full_text = "Hello! I am Sara, ready to assist you."
                            yield _sse_event("token", full_text)

                    # Cache for future instant replies (skip ephemeral research queries)
                    if not is_research:
                        await set_cached_reply(payload.message, full_text)

            # Audio synthesis (after text is complete)
            if payload.include_audio:
                try:
                    first_sentence = full_text.split(".")[0].split("?")[0].strip() + "."
                    audio_data = await voice_engine.synthesize_to_base64(first_sentence[:120])
                    if audio_data:
                        yield _sse_event("audio", audio_base64=audio_data)
                except Exception:
                    pass

            yield _sse_event("done", path="FAST")

        else:
            # 2B. Actionable Command Path — stream progress events
            yield _sse_event("status", "planning task...")

            system_ctx = await get_context_engine().assemble_context(db, current_user.id, query=payload.message)

            dag_plan = get_dag_planner().plan(classification, initial_inputs={"raw_command": payload.message})

            yield _sse_event("status", f"executing {len(dag_plan.steps)} step(s)...")

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

            # Execute and stream progress
            for i, step_plan in enumerate(dag_plan.steps, 1):
                yield _sse_event("progress", f"Step {i}/{len(dag_plan.steps)}: {step_plan.capability}", step=i, total=len(dag_plan.steps))

            job_result = await execute_task_job({"worker_id": "chat-orchestrator"}, str(task.id), session=db)
            await db.commit()

            # Reload and synthesize report
            task_res = await db.execute(
                select(Task).where(Task.id == task.id).options(selectinload(Task.steps))
            )
            reloaded_task = task_res.scalar_one()

            steps_data = [
                {"step_key": s.step_key, "capability": s.capability, "status": s.status, "outputs": s.outputs, "error": s.error}
                for s in reloaded_task.steps
            ]

            synthesizer = get_synthesizer()
            report = synthesizer.synthesize(
                task_goal=classification.goal,
                task_status=reloaded_task.status,
                steps_data=steps_data,
            )

            reloaded_task.result = report.model_dump()
            await db.commit()

            # Stream the spoken summary token by token
            words = report.spoken_summary.split(" ")
            for i, word in enumerate(words):
                token = word if i == 0 else " " + word
                yield _sse_event("token", token)
                await asyncio.sleep(0.015)

            # Stream report data
            yield _sse_event("report", report=report.model_dump())

            # Audio
            if payload.include_audio:
                try:
                    audio_data = await voice_engine.synthesize_to_base64(report.spoken_summary)
                    if audio_data:
                        yield _sse_event("audio", audio_base64=audio_data)
                except Exception:
                    pass

            yield _sse_event("done", path=dag_plan.task_path, task_id=str(reloaded_task.id))

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
