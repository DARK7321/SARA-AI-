"""Unit tests for Self-Healing and Recovery Engine."""
import pytest
from packages.connectors._sdk.contract import ToolError, ErrorClass
from packages.core.execution.recovery import RecoveryEngine, RecoveryStrategy


def test_recovery_level_1_transient_retry():
    engine = RecoveryEngine(max_l1_retries=3)
    error = ToolError(error_class=ErrorClass.TRANSIENT, message="Connection reset by peer")

    # Attempt 1 -> Retry with backoff
    dec1 = engine.evaluate_failure(error, current_attempt=1)
    assert dec1.strategy == RecoveryStrategy.RETRY_BACKOFF
    assert dec1.level == 1
    assert dec1.backoff_ms > 0
    assert dec1.can_auto_recover is True

    # Attempt 4 (exceeds max_retries) -> Escalate to human
    dec4 = engine.evaluate_failure(error, current_attempt=4)
    assert dec4.strategy == RecoveryStrategy.ESCALATE_HUMAN
    assert dec4.level == 5
    assert dec4.can_auto_recover is False


def test_recovery_level_2_auth_token_refresh():
    engine = RecoveryEngine()
    error = ToolError(error_class=ErrorClass.AUTH, message="401 Unauthorized: token expired")

    decision = engine.evaluate_failure(error)
    assert decision.strategy == RecoveryStrategy.REFRESH_TOKEN
    assert decision.level == 2
    assert decision.can_auto_recover is True


def test_recovery_level_3_tool_fallback():
    engine = RecoveryEngine()
    error = ToolError(error_class=ErrorClass.TOOL_UNAVAILABLE, message="Service 503 Unavailable")

    decision = engine.evaluate_failure(error, connector_id="connector-browser")
    assert decision.strategy == RecoveryStrategy.FALLBACK_TOOL
    assert decision.level == 3
    assert decision.fallback_connector == "browser_sandbox"


def test_recovery_level_4_verification_compensation():
    engine = RecoveryEngine()
    error = ToolError(error_class=ErrorClass.VERIFICATION_FAILED, message="Written cell value did not match")

    decision = engine.evaluate_failure(error)
    assert decision.strategy == RecoveryStrategy.COMPENSATE
    assert decision.level == 4


def test_recovery_level_5_policy_denied():
    engine = RecoveryEngine()
    error = ToolError(error_class=ErrorClass.POLICY_DENIED, message="Action not allowed by rule")

    decision = engine.evaluate_failure(error)
    assert decision.strategy == RecoveryStrategy.ESCALATE_HUMAN
    assert decision.level == 5

