import pytest
from packages.connectors._sdk.contract import (
    ToolRequest,
    ToolResponse,
    ToolContext,
    ToolAuthorization,
    ToolError,
    ErrorClass,
    compute_idempotency_key,
)
from packages.connectors._sdk.testing import FakeConnector


def test_idempotency_key_canonical_ordering():
    task_id = "task-123"
    step_id = "step-456"

    input_a = {"user": "alice", "amount": 100, "meta": {"dept": "ops", "priority": 1}}
    input_b = {"amount": 100, "meta": {"priority": 1, "dept": "ops"}, "user": "alice"}

    hash_a = compute_idempotency_key(task_id, step_id, input_a)
    hash_b = compute_idempotency_key(task_id, step_id, input_b)

    assert hash_a == hash_b, "Idempotency hash must be independent of key ordering"


@pytest.mark.asyncio
async def test_fake_connector_execution():
    connector = FakeConnector(
        predefined_responses={"fake.write": {"created": True, "id": "doc_999"}}
    )

    request = ToolRequest(
        request_id="req_001",
        tool="connector-fake",
        action="fake.write",
        input={"title": "Test Plan"},
        context=ToolContext(task_id="t1", step_id="s1"),
        idempotency_key="hash_123",
        dry_run=False,
    )

    response = await connector.execute(request)
    assert response.success is True
    assert response.data["created"] is True
    assert len(connector.call_history) == 1

    # Post condition verification
    verified = await connector.verify("fake.write", response.verification_hints)
    assert verified is True


@pytest.mark.asyncio
async def test_fake_connector_dry_run():
    connector = FakeConnector()

    request = ToolRequest(
        request_id="req_002",
        tool="connector-fake",
        action="fake.delete",
        input={"file_id": "file_123"},
        context=ToolContext(task_id="t1", step_id="s2"),
        idempotency_key="hash_456",
        dry_run=True,
    )

    response = await connector.execute(request)
    assert response.success is True
    assert response.data["simulated"] is True
    assert response.data["would_affect"] == {"file_id": "file_123"}


@pytest.mark.asyncio
async def test_fake_connector_error_injection():
    injected_err = ToolError(
        error_class=ErrorClass.RATE_LIMITED,
        message="Too many requests",
        retryable=True,
        retry_after_s=5,
    )
    connector = FakeConnector(injected_errors={"fake.write": injected_err})

    request = ToolRequest(
        request_id="req_003",
        tool="connector-fake",
        action="fake.write",
        input={"title": "Retry me"},
        context=ToolContext(task_id="t1", step_id="s3"),
        idempotency_key="hash_789",
    )

    response = await connector.execute(request)
    assert response.success is False
    assert response.error is not None
    assert response.error.error_class == ErrorClass.RATE_LIMITED
    assert response.error.retryable is True

    # Next attempt should succeed because error was popped
    retry_response = await connector.execute(request)
    assert retry_response.success is True
