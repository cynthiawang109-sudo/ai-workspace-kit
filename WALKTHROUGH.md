# Walkthrough — a guided tour of ai-workspace-kit

This tour drives the whole workspace the way it is meant to be used:
you ask an AI coding agent (Codex) questions and give it tasks; the
workspace's docs, MCP server, and skills supply the context and the
guardrails. Every step says what to type and what you should see.
Budget about 15 minutes.

**Prerequisites:** this repo cloned, a Codex setup that can open the
folder (the workspace registers its MCP servers through
`.codex/config.toml` conventions described in the README), and the
demo content synced (step 1).

## 1. Sync the workspace and check its health

```powershell
.\sync.ps1            # or ./sync.sh
.\doctor.ps1          # or ./doctor.sh
```

Sync clones or fast-forwards the five sibling repos into `projects/`.
Doctor runs 15 checks — layout, sub-repo state, the doc-search
environment, MCP registrations, `gh` login — and should end with
"all hard checks passed".

## 2. Ask questions across all the repos

Open Codex in the workspace root and ask:

> What is the health check contract every service must implement?

It should find the contract in `taskflow-api-docs` via the doc-search
MCP server. Now ask the same kind of question in natural language:

> How does the service report a down dependency?

That one exercises `search_docs_semantic` (TF-IDF cosine ranking)
instead of the keyword `search_docs`. The doc-search README explains
how the two rankings differ — and is honest that both are
bag-of-words models, not embeddings.

## 3. Draft a ticket (draft-first, enforced)

Ask Codex:

> Draft a ticket proposing we cache the board page, using the
> doc-search propose_ticket tool.

The tool can only write under `tickets/drafts/` with status `draft` —
it *cannot* create a real ticket, and your client will ask before
running it because it is annotated as a write. Review the file it
created. Promoting a draft is a human step: move it into `tickets/`,
give it the next TF id, and set its status to `open`.

## 4. Turn a ticket into a reviewed pull request

demo-app's history (PRs #1–#6) is the worked example of the loop:
branch per change (`<user>/<date>/<slug>`), tests first, then a
review against the workspace contracts. Reproduce the review half
against any open PR:

```powershell
.\projects\code-reviewer\scripts\review-pr.ps1 -Repo cynthiawang109-sudo/demo-app -Pr 6 -Sandbox danger-full-access
```

(The `-Sandbox` flag bypasses Codex's local shell sandbox; see
Troubleshooting.)

The reviewer reads the API conventions, data model, deployment and
runbook docs through doc-search, checks the diff against them,
verifies claims by running the tests, and writes its findings to
`review-demo-app-6.md`. Past reviews are worth reading: they caught a
PII leak in error diagnostics, a concurrency double-delivery, and a
"build" job that built nothing — each fixed before merge.

## 5. Run the weekly digest twice (idempotency demo)

```powershell
cd projects\demo-app
.\.venv\Scripts\python scripts\migrate.py
.\.venv\Scripts\python scripts\run_digest.py --user demo-user --week 2026-W46
.\.venv\Scripts\python scripts\run_digest.py --user demo-user --week 2026-W46
```

First run: `{"outcome": "sent", "attempts": 1}`. Second run:
`already_sent`, and `digest-outbox.jsonl` still contains exactly one
delivery. The attempt ledger, backoff, and dead-letter rules behind
this are TF-103 in `tickets/` and the incident runbook in
`taskflow-docs`.

## 6. Re-check a release gate

```powershell
.\projects\release-assistant\scripts\release-check.ps1 -App demo-app -Version v1.1.0 -Since 2026-11-01 -Sandbox danger-full-access
```

The release assistant evaluates the seven-item release checklist
against live evidence — CI on the exact commit, expand-only
migrations, a recorded rollback tag, a named on-call — and writes a
GO / NO-GO assessment. v1.1.0 was first assessed NO-GO, the blockers
were fixed, and the re-check passed:
[the v1.1.0 release](https://github.com/cynthiawang109-sudo/demo-app/releases/tag/v1.1.0)
and its [release ticket](https://github.com/cynthiawang109-sudo/demo-app/issues/7)
are the public record of that loop.

## Troubleshooting

- **`doctor` flags the demo-app checkout's branch** — it expects
  sub-repos on `main`; a feature branch checked out mid-work is the
  usual cause.
- **Codex reports "Failed to create unified exec process … runner
  pipe-in"** — its sandboxed shell runner is wedged on this machine.
  The runner scripts accept `-Sandbox danger-full-access` to bypass
  the sandbox while it is broken.
- **A search returns nothing** — doc-search only sees synced content;
  re-run step 1.
