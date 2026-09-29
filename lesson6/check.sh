#!/usr/bin/env bash
# Smoke test: the calculator, the retrieval grade for each chunking, and the full eval
# compared with the baseline in evals/baseline.json.
set -euo pipefail
cd "$(dirname "$0")"
export TOKENIZERS_PARALLELISM=false
PY=.venv/bin/python
[ -x "$PY" ] || { echo "Run ./setup.sh first."; exit 1; }

echo "== Calculator checks"
"$PY" test_tools.py | tail -1

echo "== Retrieval grade for each chunking (no model)"
"$PY" - 2>/dev/null <<'PYEOF'
import eval_app as e
from app import Index, load_chunks
cases = e.load_cases()
for strategy in ["sections", "fixed", "overlap", "whole"]:
    index = Index(load_chunks(strategy))
    hits = [h for h in (e.retrieval_hit(index, c) for c in cases) if h is not None]
    print(f"  {strategy:<9} {sum(hits)}/{len(hits)}")
PYEOF

if command -v ollama >/dev/null && ollama list >/dev/null 2>&1; then
  echo "== Full eval, compared with the baseline (${LOCAL_MODEL:-llama3.2}, 3 runs)"
  "$PY" eval_app.py --runs 3 --compare 2>/dev/null | sed -n '/^Kind/,/^Model calls/p;/Compared/,$p'
else
  echo "== Full eval: SKIPPED (Ollama is not running)"
fi

echo "All checks passed."
