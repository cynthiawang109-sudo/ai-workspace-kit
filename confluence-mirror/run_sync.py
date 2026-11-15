"""Sync one changed batch through the configured Codex Atlassian MCP connection."""
import argparse
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

WS = Path(__file__).resolve().parent.parent
PAY = Path(__file__).resolve().parent / "payloads"
STATE = Path(__file__).resolve().parent / "state.json"


def read_json(path):
    return json.loads(path.read_text(encoding="utf-8"))


def find_codex():
    executable = shutil.which("codex")
    if executable:
        return executable
    local = Path(os.environ.get("LOCALAPPDATA", Path.home() / "AppData" / "Local"))
    fallback = local / "Programs" / "OpenAI" / "Codex" / "bin" / "codex.exe"
    if fallback.is_file():
        return str(fallback)
    raise FileNotFoundError("Codex was not found on PATH or in the per-user install directory")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("batch", choices=("1", "2"))
    batch = parser.parse_args().batch
    manifest = read_json(PAY / "manifest.json")
    state = read_json(STATE)
    recorded = {page["key"]: page for page in state["pages"]}
    selected = [m for m in manifest
                if m["source"].startswith("taskflow-api-docs/") == (batch == "2")]
    sel = [m for m in selected
           if recorded.get(m["key"], {}).get("sha256") != m["sha256"]]
    if not sel:
        print(f"Batch {batch}: nothing changed; skipping Codex.")
        return 0
    for m in sel:
        if not (PAY / m["payload"]).is_file():
            raise FileNotFoundError(PAY / m["payload"])
    executable = find_codex()
    results_path = PAY / f"results-batch{batch}.json"
    # A previous run's results must never acknowledge new content.
    results_path.unlink(missing_ok=True)
    listing = "\n".join(
        f"- key={m['key']} title={m['title']!r} parent={m['parent']!r} "
        f"payload={m['payload']} recordedPageId={recorded.get(m['key'], {}).get('pageId')!r}"
        for m in sel)
    PROMPT = f"""You are running the Confluence mirror sync for the TaskFlow space (key TASKFLOW) on cynthia-taskflow.atlassian.net, using your configured Atlassian MCP server.

    The payload directory {PAY} contains manifest.json and one Markdown payload file per page. Process ONLY these entries, in the order listed (parents always appear before their children):

    {listing}

    For each entry:
    1. Read the payload file's full content.
    2. Use the recorded page ID from state.json when available; otherwise search the TASKFLOW space for an existing page with exactly this title (use searchConfluence or listConfluenceContent).
    3. If none exists, create it with createConfluenceContent: space TASKFLOW, body format `markdown`, the payload content, and the parent set to the page named by the entry's parent (resolve the parent's page ID from a page you created earlier in this run or by searching for its title). The entry with parent null is a top-level page.
    4. If one exists, update it with updateConfluenceContent using the payload content (format markdown), keeping its existing parent.
    5. Record the outcome.

    Read back every created or updated page to verify its content before recording success.
    Do not create or modify anything else. Do not modify state.json; the driver handles it. When finished, write a JSON file to {results_path} containing a list of objects with: key, title, pageId, url, action ("created" or "updated"). Then print a one-line-per-page summary."""

    process = subprocess.run([executable, "exec", "--sandbox", "workspace-write", "-"], cwd=WS, input=PROMPT,
                             capture_output=True, text=True, encoding="utf-8", errors="replace")
    print(process.stdout or "")
    print(process.stderr or "", file=sys.stderr)
    if process.returncode:
        return process.returncode
    results = read_json(results_path)
    expected = {m["key"]: m for m in sel}
    seen = set()
    for result in results:
        key = result["key"]
        if key not in expected or key in seen:
            raise ValueError(f"Unexpected or duplicate result: {key}")
        m = expected[key]
        if (result["title"] != m["title"] or not result["pageId"] or not result["url"]
                or result["action"] not in ("created", "updated")):
            raise ValueError(f"Invalid result: {key}")
        seen.add(key)
        recorded[key] = dict(key=key, title=m["title"], pageId=result["pageId"],
                             url=result["url"], sha256=m["sha256"])
    if seen != set(expected):
        raise ValueError("Batch results are incomplete; state has not been changed")
    state["pages"] = list(recorded.values())
    temporary = STATE.with_suffix(".json.tmp")
    temporary.write_text(json.dumps(state, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    temporary.replace(STATE)
    print(f"Batch {batch}: recorded {len(results)} pages in state.json.")
    return 0


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    try:
        sys.exit(main())
    except (OSError, ValueError, KeyError, TypeError) as error:
        print(f"Sync failed: {error}", file=sys.stderr)
        sys.exit(1)
