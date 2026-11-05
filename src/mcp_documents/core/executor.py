import sys
from typing import Any

import structlog

from ..tools.encrypt_tool import EncryptTool
from ..tools.markitdown_tool import MarkitdownTool
from ..tools.ppt_master_tool import PptMasterTool
from ..tools.read_tool import ReadTool
from ..tools.transform_tool import TransformTool
from ..tools.write_tool import WriteTool
from .tools import Tool

structlog.configure(
    logger_factory=structlog.PrintLoggerFactory(file=sys.stderr),
)

log = structlog.get_logger()

class ToolExecutor:
    def __init__(self):
        self._tools: dict[str, Tool] = {}
        self._register_default_tools()

    def _register_default_tools(self):
        self.register_tool(ReadTool())
        self.register_tool(WriteTool())
        self.register_tool(TransformTool())
        self.register_tool(EncryptTool())
        self.register_tool(PptMasterTool())
        self.register_tool(MarkitdownTool())

    def register_tool(self, tool: Tool):
        self._tools[tool.name] = tool
        log.info("tool_registered", tool_name=tool.name)

    async def execute(
        self,
        platform_or_tool: str,
        tool_name: str | None = None,
        params: dict[str, Any] | None = None,
        **kwargs: Any
    ) -> dict[str, Any]:
        if tool_name is None:
            # Invocación directa: execute(tool_name, params)
            target_tool = platform_or_tool
            target_params = params or kwargs or {}
        else:
            # Invocación con plataforma: execute(platform, tool_name, params)
            target_tool = tool_name
            target_params = params or kwargs or {}

        if target_tool not in self._tools:
            return {
                "success": False,
                "error": f"Tool '{target_tool}' not found."
            }

        tool = self._tools[target_tool]
        return await tool.execute_with_timing(target_params)

    def get_schemas(self, platform: str) -> list[dict[str, Any]]:
        return [tool.to_schema(platform) for tool in self._tools.values()]
