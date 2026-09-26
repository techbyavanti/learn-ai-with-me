#!/usr/bin/env bash
# Rebuild each lesson's Google Cloud notebook from build_notebook.py, then run it from top
# to bottom on this computer. It fails if any cell fails.
#
#   scripts/test_notebooks.sh                all lessons
#   scripts/test_notebooks.sh lesson4        only lesson 4
#
# The executed copies go to a temporary folder. The notebooks in the repo stay without outputs.
# Needs Ollama running (the notebooks use the local model). Set LOCAL_MODEL if needed.
set -uo pipefail
source "$(dirname "$0")/_common.sh"

OUT="$(mktemp -d)"
failed=()
for lesson in $(lessons "$@"); do
  echo; echo "################ $lesson ################"
  cd "$ROOT/$lesson" || { failed+=("$lesson (missing)"); continue; }
  if [ ! -x .venv/bin/python ]; then ./setup.sh || { failed+=("$lesson (setup)"); continue; }; fi
  .venv/bin/pip install -q -r "$ROOT/requirements-dev.txt" || { failed+=("$lesson (dev packages)"); continue; }
  .venv/bin/python build_notebook.py || { failed+=("$lesson (build)"); continue; }
  for nb in *.ipynb; do
    echo "Running $nb ..."
    if env -u ANTHROPIC_API_KEY .venv/bin/jupyter nbconvert --to notebook --execute "$nb" \
        --output "$OUT/$lesson-$nb" --ExecutePreprocessor.timeout=1800 >/dev/null 2>"$OUT/$lesson.log"; then
      echo "ok   $nb"
    else
      echo "FAIL $nb (see $OUT/$lesson.log)"
      failed+=("$lesson")
    fi
  done
  rm -rf bad_docs  # made by the lesson 4 notebook
done

echo
echo "Executed notebooks: $OUT"
if [ "${#failed[@]}" -gt 0 ]; then
  echo "FAILED: ${failed[*]}"
  exit 1
fi
echo "All notebooks ran."
