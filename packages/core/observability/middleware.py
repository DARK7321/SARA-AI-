import time
import uuid
import structlog
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware

class TraceIDMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        trace_id = str(uuid.uuid4())
        request.state.trace_id = trace_id
        
        logger = structlog.get_logger("api").bind(trace_id=trace_id)
        structlog.contextvars.bind_contextvars(trace_id=trace_id)
        
        start_time = time.time()
        
        response = await call_next(request)
        
        process_time_ms = (time.time() - start_time) * 1000
        response.headers["X-Trace-ID"] = trace_id
        
        logger.info(
            "request_completed",
            method=request.method,
            path=request.url.path,
            status_code=response.status_code,
            latency_ms=round(process_time_ms, 2)
        )
        
        return response
