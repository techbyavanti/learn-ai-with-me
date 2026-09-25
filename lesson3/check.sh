#!/usr/bin/env bash
# Smoke test: check the caches, time them, and ask one question for each model that is available.
set -euo pipefail
cd "$(dirname "$0")"
export TOKENIZERS_PARALLELISM=false
PY=.venv/bin/python
[ -x "$PY" ] || { echo "Run ./setup.sh first."; exit 1; }

echo "== Cache checks"
"$PY" test_cache.py 2>/dev/null

echo "== Benchmark (small)"
"$PY" benchmark.py --copies 20 2>/dev/null

echo "== Start the app two times"
"$PY" app.py "What is the capital of France?" 2>/dev/null | head -1
second=$("$PY" app.py "What is the capital of France?" 2>/dev/null | head -1)
echo "$second"
grep -q " 0 embedded" <<<"$second" || { echo "FAIL: the second start embedded chunks again"; exit 1; }

if command -v ollama >/dev/null && ollama list >/dev/null 2>&1; then
  echo "== Local model (${LOCAL_MODEL:-llama3.2}), two times: model, then answer cache"
  "$PY" app.py "How long until I get my money back?" 2>/dev/null | tail -2
  "$PY" app.py "How long until I get my money back?" 2>/dev/null | tail -2
else
  echo "== Local model: SKIPPED (Ollama is not running)"
fi

if [ -n "${ANTHROPIC_API_KEY:-}" ]; then
  echo "== Frontier model (--hard)"
  "$PY" app.py "Can a school with 60 users pay by bank transfer, and what discount does it get?" --hard 2>/dev/null | tail -2
else
  echo "== Frontier model: SKIPPED (ANTHROPIC_API_KEY is not set)"
fi

echo "All checks passed."
