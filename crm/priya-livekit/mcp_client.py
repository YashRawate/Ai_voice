"""
MCP Client Bridge for Priya LiveKit Voice Agent.

Manages connection to the Priya FastMCP Server using AsyncExitStack and executes tool calls over MCP.
"""
import sys
import os
import asyncio
import logging
from contextlib import AsyncExitStack
from typing import Any, Dict
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

logger = logging.getLogger("priya_mcp_client")

class MCPBridge:
    def __init__(self):
        self.session: ClientSession | None = None
        self._exit_stack: AsyncExitStack | None = None

    async def start(self):
        """Start the MCP server process and establish a Stdio ClientSession."""
        try:
            self._exit_stack = AsyncExitStack()
            server_script = os.path.join(os.path.dirname(__file__), "mcp_server.py")
            python_exe = sys.executable
            
            server_params = StdioServerParameters(
                command=python_exe,
                args=[server_script],
                env=None
            )
            
            read_stream, write_stream = await self._exit_stack.enter_async_context(
                stdio_client(server_params)
            )
            self.session = await self._exit_stack.enter_async_context(
                ClientSession(read_stream, write_stream)
            )
            await self.session.initialize()
            
            tools_result = await self.session.list_tools()
            tool_names = [t.name for t in tools_result.tools]
            logger.info(f"Connected to MCP Server successfully. Available tools: {tool_names}")
            return True
        except Exception as e:
            logger.warning(f"Failed to start MCP server bridge ({e}); fallback to direct calls enabled.")
            if self._exit_stack:
                await self._exit_stack.aclose()
                self._exit_stack = None
            self.session = None
            return False

    async def call_tool(self, tool_name: str, arguments: Dict[str, Any]) -> str:
        """Call an MCP tool and return the textual result."""
        if not self.session:
            return ""
        try:
            result = await self.session.call_tool(tool_name, arguments)
            if result and result.content:
                text_parts = [c.text for c in result.content if hasattr(c, "text")]
                return "\n".join(text_parts)
            return str(result)
        except Exception as e:
            logger.error(f"MCP tool call '{tool_name}' failed: {e}")
            return f"MCP tool error: {e}"

    async def close(self):
        """Close the MCP server connection cleanly."""
        if self._exit_stack:
            try:
                await self._exit_stack.aclose()
            except Exception:
                pass
            self._exit_stack = None
            self.session = None

# Global instance for the agent process
mcp_bridge = MCPBridge()
