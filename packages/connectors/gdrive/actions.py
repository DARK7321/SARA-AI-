"""Google Drive Action handlers with sandbox fixture support."""
import time
from typing import Any, Dict, List, Optional
import httpx

GDRIVE_API_BASE = "https://www.googleapis.com/drive/v3/files"


class GDriveSandbox:
    """In-memory Google Drive sandbox for development and testing."""

    def __init__(self):
        self.files: Dict[str, Dict[str, Any]] = {
            "file_101": {
                "id": "file_101",
                "name": "Project Roadmap 2026.docx",
                "mimeType": "application/vnd.google-apps.document",
                "content": "OmniBrain architecture roadmap and milestones.",
                "shared_with": [],
            },
            "file_102": {
                "id": "file_102",
                "name": "Expenses August 2026.xlsx",
                "mimeType": "application/vnd.google-apps.spreadsheet",
                "content": "Spreadsheet expense data.",
                "shared_with": [],
            },
        }

    def list_files(self, query: str = "", max_results: int = 20) -> List[Dict[str, Any]]:
        results = []
        q = query.lower()
        for f in self.files.values():
            if not q or q in f["name"].lower():
                results.append(f)
                if len(results) >= max_results:
                    break
        return results

    def read_file(self, file_id: str) -> Dict[str, Any]:
        if file_id in self.files:
            return self.files[file_id]
        raise ValueError(f"File {file_id} not found in Google Drive")

    def create_file(self, name: str, mime_type: str = "text/plain", content: str = "") -> Dict[str, Any]:
        file_id = f"file_{len(self.files) + 1}_{int(time.time())}"
        file_obj = {
            "id": file_id,
            "name": name,
            "mimeType": mime_type,
            "content": content,
            "created_at": time.time(),
            "shared_with": [],
        }
        self.files[file_id] = file_obj
        return file_obj

    def share_file(self, file_id: str, email: str, role: str = "reader") -> Dict[str, Any]:
        if file_id in self.files:
            share_record = {"email": email, "role": role}
            self.files[file_id]["shared_with"].append(share_record)
            return {"file_id": file_id, "shared": True, "permission": share_record}
        raise ValueError(f"File {file_id} not found in Google Drive")


class GDriveActions:
    """Dispatches Google Drive actions either to live Google API or sandbox."""

    def __init__(self, sandbox: Optional[GDriveSandbox] = None):
        self.sandbox = sandbox or GDriveSandbox()

    async def execute_action(
        self,
        action: str,
        inputs: Dict[str, Any],
        access_token: Optional[str] = None,
    ) -> Dict[str, Any]:
        # If token is None or mock, execute via Sandbox
        if not access_token or access_token.startswith("mock-"):
            if action == "drive.list":
                return {"files": self.sandbox.list_files(inputs.get("query", ""), inputs.get("max_results", 20))}
            elif action == "drive.read":
                return self.sandbox.read_file(inputs["file_id"])
            elif action == "drive.create":
                return self.sandbox.create_file(inputs["name"], inputs.get("mime_type", "text/plain"), inputs.get("content", ""))
            elif action == "drive.share":
                return self.sandbox.share_file(inputs["file_id"], inputs["email"], inputs.get("role", "reader"))
            raise ValueError(f"Unknown Drive action: {action}")

        # Live Google Drive API Execution
        headers = {"Authorization": f"Bearer {access_token}"}
        async with httpx.AsyncClient(timeout=20.0) as client:
            if action == "drive.list":
                resp = await client.get(
                    GDRIVE_API_BASE,
                    headers=headers,
                    params={"pageSize": inputs.get("max_results", 20), "q": inputs.get("query", "")},
                )
                resp.raise_for_status()
                return resp.json()

            elif action == "drive.read":
                file_id = inputs["file_id"]
                resp = await client.get(f"{GDRIVE_API_BASE}/{file_id}?fields=id,name,mimeType", headers=headers)
                resp.raise_for_status()
                return resp.json()

            elif action == "drive.create":
                metadata = {"name": inputs["name"], "mimeType": inputs.get("mime_type", "text/plain")}
                resp = await client.post(GDRIVE_API_BASE, headers=headers, json=metadata)
                resp.raise_for_status()
                return resp.json()

            elif action == "drive.share":
                file_id = inputs["file_id"]
                perm = {"type": "user", "role": inputs.get("role", "reader"), "emailAddress": inputs["email"]}
                resp = await client.post(f"{GDRIVE_API_BASE}/{file_id}/permissions", headers=headers, json=perm)
                resp.raise_for_status()
                return resp.json()

            raise ValueError(f"Unknown Drive action: {action}")

