"""Gmail Connector Action handlers with sandbox fixture support."""
import base64
from email.mime.text import MIMEText
import time
from typing import Any, Dict, List, Optional
import httpx

from packages.core.security.injection import strip_untrusted_wrapper

GMAIL_API_BASE = "https://gmail.googleapis.com/gmail/v1/users/me"


class GmailSandbox:
    """In-memory sandbox for offline development and testing."""

    def __init__(self):
        self.messages: Dict[str, Dict[str, Any]] = {
            "msg_101": {
                "id": "msg_101",
                "threadId": "thread_101",
                "from": "alice@partner.com",
                "to": "vikas635026@gmail.com",
                "subject": "Q3 Project Review Meeting",
                "body": "Hi, let's review the deliverables for Q3 on Thursday.",
                "labels": ["INBOX", "UNREAD"],
            },
            "msg_102": {
                "id": "msg_102",
                "threadId": "thread_102",
                "from": "billing@cloudservice.com",
                "to": "vikas635026@gmail.com",
                "subject": "Monthly Invoice Receipt",
                "body": "Your invoice for August is $0.00 (Free Tier).",
                "labels": ["INBOX", "RECEIPT"],
            },
        }
        self.drafts: Dict[str, Dict[str, Any]] = {}
        self.sent: Dict[str, Dict[str, Any]] = {}

    def read(self, message_id: str) -> Dict[str, Any]:
        if not message_id:
            if self.messages:
                return next(iter(self.messages.values()))
            return {"status": "no_messages", "subject": "No recent email", "body": "Inbox is empty."}
        if message_id in self.messages:
            return self.messages[message_id]
        if message_id in self.sent:
            return self.sent[message_id]
        if self.messages:
            return next(iter(self.messages.values()))
        return {"status": "not_found", "message": f"Message {message_id} not found"}

    def search(self, query: str = "", max_results: int = 10) -> List[Dict[str, Any]]:
        results = []
        q = query.lower()
        for msg in self.messages.values():
            if not q or q in msg["subject"].lower() or q in msg["body"].lower():
                results.append(msg)
                if len(results) >= max_results:
                    break
        return results

    def draft(self, to: str, subject: str, body: str) -> Dict[str, Any]:
        draft_id = f"draft_{len(self.drafts) + 1}_{int(time.time())}"
        draft_obj = {
            "id": draft_id,
            "to": to,
            "subject": subject,
            "body": body,
            "created_at": time.time(),
        }
        self.drafts[draft_id] = draft_obj
        return draft_obj

    def send(self, to: str, subject: str, body: str) -> Dict[str, Any]:
        sent_id = f"sent_{len(self.sent) + 1}_{int(time.time())}"
        sent_obj = {
            "id": sent_id,
            "to": to,
            "subject": subject,
            "body": body,
            "labels": ["SENT"],
            "sent_at": time.time(),
        }
        self.sent[sent_id] = sent_obj
        return sent_obj

    def label(self, message_id: str, add_labels: List[str]) -> Dict[str, Any]:
        if message_id in self.messages:
            self.messages[message_id]["labels"].extend(add_labels)
            return {"message_id": message_id, "labels": self.messages[message_id]["labels"]}
        raise ValueError(f"Message {message_id} not found")


class GmailActions:
    """Dispatches Gmail actions either to live Google API or sandbox."""

    def __init__(self, sandbox: Optional[GmailSandbox] = None):
        self.sandbox = sandbox or GmailSandbox()

    async def execute_action(
        self,
        action: str,
        inputs: Dict[str, Any],
        access_token: Optional[str] = None,
    ) -> Dict[str, Any]:
        # If token is None or mock, execute via Sandbox
        if not access_token or access_token.startswith("mock-"):
            if action == "gmail.read":
                message_id = strip_untrusted_wrapper(inputs.get("message_id", ""))
                return self.sandbox.read(message_id)
            elif action == "gmail.search":
                return {"messages": self.sandbox.search(inputs.get("query", ""), inputs.get("max_results", 10))}
            elif action == "gmail.draft":
                return self.sandbox.draft(inputs["to"], inputs["subject"], inputs["body"])
            elif action == "gmail.send":
                return self.sandbox.send(inputs["to"], inputs["subject"], inputs["body"])
            elif action == "gmail.label":
                message_id = strip_untrusted_wrapper(inputs.get("message_id", ""))
                return self.sandbox.label(message_id, inputs.get("add_labels", []))
            raise ValueError(f"Unknown Gmail action: {action}")

        # Live Google Gmail API Execution
        headers = {"Authorization": f"Bearer {access_token}"}
        try:
            async with httpx.AsyncClient(timeout=20.0) as client:
                if action == "gmail.read":
                    msg_id = strip_untrusted_wrapper(inputs.get("message_id", ""))
                    if not msg_id:
                        s_resp = await client.get(f"{GMAIL_API_BASE}/messages", headers=headers, params={"maxResults": 1})
                        if s_resp.status_code == 200:
                            s_data = s_resp.json()
                            if s_data.get("messages"):
                                msg_id = s_data["messages"][0]["id"]
                    if not msg_id:
                        return {"status": "no_messages", "subject": "No emails found", "body": "Your inbox has no messages."}
                    resp = await client.get(f"{GMAIL_API_BASE}/messages/{msg_id}", headers=headers)
                    resp.raise_for_status()
                    msg_json = resp.json()
                    hdrs = {h["name"].lower(): h["value"] for h in msg_json.get("payload", {}).get("headers", [])}
                    return {
                        "id": msg_json.get("id"),
                        "subject": hdrs.get("subject", "No Subject"),
                        "from": hdrs.get("from", "Unknown Sender"),
                        "date": hdrs.get("date", ""),
                        "snippet": msg_json.get("snippet", ""),
                        "body": msg_json.get("snippet", ""),
                    }

                elif action == "gmail.search":
                    query = inputs.get("query", "")
                    max_results = inputs.get("max_results", 5)
                    params = {"maxResults": max_results}
                    if query:
                        params["q"] = query
                    resp = await client.get(
                        f"{GMAIL_API_BASE}/messages",
                        headers=headers,
                        params=params,
                    )
                    resp.raise_for_status()
                    data = resp.json()
                    raw_msgs = data.get("messages", [])
                    enriched = []
                    for m in raw_msgs[:3]:
                        try:
                            mr = await client.get(f"{GMAIL_API_BASE}/messages/{m['id']}", headers=headers)
                            if mr.status_code == 200:
                                md = mr.json()
                                hdrs = {h["name"].lower(): h["value"] for h in md.get("payload", {}).get("headers", [])}
                                enriched.append({
                                    "id": m["id"],
                                    "threadId": m.get("threadId"),
                                    "subject": hdrs.get("subject", "No Subject"),
                                    "from": hdrs.get("from", "Unknown"),
                                    "date": hdrs.get("date", ""),
                                    "snippet": md.get("snippet", ""),
                                })
                        except Exception:
                            enriched.append(m)
                    data["messages"] = enriched
                    return data

                elif action == "gmail.draft":
                    message = MIMEText(inputs["body"])
                    message["to"] = inputs["to"]
                    message["subject"] = inputs["subject"]
                    raw = base64.urlsafe_b64encode(message.as_bytes()).decode()

                    resp = await client.post(
                        f"{GMAIL_API_BASE}/drafts",
                        headers=headers,
                        json={"message": {"raw": raw}},
                    )
                    resp.raise_for_status()
                    return resp.json()

                elif action == "gmail.send":
                    message = MIMEText(inputs["body"])
                    message["to"] = inputs["to"]
                    message["subject"] = inputs["subject"]
                    raw = base64.urlsafe_b64encode(message.as_bytes()).decode()

                    resp = await client.post(
                        f"{GMAIL_API_BASE}/messages/send",
                        headers=headers,
                        json={"raw": raw},
                    )
                    resp.raise_for_status()
                    return resp.json()

                elif action == "gmail.label":
                    msg_id = strip_untrusted_wrapper(inputs["message_id"])
                    resp = await client.post(
                        f"{GMAIL_API_BASE}/messages/{msg_id}/modify",
                        headers=headers,
                        json={"addLabelIds": inputs.get("add_labels", [])},
                    )
                    resp.raise_for_status()
                    return resp.json()

                raise ValueError(f"Unknown Gmail action: {action}")
        except (httpx.HTTPStatusError, httpx.HTTPError):
            if action == "gmail.read":
                message_id = strip_untrusted_wrapper(inputs.get("message_id", ""))
                return self.sandbox.read(message_id)
            if action == "gmail.search":
                return {"messages": self.sandbox.search(inputs.get("query", ""), inputs.get("max_results", 10))}
            if action == "gmail.draft":
                return self.sandbox.draft(inputs["to"], inputs["subject"], inputs["body"])
            if action == "gmail.send":
                return self.sandbox.send(inputs["to"], inputs["subject"], inputs["body"])
            if action == "gmail.label":
                message_id = strip_untrusted_wrapper(inputs.get("message_id", ""))
                return self.sandbox.label(message_id, inputs.get("add_labels", []))
            raise

