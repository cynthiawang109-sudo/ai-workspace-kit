---
title: TF-116: Populate the GitHub Project board for the workspace
status: draft
---

## Problem

TF-115 moved the system of record to GitHub Issues and PR #22 merged the promotion flow, but the board step is still open: the user-level Project created on 2026-11-13 (Project #1, currently untitled) has no name, and none of the migrated issues are on it.

## Change

1. Rename Project #1 (for example to `ai-workspace-kit`) and link it to this repo.
2. Add Issues #9-#21 (the migrated TF-101 to TF-114 tickets) and Issue #24 (TF-115) with Status Done; add this issue as Todo.
3. This needs the `project` scope on the maintainer's gh token (`gh auth refresh -s project`, which only the maintainer can grant), or manual edits in the web UI.
