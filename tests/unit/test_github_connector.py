"""Unit tests for GitHub Universal Tool Connector."""
import pytest
from packages.connectors.github.client import GitHubConnector
from packages.connectors._sdk.contract import ToolRequest, ToolContext


@pytest.mark.asyncio
async def test_github_list_issues():
    connector = GitHubConnector()
    req = ToolRequest(
        request_id="req_gh_1",
        tool="connector-github",
        action="github.list_issues",
        input={"repo": "owner/omnibrain", "state": "open"},
        context=ToolContext(task_id="t_gh", step_id="s_gh1"),
        idempotency_key="key_gh_1",
    )
    res = await connector.execute(req)
    assert res.success is True
    assert "issues" in res.data
    assert len(res.data["issues"]) >= 1
    assert "title" in res.data["issues"][0]


@pytest.mark.asyncio
async def test_github_create_issue_and_verify():
    connector = GitHubConnector()
    req = ToolRequest(
        request_id="req_gh_2",
        tool="connector-github",
        action="github.create_issue",
        input={"repo": "owner/omnibrain", "title": "New Bug Report", "body": "Found issue in worker."},
        context=ToolContext(task_id="t_gh", step_id="s_gh2"),
        idempotency_key="key_gh_2",
    )
    res = await connector.execute(req)
    assert res.success is True
    assert res.data["title"] == "New Bug Report"
    assert res.data["number"] > 0
    assert res.verification_hints["check"] == "issue_created"

    # Verify post-condition
    verified = await connector.verify(req.action, res.data)
    assert verified is True


@pytest.mark.asyncio
async def test_github_list_prs():
    connector = GitHubConnector()
    req = ToolRequest(
        request_id="req_gh_3",
        tool="connector-github",
        action="github.list_prs",
        input={"repo": "owner/omnibrain", "state": "open"},
        context=ToolContext(task_id="t_gh", step_id="s_gh3"),
        idempotency_key="key_gh_3",
    )
    res = await connector.execute(req)
    assert res.success is True
    assert "pull_requests" in res.data
    assert len(res.data["pull_requests"]) >= 1


@pytest.mark.asyncio
async def test_github_dry_run():
    connector = GitHubConnector()
    req = ToolRequest(
        request_id="req_gh_4",
        tool="connector-github",
        action="github.create_issue",
        input={"repo": "owner/omnibrain", "title": "Dry run issue"},
        context=ToolContext(task_id="t_gh", step_id="s_gh4"),
        idempotency_key="key_gh_4",
        dry_run=True,
    )
    res = await connector.execute(req)
    assert res.success is True
    assert res.data["simulated"] is True
    assert res.verification_hints["dry_run"] is True
