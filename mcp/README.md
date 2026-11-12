# mcp/ — custom MCP servers

## doc-search (milestone M2)

The workspace's own MCP server — see [`doc-search/`](doc-search/) for code,
tests, and setup. Python + FastMCP, stdio, read-only:

- `search_docs(query)` — keyword search across the documentation repos under
  `projects/` (title/heading/body weighted ranking)
- `get_doc(path)` — fetch one document by workspace-relative path
- `list_tickets(status?)` — list the demo tickets in the root `tickets/`
  folder (Markdown files standing in for an issue tracker)

In the production workspace this recreates, this slot was an off-the-shelf
server wired to internal Jira/Confluence. Here the server is hand-written and
the data sources are local files — same architectural position, everything
public and runnable.
