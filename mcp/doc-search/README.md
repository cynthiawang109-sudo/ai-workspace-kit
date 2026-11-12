# doc-search MCP server

A small, read-only [MCP](https://modelcontextprotocol.io) server written with
FastMCP. It gives an AI coding agent structured access to this workspace's
documentation and demo tickets — the local, public stand-in for the
Jira/Confluence side of the original production workspace.

## Tools

| Tool | What it does |
|---|---|
| `search_docs(query, limit=8)` | Keyword search across every Markdown doc under `projects/`; title hits ×3, heading hits ×2, body hits ×1; returns path, title, score, snippet |
| `search_docs_semantic(query, limit=8)` | TF-IDF vector-space search over the same corpus (cosine similarity); returns path, title, score (0–1), snippet |
| `get_doc(path)` | Fetch one document by workspace-relative path (only `projects/` and `tickets/` are readable) |
| `list_tickets(status?)` | List demo tickets from `tickets/*.md` front matter, optionally filtered by status |

## Keyword vs. semantic search

The two search tools are kept side by side on purpose:

- `search_docs` counts exact term hits with hand-set weights. It is
  predictable and great for known terms ("health", an error code, a
  ticket id) — but a document that repeats a common term many times can
  outrank the topically closest one.
- `search_docs_semantic` treats each document as a TF-IDF vector and
  ranks by cosine similarity to the query vector. Terms that appear in
  many documents are down-weighted by the IDF factor, so multi-term,
  natural-language questions rank by overall topical closeness.

Both are bag-of-words models: neither understands synonyms. The semantic
tool exists to show the classic vector-space step of the retrieval
ladder (and where its limits are) with zero dependencies — pure stdlib,
re-indexed per call, which is fine at documentation-repo scale.

Design points worth noting:

- **Read-only by construction** — there is no write tool; outward writes in
  this workspace go through the draft-first rule in the root `AGENTS.md`.
- **No credentials, no network** — data sources are local files only.
- **Client-agnostic** — plain MCP over stdio; registers the same way in
  Codex, Claude Code, or any other MCP client.

## Setup

```powershell
cd mcp\doc-search
python -m venv .venv
.venv\Scripts\python -m pip install -r requirements.txt pytest
```

## Run the tests

```powershell
.venv\Scripts\python -m pytest
```

The tests build a throwaway fixture workspace, so they pass whether or not
`sync` has populated `projects/`.

## Register it

**Codex** — add to `~/.codex/config.toml`:

```toml
[mcp_servers.doc-search]
command = 'C:\path\to\ai-workspace-kit\mcp\doc-search\.venv\Scripts\python.exe'
args = ['C:\path\to\ai-workspace-kit\mcp\doc-search\server.py']
```

**Claude Code**:

```powershell
claude mcp add doc-search -- C:\path\to\ai-workspace-kit\mcp\doc-search\.venv\Scripts\python.exe C:\path\to\ai-workspace-kit\mcp\doc-search\server.py
```

The server finds the workspace root from its own location
(`<root>/mcp/doc-search/server.py`); set `AI_WORKSPACE_ROOT` to override.
