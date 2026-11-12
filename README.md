# ai-workspace-kit

[![doc-search tests](https://github.com/cynthiawang109-sudo/ai-workspace-kit/actions/workflows/doc-search-tests.yml/badge.svg)](https://github.com/cynthiawang109-sudo/ai-workspace-kit/actions/workflows/doc-search-tests.yml)

A **tool-agnostic AI development workspace**: a small meta-repo that checks out
a set of related repositories side by side — living documentation, a code
reviewer, a process assistant, and demo application code — so an AI coding
agent (Codex, Claude Code, or any client that reads `AGENTS.md` / speaks MCP)
can pull cross-repository context on demand instead of guessing.

This is a clean-room, public re-creation of a workspace pattern used in
production engineering work: documentation repos treated as the source of
truth, reviews and assistants consuming them through an index, and a one-command
sync that rebuilds the whole workspace anywhere.

The demo domain is **TaskFlow**, a fictional project-management SaaS. All
content is original and fictional — no employer code, data, or system names.

## Architecture

```mermaid
flowchart TB
    S["sync.ps1 / sync.sh"] -->|clone & update| CR["code-reviewer"]
    S -->|clone & update| RA["release-assistant"]
    S -->|clone & update| DOCS["documentation repos x2 (extensible to x4)"]
    W["ai-workspace-kit workspace"] --- CR
    W --- RA
    W --- APP["demo-app"]
    CR -->|reads system background| DOCS
    U["You / Codex (primary) / Claude Code"] --> W
    U --> MCP["MCP connectors"]
    MCP --> GH["GitHub MCP server -> GitHub Issues / PRs"]
    MCP --> DS["doc-search MCP server (custom, M2) -> local docs + tickets"]
```

## Layout

| Path | What it is |
|---|---|
| `sync.ps1` / `sync.sh` | Clone or fast-forward-update every repo in `repos.txt` into `projects/` |
| `doctor.ps1` / `doctor.sh` | One-command health check: layout, sub-repo git state, doc-search venv, Codex MCP registration, token presence |
| `repos.txt` | The workspace manifest: one `name url` pair per line |
| `AGENTS.md` | Workspace conventions every agent session follows (read order, cross-repo references, write governance) |
| `CLAUDE.md` | Thin pointer to `AGENTS.md` so Claude clients land in the same place |
| `.codex/config.toml.example` | MCP server registration template — secrets come from environment variables, never from this repo |
| `mcp/` | The custom `doc-search` MCP server (milestone M2) |
| `projects/` | Synced checkouts (git-ignored; each is its own repository) |

Synced projects:

| Directory | Purpose |
|---|---|
| `projects/taskflow-docs/` | TaskFlow system documentation (overview, deployment, runbook) |
| `projects/taskflow-api-docs/` | TaskFlow API conventions and data model |
| `projects/code-reviewer/` | Review standards, per-project review notes, documentation index |
| `projects/release-assistant/` | Release checklists and change-process documentation |
| `projects/demo-app/` | Demo FastAPI service the other repos describe and review |

## Quick start

```powershell
git clone https://github.com/cynthiawang109-sudo/ai-workspace-kit
cd ai-workspace-kit
.\sync.ps1            # or ./sync.sh in Git Bash / Linux / macOS
```

Then open the folder in your agent (Codex: `codex`, or the VS Code extension;
Claude Code works too) and ask something that needs more than one repo, e.g.
*"Where is demo-app's health-check contract defined, and does the
implementation follow it?"* — the answer lives in `taskflow-api-docs`, the code
in `demo-app`.

Re-run the sync script any time: it is idempotent, clones what is missing, and
fast-forward-pulls what exists. A `pull --ff-only` failure means that checkout
has local commits — the script reports it and moves on rather than clobbering
local work.

Run `.\doctor.ps1` (or `./doctor.sh`) any time to check whether this machine's
setup is complete: it verifies the layout, each checkout's git state, the
doc-search virtual environment, Codex's MCP registrations, and that the
GitHub token variable is set (presence only — it never prints secrets).

## Design notes

- **Index + on-demand fetch, not embeddings.** The reviewer keeps a small
  index of the documentation repos (`code-reviewer/context/doc-repos.md`) and
  fetches the specific file it needs. Cheap, inspectable, and always current.
- **Every project works standalone.** Cross-references are optional by
  convention: "if `../<sibling>` exists, use it for X" — nothing hard-requires
  the full workspace.
- **Draft-first writes.** Agents may read freely, but any outward write (issue,
  PR comment, ticket) is drafted for human approval first, then verified after
  posting. See `AGENTS.md`.
- **Secrets live outside the repo.** Tokens are read from environment
  variables; only `*.example` templates are committed.

## Roadmap

- **M1** — workspace skeleton: meta-repo, sync scripts, doc repos, demo app ✅
- **M2** — custom `doc-search` MCP server (Python / FastMCP): keyword search +
  fetch over the documentation repos and local Markdown tickets ✅
- **M3** — code-reviewer on a real pull request (GitHub Actions + Codex review)
- **M4** — case study: the production pattern this recreates, its trade-offs,
  and what transfers to other teams
