#!/usr/bin/env bash
# sync.sh - clone or fast-forward-update every repo listed in repos.txt
# into projects/. Idempotent. Usage:
#   ./sync.sh          sync everything
#   ./sync.sh docs     sync only repos whose name matches *docs*
set -u
cd "$(dirname "$0")"

ONLY="${1:-}"
mkdir -p projects
failed=""

while read -r name url; do
    case "$name" in
        ""|\#*) continue ;;
    esac
    if [ -n "$ONLY" ]; then
        case "$name" in
            *"$ONLY"*) ;;
            *) continue ;;
        esac
    fi
    dest="projects/$name"
    if [ -d "$dest/.git" ]; then
        echo "== $name : pull --ff-only"
        if ! git -C "$dest" pull --ff-only; then
            echo "WARNING: $name pull failed (local commits or conflicts?) - skipped, nothing overwritten" >&2
            failed="$failed $name"
        fi
    elif [ -e "$dest" ]; then
        echo "WARNING: $name : $dest exists but is not a git checkout - skipped" >&2
        failed="$failed $name"
    else
        echo "== $name : clone"
        if ! git clone "$url" "$dest"; then
            failed="$failed $name"
        fi
    fi
done < repos.txt

if [ -n "$failed" ]; then
    echo "Sync finished with problems:$failed" >&2
    exit 1
fi
echo "Sync complete."
