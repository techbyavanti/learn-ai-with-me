# Ask My Notes

> New here? Start with [HOW_TO_RUN.md](HOW_TO_RUN.md).

A small RAG app in about 60 lines of Python. This is the code from the post
["One Laptop, Two Models, 60 Lines: Build Your First Mini RAG App"](https://techbyavanti.substack.com/p/one-laptop-two-models-60-lines-build) (Tech by Avanti).

The app has four parts:

1. An encoder (`all-MiniLM-L6-v2`) turns each note into an embedding.
2. A search function finds the notes that are closest to the question.
3. A decoder writes an answer from those notes.
4. A router sends the prompt to a local model (Ollama) or to a frontier model (Claude).

## Files

| File | Purpose |
|---|---|
| `app.py` | The pipeline and a command-line interface |
| `notes.py` | The sample notes. Replace them with your texts. |
| `eval_retrieval.py` | A small eval for the search part |
| `setup.sh` | Creates `.venv`, installs the packages, and pulls the Ollama model |
| `check.sh` | Smoke test: runs the eval and one question for each available model |
| `ask_my_notes_gcp.ipynb` | Jupyter notebook for Google Cloud (Vertex AI Workbench or Colab Enterprise) |
| `HOW_TO_RUN.md` | Step-by-step guide for your computer and for Google Cloud |

## Quick start

```bash
./setup.sh                     # one time
source .venv/bin/activate
./check.sh                     # make sure everything works
python app.py "How long do refunds take?"
```

## Setup

You need Python 3.10 or later (tested with Python 3.14). `./setup.sh` does the
steps below for you.

```bash
python -m venv .venv
source .venv/bin/activate      # on Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

Install [Ollama](https://ollama.com), then download a small model:

```bash
ollama pull llama3.2
```

For the frontier model, get an API key from the Claude Console. Put the key in an
environment variable. Do not write the key in your code.

```bash
export ANTHROPIC_API_KEY=your-key-here
```

The first run downloads the encoder model. This takes some time.

To use a different model without changing the code, set an environment variable.
For example, if `ollama list` shows `llama3.2:3b` and not `llama3.2`:

```bash
export LOCAL_MODEL=llama3.2:3b
```

## Usage

Ask one question with the local model:

```bash
python app.py "How long do refunds take?"
```

Use the frontier model for a difficult question:

```bash
python app.py "Which plan do I need for 5 projects, and what does it cost?" --hard
```

Show the search results before the answer:

```bash
python app.py "When can I visit the office?" --show-search
```

Start chat mode:

```bash
python app.py
```

A question that your notes do not answer must give "I do not know":

```bash
python app.py "What is the capital of France?"
```

## Test the search part

```bash
python eval_retrieval.py
```

Run this eval each time you change the encoder, the notes, or the value of `k`.
If an answer is wrong, look at the search results first. The decoder cannot fix
bad search results.

## Settings

Change these values at the top of `app.py`. `LOCAL_MODEL` and `FRONTIER_MODEL` can
also be set as environment variables.

| Setting | Default | Purpose |
|---|---|---|
| `ENCODER_MODEL` | `all-MiniLM-L6-v2` | The encoder for notes and questions |
| `LOCAL_MODEL` | `llama3.2` | The open weight model in Ollama |
| `FRONTIER_MODEL` | `claude-sonnet-5` | The model for `--hard` questions |
| `MIN_SCORE` | `0.3` | Below this score, the app does not call a model |

Always use the same encoder for the notes and for the questions. If you change the
encoder, the app embeds the notes again when it starts.

## Troubleshooting

| Message | Fix |
|---|---|
| `the Ollama model 'llama3.2' is not installed` | Run `ollama pull llama3.2`, or set `LOCAL_MODEL` to a model from `ollama list` |
| `cannot connect to Ollama` | Start Ollama (open the app, or run `ollama serve`) |
| `--hard needs the ANTHROPIC_API_KEY environment variable` | `export ANTHROPIC_API_KEY=...` |
| `Warning: You are sending unauthenticated requests to the HF Hub` | Harmless. Set `HF_TOKEN` to hide it. |

## Limits

This app is a start, not a product:

- **Chunking:** Each note is one chunk. Long documents must be cut into parts first.
- **Guardrails:** The "I do not know" instruction is a very small guardrail.
- **Caching:** The app embeds all notes each time it starts. For large data, save the vectors with `np.save()`.
- **Agent loops:** The app does one search and gives one answer.
