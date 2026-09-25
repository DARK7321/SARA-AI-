"""Main entrypoint for the OmniBrain API service."""
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

from packages.core.observability.logging import setup_logging, get_logger
from packages.core.observability.middleware import TraceIDMiddleware
from apps.api.routers import (
    auth,
    health,
    tasks,
    approvals,
    connectors,
    chat,
    notifications,
    workflows,
    webhooks,
    mobile,
    safety,
    aliases,
    frameworks,
    voice,
)
from apps.api.settings import get_settings
from packages.core.schemas.common import APIResponse

settings = get_settings()
logger = get_logger("main")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan context manager for startup and shutdown events."""
    setup_logging(settings.LOG_LEVEL)
    logger.info("OmniBrain API starting...")
    yield
    logger.info("OmniBrain API shutting down...")


app = FastAPI(
    title="OmniBrain API",
    version="0.2.0-websearch-fix",
    docs_url="/docs",
    lifespan=lifespan,
)

app.add_middleware(TraceIDMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:8000",
        "http://0.0.0.0:3000",
        "https://sara-ai-kohl.vercel.app",
        "https://sara-ai-fawn.vercel.app",
    ],
    allow_origin_regex=r"https://.*\.vercel\.app",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router, prefix="/v1/auth", tags=["auth"])
app.include_router(health.router, prefix="/v1/health", tags=["health"])
app.include_router(tasks.router, prefix="/v1/tasks", tags=["tasks"])
app.include_router(approvals.router, prefix="/v1/approvals", tags=["approvals"])
app.include_router(connectors.router, prefix="/v1/connectors", tags=["connectors"])
app.include_router(chat.router, prefix="/v1/chat", tags=["chat"])
app.include_router(notifications.router, prefix="/v1", tags=["notifications", "memory", "proactive"])
app.include_router(workflows.router, prefix="/v1", tags=["workflows"])
app.include_router(webhooks.router, prefix="/v1", tags=["webhooks", "events"])
app.include_router(mobile.router, prefix="/v1", tags=["mobile", "companion"])
app.include_router(safety.router, prefix="/v1", tags=["safety", "policies"])
app.include_router(aliases.router, prefix="/v1/aliases", tags=["aliases"])
app.include_router(frameworks.router, prefix="/v1/frameworks", tags=["frameworks", "agents"])
app.include_router(voice.router, prefix="/v1/voice", tags=["voice", "cloning"])


@app.get("/", response_model=APIResponse)
async def root(request: Request):
    """Root endpoint welcoming user and reporting API version."""
    return APIResponse(
        ok=True,
        data={"message": "Welcome to OmniBrain", "version": "0.2.0-websearch-fix"},
        trace_id=getattr(request.state, "trace_id", None),
    )
