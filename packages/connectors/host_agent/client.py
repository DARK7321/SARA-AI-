import os, jwt, time, httpx
from typing import Any, Dict, List
from packages.connectors._sdk.base import BaseConnector
from packages.connectors._sdk.contract import ToolRequest, ToolResponse, ToolMetadata, ToolError, ErrorClass

class HostAgentConnector(BaseConnector):
    def __init__(self):
        super().__init__(
            connector_id="connector-host-agent",
            name="Windows Host Agent",
            version="1.0"
        )
        self.secret = os.environ.get("OMNIBRAIN_HOST_JWT_SECRET", "OMNIBRAIN_HOST_JWT_SECRET_DEV_KEY")
        self.url = os.environ.get("HOST_AGENT_URL", "http://host.docker.internal:7788")

    def _token(self):
        return jwt.encode(
            {"aud": "host-agent", "iss": "omnibrain-api", "exp": int(time.time()) + 60},
            self.secret,
            algorithm="HS256"
        )

    async def execute(self, request: ToolRequest) -> ToolResponse:
        start_time = time.time()
        
        # Prepare the payload matching the host agent's ActionRequest schema
        action_payload = {
            "capability": request.action,
            **request.input
        }
        
        # If action is not in file_op, host.file_op needs to be mapped to the action field
        if request.action.startswith("host.file_op:"):
            parts = request.action.split(":")
            action_payload["capability"] = "host.file_op"
            action_payload["action"] = parts[1]

        req_payload = {
            "request_id": request.request_id,
            "task_id": request.context.task_id,
            "step_id": request.context.step_id,
            "idempotency_key": request.idempotency_key,
            "approval_id": request.authorization.approval_id,
            "action": action_payload
        }

        try:
            async with httpx.AsyncClient(timeout=25) as client:
                res = await client.post(
                    f"{self.url}/actions",
                    json=req_payload,
                    headers={"Authorization": f"Bearer {self._token()}"}
                )
                res.raise_for_status()
                data = res.json()
                
                latency = int((time.time() - start_time) * 1000)
                if data.get("success"):
                    return ToolResponse(
                        success=True,
                        data=data.get("data", {}),
                        metadata=ToolMetadata(latency_ms=latency)
                    )
                else:
                    err = data.get("error", {})
                    err_cls = ErrorClass.POLICY_DENIED if err.get("class") == "POLICY_DENIED" else ErrorClass.TOOL_UNAVAILABLE
                    return ToolResponse(
                        success=False,
                        error=ToolError(error_class=err_cls, message=err.get("message", "Unknown error")),
                        metadata=ToolMetadata(latency_ms=latency)
                    )
        except Exception as e:
            return ToolResponse(
                success=False,
                error=ToolError(error_class=ErrorClass.TOOL_UNAVAILABLE, message=str(e))
            )

