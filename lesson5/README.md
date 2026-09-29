# Ask My Docs: an agent loop

> New here? Start with [HOW_TO_RUN.md](HOW_TO_RUN.md).

This is the code from the post ["One Search Is Not Always Enough: Build a Small Agent Loop"](https://techbyavanti.substack.com/p/one-search-is-not-always-enough-build)
(Tech by Avanti). It is the [lesson 4](../lesson4/) ([post](https://techbyavanti.substack.com/p/your-rag-app-will-make-things-up)) app (caches and guardrails) with an agent:
the model decides when to search, when to calculate, and when to answer.

| Part | What it does |
|---|---|
| Tools (`tools.py`) | `search` (the lesson 2 search) and `calculate` (only numbers and + - * /, no code) |
| Loop (`agent.py`) | Asks the model, runs its tool calls, and repeats until it answers |
| Rule 1 | Search first: an answer or a calculation before any search is sent back |
| Rule 2 | Before the loop accepts an answer, every number must come from a search, the calculator, or the question; if not, the answer is sent back |
| Limits | 6 model calls, 4 searches, no repeated search, 2 answers sent back |
| Guardrails | The lesson 4 checks run on the final answer, with the calculator results as evidence |

## Results

From `python eval_agent.py --models llama3.2:3b qwen2.5:7b-instruct --runs 3`
(12 questions, 8 of them multi-step, 3 runs = 36 answers for each row):

| Model | Mode | Multi-step correct | Simple correct | Blocked | Other | Calls | Seconds |
|---|---|---|---|---|---|---|---|
| llama3.2 (3B) | one search | 3/24 | 12/12 | 20/36 | 1/36 | 1.0 | 1.5 |
| llama3.2 (3B) | agent | 3/24 | 12/12 | 12/36 | 9/36 | 3.0 | 3.1 |
| qwen2.5 (7B) | one search | 2/24 | 12/12 | 22/36 | 0/36 | 1.0 | 3.6 |
| qwen2.5 (7B) | agent | 9/24 | 12/12 | 6/36 | 9/36 | 2.8 | 4.6 |

Blocked = stopped by the guardrails. Other = the answer got to the user, but it is wrong,
incomplete, or "I do not know". The answers change from run to run.

## Files

| File | Purpose |
|---|---|
| `tools.py` | The tool descriptions for the model, and the safe calculator |
| `agent.py` | The agent loop, its rules, and its limits |
| `app.py` | The lesson 4 app with `ask_agent` (default), `--single`, and `--show-steps` |
| `eval_agent.py` | One search against the agent (`--models`, `--runs`, `-v`) |
| `test_tools.py` | Checks the calculator, including expressions it must refuse |
| `guardrails.py`, `eval_guardrails.py`, `cache.py`, `chunking.py`, `docs/` | From lesson 4; the number check now also accepts the question and calculator results |
| `setup.sh` / `check.sh` | Set up, and run all checks |
| `build_notebook.py` | Builds `ask_my_docs_agent_gcp.ipynb` |
| `ask_my_docs_agent_gcp.ipynb` | Jupyter notebook for Google Cloud (Vertex AI Workbench or Colab Enterprise) |
| `HOW_TO_RUN.md` | Step-by-step guide for your computer and for Google Cloud |

## Quick start

```bash
./setup.sh                     # one time
source .venv/bin/activate
./check.sh                     # make sure everything works
python app.py "For 5 users, how much do we save in one year with the yearly plan instead of the monthly plan?" --show-steps --show-guard
```

For a better agent: `ollama pull qwen2.5:7b-instruct` and `export AGENT_MODEL=qwen2.5:7b-instruct`.

## Limits

- The agent is only as good as the model that plans. `llama3.2` (3B) did not improve with the agent.
- The checks can see that a number came from the calculator, not that it was the right
  calculation (a forgotten discount passes).
- About 3 model calls for each question instead of 1.
- `--hard` (the frontier model) still uses one search. The agent uses the local model.
