#!/usr/bin/env bash
# doctor.sh - one-command health check for this workspace (bash twin of
# doctor.ps1). Verifies layout, sub-repo git state, the doc-search
# virtual environment, Codex MCP registration, and the presence (never
# the value) of the GitHub token. Exits non-zero on any failed check.
#
# Usage:  ./doctor.sh        (from the workspace root)

set -u
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
FAIL=0
WARN=0

report() { # status name detail
  [ "$1" = "fail" ] && FAIL=$((FAIL + 1))
  [ "$1" = "warn" ] && WARN=$((WARN + 1))
  printf '%-6s %s - %s\n' "[$1]" "$2" "$3"
}

echo "ai-workspace-kit doctor - $ROOT"
echo

REPOS=$(grep -v '^#' "$ROOT/repos.txt" | awk 'NF {print $1}')

# 1. Workspace layout.
for name in $REPOS; do
  if [ -d "$ROOT/projects/$name" ]; then
    report ok "layout/$name" "present"
  else
    report fail "layout/$name" "missing - run ./sync.sh"
  fi
done

# 2. Git state of each checkout.
for name in $REPOS; do
  path="$ROOT/projects/$name"
  [ -d "$path" ] || continue
  branch=$(git -C "$path" rev-parse --abbrev-ref HEAD 2>/dev/null)
  dirty=$(git -C "$path" status --porcelain 2>/dev/null | wc -l | tr -d ' ')
  if [ "$branch" != "main" ]; then
    report warn "git/$name" "on branch '$branch', expected 'main'"
  elif [ "$dirty" -gt 0 ]; then
    report warn "git/$name" "$dirty uncommitted change(s)"
  else
    report ok "git/$name" "main, clean"
  fi
done

# 3. doc-search virtual environment.
VENV_PY="$ROOT/mcp/doc-search/.venv/bin/python"
# Windows venvs use Scripts/python.exe instead of bin/python.
[ -x "$VENV_PY" ] || VENV_PY="$ROOT/mcp/doc-search/.venv/Scripts/python.exe"
if [ ! -x "$VENV_PY" ]; then
  report fail "doc-search venv" "missing - see mcp/doc-search/README.md setup"
else
  ver=$("$VENV_PY" -c "import fastmcp, sys; print(sys.version.split()[0] + ' / fastmcp ' + fastmcp.__version__)" 2>/dev/null)
  if [ -n "$ver" ]; then
    report ok "doc-search venv" "$ver"
  else
    report fail "doc-search venv" "present but fastmcp is not importable"
  fi
fi

# 4. Codex MCP registration (config-file check; the CLI prints the same).
CODEX_CFG="$HOME/.codex/config.toml"
if [ -f "$CODEX_CFG" ]; then
  if grep -q 'mcp_servers.doc-search' "$CODEX_CFG"; then
    report ok "codex mcp/doc-search" "registered"
  else
    report fail "codex mcp/doc-search" "not registered - see mcp/README.md"
  fi
  if grep -q 'mcp_servers.github' "$CODEX_CFG"; then
    report ok "codex mcp/github" "registered"
  else
    report warn "codex mcp/github" "not registered - see mcp/README.md"
  fi
else
  report warn "codex" "no ~/.codex/config.toml - MCP registration unchecked"
fi

# 5. GITHUB_PAT present (value never printed).
if [ -n "${GITHUB_PAT:-}" ]; then
  report ok "GITHUB_PAT" "set (length ${#GITHUB_PAT})"
else
  report warn "GITHUB_PAT" "not set in this shell - the github MCP server cannot authenticate"
fi

# 6. gh CLI login.
if command -v gh >/dev/null 2>&1; then
  status=$(gh auth status 2>&1)
  if echo "$status" | grep -q 'Logged in to github.com'; then
    if echo "$status" | grep -q 'workflow'; then
      report ok "gh" "logged in, workflow scope present"
    else
      report warn "gh" "logged in but workflow scope missing - cannot push Actions files"
    fi
  else
    report fail "gh" "not logged in (or token invalid)"
  fi
else
  report warn "gh" "CLI not found"
fi

echo
if [ "$FAIL" -gt 0 ]; then
  echo "Result: $FAIL failing check(s), $WARN warning(s)."
  exit 1
fi
echo "Result: all hard checks passed ($WARN warning(s))."
exit 0
