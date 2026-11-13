# Retrieval evaluation

Date: 2026-11-13

Intended model: `sentence-transformers/all-MiniLM-L6-v2`.

Real-model evaluation and synonym smoke test have not been run: the existing
environment lacks sentence-transformers, and this implementation session
prohibited installing packages. No real-model hit rates are claimed.

The 12-query corpus is in `eval/queries.json`. With the optional dependencies
available, run `.venv/Scripts/python scripts/run_eval.py --write` from this
directory to replace this note with measured hit@1, hit@3 and per-query tables.
The deterministic fake embedder tests validate mechanics, not semantic quality.
