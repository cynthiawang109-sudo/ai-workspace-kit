# ai-workspace-kit — workspace conventions

This file is the contract every AI agent session in this workspace follows.
It applies at the workspace root; individual projects may add their own
`AGENTS.md` with project-specific rules.

## Read order

1. This file and the root `README.md` (layout, manifest, design notes).
2. `code-reviewer/context/doc-repos.md` — the index of documentation repos.
   Use it to decide *where* a fact lives before opening files at random.
3. The specific documentation file the index points to. Documentation repos
   under `projects/` are the source of truth for the systems they describe;
   if code and docs disagree, say so — do not silently pick one.

## Workspace checkouts

Run `./sync.sh` or `.\sync.ps1` first if `projects/` is empty or stale.
Checkouts materialize the versions pinned in `versions.txt`. Do not commit
inside a checkout without pushing to that project's own repository.

After merging sub-repo work, bump the pins and commit `versions.txt`.

| Directory | Role |
|---|---|
| `projects/taskflow-docs/` | System documentation: overview, deployment, runbook |
| `projects/taskflow-api-docs/` | API conventions, data model |
| `projects/code-reviewer/` | Review standards + per-project review state |
| `projects/release-assistant/` | Release/process documentation |
| `projects/demo-app/` | Demo application code |

## Cross-project references

- Reference siblings by relative path, e.g. from `code-reviewer`:
  `../taskflow-docs/`.
- References are **optional by design**: write "if `../<sibling>` exists, use
  it for X" rather than hard-requiring the workspace. Every project must stay
  usable standalone.

## Ticket system

- New work items start as GitHub Issues on the workspace Project board.
- `tickets/*.md` is the pre-TF-115 archive: read-only history.
- Agent-proposed work still starts as a local draft via doc-search
  `propose_ticket`; a human promotes it with `scripts/promote-draft.ps1`
  (or `.sh`), with the Project configured to add the Issue to the board.

## Write governance (draft-first)

- Reading is free. **Writing outward is not**: any issue, PR comment, review,
  or ticket an agent creates must be drafted in the conversation first and
  posted only after explicit human approval in that conversation.
- After posting, re-read the created item and verify it landed as drafted
  before reporting success.
- Mechanical steps inside an already-approved action (labels or links named in
  the approval) do not need separate approval.

## Secrets

- Never commit tokens or keys. MCP servers take credentials from environment
  variables; committed config files are `*.example` templates only.
- If you find what looks like a real secret in the tree, stop and report it —
  do not copy it anywhere.

## Style for docs in this workspace

- One topic per file; keep the index (`doc-repos.md`, READMEs) current when
  adding or renaming a document.
- Fictional demo data only: TaskFlow is invented — never introduce real
  company, customer, or system names into any file here.
