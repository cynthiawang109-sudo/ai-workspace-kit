# mcp/ — custom MCP servers

This folder will hold the workspace's own MCP server, built in milestone M2:

**doc-search** (Python, FastMCP, stdio) — tools over the workspace's local
documentation and ticket data:

- `search_docs(query)` — keyword search across the documentation repos under
  `projects/` (title + heading + body hits, ranked)
- `get_doc(path)` — fetch one document by workspace-relative path
- `list_tickets(status?)` — list the demo tickets in `tickets/` (Markdown
  files standing in for an issue tracker)

Design constraints:

- Read-only. Writes to real trackers go through the draft-first governance in
  the root `AGENTS.md`, never through this server.
- No credentials needed: all data sources are local files.
- Protocol-level MCP: the same server registers in Codex
  (`.codex/config.toml`), Claude Code (`.mcp.json`), or any other MCP client.
