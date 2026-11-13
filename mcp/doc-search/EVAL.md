# Retrieval evaluation

Date: 2026-11-13

Model: `sentence-transformers/all-MiniLM-L6-v2`; embedder: `sentence-transformers`.

Scores measure expected paths among chunk results; duplicate paths count as slots.

| Mode | Hit@1 | Hit@3 |
|---|---|---|
| search_docs | 1/12 (8.3%) | 5/12 (41.7%) |
| search_docs_semantic | 2/12 (16.7%) | 6/12 (50.0%) |
| search_docs_embeddings | 6/12 (50.0%) | 8/12 (66.7%) |

| Query | Kind | Mode | Hit@1 | Hit@3 | Top paths |
|---|---|---|---|---|---|
| health checks 503 degraded | exact | search_docs | 0 | 0 | projects/release-assistant/release-notes-demo-app-v1.1.0.draft.md, projects/release-assistant/release-notes-demo-app-v1.2.0.draft.md, projects/code-reviewer/projects/demo-app.md |
| health checks 503 degraded | exact | search_docs_semantic | 0 | 1 | projects/release-assistant/manual.release-notes-demo-app-v1.1.0.draft.md, projects/release-assistant/release-notes-demo-app-v1.1.0.draft.md, projects/taskflow-api-docs/api-conventions.md |
| health checks 503 degraded | exact | search_docs_embeddings | 1 | 1 | projects/taskflow-api-docs/api-conventions.md, projects/code-reviewer/projects/taskflow-api-docs.md, projects/code-reviewer/projects/taskflow-api-docs.md |
| cursor pagination next_cursor | exact | search_docs | 0 | 1 | projects/taskflow-docs/adr/0002-cursor-pagination.md, projects/code-reviewer/projects/taskflow-api-docs.md, projects/taskflow-api-docs/api-conventions.md |
| cursor pagination next_cursor | exact | search_docs_semantic | 0 | 1 | projects/taskflow-docs/adr/0002-cursor-pagination.md, projects/taskflow-api-docs/api-conventions.md, projects/taskflow-docs/SUMMARY.md |
| cursor pagination next_cursor | exact | search_docs_embeddings | 0 | 0 | projects/taskflow-docs/adr/0002-cursor-pagination.md, projects/taskflow-docs/adr/0002-cursor-pagination.md, projects/taskflow-docs/adr/0002-cursor-pagination.md |
| comments supersedes_id append-only | exact | search_docs | 1 | 1 | projects/taskflow-api-docs/data-model.md, projects/release-assistant/release-notes-demo-app-v1.2.0.draft.md, projects/code-reviewer/projects/taskflow-api-docs.md |
| comments supersedes_id append-only | exact | search_docs_semantic | 1 | 1 | projects/taskflow-api-docs/data-model.md, projects/demo-app/CHANGELOG.md, projects/code-reviewer/projects/taskflow-api-docs.md |
| comments supersedes_id append-only | exact | search_docs_embeddings | 1 | 1 | projects/taskflow-api-docs/data-model.md, projects/demo-app/CHANGELOG.md, projects/code-reviewer/projects/taskflow-api-docs.md |
| deployment rollback container tag | exact | search_docs | 0 | 1 | projects/release-assistant/release-notes-demo-app-v1.1.0.draft.md, projects/release-assistant/release-notes-demo-app-v1.2.0.draft.md, projects/taskflow-docs/deployment.md |
| deployment rollback container tag | exact | search_docs_semantic | 1 | 1 | projects/taskflow-docs/deployment.md, projects/release-assistant/release-checklist.md, projects/code-reviewer/.github/pull_request_template.md |
| deployment rollback container tag | exact | search_docs_embeddings | 1 | 1 | projects/taskflow-docs/deployment.md, projects/taskflow-docs/deployment.md, projects/code-reviewer/.github/pull_request_template.md |
| worker queue poison job | exact | search_docs | 0 | 1 | projects/taskflow-docs/adr/0003-rq-over-celery.md, projects/taskflow-docs/incident-runbook.md, projects/taskflow-docs/architecture.md |
| worker queue poison job | exact | search_docs_semantic | 0 | 1 | projects/taskflow-docs/adr/0003-rq-over-celery.md, projects/taskflow-docs/incident-runbook.md, projects/taskflow-docs/observability.md |
| worker queue poison job | exact | search_docs_embeddings | 1 | 1 | projects/taskflow-docs/incident-runbook.md, projects/taskflow-docs/adr/0003-rq-over-celery.md, projects/taskflow-docs/architecture.md |
| redis pub/sub board presence | exact | search_docs | 0 | 1 | projects/taskflow-docs/architecture.md, projects/taskflow-docs/system-overview.md, projects/code-reviewer/projects/taskflow-docs.md |
| redis pub/sub board presence | exact | search_docs_semantic | 0 | 1 | projects/taskflow-docs/architecture.md, projects/taskflow-docs/system-overview.md, projects/taskflow-docs/adr/0003-rq-over-celery.md |
| redis pub/sub board presence | exact | search_docs_embeddings | 0 | 1 | projects/taskflow-docs/architecture.md, projects/taskflow-docs/system-overview.md, projects/taskflow-docs/backup-and-recovery.md |
| How do we undo a broken rollout? | paraphrase | search_docs | 0 | 0 | projects/demo-app/.venv/Lib/site-packages/fastapi/.agents/skills/fastapi/SKILL.md, projects/release-assistant/release-notes-demo-app-v1.1.0.draft.md, projects/code-reviewer/projects/demo-app.md |
| How do we undo a broken rollout? | paraphrase | search_docs_semantic | 0 | 0 | projects/code-reviewer/context/doc-repos.md, projects/code-reviewer/skills/review-docs/SKILL.md, projects/demo-app/SECURITY.md |
| How do we undo a broken rollout? | paraphrase | search_docs_embeddings | 0 | 1 | projects/demo-app/CHANGELOG.md, projects/taskflow-docs/deployment.md, projects/code-reviewer/.github/pull_request_template.md |
| Where does repeatedly unsuccessful background work end up? | paraphrase | search_docs | 0 | 0 | projects/demo-app/.venv/Lib/site-packages/fastapi/.agents/skills/fastapi/SKILL.md, projects/demo-app/.venv/Lib/site-packages/fastapi/.agents/skills/fastapi/references/dependencies.md, projects/code-reviewer/projects/demo-app.md |
| Where does repeatedly unsuccessful background work end up? | paraphrase | search_docs_semantic | 0 | 0 | projects/taskflow-docs/adr/0003-rq-over-celery.md, projects/taskflow-docs/architecture.md, projects/code-reviewer/context/doc-repos.md |
| Where does repeatedly unsuccessful background work end up? | paraphrase | search_docs_embeddings | 0 | 0 | projects/taskflow-docs/adr/0003-rq-over-celery.md, projects/taskflow-docs/observability.md, projects/taskflow-docs/adr/0003-rq-over-celery.md |
| How can a caller tell whether a process is ready to accept requests? | paraphrase | search_docs | 0 | 0 | projects/demo-app/.venv/Lib/site-packages/fastapi/.agents/skills/fastapi/SKILL.md, projects/release-assistant/release-notes-demo-app-v1.1.0.draft.md, projects/release-assistant/release-notes-demo-app-v1.2.0.draft.md |
| How can a caller tell whether a process is ready to accept requests? | paraphrase | search_docs_semantic | 0 | 0 | projects/release-assistant/README.md, projects/taskflow-api-docs/rate-limiting.md, projects/taskflow-docs/authentication.md |
| How can a caller tell whether a process is ready to accept requests? | paraphrase | search_docs_embeddings | 0 | 0 | projects/taskflow-docs/architecture.md, projects/taskflow-docs/authentication.md, projects/release-assistant/manual.release-notes-demo-app-v1.1.0.draft.md |
| Are earlier versions of a discussion entry preserved after correction? | synonym | search_docs | 0 | 0 | projects/demo-app/.venv/Lib/site-packages/fastapi/.agents/skills/fastapi/SKILL.md, projects/release-assistant/release-notes-demo-app-v1.1.0.draft.md, projects/release-assistant/release-notes-demo-app-v1.2.0.draft.md |
| Are earlier versions of a discussion entry preserved after correction? | synonym | search_docs_semantic | 0 | 0 | projects/demo-app/SECURITY.md, projects/taskflow-docs/adr/0002-cursor-pagination.md, projects/demo-app/.venv/Lib/site-packages/httpcore-1.0.9.dist-info/licenses/LICENSE.md |
| Are earlier versions of a discussion entry preserved after correction? | synonym | search_docs_embeddings | 1 | 1 | projects/taskflow-api-docs/data-model.md, projects/demo-app/CHANGELOG.md, projects/code-reviewer/skills/review-docs/SKILL.md |
| Who authorizes pushing a build live? | paraphrase | search_docs | 0 | 0 | projects/demo-app/.venv/Lib/site-packages/fastapi/.agents/skills/fastapi/SKILL.md, projects/release-assistant/release-notes-demo-app-v1.1.0.draft.md, projects/release-assistant/release-notes-demo-app-v1.2.0.draft.md |
| Who authorizes pushing a build live? | paraphrase | search_docs_semantic | 0 | 0 | projects/taskflow-docs/security.md, projects/taskflow-docs/environments.md, projects/release-assistant/release-notes-demo-app-v1.1.0.draft.md |
| Who authorizes pushing a build live? | paraphrase | search_docs_embeddings | 0 | 0 | projects/code-reviewer/skills/review-pr/SKILL.md, projects/taskflow-docs/environments.md, projects/taskflow-docs/security.md |
| What should responders do if private contact information escapes into diagnostics? | synonym | search_docs | 0 | 0 | projects/code-reviewer/skills/review-docs/SKILL.md, projects/release-assistant/release-notes-demo-app-v1.2.0.draft.md, projects/release-assistant/release-notes-demo-app-v1.1.0.draft.md |
| What should responders do if private contact information escapes into diagnostics? | synonym | search_docs_semantic | 0 | 0 | projects/demo-app/.pytest_cache/README.md, projects/code-reviewer/context/doc-repos.md, projects/code-reviewer/SECURITY.md |
| What should responders do if private contact information escapes into diagnostics? | synonym | search_docs_embeddings | 1 | 1 | projects/taskflow-docs/incident-runbook.md, projects/taskflow-docs/incident-runbook.md, projects/demo-app/SECURITY.md |
