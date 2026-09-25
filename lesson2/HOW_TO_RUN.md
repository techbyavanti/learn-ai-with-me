# How to Run Ask My Docs (lesson 2)

There are two ways to run lesson 2:

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
cd learn-ai-with-me/lesson2
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

Expected output:

```
== Chunking eval
Encoder reads at most 256 tokens of each chunk.

Strategy   Chunks  Hit rate  Words sent
whole           6       81%         896
fixed          33       81%         169
overlap        45      100%         177
sections       26      100%         205
== Unknown question (no model call)
26 chunks (sections)
I do not know. No document matches this question.
== Local model (llama3.2)
26 chunks (sections)
... it takes 5 to 7 business days ...
== Frontier model: SKIPPED (ANTHROPIC_API_KEY is not set)
All checks passed.
```

The model's words change from run to run. The eval numbers do not.

### 6. Ask questions

```bash
python app.py "How long until I get my money back?"                      # sections chunking (default)
python app.py "How long until I get my money back?" --strategy whole --show-search
python app.py "Can a school with 60 users pay by bank transfer?" --hard   # frontier model
python app.py --docs path/to/your/docs                                   # chat mode with your files
```

If `ollama list` shows a different name for the model (for example `llama3.2:3b`),
set it before you run the app:

```bash
export LOCAL_MODEL=llama3.2:3b
```

---

## B. On Google Cloud (Jupyter notebook)

The notebook [`ask_my_docs_gcp.ipynb`](ask_my_docs_gcp.ipynb) does all the steps for you:
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

5. In the file browser, open `learn-ai-with-me/lesson2/ask_my_docs_gcp.ipynb`.
6. Select the **Python 3** kernel, then **Run → Run All Cells**.
7. When the notebook asks for `ANTHROPIC_API_KEY`, paste your key, or press Enter to skip.

### Option 2: Colab Enterprise

1. In the Google Cloud console, open **Vertex AI → Colab Enterprise**.
2. Click **Import** and choose **URL**. Use:

   ```
   https://github.com/techbyavanti/learn-ai-with-me/blob/main/lesson2/ask_my_docs_gcp.ipynb
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
| 5. Compare | Runs the chunking eval for all four strategies |
| 6. Search results | Shows the top chunks of each strategy for one question |
| 7. Local model | Asks questions with the local model |
| 8. Frontier model | Asks a question with Claude (only with an API key) |
| 9. Your documents | Chunks and searches a folder of your own `.md` files |
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
