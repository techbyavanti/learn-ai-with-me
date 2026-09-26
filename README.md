# learn-ai-with-me

This repository contains the code for the blog posts on
[Tech by Avanti](https://techbyavanti.substack.com/).

## Lessons

| Folder | Post | What it builds |
|---|---|---|
| [`lesson1`](lesson1/) ([how to run](lesson1/HOW_TO_RUN.md)) | [One Laptop, Two Models, 60 Lines: Build Your First Mini RAG App](https://techbyavanti.substack.com/p/one-laptop-two-models-60-lines-build) | "Ask My Notes": a small RAG app with a local (Ollama) and a frontier (Claude) model |
| [`lesson2`](lesson2/) ([how to run](lesson2/HOW_TO_RUN.md)) | [Your RAG App Works on Notes. Then You Give It a Real Document.](https://techbyavanti.substack.com/p/your-rag-app-works-on-notes-then) | "Ask My Docs": chunking long documents, with an eval that compares four strategies |
| [`lesson3`](lesson3/) ([how to run](lesson3/HOW_TO_RUN.md)) | [Stop Embedding the Same Text Twice: Caching for Your RAG App](https://techbyavanti.substack.com/p/stop-embedding-the-same-text-twice) | "Ask My Docs" with a vector cache and an answer cache, and a benchmark |
| [`lesson4`](lesson4/) ([how to run](lesson4/HOW_TO_RUN.md)) | Your RAG App Will Make Things Up. Here Is How to Catch It. | "Ask My Docs" with input, document, and output guardrails, and an eval that measures them |

Each lesson has its own README, `requirements.txt`, and a `setup.sh` / `check.sh` pair:

```bash
cd lesson1
./setup.sh && ./check.sh
```

## For the author

[MAINTAINING.md](MAINTAINING.md) explains how to run all lessons (`scripts/check_all.sh`),
what to do when packages or models change, how to re-measure the numbers in the posts, and
how to add a new lesson.
