# Maintaining learn-ai-with-me

This guide is for you, the author. It explains how to run everything, what to do when
something changes, how to re-measure the numbers in the posts, and how to add a new lesson.
Everything here works without Claude.

## Contents

1. [How the repository works](#1-how-the-repository-works)
2. [One-time setup](#2-one-time-setup)
3. [Run everything](#3-run-everything)
4. [When something changes](#4-when-something-changes)
5. [Re-measure the numbers in the posts](#5-re-measure-the-numbers-in-the-posts)
6. [Create a new lesson](#6-create-a-new-lesson)
7. [Publish](#7-publish)
8. [Troubleshooting](#8-troubleshooting)

---

## 1. How the repository works

Each lesson is a separate folder with its own virtual environment. A lesson never imports
code from another lesson. When a lesson builds on the one before, it has a copy of the code.
This way, a reader can clone the repository and run one lesson alone.

```
learn-ai-with-me/
├── README.md              list of lessons, with links to the posts
├── MAINTAINING.md         this guide
├── requirements-dev.txt   tools to build and test notebooks (not for readers)
├── scripts/               tools for you (see below)
├── lesson1/  Ask My Notes: a small RAG app
├── lesson2/  chunking
├── lesson3/  caching
└── lesson4/  guardrails
```

Every lesson has the same files:

| File | What it is |
|---|---|
| `README.md` | What the lesson does, the results, and the quick start |
| `HOW_TO_RUN.md` | Step-by-step guide for readers: computer and Google Cloud |
| `requirements.txt` | Python packages for the lesson |
| `setup.sh` | Creates `.venv`, installs the packages, pulls the Ollama model |
| `check.sh` | Smoke test. Exits with an error if something is broken |
| `app.py` | The app, with a command line (`python app.py --help`) |
| an eval script | Measures the idea of the lesson (see section 5) |
| `build_notebook.py` | Builds the Google Cloud notebook. **Edit this, not the `.ipynb`** |
| `*_gcp.ipynb` | The notebook, without outputs |

The scripts in `scripts/`:

| Script | What it does |
|---|---|
| `scripts/check_all.sh` | Runs `setup.sh` (if needed) and `check.sh` in every lesson |
| `scripts/test_notebooks.sh` | Rebuilds every notebook and runs it from top to bottom |
| `scripts/new_lesson.sh N` | Starts lesson N as a copy of lesson N-1 |
| `scripts/publish.sh "message"` | Commits all changes and pushes to GitHub (asks first) |

All scripts take lesson names to limit the work, for example `scripts/check_all.sh lesson2`.

Files that are never committed (see `.gitignore`): `.venv/`, `.cache/`, `__pycache__/`, `.idea/`.

## 2. One-time setup

1. Install Python 3.10 or later, Git, and [Ollama](https://ollama.com).
2. Download the local model:

   ```bash
   ollama pull llama3.2
   ```

   If `ollama list` shows a different name (for example `llama3.2:3b`), tell the lessons:

   ```bash
   echo 'export LOCAL_MODEL=llama3.2:3b' >> ~/.zshrc && source ~/.zshrc
   ```

3. Optional: for the frontier model (`--hard`), get an API key from the Claude Console:

   ```bash
   echo 'export ANTHROPIC_API_KEY=your-key-here' >> ~/.zshrc && source ~/.zshrc
   ```

   Without a key, all checks still pass. They print `SKIPPED` for the frontier model.

4. Run everything one time (this creates a `.venv` in each lesson):

   ```bash
   scripts/check_all.sh
   ```

## 3. Run everything

| I want to... | Command |
|---|---|
| Check that all lessons work | `scripts/check_all.sh` |
| Check one lesson | `scripts/check_all.sh lesson3` or `cd lesson3 && ./check.sh` |
| Check that the notebooks work | `scripts/test_notebooks.sh` (needs Ollama; some minutes) |
| Start again from zero | `scripts/check_all.sh --fresh` (deletes each `.venv` and `.cache`) |
| Ask a question | `cd lesson4 && source .venv/bin/activate && python app.py "..."` |

A good habit: run `scripts/check_all.sh` before you publish a post, and one time each
month, because the packages and the models change.

The model answers change from run to run. `check.sh` does not test the exact words of an
answer. It tests the parts that do not change: the evals, the caches, and the guardrails.

## 4. When something changes

| What changed | What to do |
|---|---|
| **New versions of the Python packages** (monthly habit) | `scripts/check_all.sh --upgrade`. If it fails, read the error. Pin the last good version in that lesson's `requirements.txt`, for example `sentence-transformers>=3.0,<6`. |
| **New Python version on your computer** | `scripts/check_all.sh --fresh` |
| **You pulled a new version of the Ollama model** | `rm -rf lesson*/.cache` (the answer cache still has the old answers), then `scripts/check_all.sh` |
| **You changed the local model** (for example `qwen2.5:7b-instruct`) | `export LOCAL_MODEL=...`, then `scripts/check_all.sh`. To make it the default for readers, change the default of `LOCAL_MODEL` at the top of each `app.py` and in each `setup.sh` (`${LOCAL_MODEL:-llama3.2}`). |
| **A new Claude model** | Change `FRONTIER_MODEL` at the top of each `app.py` (or `export FRONTIER_MODEL=...`). Check the model id in the Claude documentation. |
| **You changed the encoder** (`ENCODER_MODEL`) | `rm -rf lesson*/.cache`, then re-measure (section 5): the numbers in the posts change. |
| **You edited the help pages in `docs/`** | Run the lesson's eval (section 5). The caches update by themselves. Note: lessons 2, 3, and 4 each have their own copy of `docs/`. |
| **You edited `app.py` or another lesson file** | `cd lessonN && ./check.sh`. If the change is in an older lesson, check if the later lessons have the same code (they are copies) and change them too. |
| **You changed a notebook** | Edit `build_notebook.py`, then `scripts/test_notebooks.sh lessonN`. Never edit the `.ipynb` by hand: the next build overwrites it. |
| **A reader reports a bug** | Reproduce it with the reader's command. Fix it in that lesson (and in later lessons with the same code). `./check.sh`, then publish. |
| **A post is published on Substack** | Add the link to the lesson title in the root `README.md` and in `lessonN/README.md`. Publish. |

## 5. Re-measure the numbers in the posts

The posts and the READMEs contain measured numbers. If you change a lesson, run its
measurement again, and update the README (and the post, if you want).

| Lesson | Command | What it prints | Where the numbers are |
|---|---|---|---|
| 1 | `python eval_retrieval.py` | Retrieval hit rate (100%) | post: Step 5 |
| 2 | `python eval_chunking.py -v` | Chunks, hit rate, and words sent for each strategy | `lesson2/README.md`, post: the results table |
| 3 | `python test_cache.py` | When the cache embeds again | post: "When must you embed again?" |
| 3 | `python benchmark.py --copies 2000 --device cpu --answers` | Times with and without the caches (some minutes) | `lesson3/README.md`, post: "Where the time goes" and "The results" |
| 4 | `python eval_guardrails.py` | Input, document, and output checks (no model) | `lesson4/README.md`, post: the eval tables |
| 4 | `python eval_guardrails.py --live --runs 5` | Real answers and the judge (some minutes) | `lesson4/README.md`, post: the output table |

Run these inside the lesson folder, with its environment active (`source .venv/bin/activate`).

Times depend on the computer. The posts say "on my laptop" (Apple M5, 10 cores). Numbers
with the local model change from run to run: use `--runs 5` or more for numbers that you
publish, and say that they change.

## 6. Create a new lesson

This is the process that the first four lessons followed.

**1. Start the folder.**

```bash
scripts/new_lesson.sh 5
```

This copies lesson 4 to lesson 5 (without `.venv`, `.cache`, and the notebook).

**2. Build the idea.** Change the code for the topic. Keep the style of the other lessons:
short functions, plain English in comments, the same names (`load_chunks`, `Index`,
`build_prompt`, `ask`). A reader should see only the new part change.

**3. Measure it.** Write an eval script that answers: did the new idea help, and what did it
cost? Every number in the post must come from this script. Try to break the app before you
fix it, and show the failure in the post.

**4. Update the lesson files.**

- `check.sh`: run the eval, and fail (`exit 1`) if a result that must not change is wrong.
- `README.md`: what the lesson does, the results table, files, quick start, limits.
- `HOW_TO_RUN.md`: the commands and the expected output.
- `build_notebook.py`: the cells for the new topic (sections 5 to 9 are lesson-specific).

**5. Test.**

```bash
cd lesson5 && ./setup.sh && ./check.sh && cd ..
scripts/test_notebooks.sh lesson5
scripts/check_all.sh
```

**6. Add the lesson to the table in the root `README.md`.**

**7. Write the post.** The posts use the same structure:

1. Title and subtitle, then "In my last post..." with a link.
2. A box with the GitHub folder and "The series so far" (all earlier posts, with links).
3. The problem, shown with a real failure from the app.
4. The fixes, one section each, with the code.
5. "Measure it": the eval and its table.
6. "Run it all together": clone, `./setup.sh`, `./check.sh`, a few commands, and the notebook.
7. "What I learned from this build" (three points), "What this app does not do yet",
   the topic of the next post.
8. The question for the readers, subscribe, GitHub and LinkedIn links.

Style: short sentences, simple words, one idea for each paragraph. Before you publish,
check each number and each quote in the post against the output of the eval.

**8. Publish** (section 7).

## 7. Publish

**The code:**

```bash
scripts/check_all.sh
scripts/publish.sh "Add lesson 5: agent loops"
```

**The post (Substack):**

1. Title and subtitle go in the Substack title and subtitle fields.
2. Paste the rest. Code blocks, tables, and links keep their format.
3. After you publish, copy the link without the part after `?`
   (for example `https://techbyavanti.substack.com/p/stop-embedding-the-same-text-twice`).
4. Add the link to the root `README.md` and `lessonN/README.md`, then
   `scripts/publish.sh "Link lesson N post"`.

**LinkedIn** (the format of the earlier posts):

```
<emoji> <hook: the problem in one line, taken from the title>

<one line that makes it concrete>

<3 lines with the results, one emoji each>

💡 The biggest lesson: <one sentence>

📖 Read the post: <Substack link>
🛠️ Get the code: https://github.com/techbyavanti/learn-ai-with-me

#AI #RAG #Python #LLM #GenerativeAI
```

LinkedIn tends to show posts with external links to fewer people. You can put the two links
in the first comment instead.

**The series list** (for the box at the top of each new post):

1. [I Wanted to Learn AI Engineering. Here Is Where I Started.](https://techbyavanti.substack.com/p/i-wanted-to-learn-ai-engineering)
2. [The 5 Design Patterns AI Developers Actually Use](https://techbyavanti.substack.com/p/the-5-design-patterns-ai-developers)
3. [One Laptop, Two Models, 60 Lines: Build Your First Mini RAG App](https://techbyavanti.substack.com/p/one-laptop-two-models-60-lines-build) (lesson 1)
4. [Your RAG App Works on Notes. Then You Give It a Real Document.](https://techbyavanti.substack.com/p/your-rag-app-works-on-notes-then) (lesson 2)
5. [Stop Embedding the Same Text Twice: Caching for Your RAG App](https://techbyavanti.substack.com/p/stop-embedding-the-same-text-twice) (lesson 3)
6. Your RAG App Will Make Things Up. Here Is How to Catch It. (lesson 4; add the link when it is published)

## 8. Troubleshooting

| Problem | Fix |
|---|---|
| `the Ollama model 'llama3.2' is not installed` | `ollama pull llama3.2`, or `export LOCAL_MODEL=<name from ollama list>` |
| `cannot connect to Ollama` | Open the Ollama app, or run `ollama serve` |
| `Run ./setup.sh first.` | `cd lessonN && ./setup.sh` |
| `pip install` fails after a Python update | `scripts/check_all.sh --fresh` |
| A check fails after `--upgrade` | Pin the last good version in `requirements.txt` (section 4) |
| `Warning: You are sending unauthenticated requests to the HF Hub` | Harmless. Set `HF_TOKEN` to hide it. |
| Old answers after a model change | `rm -rf lesson*/.cache` |
| A notebook fails in `scripts/test_notebooks.sh` | Open the log file that the script names. Fix `build_notebook.py`, not the `.ipynb`. |
| `scripts/publish.sh` shows files that you do not want | Answer `n`. Delete them or add them to `.gitignore`, then run it again. |
| `git push` is rejected | `git pull --rebase`, then `scripts/publish.sh` again |
