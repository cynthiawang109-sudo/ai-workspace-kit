"""Compare all three retrieval modes on the checked-out corpus, without MCP."""
import argparse
import datetime
import json
import os
import sys
from pathlib import Path


SERVER_DIR = Path(__file__).resolve().parents[1]
ROOT = SERVER_DIR.parents[1]
sys.path.insert(0, str(SERVER_DIR))
os.environ["AI_WORKSPACE_ROOT"] = str(ROOT)

import server
from embeddings import DEFAULT_MODEL


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--write", action="store_true", help="write EVAL.md")
    args = parser.parse_args()
    queries = json.loads((SERVER_DIR / "eval" / "queries.json").read_text(encoding="utf-8"))
    modes = ["search_docs", "search_docs_semantic", "search_docs_embeddings"]
    totals = {mode: [0, 0] for mode in modes}
    details = ["| Query | Kind | Mode | Hit@1 | Hit@3 | Top paths |",
               "|---|---|---|---|---|---|"]
    for item in queries:
        for mode in modes:
            tool = getattr(server, mode)
            # FastMCP versions that wrap decorated functions expose .fn.
            results = getattr(tool, "fn", tool)(item["query"], limit=3)
            paths = [r["path"] for r in results]
            hits = [int(bool(set(paths[:k]) & set(item["expect"]))) for k in (1, 3)]
            totals[mode] = [a + b for a, b in zip(totals[mode], hits)]
            details.append(f"| {item['query']} | {item['kind']} | {mode} | "
                           f"{hits[0]} | {hits[1]} | {', '.join(paths)} |")
    summary = ["| Mode | Hit@1 | Hit@3 |", "|---|---|---|"]
    for mode, (one, three) in totals.items():
        summary.append(f"| {mode} | {one}/{len(queries)} ({one / len(queries):.1%}) | "
                       f"{three}/{len(queries)} ({three / len(queries):.1%}) |")
    model = os.environ.get("DOC_SEARCH_EMBEDDING_MODEL", DEFAULT_MODEL)
    embedder = os.environ.get("DOC_SEARCH_EMBEDDER", "sentence-transformers")
    report = (f"# Retrieval evaluation\n\nDate: {datetime.date.today().isoformat()}\n\n"
              f"Model: `{model}`; embedder: `{embedder}`.\n\n"
              "Scores measure expected paths among chunk results; duplicate paths count as slots.\n\n"
              + "\n".join(summary) + "\n\n" + "\n".join(details) + "\n")
    print(report)
    if args.write:
        (SERVER_DIR / "EVAL.md").write_text(report, encoding="utf-8")


if __name__ == "__main__":
    main()
