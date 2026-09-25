# Ask My Docs: chunking

> New here? Start with [HOW_TO_RUN.md](HOW_TO_RUN.md).

This is the code from the post "Your RAG App Works on Notes. Then You Give It a Real
Document." (Tech by Avanti). It is the [lesson 1](../lesson1/) app, changed for long
documents.

Lesson 1 used short notes: one fact, one chunk. Real documents are long and talk about
many topics, so you must cut them into chunks first. This lesson compares four ways to cut:

| Strategy | What it does | Chunks | Hit rate | Words sent |
|---|---|---|---|---|
| `whole` | One page is one chunk | 6 | 81% | 896 |
| `fixed` | A chunk every 60 words | 33 | 81% | 169 |
| `overlap` | 60-word chunks that share 20 words | 45 | 100% | 177 |
| `sections` | Cut at headings, keep paragraphs together, add the heading | 26 | 100% | 205 |

Results from `python eval_chunking.py` (16 questions, top 3 chunks). "Words sent" is the
average number of words that go to the model for each question.

## Files

| File | Purpose |
|---|---|
| `docs/` | Six help pages (about 1,800 words). Replace them with your own `.md` files. |
| `chunking.py` | The four chunking strategies |
| `app.py` | Load, chunk, embed, search, and answer, with a command-line interface |
| `eval_chunking.py` | Compares the strategies (`-v` shows the missed questions) |
| `setup.sh` | Creates `.venv`, installs the packages, and pulls the Ollama model |
| `check.sh` | Smoke test: runs the eval and one question for each available model |
| `ask_my_docs_gcp.ipynb` | Jupyter notebook for Google Cloud (Vertex AI Workbench or Colab Enterprise) |
| `HOW_TO_RUN.md` | Step-by-step guide for your computer and for Google Cloud |

## Quick start

```bash
./setup.sh                     # one time
source .venv/bin/activate
./check.sh                     # make sure everything works
python eval_chunking.py        # compare the strategies
python app.py "How long until I get my money back?" --show-search
```

## Usage

```bash
python app.py "How long until I get my money back?"                     # sections (default)
python app.py "How long until I get my money back?" --strategy whole --show-search
python app.py "Can a school with 60 users pay by bank transfer?" --hard  # frontier model
python app.py --docs path/to/your/docs                                  # chat mode, your files
```

## Settings

| Setting | Where | Default |
|---|---|---|
| `LOCAL_MODEL` | environment variable | `llama3.2` |
| `FRONTIER_MODEL` | environment variable | `claude-sonnet-5` |
| `ANTHROPIC_API_KEY` | environment variable | none (needed for `--hard`) |
| `MIN_SCORE` | top of `app.py` | `0.3` |
| chunk size and overlap | `chunking.py` | 60 words, 20 overlap; sections up to 120 words |

## Limits

- `sections` needs headings (`## Heading`). For text without headings, use `overlap`.
- The app embeds all chunks each time it starts. That is fine for a few pages, but not for
  thousands. This is the topic of the next lesson.
