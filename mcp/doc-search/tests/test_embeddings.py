"""Embedding tools exercised against a throwaway corpus, without model downloads."""
import importlib
import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from test_server import call


@pytest.fixture()
def modules(tmp_path, monkeypatch):
    docs = tmp_path / "projects" / "demo-docs"
    docs.mkdir(parents=True)
    (docs / "api.md").write_text(
        "Preamble.\n# API conventions\n## Health checks\n"
        "Every service exposes a health endpoint.\n### Failure\n"
        "Unavailable dependencies return degraded.\n## Pagination\nCursor paging.\n",
        encoding="utf-8",
    )
    (docs / "other.md").write_text("# Other\nNothing relevant.\n", encoding="utf-8")
    for relative in (
        ".git/README.md", ".venv/pkg/README.md", "venv/pkg/README.md",
        "node_modules/pkg/README.md", "__pycache__/README.md", ".pytest_cache/README.md",
    ):
        generated = docs / relative
        generated.parent.mkdir(parents=True)
        generated.write_text("# Generated\n\nzqxwv generated junk marker\n", encoding="utf-8")
    monkeypatch.setenv("AI_WORKSPACE_ROOT", str(tmp_path))
    monkeypatch.setenv("DOC_SEARCH_EMBEDDER", "fake")
    import server
    import embeddings

    importlib.reload(server)
    importlib.reload(embeddings)
    monkeypatch.setattr(embeddings, "INDEX_DIR", tmp_path / "index")
    return server, embeddings


def test_chunk_heading_trails(modules):
    server, embeddings = modules
    path = server.PROJECTS_DIR / "demo-docs" / "api.md"
    chunks = embeddings.chunk_document(path, path.read_text(encoding="utf-8"))
    assert [c["heading"] for c in chunks] == [
        "API conventions", "API conventions", "API conventions > Health checks",
        "API conventions > Health checks > Failure", "API conventions > Pagination",
    ]
    assert chunks[0]["text"] == "Preamble."
    assert chunks[2]["text"] == "Every service exposes a health endpoint."


def test_search_excludes_generated_directories(modules):
    server, embeddings = modules
    allowed = {"projects/demo-docs/api.md", "projects/demo-docs/other.md"}
    # Hashed fake embeddings can match unrelated tokens, so inspect paths
    # rather than requiring the marker query to return no results.
    for query in ("zqxwv generated junk marker", "health endpoint service"):
        data = call(server, "search_docs_embeddings", {"query": query, "limit": 100})
        assert all(hit["path"] in allowed for hit in data)
        if query == "health endpoint service":
            assert data[0]["path"] == "projects/demo-docs/api.md"
    assert {chunk["path"] for chunk in embeddings.load_index()} == allowed


def test_search_ranking_and_shape(modules):
    server, embeddings = modules
    data = call(server, "search_docs_embeddings", {"query": "health endpoint service"})
    assert data[0]["path"] == "projects/demo-docs/api.md"
    assert data[0]["heading"] == "API conventions > Health checks"
    assert data[0]["snippet"] == "Every service exposes a health endpoint."
    assert all(set(r) == {"path", "title", "score", "snippet", "heading"} for r in data)
    assert all(r["score"] and -1 <= r["score"] <= 1 for r in data)
    assert data == sorted(data, key=lambda r: (-r["score"], r["path"], r["heading"]))
    manifest = json.loads((embeddings.INDEX_DIR / "manifest.json").read_text())
    assert manifest["embedder"] == "fake"
    assert manifest["chunk_count"] == len(embeddings.load_index())


def test_edit_rebuilds_index(modules):
    server, embeddings = modules
    call(server, "search_docs_embeddings", {"query": "health"})
    before = json.loads((embeddings.INDEX_DIR / "manifest.json").read_text())
    path = server.PROJECTS_DIR / "demo-docs" / "api.md"
    path.write_text("# Updated\nNew health endpoint content.\n", encoding="utf-8")
    data = call(server, "search_docs_embeddings", {"query": "health endpoint"})
    assert data[0]["snippet"] == "New health endpoint content."
    after = json.loads((embeddings.INDEX_DIR / "manifest.json").read_text())
    assert before["fingerprint"] != after["fingerprint"]


def test_model_change_rebuilds_index(modules, monkeypatch):
    _, embeddings = modules
    embeddings.load_index()
    monkeypatch.setenv("DOC_SEARCH_EMBEDDING_MODEL", "fixture-model")
    embeddings.load_index()
    manifest = json.loads((embeddings.INDEX_DIR / "manifest.json").read_text())
    assert manifest["model"] == "fixture-model"


def test_empty_query_and_zero_vector(modules):
    server, embeddings = modules
    assert call(server, "search_docs_embeddings", {"query": "!!!"}) == []
    assert embeddings.get_embedder().encode([""]) == [[0.0] * 64]
    assert len(embeddings.get_embedder().encode(["health"])[0]) == 64


def test_atx_levels_and_fenced_body(modules):
    server, embeddings = modules
    chunks = embeddings.chunk_document(server.PROJECTS_DIR / "sample.md",
        "# Root\n```md\n## Not a heading\n```\n###### Deep ###\nBody\n## Next\nEnd")
    assert [c["heading"] for c in chunks] == ["Root", "Root > Deep", "Root > Next"]
    assert "## Not a heading" in chunks[0]["text"]
