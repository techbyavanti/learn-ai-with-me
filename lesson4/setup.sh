#!/usr/bin/env bash
# Create a virtual environment and install the dependencies.
set -euo pipefail
cd "$(dirname "$0")"

python3 -m venv .venv
.venv/bin/pip install --upgrade pip -q
.venv/bin/pip install -r requirements.txt -q

if command -v ollama >/dev/null; then
  model="${LOCAL_MODEL:-llama3.2}"
  if ! ollama list | awk 'NR>1 {print $1}' | grep -qx -e "$model" -e "$model:latest"; then
    echo "Pulling Ollama model $model ..."
    ollama pull "$model"
  fi
else
  echo "Ollama is not installed. Get it from https://ollama.com to use the local model."
fi

echo "Done. Activate the environment with: source .venv/bin/activate"
