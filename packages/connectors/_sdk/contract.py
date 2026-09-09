"""Universal Tool Contract for OmniBrain.

Implements the contract defined in Part 5 & Part 9 of the Master Blueprint.
Every connector action strictly adheres to this contract.
"""
from enum import Enum
import hashlib
import json
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class ErrorClass(str, Enum):
    """Failure taxonomy mapping to deterministic recovery levels."""
    TRANSIENT = "TRANSIENT"                  # Network timeout, 5xx -> L1 retry
    RATE_LIMITED = "RATE_LIMITED"            # 429 Too Many Requests -> L1 retry after throttle
    AUTH = "AUTH"                            # 401/403 Token expired -> L2 refresh token
    TOOL_UNAVAILABLE = "TOOL_UNAVAILABLE"    # Health OFFLINE/DEGRADED -> L3 tool fallback
    VALIDATION = "VALIDATION"                # Schema mismatch -> L4 replan step
    VERIFICATION_FAILED = "VERIFICATION_FAILED"  # Post-condition check failed -> L4 compensation/replan
    POLICY_DENIED = "POLICY_DENIED"          # DENY rule triggered -> Stop
    AMBIGUOUS = "AMBIGUOUS"                  # Missing info -> L5 human intervention
    BUDGET_EXCEEDED = "BUDGET_EXCEEDED"      # Daily or task cap hit -> Pause & notify


class SideEffectType(str, Enum):
    """Side effect classification for approval and verification strictness."""
    NONE = "NONE"                            # In-memory transformation
    READ = "READ"                            # Read-only API call
    WRITE = "WRITE"                          # Safe modification / draft
    DESTRUCTIVE = "DESTRUCTIVE"              # Delete, overwrite, permanent change
    EXTERNAL_SEND = "EXTERNAL_SEND"          # Outgoing email, message, payment


class ToolContext(BaseModel):
    task_id: str
    step_id: str
    agent: Optional[str] = "orchestrator"
    trace_id: Optional[str] = None


class ToolAuthorization(BaseModel):
    policy_decision_id: Optional[str] = None
    approval_id: Optional[str] = None
    scopes: List[str] = Field(default_factory=list)


class ToolError(BaseModel):
    error_class: ErrorClass
    message: str
    retryable: bool = False
    retry_after_s: Optional[int] = None
    details: Optional[Dict[str, Any]] = None


class ToolMetadata(BaseModel):
    latency_ms: int = 0
    cost: float = 0.0
    provider_request_id: Optional[str] = None
    retries: int = 0
    cached: bool = False


class ToolRequest(BaseModel):
    request_id: str
    tool: str
    action: str
    version: str = "1.0"
    input: Dict[str, Any] = Field(default_factory=dict)
    context: ToolContext
    authorization: ToolAuthorization = Field(default_factory=ToolAuthorization)
    timeout_ms: int = 15000
    idempotency_key: str
    dry_run: bool = False


class ToolResponse(BaseModel):
    success: bool
    data: Dict[str, Any] = Field(default_factory=dict)
    metadata: ToolMetadata = Field(default_factory=ToolMetadata)
    error: Optional[ToolError] = None
    verification_hints: Optional[Dict[str, Any]] = None


def compute_idempotency_key(task_id: str, step_id: str, canonical_input: Dict[str, Any]) -> str:
    """Compute a deterministic SHA-256 idempotency key.
    
    Guarantees that identical inputs within a task step never trigger duplicate side-effects.
    """
    normalized_json = json.dumps(canonical_input, sort_keys=True, separators=(",", ":"))
    payload = f"{task_id}:{step_id}:{normalized_json}".encode("utf-8")
    return hashlib.sha256(payload).hexdigest()
