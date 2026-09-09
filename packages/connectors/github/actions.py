"""GitHub Action handlers with sandbox fixture support."""
import time
from typing import Any, Dict, List, Optional
import httpx

GITHUB_API_BASE = "https://api.github.com"


class GitHubSandbox:
    """In-memory GitHub sandbox for offline development and unit tests."""

    def __init__(self):
        self.issues: Dict[str, List[Dict[str, Any]]] = {
            "owner/omnibrain": [
                {
                    "id": 101,
                    "number": 1,
                    "title": "feat: add webhook integration",
                    "body": "Add support for incoming external webhooks.",
                    "state": "open",
                    "labels": [{"name": "enhancement"}],
                    "created_at": "2026-09-08T09:00:00Z",
                },
                {
                    "id": 102,
                    "number": 2,
                    "title": "bug: latency spike in vector query",
                    "body": "Investigate pgvector indexing parameters.",
                    "state": "open",
                    "labels": [{"name": "bug"}],
                    "created_at": "2026-09-08T10:00:00Z",
                },
            ]
        }
        self.pull_requests: Dict[str, List[Dict[str, Any]]] = {
            "owner/omnibrain": [
                {
                    "id": 201,
                    "number": 3,
                    "title": "refactor: modularize worker pipelines",
                    "state": "open",
                    "user": {"login": "lead-dev"},
                    "created_at": "2026-09-08T11:00:00Z",
                }
            ]
        }

    def list_issues(self, repo: str = "owner/omnibrain", state: str = "open") -> List[Dict[str, Any]]:
        repo_issues = self.issues.get(repo, [])
        return [i for i in repo_issues if state == "all" or i.get("state") == state]

    def create_issue(
        self,
        repo: str = "owner/omnibrain",
        title: str = "New Issue",
        body: str = "",
        labels: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        repo_issues = self.issues.setdefault(repo, [])
        issue_no = len(repo_issues) + 1
        issue_obj = {
            "id": int(time.time()),
            "number": issue_no,
            "title": title,
            "body": body,
            "state": "open",
            "labels": [{"name": l} for l in (labels or [])],
            "created_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        }
        repo_issues.append(issue_obj)
        return issue_obj

    def list_pull_requests(self, repo: str = "owner/omnibrain", state: str = "open") -> List[Dict[str, Any]]:
        repo_prs = self.pull_requests.get(repo, [])
        return [p for p in repo_prs if state == "all" or p.get("state") == state]


class GitHubActions:
    """Dispatches GitHub actions to live API or sandbox."""

    def __init__(self, sandbox: Optional[GitHubSandbox] = None):
        self.sandbox = sandbox or GitHubSandbox()

    async def execute_action(
        self,
        action: str,
        inputs: Dict[str, Any],
        access_token: Optional[str] = None,
    ) -> Any:
        # If no access token or mock token, use sandbox
        if not access_token or access_token.startswith("mock-"):
            if action == "github.list_issues":
                return self.sandbox.list_issues(
                    repo=inputs.get("repo", "owner/omnibrain"),
                    state=inputs.get("state", "open"),
                )
            elif action == "github.create_issue":
                return self.sandbox.create_issue(
                    repo=inputs.get("repo", "owner/omnibrain"),
                    title=inputs.get("title", "Untitled Issue"),
                    body=inputs.get("body", ""),
                    labels=inputs.get("labels", []),
                )
            elif action == "github.list_prs":
                return self.sandbox.list_pull_requests(
                    repo=inputs.get("repo", "owner/omnibrain"),
                    state=inputs.get("state", "open"),
                )
            else:
                raise ValueError(f"Unsupported GitHub action: {action}")

        # Live GitHub API execution
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Accept": "application/vnd.github+json",
            "User-Agent": "OmniBrain-Assistant",
        }
        async with httpx.AsyncClient(timeout=15.0) as client:
            repo = inputs.get("repo", "owner/omnibrain")
            if action == "github.list_issues":
                state = inputs.get("state", "open")
                resp = await client.get(
                    f"{GITHUB_API_BASE}/repos/{repo}/issues?state={state}",
                    headers=headers,
                )
                resp.raise_for_status()
                return resp.json()
            elif action == "github.create_issue":
                payload = {
                    "title": inputs.get("title"),
                    "body": inputs.get("body", ""),
                    "labels": inputs.get("labels", []),
                }
                resp = await client.post(
                    f"{GITHUB_API_BASE}/repos/{repo}/issues",
                    headers=headers,
                    json=payload,
                )
                resp.raise_for_status()
                return resp.json()
            elif action == "github.list_prs":
                state = inputs.get("state", "open")
                resp = await client.get(
                    f"{GITHUB_API_BASE}/repos/{repo}/pulls?state={state}",
                    headers=headers,
                )
                resp.raise_for_status()
                return resp.json()
            else:
                raise ValueError(f"Unsupported GitHub action: {action}")

