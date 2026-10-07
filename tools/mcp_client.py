"""Small synchronous client: starts the MCP search server and calls one tool."""
import asyncio
import json
import sys
from pathlib import Path

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

SERVER = Path(__file__).resolve().parent.parent / "mcp_server" / "search_server.py"


class SearchClient:
    def __init__(self, db_path):
        self.db_path = str(Path(db_path).resolve())

    async def _call(self, name, args):
        params = StdioServerParameters(
            command=sys.executable,
            args=[str(SERVER)],
            env={"SYNTHESIS_DB": self.db_path},
        )
        async with stdio_client(params) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                result = await session.call_tool(name, args)
        text = result.content[0].text if result.content else ""
        if result.isError:
            raise RuntimeError(f"MCP tool {name} failed: {text}")
        return json.loads(text)

    def call(self, name, **args):
        return asyncio.run(self._call(name, args))