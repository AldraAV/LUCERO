from typing import Any

import structlog
from fastapi import APIRouter, Body, HTTPException

from ...core.executor import ToolExecutor
from ...schemas import ToolResponse

router = APIRouter()
executor = ToolExecutor()

log = structlog.get_logger()

@router.post("/execute", response_model=ToolResponse)
async def execute_tool(
    platform: str,
    tool_name: str,
    params: dict[str, Any] = Body(...)
):
    """Execute a tool on the specified platform."""
    
    try:
        result = await executor.execute(
            platform=platform,
            tool_name=tool_name,
            params=params
        )
        
        return ToolResponse(
            success=result.get("success", False),
            data=result.get("data", {}),
            error=result.get("error"),
            elapsed_ms=result.get("elapsed_ms", 0.0)
        )
    
    except Exception as e:
        log.error("execute_error", error=str(e), tool=tool_name)
        raise HTTPException(status_code=500, detail=str(e))
