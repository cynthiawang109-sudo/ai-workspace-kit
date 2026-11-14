#!/usr/bin/env bash
# Human-run promotion: doc-search stays credential-free and is not involved.
set -euo pipefail
die() { echo "promote-draft: $*" >&2; exit 1; }
draft=${1:-}
[[ -n "$draft" ]] || die 'Usage: promote-draft.sh DRAFT [--project N]'
shift
project=${AI_WORKSPACE_PROJECT:-}
if (($#)); then
    [[ $# == 2 && $1 == --project ]] || die 'Usage: promote-draft.sh DRAFT [--project N]'
    project=$2
fi
[[ -z "$project" || "$project" =~ ^[0-9]+$ ]] || die 'Project must be a project number.'
command -v gh >/dev/null 2>&1 || die 'gh is missing; install the GitHub CLI first.'
gh auth status >/dev/null 2>&1 || die 'gh is not logged in; run gh auth login first.'
[[ -f "$draft" ]] || die "Draft file does not exist: $draft"
root=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd -P)
allowed=$(realpath -- "$root/tickets/drafts")
path=$(realpath -- "$draft")
[[ "$path" == "$allowed/"* && "$path" == "$root/tickets/drafts/"* ]] || die 'Draft must be under tickets/drafts/.'
# Like list_tickets, split at the first two --- markers and first colon.
content=''
IFS= read -r -d '' content < "$path" || true
[[ "$content" == ---* ]] || die 'Draft must have --- delimited front matter.'
rest=${content#---}
[[ "$rest" == *---* ]] || die 'Draft must have --- delimited front matter.'
meta=${rest%%---*}
body=${rest#*---}
title=''
status=''
trim() { local value=$1; value="${value#"${value%%[![:space:]]*}"}"; REPLY="${value%"${value##*[![:space:]]}"}"; }
while IFS= read -r line; do
    [[ "$line" == *:* ]] || continue
    trim "${line%%:*}"; key=$REPLY
    trim "${line#*:}"; value=$REPLY
    case "$key" in title) title=$value ;; status) status=$value ;; esac
done <<< "$meta"
[[ "$status" == draft ]] || die 'Draft status must be draft.'
[[ -n "$title" ]] || die 'Draft title is required.'
relative=${path#"$root/"}
url=$(printf '%s\n\nPromoted from %s (draft-first: filed by a human via scripts/promote-draft)\n' "$body" "$relative" |
    gh issue create --repo cynthiawang109-sudo/ai-workspace-kit --title "$title" --body-file -)
echo "$url"
if [[ -n "$project" ]]; then
    gh project item-add "$project" --owner cynthiawang109-sudo --url "$url" || die "Issue created at $url, but adding it to Project $project failed."
    echo "Added to Project $project."
else
    echo 'No Project configured; issue was not added to a board.'
fi
