#!/usr/bin/env bash
# Commit all changes and push them to GitHub.
#
#   scripts/publish.sh "Add lesson 5: agent loops"
#
# It shows what will be committed and asks before it commits.
set -euo pipefail
source "$(dirname "$0")/_common.sh"

MSG="${1:?Give a commit message, for example: scripts/publish.sh \"Update lesson 2\"}"
cd "$ROOT"
git add -A
if git diff --cached --quiet; then
  echo "Nothing to commit."
  exit 0
fi
git status --short
read -r -p "Commit these files and push to GitHub? [y/N] " answer
[ "$answer" = "y" ] || [ "$answer" = "Y" ] || { git reset -q; echo "Stopped. Nothing was committed."; exit 1; }
git commit -q -m "$MSG"
git push
echo "Pushed: $(git log -1 --oneline)"
