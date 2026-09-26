#!/usr/bin/env bash
# Start a new lesson as a copy of the last one.
#
#   scripts/new_lesson.sh 5
#
# Copies lesson4 (or the lesson before the number you give) to lesson5, without .venv,
# .cache, and the old notebook. Then it prints the next steps from MAINTAINING.md.
set -euo pipefail
source "$(dirname "$0")/_common.sh"

N="${1:?Give the new lesson number, for example: scripts/new_lesson.sh 5}"
PREV="lesson$((N - 1))"
NEW="lesson$N"
cd "$ROOT"
[ -d "$PREV" ] || { echo "$PREV does not exist."; exit 1; }
[ ! -e "$NEW" ] || { echo "$NEW already exists."; exit 1; }

mkdir "$NEW"
tar -C "$PREV" --exclude .venv --exclude .cache --exclude __pycache__ --exclude '*.ipynb' -cf - . | tar -C "$NEW" -xf -
# The notebook builder and the guide name their lesson; point them at the new one.
sed -i.bak "s/$PREV/$NEW/g" "$NEW/build_notebook.py" "$NEW/HOW_TO_RUN.md" && rm -f "$NEW"/*.bak
sed -i.bak "s/lesson $((N - 1))/lesson $N/g" "$NEW/HOW_TO_RUN.md" "$NEW/build_notebook.py" && rm -f "$NEW"/*.bak

cat <<MSG
Created $NEW from $PREV.

Next steps (details in MAINTAINING.md, "Create a new lesson"):
  1. Change the code in $NEW, and add an eval script that measures the new idea.
  2. Update $NEW/check.sh, README.md, HOW_TO_RUN.md, and build_notebook.py.
  3. cd $NEW && ./setup.sh && ./check.sh
  4. scripts/test_notebooks.sh $NEW
  5. Add $NEW to the table in the root README.md.
  6. scripts/publish.sh "Add lesson $N: <topic>"
MSG
