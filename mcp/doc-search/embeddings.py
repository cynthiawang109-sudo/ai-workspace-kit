"""Section embeddings with a content-validated, local derived index.

Importing this module does not import sentence-transformers or torch.
The fake embedder is a deterministic test double, not a semantic model.
"""
import hashlib
import json
import math
import os
import re
from functools import lru_cache
from pathlib import Path


INDEX_DIR = Path(__file__).resolve().parent / ".index"
DEFAULT_MODEL = "sentence-transformers/all-MiniLM-L6-v2"


class _FakeEmbedder:
    def encode(self, texts):
        from server import _tokenize

        vectors = []
        for text in texts:
            vector = [0.0] * 64
            for token in _tokenize(text):
                slot = int(hashlib.sha256(token.encode("utf-8")).hexdigest(), 16) % 64
                vector[slot] += 1.0
            norm = math.sqrt(sum(v * v for v in vector))
            vectors.append([v / norm for v in vector] if norm else vector)
        return vectors


class _RealEmbedder:
    def __init__(self, model):
        try:
            from sentence_transformers import SentenceTransformer
        except ImportError as exc:
            raise RuntimeError(
                "sentence-transformers is not installed; "
                "install the optional embeddings dependencies with: "
                "pip install -r requirements-embeddings.txt"
            ) from exc
        self.model = SentenceTransformer(model)

    def encode(self, texts):
        return self.model.encode(texts, normalize_embeddings=True).tolist()


@lru_cache(maxsize=2)
def _embedder(name, model):
    if name == "fake":
        return _FakeEmbedder()
    if name != "sentence-transformers":
        raise ValueError(f"unknown DOC_SEARCH_EMBEDDER: {name}")
    return _RealEmbedder(model)


def get_embedder():
    """Return the configured embedder, loading the real model only on demand."""
    return _embedder(
        os.environ.get("DOC_SEARCH_EMBEDDER", "sentence-transformers"),
        os.environ.get("DOC_SEARCH_EMBEDDING_MODEL", DEFAULT_MODEL),
    )


def chunk_document(path, text):
    """Split ATX sections into body chunks carrying their full heading trail.

    The preamble uses the document title. Empty section bodies are retained
    so a heading alone remains searchable. Fenced code is treated as body.
    """
    from server import ROOT, _doc_title

    path = Path(path)
    title = _doc_title(text, path)
    relative = path.relative_to(ROOT).as_posix()
    chunks, trail, body = [], [], []
    heading = title
    fence = None

    def flush():
        chunks.append({"path": relative, "title": title,
                       "heading": heading, "text": "\n".join(body).strip()})

    for line in text.splitlines():
        marker = re.match(r"^ {0,3}(`{3,}|~{3,})(.*)$", line)
        if marker:
            run, tail = marker.groups()
            if fence is None:
                fence = run
            elif run[0] == fence[0] and len(run) >= len(fence) and not tail.strip():
                fence = None
            body.append(line)
            continue
        match = None if fence else re.match(r"^ {0,3}(#{1,6})(?:[ \t]+(.*)|$)", line)
        if match:
            if trail or any(part.strip() for part in body):
                flush()
            level = len(match[1])
            label = re.sub(r"[ \t]+#+[ \t]*$", "", match[2] or "").strip()
            trail = [(n, label_) for n, label_ in trail if n < level]
            trail.append((level, label))
            heading = " > ".join(label_ for _, label_ in trail)
            body = []
        else:
            body.append(line)
    if trail or any(part.strip() for part in body):
        flush()
    return chunks


def build_index(documents, manifest):
    """Embed a byte snapshot of the corpus and persist its derived cache."""
    chunks = []
    for path, content in documents:
        chunks.extend(chunk_document(path, content.decode("utf-8", errors="replace")))
    if chunks:
        vectors = get_embedder().encode([
            f"{c['title']} > {c['heading']}\n{c['text']}" for c in chunks
        ])
        for chunk, vector in zip(chunks, vectors):
            chunk["embedding"] = vector
    INDEX_DIR.mkdir(parents=True, exist_ok=True)
    (INDEX_DIR / "chunks.jsonl").write_text(
        "".join(json.dumps(c, ensure_ascii=False) + "\n" for c in chunks),
        encoding="utf-8",
    )
    (INDEX_DIR / "manifest.json").write_text(
        json.dumps({**manifest, "chunk_count": len(chunks)}, indent=2), encoding="utf-8"
    )
    return chunks


def load_index():
    """Reuse the cache only when corpus bytes, model and embedder match."""
    from server import ROOT, _iter_docs

    documents = [(p, p.read_bytes()) for p in _iter_docs()]
    hashes = sorted((p.relative_to(ROOT).as_posix(), hashlib.sha256(b).hexdigest())
                    for p, b in documents)
    manifest = {
        "model": os.environ.get("DOC_SEARCH_EMBEDDING_MODEL", DEFAULT_MODEL),
        "embedder": os.environ.get("DOC_SEARCH_EMBEDDER", "sentence-transformers"),
        "fingerprint": hashlib.sha256(json.dumps(hashes).encode("utf-8")).hexdigest(),
    }
    try:
        saved = json.loads((INDEX_DIR / "manifest.json").read_text(encoding="utf-8"))
        if all(saved.get(k) == v for k, v in manifest.items()):
            chunks = [json.loads(line) for line in
                      (INDEX_DIR / "chunks.jsonl").read_text(encoding="utf-8").splitlines()]
            if len(chunks) == saved.get("chunk_count"):
                return chunks
    except (OSError, ValueError):
        pass
    return build_index(documents, manifest)


def search(query, limit=8):
    """Rank section chunks by pure-Python cosine; cache writes are local."""
    from server import _tokenize

    if limit <= 0 or not _tokenize(query):
        return []
    chunks = load_index()
    if not chunks:
        return []
    vector = get_embedder().encode([query])[0]
    norm = math.sqrt(sum(v * v for v in vector))
    results = []
    for chunk in chunks:
        other = chunk["embedding"]
        denominator = norm * math.sqrt(sum(v * v for v in other))
        score = round(sum(a * b for a, b in zip(vector, other)) / denominator, 4) if denominator else 0
        if not score:
            continue
        results.append({
            "path": chunk["path"], "title": chunk["title"], "score": score,
            "snippet": next((line.strip()[:200] for line in chunk["text"].splitlines()
                             if line.strip()), ""),
            "heading": chunk["heading"],
        })
    results.sort(key=lambda r: (-r["score"], r["path"], r["heading"]))
    return results[:limit]
