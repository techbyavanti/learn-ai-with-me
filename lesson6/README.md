# Ask My Docs: one eval for everything

> New here? Start with [HOW_TO_RUN.md](HOW_TO_RUN.md).

This is the code from the post "How Do You Know Your AI App Got Better? Build One Eval for
Everything" (Tech by Avanti). It adds one eval for the whole app from
[lesson 5](../lesson5/) ([post](https://techbyavanti.substack.com/p/one-search-is-not-always-enough-build)).
The app code is the same as in lesson 5.

| Part | File | What it does |
|---|---|---|
| Test set | `evals/evalset.jsonl` | 28 cases: 12 simple, 6 multi-step, 6 unanswerable, 4 attacks |
| Graders | `eval_app.py` | Pass or fail for each answer, with a reason; a separate grade for the search |
| Repeated runs | `eval_app.py --runs 3` | The pass rate for each kind, with the lowest and highest run |
| Judge check | `eval_judge.py`, `evals/labeled_answers.jsonl` | How often a judge model agrees with answers labeled by hand |
| Regressions | `eval_app.py --compare`, `evals/baseline.json` | Fails when a kind drops > 10 points, a case now fails most of the time, or an attack gets through |

## Results

`python eval_app.py --runs 3` (one search, `llama3.2:3b`) and
`AGENT_MODEL=qwen2.5:7b-instruct python eval_app.py --mode agent --runs 3`:

| Kind | Cases | One search, llama3.2 | Agent, qwen2.5 |
|---|---|---|---|
| simple | 12 | 97% | 100% |
| multi-step | 6 | 0% | 33% |
| unanswerable | 6 | 100% | 83% |
| attack | 4 | 100% | 100% |
| **all** | 28 | **77%** | **82%** |

Three sessions of the same eval gave 81%, 97%, and 94% for simple questions: small changes
can be chance.

`python eval_judge.py --models llama3.2:3b qwen2.5:7b-instruct` (29 labeled answers):

| Judge | Agrees with me | Wrong answers caught | Correct answers blocked |
|---|---|---|---|
| llama3.2 (3B) | 24 of 29 | 17 of 17 | 5 of 12 |
| qwen2.5 (7B) | 26 of 29 | 15 of 17 | 1 of 12 |

A bad change on purpose (`--strategy fixed --compare`): simple dropped 8 and 17 points in two
tries, and both times the compare named the backup question and failed.

## Files

| File | Purpose |
|---|---|
| `eval_app.py` | The eval (`--mode`, `--runs`, `--strategy`, `--save-baseline`, `--compare`, `-v`) |
| `eval_judge.py` | Grades a judge model against the labeled answers |
| `evals/` | The test set, the labeled answers, and the baseline (results go to `evals/results/`, not in Git) |
| `app.py`, `agent.py`, `tools.py`, `guardrails.py`, `cache.py`, `chunking.py`, `docs/` | From lesson 5 |
| `eval_guardrails.py`, `test_tools.py` | From lessons 4 and 5 |
| `setup.sh` / `check.sh` | Set up; the calculator, the retrieval grade, and the eval against the baseline |
| `build_notebook.py` | Builds `ask_my_docs_evals_gcp.ipynb` |
| `ask_my_docs_evals_gcp.ipynb` | Jupyter notebook for Google Cloud (Vertex AI Workbench or Colab Enterprise) |
| `HOW_TO_RUN.md` | Step-by-step guide for your computer and for Google Cloud |

## Quick start

```bash
./setup.sh                           # one time
source .venv/bin/activate
./check.sh                           # includes the eval against the baseline (a few minutes)
python eval_app.py -v                # every answer, graded
python eval_app.py --strategy fixed --compare    # a bad change: the compare fails
```

When you change the app, run `python eval_app.py --compare`. When a change is good and you
want to keep it, save it: `python eval_app.py --save-baseline`.

## Limits

- 28 cases is a start. Add every bug that users find as a new case.
- The graders check facts with text matching. A correct answer in other words (for example
  "twelve hundred" for 1200) fails. Read the failures before you trust a score.
- A judge model is not used in the eval, because neither local judge agreed with the labels
  well enough.
- The results store what the user saw. When the guardrails block an answer, the model's
  original answer is not saved.
