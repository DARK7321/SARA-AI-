"""Model Context Protocol (MCP) Action handlers with sandbox fixture support."""
import json
import time
from typing import Any, Dict, List, Optional
import httpx


class MCPSandbox:
    """In-memory MCP sandbox simulating standard MCP tool servers."""

    def __init__(self):
        self.files: Dict[str, str] = {
            "README.md": "# OmniBrain Project\nAutonomous Personal AI Operating System.",
            "config/settings.json": '{"theme": "dark", "version": "2.0"}',
            "data/metrics.csv": "timestamp,latency_ms,requests\n2026-09-08T10:00:00Z,42,120",
        }
        self.sqlite_tables: Dict[str, List[Dict[str, Any]]] = {
            "users": [
                {"id": 1, "username": "admin", "role": "owner"},
                {"id": 2, "username": "guest", "role": "viewer"},
            ],
            "audit_logs": [
                {"id": 101, "event": "LOGIN_SUCCESS", "timestamp": "2026-09-08T09:00:00Z"},
            ],
        }

    def read_file(self, path: str) -> Dict[str, Any]:
        content = self.files.get(path, f"Simulated content of {path}")
        return {
            "path": path,
            "content": content,
            "size_bytes": len(content.encode("utf-8")),
        }

    def list_dir(self, directory: str = ".") -> Dict[str, Any]:
        return {
            "directory": directory,
            "entries": list(self.files.keys()),
            "total": len(self.files),
        }

    def sqlite_query(self, query: str) -> Dict[str, Any]:
        return {
            "query": query,
            "rows": self.sqlite_tables.get("users", []),
            "row_count": len(self.sqlite_tables.get("users", [])),
        }

    def fetch_url(self, url: str) -> Dict[str, Any]:
        return {
            "url": url,
            "status": 200,
            "body": f"Mock MCP fetch response from {url}",
        }


class MCPActions:
    """Dispatches MCP tool calls to live JSON-RPC server or sandbox."""

    def __init__(self, sandbox: Optional[MCPSandbox] = None):
        self.sandbox = sandbox or MCPSandbox()

    async def execute_action(
        self,
        action: str,
        inputs: Dict[str, Any],
        server_url: Optional[str] = None,
    ) -> Dict[str, Any]:
        # Offline sandbox fallback
        if not server_url or server_url.startswith(("mock-", "sandbox")):
            if action == "mcp.filesystem.read_file":
                return self.sandbox.read_file(path=inputs.get("path", "README.md"))
            elif action == "mcp.filesystem.list_dir":
                return self.sandbox.list_dir(directory=inputs.get("directory", "."))
            elif action == "mcp.sqlite.query":
                return self.sandbox.sqlite_query(query=inputs.get("query", "SELECT 1"))
            elif action == "mcp.fetch.get":
                return self.sandbox.fetch_url(url=inputs.get("url", "https://example.com"))
            else:
                return {
                    "action": action,
                    "simulated": True,
                    "inputs": inputs,
                }

        # Live JSON-RPC MCP Server invocation
        headers = {"Content-Type": "application/json"}
        json_rpc_payload = {
            "jsonrpc": "2.0",
            "id": int(time.time()),
            "method": "tools/call",
            "params": {
                "name": action.replace("mcp.", ""),
                "arguments": inputs,
            },
        }

        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.post(server_url, json=json_rpc_payload, headers=headers)
            resp.raise_for_status()
            res_json = resp.json()
            if "error" in res_json:
                raise ValueError(f"MCP Server Error: {res_json['error']}")
            return res_json.get("result", {})

