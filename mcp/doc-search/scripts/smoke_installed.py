"""Smoke-test an installed console script from outside the checkout.

Usage: python smoke_installed.py /path/to/taskflow-doc-search /path/to/workspace
The interpreter running this client needs the base MCP dependencies.
"""
import asyncio
import os
from pathlib import Path
import sys

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


async def main():
    executable = str(Path(sys.argv[1]).resolve())
    workspace = str(Path(sys.argv[2]).resolve())
    params = StdioServerParameters(
        command=executable,
        env={**os.environ, "AI_WORKSPACE_ROOT": workspace},
    )
    async with stdio_client(params) as (reader, writer):
        async with ClientSession(reader, writer) as client:
            initialized = await client.initialize()
            tools = await client.list_tools()
            names = {tool.name for tool in tools.tools}
            expected = {
                "search_docs", "search_docs_semantic", "search_docs_embeddings",
                "get_doc", "list_tickets", "propose_ticket",
            }
            assert names == expected, names
            result = (await client.call_tool("search_docs", {"query": "TaskFlow"})).model_dump(by_alias=True)
            assert not result.get("isError", False), result
            assert result["structuredContent"], result
            hits = result["structuredContent"].get("result", [])
            assert hits, "Expected TaskFlow documentation in the workspace"
            for name, arguments in [
                ("search_docs_semantic", {"query": "TaskFlow"}),
                ("get_doc", {"path": hits[0]["path"]}),
                ("list_tickets", {}),
                # Exercise the optional tool without downloading a model or
                # changing the workspace's existing embeddings cache.
                ("search_docs_embeddings", {"query": "!!!"}),
            ]:
                response = (await client.call_tool(name, arguments)).model_dump(by_alias=True)
                assert not response.get("isError", False), response
                print(name + ": OK")
            print("Initialized:", initialized.model_dump(by_alias=True)["serverInfo"]["name"])
            print("Tools:", ", ".join(sorted(names)))
            print("search_docs:", result["structuredContent"])


if __name__ == "__main__":
    asyncio.run(main())
