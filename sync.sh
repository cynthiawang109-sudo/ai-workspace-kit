#!/usr/bin/env bash
# Materialize versions.txt pins in projects/. Dirty checkouts are warned and skipped.
# Main-tip pins stay on main; historical pins use detached HEAD.
# Usage: ./sync.sh [substring] [--update-pins]
# --update-pins fetches origin/main and rewrites selected pins without moving checkouts.
set -u
cd "$(dirname "$0")"
ONLY=""
UPDATE=0
for arg in "$@"; do
    case "$arg" in
        --update-pins) UPDATE=1 ;;
        --*) echo "Unknown option: $arg" >&2; exit 1 ;;
        *) ONLY="$arg" ;;
    esac
done
[ -f versions.txt ] || { echo "ERROR: versions.txt missing" >&2; exit 1; }
failed=""
changed=0
# Preserve comments, line endings and all unselected pins; only write when changed.
while read -r name url; do
    case "$name" in ""|\#*) continue ;; esac
    url=${url%$'\r'}
    [[ "$name" == *"$ONLY"* ]] || continue
    pin=$(awk -v name="$name" '$1 == name {sub(/\r$/, "", $2); print $2; exit}' versions.txt)
    if [[ ! "$pin" =~ ^[0-9a-fA-F]{40}$ ]]; then
        echo "ERROR: $name : missing or invalid pin in versions.txt" >&2
        failed="$failed $name"; continue
    fi
    dest="projects/$name"
    temporary=""
    if [ -e "$dest" ] && [ ! -e "$dest/.git" ]; then
        echo "ERROR: $name : $dest exists but is not a git checkout" >&2
        failed="$failed $name"; continue
    fi
    if [ "$UPDATE" -eq 0 ] && [ -e "$dest/.git" ]; then
        if ! dirty=$(git -C "$dest" status --porcelain); then
            failed="$failed $name"; continue
        fi
        if [ -n "$dirty" ]; then
            echo "WARNING: $name : uncommitted changes - skipped, nothing touched" >&2
            continue
        fi
    fi
    if [ ! -e "$dest/.git" ]; then
        if [ "$UPDATE" -eq 1 ]; then
            temporary=$(mktemp -d) || exit 1
            dest="$temporary"
            if ! git init --bare -q "$dest" || ! git -C "$dest" remote add origin "$url"; then
                rm -rf -- "$temporary"; failed="$failed $name"; continue
            fi
        else
            mkdir -p projects
            echo "== $name : clone"
            if ! git clone "$url" "$dest"; then failed="$failed $name"; continue; fi
        fi
    fi
    if ! git -C "$dest" fetch origin +refs/heads/main:refs/remotes/origin/main; then
        [ -z "$temporary" ] || rm -rf -- "$temporary"
        failed="$failed $name"; continue
    fi
    tip=$(git -C "$dest" rev-parse refs/remotes/origin/main)
    if [ "$UPDATE" -eq 1 ]; then
        if [ "$pin" != "$tip" ]; then
            # Bash builtins preserve CRLF and trailing newlines on Windows too.
            contents=""
            IFS= read -r -d '' contents < versions.txt || :
            if [[ "$contents" =~ (^|$'\n')("$name"[[:blank:]]+)$pin ]]; then
                prefix=${BASH_REMATCH[2]}
                contents=${contents/"$prefix$pin"/"$prefix$tip"}
            fi
            if ! printf '%s' "$contents" > versions.txt; then
                failed="$failed $name"
                [ -z "$temporary" ] || rm -rf -- "$temporary"
                continue
            fi
            echo "== $name : pin $pin -> $tip"
            changed=$((changed + 1))
        fi
        [ -z "$temporary" ] || rm -rf -- "$temporary"
        continue
    fi
    head=$(git -C "$dest" rev-parse HEAD)
    branch=$(git -C "$dest" rev-parse --abbrev-ref HEAD)
    if [ "$head" = "$pin" ] && { [ "$pin" != "$tip" ] || [ "$branch" != HEAD ]; }; then
        echo "== $name : already at pin $pin"
    elif [ "$pin" = "$tip" ]; then
        if ! git -C "$dest" checkout main || ! git -C "$dest" merge --ff-only "$tip"; then
            failed="$failed $name"
        elif [ "$(git -C "$dest" rev-parse HEAD)" != "$pin" ]; then
            echo "ERROR: $name : main has local commits beyond pin $pin" >&2
            failed="$failed $name"
        fi
    elif ! git -C "$dest" checkout --detach "$pin"; then
        echo "ERROR: $name : cannot check out pin $pin" >&2
        failed="$failed $name"
    fi
done < repos.txt
if [ -n "$failed" ]; then echo "Sync finished with problems:$failed" >&2; exit 1; fi
if [ "$UPDATE" -eq 1 ]; then echo "Pin update complete: $changed changed pin(s)."; else echo "Sync complete."; fi
