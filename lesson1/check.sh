#!/usr/bin/env bash
# Smoke test: run the retrieval eval and one question for each model that is available.
set -euo pipefail
cd "$(dirname "$0")"
export TOKENIZERS_PARALLELISM=false
PY=.venv/bin/python
[ -x "$PY" ] || { echo "Run ./setup.sh first."; exit 1; }

echo "== Retrieval eval"
out=$("$PY" eval_retrieval.py 2>/dev/null)
echo "$out"
grep -q "hit rate: 100%" <<<"$out" || { echo "FAIL: retrieval eval below 100%"; exit 1; }

echo "== Unknown question (no model call)"
"$PY" app.py "What is the capital of France?" 2>/dev/null

if command -v ollama >/dev/null && ollama list >/dev/null 2>&1; then
  echo "== Local model (${LOCAL_MODEL:-llama3.2})"
  "$PY" app.py "How long do refunds take?" 2>/dev/null
else
  echo "== Local model: SKIPPED (Ollama is not running)"
fi

if [ -n "${ANTHROPIC_API_KEY:-}" ]; then
  echo "== Frontier model (--hard)"
  "$PY" app.py "Which plan do I need for 5 projects, and what does it cost?" --hard 2>/dev/null
else
  echo "== Frontier model: SKIPPED (ANTHROPIC_API_KEY is not set)"
fi

echo "All checks passed."
