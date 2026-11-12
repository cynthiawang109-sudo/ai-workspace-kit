"""Tests for the doc-search MCP server.

They build a tiny throwaway workspace (docs + tickets) in a temp folder,
point AI_WORKSPACE_ROOT at it, reload the server module, and exercise the
tools through FastMCP's in-process client — so the suite passes on any
checkout, whether or not sync has run.
"""
import asyncio
import importlib
import sys
from pathlib import Path

import pytest
from fastmcp import Client

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


@pytest.fixture()
def server_mod(tmp_path, monkeypatch):
    docs = tmp_path / "projects" / "demo-docs"
    docs.mkdir(parents=True)
    (docs / "api.md").write_text(
        "# API conventions\n\n## Health checks\n\nEvery service exposes /health.\n",
        encoding="utf-8",
    )
    (docs / "other.md").write_text("# Other\n\nNothing relevant.\n", encoding="utf-8")
    tickets = tmp_path / "tickets"
    tickets.mkdir()
    (tickets / "TF-1.md").write_text(
        "---\nid: TF-1\ntitle: Fix health endpoint\nstatus: open\npriority: high\n---\nBody.\n",
        encoding="utf-8",
    )
    (tickets / "TF-2.md").write_text(
        "---\nid: TF-2\ntitle: Old cleanup\nstatus: done\npriority: low\n---\nBody.\n",
        encoding="utf-8",
    )
    monkeypatch.setenv("AI_WORKSPACE_ROOT", str(tmp_path))
    import server

    importlib.reload(server)
    return server


def call(server_mod, tool, args):
    async def _run():
        async with Client(server_mod.mcp) as c:
            result = await c.call_tool(tool, args)
            return result.data

    return asyncio.run(_run())


def test_search_ranks_contract_doc_first(server_mod):
    data = call(server_mod, "search_docs", {"query": "health"})
    assert data, "expected at least one hit"
    assert data[0]["path"].endswith("api.md")


def test_semantic_search_ranks_topical_doc_first(server_mod):
    # A natural-language, multi-term query: no single term should need to
    # dominate for the API doc to beat the unrelated one.
    data = call(
        server_mod,
        "search_docs_semantic",
        {"query": "which endpoint does every service expose for health checks"},
    )
    assert data, "expected at least one hit"
    assert data[0]["path"].endswith("api.md")
    assert 0 < data[0]["score"] <= 1  # cosine similarity


def test_semantic_search_without_overlap_returns_empty(server_mod):
    data = call(
        server_mod, "search_docs_semantic", {"query": "quantum banana hammock"}
    )
    assert data == []


def test_semantic_search_respects_limit(server_mod):
    data = call(server_mod, "search_docs_semantic", {"query": "health", "limit": 1})
    assert len(data) == 1


def test_get_doc_roundtrip_and_traversal_guard(server_mod):
    text = call(server_mod, "get_doc", {"path": "projects/demo-docs/api.md"})
    assert "Health checks" in text
    with pytest.raises(Exception):
        call(server_mod, "get_doc", {"path": "../outside.md"})


def test_list_tickets_and_status_filter(server_mod):
    all_tickets = call(server_mod, "list_tickets", {})
    assert {t["id"] for t in all_tickets} == {"TF-1", "TF-2"}
    open_only = call(server_mod, "list_tickets", {"status": "open"})
    assert [t["id"] for t in open_only] == ["TF-1"]
