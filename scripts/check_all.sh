#!/usr/bin/env bash
# Set up (if needed) and run check.sh in every lesson, or in the lessons you name.
#
#   scripts/check_all.sh                     all lessons
#   scripts/check_all.sh lesson2 lesson4     only these lessons
#   scripts/check_all.sh --upgrade           first upgrade the Python packages to the newest versions
#   scripts/check_all.sh --fresh             first delete and re-create each .venv and .cache
#
# Uses LOCAL_MODEL and ANTHROPIC_API_KEY from your environment, like the lessons.
set -uo pipefail
source "$(dirname "$0")/_common.sh"

UPGRADE=0; FRESH=0; ARGS=()
for a in "$@"; do
  case "$a" in
    --upgrade) UPGRADE=1 ;;
    --fresh) FRESH=1 ;;
    *) ARGS+=("$a") ;;
  esac
done

failed=()
for lesson in $(lessons ${ARGS[@]+"${ARGS[@]}"}); do
  echo; echo "################ $lesson ################"
  cd "$ROOT/$lesson" || { failed+=("$lesson (missing)"); continue; }
  if [ "$FRESH" = 1 ]; then rm -rf .venv .cache; fi
  if [ ! -x .venv/bin/python ]; then ./setup.sh || { failed+=("$lesson (setup)"); continue; }; fi
  if [ "$UPGRADE" = 1 ]; then
    .venv/bin/pip install -q --upgrade -r requirements.txt || { failed+=("$lesson (upgrade)"); continue; }
  fi
  ./check.sh || failed+=("$lesson")
done

echo
if [ "${#failed[@]}" -gt 0 ]; then
  echo "FAILED: ${failed[*]}"
  exit 1
fi
echo "All lessons passed."
