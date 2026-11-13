"""doc-search — an MCP server for the ai-workspace-kit workspace.

Tools (all local files, no credentials; read-only except the last one):

- search_docs(query)   keyword search across the documentation repos that
                       sync checked out under projects/
- search_docs_semantic(query)
                       TF-IDF vector-space search over the same corpus
- get_doc(path)        fetch one document by workspace-relative path
- list_tickets(status) list the demo tickets stored as Markdown in tickets/
- propose_ticket(title, body)
                       write a ticket DRAFT under tickets/drafts/ — the
                       server's only write, draft-first by construction:
                       it can never create or modify a real ticket

Workspace root resolution: the AI_WORKSPACE_ROOT environment variable wins;
otherwise the server assumes it lives at <root>/mcp/doc-search/server.py.

Run (stdio):  python server.py
"""
import math
import os
import re
import sys
from collections import Counter
from pathlib import Path

from fastmcp import FastMCP


def _force_utf8_stdio() -> None:
    """Force UTF-8 on stdin/stdout/stderr.

    On Windows machines whose system locale is not UTF-8 (e.g. Chinese
    Windows defaults Python's stdio to GBK), a stdio MCP server otherwise
    emits non-UTF-8 bytes. Strict hosts (Codex's rmcp launcher) read the
    streams as UTF-8, fail to decode them, and tear the connection down
    during the initialize handshake. Pinning UTF-8 here makes the server
    behave identically on any locale. Clients can also set PYTHONUTF8=1
    in the server env; doing both is harmless.
    """
    for stream in (sys.stdin, sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure is not None:
            try:
                reconfigure(encoding="utf-8", errors="replace")
            except (ValueError, OSError):
                pass


_force_utf8_stdio()


def workspace_root() -> Path:
    env = os.environ.get("AI_WORKSPACE_ROOT")
    if env:
        return Path(env).resolve()
    return Path(__file__).resolve().parents[2]


ROOT = workspace_root()
PROJECTS_DIR = ROOT / "projects"
TICKETS_DIR = ROOT / "tickets"

mcp = FastMCP("doc-search")


def _iter_docs():
    if not PROJECTS_DIR.exists():
        return
    for p in sorted(PROJECTS_DIR.rglob("*.md")):
        if ".git" in p.parts:
            continue
        yield p


def _doc_title(text: str, path: Path) -> str:
    for line in text.splitlines():
        if line.startswith("# "):
            return line[2:].strip()
    return path.stem


# The search/read tools only read local files. Declaring that in the MCP
# annotations matters: clients such as Codex auto-approve read-only
# tools but stop un-annotated ones for manual approval (and refuse them
# outright in non-interactive runs).
READ_ONLY = {"readOnlyHint": True, "destructiveHint": False, "openWorldHint": False}

# The one write tool (propose_ticket) is annotated honestly as a write:
# clients will ask the user before running it, which is exactly the
# human-in-the-loop point of draft-first.
DRAFT_WRITE = {"readOnlyHint": False, "destructiveHint": False, "openWorldHint": False}


@mcp.tool(annotations=READ_ONLY)
def search_docs(query: str, limit: int = 8) -> list[dict]:
    """Keyword search over the workspace documentation repos.

    Ranking is deliberately simple and inspectable: a hit in a document
    title counts 3, in a heading 2, in body text 1. Returns workspace-
    relative path, title, score, and the first matching line as a snippet.
    """
    terms = [t for t in re.split(r"\W+", query.lower()) if t]
    if not terms:
        return []
    results = []
    for p in _iter_docs():
        text = p.read_text(encoding="utf-8", errors="replace")
        title = _doc_title(text, p)
        score = sum(3 * title.lower().count(t) for t in terms)
        snippet = ""
        for line in text.splitlines():
            low = line.lower()
            hits = sum(low.count(t) for t in terms)
            if not hits:
                continue
            score += 2 * hits if line.lstrip().startswith("#") else hits
            if not snippet:
                snippet = line.strip()[:200]
        if score:
            results.append(
                {
                    "path": p.relative_to(ROOT).as_posix(),
                    "title": title,
                    "score": score,
                    "snippet": snippet,
                }
            )
    results.sort(key=lambda r: (-r["score"], r["path"]))
    return results[:limit]


def _tokenize(text: str) -> list[str]:
    return [t for t in re.split(r"\W+", text.lower()) if t]


@mcp.tool(annotations=READ_ONLY)
def search_docs_semantic(query: str, limit: int = 8) -> list[dict]:
    """Vector-space (TF-IDF, cosine similarity) search over the docs.

    The contrast with search_docs is deliberate. Keyword search counts
    exact hits with hand-set weights (title x3, heading x2, body x1), so
    a document that repeats a common term many times can outrank the
    topically closest one. Here each document is a TF-IDF vector: terms
    that appear in many documents (low information) are down-weighted by
    the IDF factor, and ranking is by cosine similarity to the query
    vector, i.e. overall topical closeness across all query terms.

    It is still a bag-of-words model - no synonym or embedding magic.
    Pure stdlib; the corpus is re-indexed on every call, which is fine
    at documentation-repo scale and keeps the server stateless.
    """
    query_tokens = _tokenize(query)
    if not query_tokens:
        return []
    docs = []
    for p in _iter_docs():
        text = p.read_text(encoding="utf-8", errors="replace")
        docs.append((p, text, _tokenize(text)))
    if not docs:
        return []

    n = len(docs)
    doc_freq: Counter = Counter()
    for _, _, tokens in docs:
        doc_freq.update(set(tokens))
    idf = {t: math.log((n + 1) / (c + 1)) + 1.0 for t, c in doc_freq.items()}

    def vectorize(tokens: list[str]) -> dict[str, float]:
        counts = Counter(tokens)
        total = max(len(tokens), 1)
        return {t: (c / total) * idf[t] for t, c in counts.items() if t in idf}

    query_vec = vectorize(query_tokens)
    query_norm = math.sqrt(sum(v * v for v in query_vec.values()))
    if not query_norm:
        return []

    results = []
    for p, text, tokens in docs:
        doc_vec = vectorize(tokens)
        dot = sum(query_vec[t] * doc_vec.get(t, 0.0) for t in query_vec)
        doc_norm = math.sqrt(sum(v * v for v in doc_vec.values()))
        if not doc_norm or dot <= 0:
            continue
        snippet = ""
        terms = set(query_tokens)
        for line in text.splitlines():
            if terms & set(_tokenize(line)):
                snippet = line.strip()[:200]
                break
        results.append(
            {
                "path": p.relative_to(ROOT).as_posix(),
                "title": _doc_title(text, p),
                "score": round(dot / (query_norm * doc_norm), 4),
                "snippet": snippet,
            }
        )
    results.sort(key=lambda r: (-r["score"], r["path"]))
    return results[:limit]


@mcp.tool(annotations=READ_ONLY)
def get_doc(path: str) -> str:
    """Fetch one Markdown document by workspace-relative path, e.g.
    "projects/taskflow-docs/system-overview.md" or "tickets/TF-101.md".
    Paths outside projects/ and tickets/ are refused.
    """
    target = (ROOT / path).resolve()
    allowed = [PROJECTS_DIR.resolve(), TICKETS_DIR.resolve()]
    if (
        target.suffix != ".md"
        or not target.exists()
        or not any(str(target).startswith(str(a)) for a in allowed)
    ):
        raise ValueError(f"document not found or not allowed: {path}")
    return target.read_text(encoding="utf-8", errors="replace")


def _parse_ticket(p: Path) -> dict:
    text = p.read_text(encoding="utf-8", errors="replace")
    meta: dict[str, str] = {}
    if text.startswith("---"):
        parts = text.split("---", 2)
        if len(parts) >= 3:
            for line in parts[1].splitlines():
                if ":" in line:
                    k, v = line.split(":", 1)
                    meta[k.strip()] = v.strip()
    return {
        "id": meta.get("id", p.stem),
        "title": meta.get("title", ""),
        "status": meta.get("status", ""),
        "priority": meta.get("priority", ""),
        "path": p.relative_to(ROOT).as_posix(),
    }


@mcp.tool(annotations=READ_ONLY)
def list_tickets(status: str | None = None) -> list[dict]:
    """List the demo tickets (Markdown files in tickets/, standing in for an
    issue tracker). Optionally filter by status: open, in-progress, done.
    """
    out = []
    if TICKETS_DIR.exists():
        for p in sorted(TICKETS_DIR.glob("*.md")):
            t = _parse_ticket(p)
            if status and t["status"] != status:
                continue
            out.append(t)
    return out


@mcp.tool(annotations=DRAFT_WRITE)
def propose_ticket(title: str, body: str, priority: str = "medium") -> dict:
    """Propose a new ticket as a DRAFT under tickets/drafts/.

    Draft-first is enforced here, not left to convention: this is the
    server's only write tool, and it can only create a new file in
    tickets/drafts/ with status "draft". It cannot create, modify, or
    delete real tickets in tickets/. A human reviews the draft and
    promotes it — moves it into tickets/ with a real TF id — if it
    should become a ticket. Returns the draft's workspace-relative
    path.
    """
    # One line, and no "---": the ticket parser splits front matter on
    # that marker, so a title containing it would corrupt the draft.
    clean_title = " ".join(title.split()).replace("---", "-")
    slug = re.sub(r"[^a-z0-9]+", "-", clean_title.lower()).strip("-")[:60]
    slug = slug.strip("-") or "untitled"
    if priority not in ("low", "medium", "high"):
        raise ValueError("priority must be low, medium or high")
    drafts_dir = TICKETS_DIR / "drafts"
    drafts_dir.mkdir(parents=True, exist_ok=True)
    path = drafts_dir / f"draft-{slug}.md"
    if path.exists():
        raise ValueError(
            f"a draft already exists at tickets/drafts/{path.name};"
            " choose a different title"
        )
    text = (
        "---\n"
        f"id: draft-{slug}\n"
        f"title: {clean_title}\n"
        "status: draft\n"
        f"priority: {priority}\n"
        "---\n\n"
        f"{body.strip()}\n"
    )
    path.write_text(text, encoding="utf-8")
    return {
        "path": path.relative_to(ROOT).as_posix(),
        "status": "draft",
        "note": (
            "Draft only: a human must review it and move it into"
            " tickets/ with a real TF id for it to become a ticket."
        ),
    }


if __name__ == "__main__":
    # No startup banner: a stdio server should keep stderr quiet, and the
    # banner's box-drawing characters are exactly the kind of non-ASCII
    # output that breaks under non-UTF-8 locales (see _force_utf8_stdio).
    mcp.run(show_banner=False)  # stdio transport by default
