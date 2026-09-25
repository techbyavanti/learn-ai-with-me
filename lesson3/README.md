# Ask My Docs: caching

> New here? Start with [HOW_TO_RUN.md](HOW_TO_RUN.md).

This is the code from the post "Stop Embedding the Same Text Twice: Caching for Your RAG
App" (Tech by Avanti). It is the [lesson 2](../lesson2/) app with two caches.

| Cache | File | Key | Saves |
|---|---|---|---|
| Vector cache | `.cache/vectors-<folder>.npz` | encoder name + chunk text | the embedding step at each start |
| Answer cache | `.cache/answers.json` | model name + full prompt | a model call for a repeated question |

Because each key is a fingerprint of the exact text, the app embeds again exactly what
changed: one edited section, a new page, a new chunking strategy, or a new encoder.

## Results

From `python benchmark.py --copies 2000 --device cpu` on a laptop (Apple M5, CPU only):

| Pages | Chunks | No cache | With cache | After 1 edit | Cache file |
|---|---|---|---|---|---|
| 6 | 26 | 0.19 s | 0.00 s | 0.01 s | 0.04 MB |
| 12,000 | 52,000 | 107 s | 0.09 s | 0.10 s | 83 MB |

Loading the encoder takes about 5 seconds at each start. The cache cannot remove this
fixed cost. Chat mode loads the encoder one time for many questions.

## Files

| File | Purpose |
|---|---|
| `cache.py` | `VectorCache` and `AnswerCache` |
| `app.py` | The lesson 2 app, with the two caches (`--no-cache` turns them off) |
| `test_cache.py` | Checks when the cache embeds again (edit, new page, new chunking, new encoder) |
| `benchmark.py` | Times the start with and without the cache (`--copies`, `--device`, `--answers`) |
| `chunking.py`, `docs/` | The same as lesson 2 |
| `setup.sh` / `check.sh` | Set up, and run all checks |
| `ask_my_docs_cache_gcp.ipynb` | Jupyter notebook for Google Cloud (Vertex AI Workbench or Colab Enterprise) |
| `HOW_TO_RUN.md` | Step-by-step guide for your computer and for Google Cloud |

## Quick start

```bash
./setup.sh                     # one time
source .venv/bin/activate
./check.sh                     # make sure everything works
python app.py "How long until I get my money back?"   # first start: embeds, asks the model
python app.py "How long until I get my money back?"   # second start: all from the caches
```

## When to delete the cache

The keys see the encoder name, the chunk text, the model name, and the prompt. Delete the
`.cache` folder when you change something that the keys do not see:

- the encoder settings (for example `normalize_embeddings`)
- a new version of a model with the same name
- the answer cache has a bad answer that you want to remove

## Limits

- The answer cache matches only the exact same prompt. "I forgot my password" and
  "How do I reset my password?" are two different keys.
- The answer cache stores the questions of your users. Treat the file like private data.
- The vector cache is one file. For millions of chunks, use a vector database.
