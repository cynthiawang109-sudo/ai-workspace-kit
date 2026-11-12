"""Manual smoke test over real stdio transport.

Starts server.py as a subprocess the same way an MCP client would, lists
its tools, and calls each one against the real workspace. Run after setup:

    .venv\\Scripts\\python scripts\\smoke_test.py
"""
import asyncio
import sys
from pathlib import Path

from fastmcp import Client
from fastmcp.client.transports import StdioTransport

HERE = Path(__file__).resolve().parents[1]


async def main() -> None:
    transport = StdioTransport(
        command=sys.executable,
        args=[str(HERE / "server.py")],
    )
    async with Client(transport) as client:
        tools = await client.list_tools()
        print("tools:", [t.name for t in tools])

        hits = await client.call_tool("search_docs", {"query": "health"})
        print("search_docs('health') ->")
        for h in hits.data:
            print(f"  {h['score']:>3}  {h['path']}")

        tickets = await client.call_tool("list_tickets", {"status": "open"})
        print("list_tickets(status='open') ->", [t["id"] for t in tickets.data])

        doc = await client.call_tool(
            "get_doc", {"path": "projects/taskflow-docs/system-overview.md"}
        )
        print("get_doc(system-overview) ->", len(doc.data), "chars")


if __name__ == "__main__":
    asyncio.run(main())
