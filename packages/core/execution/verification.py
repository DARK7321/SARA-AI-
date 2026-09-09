"""Verification Engine for OmniBrain.

Enforces Principle 5: 'Verify, don't assume'.
An API 200 response is not proof. We check post-conditions for anything that matters.
"""
from enum import Enum
from typing import Any, Dict, Optional
from packages.connectors._sdk.base import BaseConnector


class VerificationStatus(str, Enum):
    VERIFIED = "VERIFIED"
    VERIFICATION_FAILED = "VERIFICATION_FAILED"
    UNABLE_TO_VERIFY = "UNABLE_TO_VERIFY"


class VerificationEngine:
    """Verifies that an external action produced the expected side effect."""

    async def verify_action(
        self,
        connector: BaseConnector,
        action: str,
        verification_hints: Optional[Dict[str, Any]],
    ) -> VerificationStatus:
        """Run post-condition verification against the target connector."""
        if not verification_hints:
            # Tool did not expose verification hints
            return VerificationStatus.UNABLE_TO_VERIFY

        try:
            is_verified = await connector.verify(action, verification_hints)
            return VerificationStatus.VERIFIED if is_verified else VerificationStatus.VERIFICATION_FAILED
        except Exception:
            return VerificationStatus.VERIFICATION_FAILED

