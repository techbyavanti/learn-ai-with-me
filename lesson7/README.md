# Ask My Docs: from script to app

> New here? Start with [HOW_TO_RUN.md](HOW_TO_RUN.md).

This is the code from the post "From Script to App: Turn Your RAG Script Into a Web App"
(Tech by Avanti). It is the [lesson 5](../lesson5/) ([post](https://techbyavanti.substack.com/p/one-search-is-not-always-enough-build)) app, measured with the eval from lesson 6, as a web app: one process loads
the documents, the vectors, the encoder, and the model one time, then answers many people
in a browser. The post builds it in six steps: measure the script, load once, add an API,
add a web page, make it safe for many people, and measure it.

| Part | What it does |
|---|---|
| `lifespan` | Loads everything before the first request, and warms up the model |
| `POST /ask` | `{"question": "...", "mode": "agent" or "single", "steps": true/false}` → the answer as JSON |
| `GET /health` | Status, what was loaded, uptime, questions served |
| `GET /` | The app page (`static/index.html`): questions and answers, an agent switch, the agent's steps, a status line, and links like `/?q=...` that ask a question |
| Locks | The encoder and the answer cache are used by one request at a time |
| `MAX_BUSY` (default 2) | At most this many requests work with the model at the same time |
| `QUEUE_TIMEOUT` (default 60 s) | A request that waits longer gets "busy, try again" (HTTP 503) |
| Agent answer cache | Key = question + a fingerprint of all chunks; only answers that passed the guardrails |

## Results

The lesson 5 script needs about 5 seconds to start for each question. The app starts one
time (6.1 s), then answers. From `python load_test.py --users 1 4 8` (16 questions, one search,
`llama3.2:3b`, `MAX_BUSY=2`, on a laptop):

| People at the same time | Median wait | p95 wait | Questions each second |
|---|---|---|---|
| 1 | 0.58 s | 1.45 s | 1.46 |
| 4 | 1.59 s | 2.55 s | 2.15 |
| 8 | 3.24 s | 4.07 s | 2.16 |

With 8 people: `MAX_BUSY=1` gave 1.79 questions each second, `MAX_BUSY=4` gave 2.13 (no gain
over 2: the model is the limit). Answers from the cache: 0.11 s median, 62 questions each
second. The agent: 0.66 questions each second with 1 person, 0.75 with 4.

## Files

| File | Purpose |
|---|---|
| `server.py` | The app server (FastAPI): load once, `/ask`, `/health`, `/` |
| `static/index.html` | The web page that people use (plain HTML and JavaScript) |
| `load_test.py` | Sends questions with many people at the same time (`--users`, `--mode`, `--repeat`) |
| `app.py`, `agent.py`, `tools.py`, `guardrails.py`, `cache.py`, `chunking.py`, `docs/` | From lesson 5 |
| `eval_app.py`, `eval_judge.py`, `evals/` | The eval from lesson 6: `check.sh` runs it against the baseline |
| `eval_guardrails.py`, `test_tools.py` | From lessons 4 and 5 |
| `setup.sh` / `check.sh` | Set up; start the service, check it, and stop it |
| `build_notebook.py` | Builds `ask_my_docs_app_gcp.ipynb` |
| `ask_my_docs_app_gcp.ipynb` | Jupyter notebook for Google Cloud (Vertex AI Workbench or Colab Enterprise) |
| `HOW_TO_RUN.md` | Step-by-step guide for your computer and for Google Cloud |

## Quick start

```bash
./setup.sh                               # one time
source .venv/bin/activate
./check.sh                               # starts the app, tests it, and stops it
uvicorn server:app --port 8000           # start the app; open http://localhost:8000
python load_test.py --users 1 4 8        # in a second terminal
```

If port 8000 is busy on your computer, use another one: `--port 8001` and
`python load_test.py --url http://localhost:8001`.

## Limits

- One process on one computer. For more people, run more copies behind a load balancer, or
  use a bigger machine with a GPU for the model.
- The service has no login. Do not put it on the internet as it is.
- A new document needs a restart of the service (the documents load at the start).
