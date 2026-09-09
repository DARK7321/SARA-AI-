"""Deterministic Self-Healing and Failure Recovery Engine for OmniBrain.

Implements the 5-level failure taxonomy defined in Part 9 of the Master Blueprint:
- Level 1: Transient -> Exponential backoff with jitter
- Level 2: Auth -> Automatic token refresh & retry
- Level 3: Tool Unavailable -> Fallback tool routing
- Level 4: Verification/Validation -> Step compensation or rollback
- Level 5: Policy/Ambiguous -> HITL escalation
"""
from enum import Enum
import math
import random
import time
from typing import Any, Dict, List, Optional
from uuid import UUID

from packages.connectors._sdk.contract import ErrorClass, ToolError


class RecoveryStrategy(str, Enum):
    RETRY_BACKOFF = "RETRY_BACKOFF"
    REFRESH_TOKEN = "REFRESH_TOKEN"
    FALLBACK_TOOL = "FALLBACK_TOOL"
    COMPENSATE = "COMPENSATE"
    ESCALATE_HUMAN = "ESCALATE_HUMAN"


class RecoveryDecision:
    def __init__(
        self,
        strategy: RecoveryStrategy,
        level: int,
        reason: str,
        backoff_ms: int = 0,
        fallback_connector: Optional[str] = None,
        can_auto_recover: bool = True,
    ):
        self.strategy = strategy
        self.level = level
        self.reason = reason
        self.backoff_ms = backoff_ms
        self.fallback_connector = fallback_connector
        self.can_auto_recover = can_auto_recover


class RecoveryEngine:
    """Classifies tool execution errors and coordinates self-healing recovery."""

    def __init__(self, max_l1_retries: int = 3):
        self.max_l1_retries = max_l1_retries
        self.fallback_map: Dict[str, str] = {
            "browser": "browser_sandbox",
            "sheets": "sheets_sandbox",
            "drive": "drive_sandbox",
            "gmail": "gmail_sandbox",
        }

    def evaluate_failure(
        self,
        error: ToolError,
        current_attempt: int = 1,
        connector_id: Optional[str] = None,
    ) -> RecoveryDecision:
        """Evaluate an execution failure and return deterministic self-healing strategy."""
        err_class = error.error_class

        # Level 1: Transient or Rate Limited
        if err_class in (ErrorClass.TRANSIENT, ErrorClass.RATE_LIMITED):
            if current_attempt <= self.max_l1_retries:
                # Exponential backoff with jitter: 2^(attempt-1) * base + jitter
                base_s = 0.5
                backoff_s = (2 ** (current_attempt - 1)) * base_s + random.uniform(0.05, 0.2)
                backoff_ms = int(backoff_s * 1000)
                return RecoveryDecision(
                    strategy=RecoveryStrategy.RETRY_BACKOFF,
                    level=1,
                    reason=f"Level 1 Self-Healing: Transient failure '{error.message}', retrying in {backoff_ms}ms (Attempt {current_attempt}/{self.max_l1_retries})",
                    backoff_ms=backoff_ms,
                    can_auto_recover=True,
                )
            else:
                return RecoveryDecision(
                    strategy=RecoveryStrategy.ESCALATE_HUMAN,
                    level=5,
                    reason=f"Level 1 Retries exhausted after {self.max_l1_retries} attempts. Escalating.",
                    can_auto_recover=False,
                )

        # Level 2: Auth Failure
        elif err_class == ErrorClass.AUTH:
            return RecoveryDecision(
                strategy=RecoveryStrategy.REFRESH_TOKEN,
                level=2,
                reason="Level 2 Self-Healing: Token expired or invalid, refreshing OAuth credentials.",
                can_auto_recover=True,
            )

        # Level 3: Tool Unavailable
        elif err_class == ErrorClass.TOOL_UNAVAILABLE:
            connector_name = (connector_id or "").replace("connector-", "").lower()
            fallback = self.fallback_map.get(connector_name, "fake")
            return RecoveryDecision(
                strategy=RecoveryStrategy.FALLBACK_TOOL,
                level=3,
                reason=f"Level 3 Self-Healing: Primary connector '{connector_id}' offline. Routing to fallback '{fallback}'.",
                fallback_connector=fallback,
                can_auto_recover=True,
            )

        # Level 4: Validation or Verification Failure
        elif err_class in (ErrorClass.VALIDATION, ErrorClass.VERIFICATION_FAILED):
            return RecoveryDecision(
                strategy=RecoveryStrategy.COMPENSATE,
                level=4,
                reason=f"Level 4 Self-Healing: Verification failed '{error.message}'. Triggering compensation rollback.",
                can_auto_recover=False,
            )

        # Level 5: Policy Denied / Ambiguous / Budget Exceeded
        else:
            return RecoveryDecision(
                strategy=RecoveryStrategy.ESCALATE_HUMAN,
                level=5,
                reason=f"Level 5 Policy Guard: Operation requires human resolution ({error.message}).",
                can_auto_recover=False,
            )

