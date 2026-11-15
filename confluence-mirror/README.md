# Confluence mirror

Mirrors `projects/taskflow-docs/` and `projects/taskflow-api-docs/` into the
TASKFLOW space at https://cynthia-taskflow.atlassian.net. Git is the source
of truth. Confluence edits are overwritten when a page is next synced;
unchanged pages are skipped, so a manual Confluence edit alone does not
trigger an update.

## Run a sync

Use Python 3.10+ (standard library only). Materialize the docs checkouts with
`./sync.sh` or `.\sync.ps1` first if they are missing or stale. Review the
source changes before running a sync: these commands write to Confluence.
From the workspace root:

```powershell
python confluence-mirror/prepare.py
python confluence-mirror/run_sync.py 1
python confluence-mirror/run_sync.py 2
```

Paths resolve from the scripts, so the commands also work from another
working directory when given the appropriate script path. Run the batches
sequentially, with batch 1 first so parents exist for batch 2. Do not run
multiple sync drivers concurrently or regenerate payloads during a sync.

`prepare.py`, adapted from the live-run `conf_prepare.py`, writes Markdown
payloads and `manifest.json` to the ignored `payloads/` directory. It preserves
the original relative-link rewriting to GitHub `blob/main` URLs and mirror
footer, including the first 16 hex characters of the body's SHA-256 hash.
The generated home page, README section pages, ADR index and OpenAPI wrapper
also retain the original content rules.

`run_sync.py`, adapted from `codex_conf_sync.py`, delegates MCP writes to
`codex exec --sandbox workspace-write -`, using the workspace's configured Atlassian MCP and OAuth
connection. Codex must already be installed, signed in, and able to use that
connection. The driver looks for `codex` on PATH, then falls back to
`%LOCALAPPDATA%\Programs\OpenAI\Codex\bin\codex.exe` (the standard per-user
Windows installation). No credentials are stored in this repository.
Codex uses the recorded page IDs, searches exact titles for new entries,
creates missing pages under the specified parent, and updates existing pages
while keeping their parent. It reads pages back to verify writes before
recording results in `payloads/results-batchN.json`.

## Page tree

The initial mirror has 23 pages:

```text
TaskFlow documentation                         (generated mirror home)
|-- taskflow-docs                               (README section page)
|   |-- system overview, architecture, authentication, security
|   |-- deployment, environments, observability, backup and recovery
|   |-- incident runbook
|   `-- Architecture decision records          (generated index)
|       |-- ADR-0001: PostgreSQL as the primary store
|       |-- ADR-0002: Cursor pagination for all list endpoints
|       `-- ADR-0003: RQ for background jobs, over Celery
`-- taskflow-api-docs                           (README section page)
    |-- API conventions, data model, endpoint reference
    |-- error code catalog, rate limiting, webhooks
    `-- OpenAPI specification                  (wrapped openapi.yaml)
```

The document lists and parent titles are defined in `prepare.py`.
Batch 1 includes everything except sources beginning `taskflow-api-docs/`
(15 pages initially); batch 2 includes those API sources (8 pages).

## Incremental state and recovery

`state.json` records the site, space key, and each page's key, title, page ID,
URL and hash. It is seeded from the live run's manifest and both results
files, covering all 23 created pages. Each batch compares manifest hashes
with state and sends only changed or unrecorded pages to Codex. An unchanged
batch exits successfully without invoking Codex. This does not detect remote
edits or deletions. To deliberately refresh a page, remove its `sha256` field
from state, prepare again, then run its batch.

After Codex exits successfully, the driver validates that the fresh results
contain exactly the requested pages and atomically replaces state with their
manifest hashes and returned IDs/URLs, preserving other entries. Failed runs,
missing or invalid results leave state unchanged and exit nonzero. Remote
writes may already have occurred; inspect the output and rerun to reconcile
them. Old batch results are removed before invoking Codex so they cannot
acknowledge a new payload. The tool does not delete pages removed from the
manifest. Review and commit `state.json` after a successful sync so the next
checkout retains the page identities and incremental baseline.

## Operational notes

The site runs Confluence on a trial that converts to the Free plan. The
space homepage automatically created by Confluence is separate from the
mirrored **TaskFlow documentation** page; the mirror does not replace it.
