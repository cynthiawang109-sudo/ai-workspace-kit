# doc-search MCP server

A small [MCP](https://modelcontextprotocol.io) server written with FastMCP.
It gives an AI coding agent structured access to this workspace's
documentation and demo tickets — the local, public stand-in for the
Jira/Confluence side of the original production workspace. Five tools are
annotated read-only (embeddings maintains a derived local cache); the sixth can only write ticket *drafts* (see below).

## Tools

| Tool | What it does |
|---|---|
| `search_docs(query, limit=8)` | Keyword search across every Markdown doc under `projects/`; title hits ×3, heading hits ×2, body hits ×1; returns path, title, score, snippet |
| `search_docs_semantic(query, limit=8)` | TF-IDF vector-space search over the same corpus (cosine similarity); returns path, title, score (0–1), snippet |
| `search_docs_embeddings(query, limit=8)` | Sentence embeddings over heading chunks; returns path, title, cosine score, snippet, heading; caches in `.index/` |
| `get_doc(path)` | Fetch one document by workspace-relative path (only `projects/` and `tickets/` are readable) |
| `list_tickets(status?)` | List the pre-TF-115 archive from `tickets/*.md` front matter, optionally filtered by status |
| `propose_ticket(title, body, priority="medium")` | Write a ticket **draft** to `tickets/drafts/draft-<slug>.md` — the server's only source-content write; it cannot create or modify real tickets |

## Draft-first writes

`propose_ticket` mirrors the production workspace's rule for outward
writes (there: Jira changes start as drafts a human approves). The
boundary is enforced by the tool, not by politeness: it writes only
new files under `tickets/drafts/`, always with `status: draft`, it
refuses to overwrite an existing draft, and it is annotated as a
write, so clients ask the user before calling it. `tickets/` is the pre-TF-115
archive; `list_tickets` never shows drafts as tickets. A human reviews and
promotes a draft with `scripts/promote-draft.ps1` (or `.sh`), which files
an Issue instead of moving the file into `tickets/`. Set `AI_WORKSPACE_PROJECT`
to the workspace Project number, or pass `-Project N` / `--project N`, to
also add the Issue to the board. Without a Project, the script prints the
Issue URL and notes that it was not added to a board. The draft is preserved.
The doc-search server stays credential-free and never calls GitHub.

## Three rungs of document search

1. `search_docs` counts exact term hits with title/heading/body weights.
   It is predictable for known terms, but repetition can dominate ranking.
2. `search_docs_semantic` uses TF-IDF cosine similarity over whole documents.
   It down-weights common terms and balances multi-term queries. Both of
   these first two rungs are bag-of-words models: neither understands synonyms.
   They use only the standard library and rebuild their vectors per call.
3. `search_docs_embeddings` uses sentence-transformers over ATX heading
   sections, embedding the document title, heading trail and body. It can
   retrieve paraphrases and synonyms, but relevance is model-dependent.
   Cosine ranking uses pure Python. A content-hash fingerprint invalidates
   the derived `.index/` cache when documents or the model change.

- **Local documents**: searches never modify the source documents. Embeddings
  writes a derived cache; `propose_ticket` writes drafts under the rules above.
- **No credentials**: keyword and TF-IDF need no network. Embeddings downloads
  its model once, then runs fully locally.
- **Client-agnostic**: plain MCP over stdio.

## Setup

```powershell
cd mcp\doc-search
python -m venv .venv
.venv\Scripts\python -m pip install -r requirements.txt pytest
```

Optional embeddings dependencies (includes torch):

```powershell
.venv\Scripts\python -m pip install -r requirements-embeddings.txt
```

`DOC_SEARCH_EMBEDDING_MODEL` overrides the default
`sentence-transformers/all-MiniLM-L6-v2`. `DOC_SEARCH_EMBEDDER=fake` selects
only a deterministic hashed-token test double, without semantic understanding.

Evaluate the synced corpus with `python scripts/run_eval.py`; add `--write`
to record the dated results in [EVAL.md](EVAL.md). The eval is not run in CI.

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
