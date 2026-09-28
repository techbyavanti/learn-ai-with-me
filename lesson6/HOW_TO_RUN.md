# How to Run Ask My Docs as a Service (lesson 6)

There are two ways to run lesson 6:

- **A. On your computer** (macOS, Linux, or Windows)
- **B. On Google Cloud** in a Jupyter notebook (Vertex AI Workbench or Colab Enterprise)

In both cases the frontier model (Claude) is optional. Without an API key, everything
works except questions with `--hard`.

---

## A. On your computer

### 1. Install the tools

- Python 3.10 or later: `python3 --version`
- [Ollama](https://ollama.com), for the local model
- Git

### 2. Get the code

```bash
git clone https://github.com/techbyavanti/learn-ai-with-me.git
cd learn-ai-with-me/lesson6
```

### 3. Set up

macOS and Linux:

```bash
./setup.sh
source .venv/bin/activate
```

`setup.sh` creates the `.venv` folder, installs the packages, and downloads the
`llama3.2` model with Ollama if it is missing.

Windows (PowerShell):

```powershell
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
ollama pull llama3.2
```

### 4. (Optional) Add your Claude API key

Get a key from the Claude Console. Do not write the key in your code.

```bash
export ANTHROPIC_API_KEY=your-key-here          # macOS and Linux
$env:ANTHROPIC_API_KEY = "your-key-here"        # Windows PowerShell
```

### 5. Check that everything works

```bash
./check.sh
```

Expected output (the times change from computer to computer):

```
== Calculator checks
All calculator checks passed.
== Start the service on port 8765
Ready: 26 chunks, loaded in 6.2 s
== GET /health
{"status":"ok","chunks":26,...}
== POST /ask (one search), then the same question with the agent
{"answer":"... 5 to 7 business days ...","mode":"single",...}
...
== Small load test (4 people at the same time)
Users Mode    Questions  Median s    p95 s    Max s  Questions/s  Failed
    4 single         16      1.70     2.12     2.28         2.22       0
All checks passed.
```

### 6. Start the service and ask questions

```bash
uvicorn server:app --port 8000
```

Wait for `Ready: 26 chunks`. Then open http://localhost:8000 in a browser, or use a second terminal:

```bash
curl -s localhost:8000/health
curl -s localhost:8000/ask -H 'Content-Type: application/json' \
     -d '{"question": "How long until I get my money back?", "mode": "single"}'
python load_test.py --users 1 4 8                  # the load test
python load_test.py --users 8 --mode agent         # the agent under load
```

Settings (environment variables, before `uvicorn`): `MAX_BUSY` (default 2), `QUEUE_TIMEOUT`
(default 60 seconds), `LOCAL_MODEL`, `AGENT_MODEL`. Example:
`MAX_BUSY=4 QUEUE_TIMEOUT=5 uvicorn server:app --port 8000`.

If you see `address already in use`, another program uses the port. Use `--port 8001`, and
`--url http://localhost:8001` for the load test. Stop the service with Ctrl+C.

If `ollama list` shows a different name for the model (for example `llama3.2:3b`),
set it before you run the app:

```bash
export LOCAL_MODEL=llama3.2:3b
```

---

## B. On Google Cloud (Jupyter notebook)

The notebook [`ask_my_docs_service_gcp.ipynb`](ask_my_docs_service_gcp.ipynb) does all the steps for you:
it gets the code, installs the packages and Ollama, downloads the model, and runs the app.

### Option 1: Vertex AI Workbench

1. In the Google Cloud console, open **Vertex AI → Workbench**.
   Enable the **Notebooks API** if the console asks.
2. Click **Create new**. Use a machine with at least 4 vCPUs and 16 GB RAM
   (for example `e2-standard-4`). A T4 GPU is optional; it makes the local model faster.
3. When the instance is ready, click **Open JupyterLab**.
4. Open a terminal (**File → New → Terminal**) and run:

   ```bash
   git clone https://github.com/techbyavanti/learn-ai-with-me.git
   ```

5. In the file browser, open `learn-ai-with-me/lesson6/ask_my_docs_service_gcp.ipynb`.
6. Select the **Python 3** kernel, then **Run → Run All Cells**.
7. When the notebook asks for `ANTHROPIC_API_KEY`, paste your key, or press Enter to skip.

### Option 2: Colab Enterprise

1. In the Google Cloud console, open **Vertex AI → Colab Enterprise**.
2. Click **Import** and choose **URL**. Use:

   ```
   https://github.com/techbyavanti/learn-ai-with-me/blob/main/lesson6/ask_my_docs_service_gcp.ipynb
   ```

   Or download the notebook file and upload it.
3. Connect to a runtime (the default runtime is enough), then click **Run all**.
   The first cell clones the repository, so the notebook does not need other files.

### What the notebook does

| Section | What happens |
|---|---|
| 1. Get the code | Clones the repository if `app.py` is not in the current folder |
| 2. Install packages | `pip install -r requirements.txt` |
| 3. Ollama | Installs Ollama (Linux) and starts it in the background |
| 4. Settings | Sets the model names, asks for the API key, downloads the local model |
| 5. Start the service | Starts `uvicorn` in the background on a free port |
| 6. Health check | `GET /health` |
| 7. Ask | One search and the agent, through `POST /ask` |
| 8. Load test | 1, 4, and 8 people at the same time |
| 9. From the cache | The same questions two times |
| 10. Clean up | Stops Ollama |

### Costs

Workbench instances and Colab runtimes cost money while they run.
**Stop the instance or the runtime when you are done.** Claude API calls are billed
separately to your Anthropic account.

---

## Troubleshooting

| Problem | Fix |
|---|---|
| `the Ollama model 'llama3.2' is not installed` | Run `ollama pull llama3.2`, or set `LOCAL_MODEL` to a name from `ollama list` |
| `cannot connect to Ollama` | Start Ollama: open the app, or run `ollama serve` |
| `--hard needs the ANTHROPIC_API_KEY environment variable` | Set `ANTHROPIC_API_KEY` (step A4, or enter it in the notebook) |
| `Warning: You are sending unauthenticated requests to the HF Hub` | Harmless. Set `HF_TOKEN` to hide it. |
| The first run is slow | The encoder and the local model download once. Later runs are fast. |
| The local model says "I do not know" for a question that the documents answer | Small models can be too careful. Run with `--show-search` to check that the correct chunk is found, then try `--hard` or a larger model (for example `LOCAL_MODEL=qwen2.5:7b-instruct`). |
| Notebook: `apt-get` or `sudo` fails | Install Ollama from a terminal with `curl -fsSL https://ollama.com/install.sh \| sh`, then run the notebook again |
