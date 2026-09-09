from pydantic import BaseModel
from typing import Any, Optional

class APIResponse(BaseModel):
    ok: bool
    data: Any = None
    error: Optional[dict] = None  # {code, message, details}
    trace_id: Optional[str] = None

class ErrorDetail(BaseModel):
    code: str
    message: str
    details: Optional[Any] = None
