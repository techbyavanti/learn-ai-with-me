"""Build the Google Cloud notebook for this lesson.

Run: python build_notebook.py   (needs: pip install nbformat)
The notebook is written without outputs. Edit the cells here, not in the .ipynb file.
"""

from pathlib import Path

import nbformat as nbf

md = nbf.v4.new_markdown_cell
code = nbf.v4.new_code_cell

cells = [
md("""# Ask My Docs with Caching on Google Cloud

This notebook runs the lesson 3 app from
[learn-ai-with-me](https://github.com/techbyavanti/learn-ai-with-me) on Google Cloud.
It works in **Vertex AI Workbench** and in **Colab Enterprise**.

Lesson 3 is about **caching**. The app has two caches:

| Cache | Key | Saves |
|---|---|---|
| Vector cache (`.cache/vectors-*.npz`) | encoder name + chunk text | the embedding step at each start |
| Answer cache (`.cache/answers.json`) | model name + full prompt | a model call for a repeated question |

**Machine:** 4 vCPUs and 16 GB RAM is enough (for example `e2-standard-4`). With a GPU,
the benchmark is faster, but the cache gives the same result.

Run the cells from top to bottom."""),

md("## 1. Get the code\n\nIf `app.py` is not in the current folder, this cell clones the repository."),
code("""import os
import subprocess

REPO = "https://github.com/techbyavanti/learn-ai-with-me.git"

if not os.path.exists("app.py"):
    if not os.path.exists("learn-ai-with-me"):
        subprocess.run(["git", "clone", "--depth", "1", REPO], check=True)
    os.chdir("learn-ai-with-me/lesson3")

print("Working folder:", os.getcwd())
print(sorted(os.listdir(".")))"""),

md("## 2. Install the Python packages"),
code("%pip install -q -r requirements.txt"),

md("""## 3. Install and start Ollama

Ollama runs the local, open weight model. This cell installs it on Linux
(Workbench and Colab Enterprise use Linux) and skips the install if Ollama is already there."""),
code("""import shutil
import sys

SUDO = [] if os.geteuid() == 0 else ["sudo"]

if shutil.which("ollama") is None:
    # The Ollama installer needs zstd to unpack the download.
    subprocess.run(SUDO + ["apt-get", "update", "-qq"], check=True)
    subprocess.run(SUDO + ["apt-get", "install", "-y", "-qq", "zstd", "pciutils"], check=True)
    subprocess.run("curl -fsSL https://ollama.com/install.sh | sh", shell=True, check=True)
else:
    print("Ollama is already installed:", shutil.which("ollama"))"""),
code("""import time
import urllib.request


def ollama_running():
    try:
        urllib.request.urlopen("http://localhost:11434", timeout=2)
        return True
    except OSError:
        return False


if not ollama_running():
    ollama_log = open("ollama.log", "w")
    ollama_process = subprocess.Popen(["ollama", "serve"], stdout=ollama_log, stderr=subprocess.STDOUT)
    for _ in range(30):
        if ollama_running():
            break
        time.sleep(1)

print("Ollama is running:", ollama_running())"""),

md("""## 4. Settings

- `LOCAL_MODEL`: the Ollama model. `llama3.2` is about 2 GB.
- `FRONTIER_MODEL`: the Claude model for `hard=True` questions.
- `ANTHROPIC_API_KEY`: only needed for the frontier model. Leave it empty to skip that part.

Do not write the API key in the notebook. The next cell reads it from the environment,
or asks for it."""),
code("""LOCAL_MODEL = os.environ.get("LOCAL_MODEL", "llama3.2")
FRONTIER_MODEL = os.environ.get("FRONTIER_MODEL", "claude-sonnet-5")

os.environ["LOCAL_MODEL"] = LOCAL_MODEL
os.environ["FRONTIER_MODEL"] = FRONTIER_MODEL
os.environ["TOKENIZERS_PARALLELISM"] = "false"

if not os.environ.get("ANTHROPIC_API_KEY"):
    from getpass import getpass

    try:
        key = getpass("ANTHROPIC_API_KEY (press Enter to skip): ").strip()
    except Exception:  # no input box, for example in a scheduled run
        key = ""
    if key:
        os.environ["ANTHROPIC_API_KEY"] = key

print("Frontier model enabled:", bool(os.environ.get("ANTHROPIC_API_KEY")))"""),
code("""# Download the local model (skipped if it is already there).
subprocess.run(["ollama", "pull", LOCAL_MODEL], check=True)"""),

md("## 5. Check when the cache embeds again\n\nThe first run downloads the encoder."),
code("""import test_cache

test_cache.main()"""),

md("""## 6. Benchmark

The benchmark makes copies of the six help pages (for timing only) and measures the
embedding step without the cache, with the cache, and after one edit.
`--copies 200` makes 1,200 pages. Use `--copies 2000` for 12,000 pages (this takes some minutes on a CPU)."""),
code("""subprocess.run([sys.executable, "benchmark.py", "--copies", "200", "--answers"], check=True)"""),

md("## 7. Start the app two times"),
code("""import time

from app import AnswerCache, CACHE_DIR, Index, ask, load_chunks, vector_cache_path

for run in ["first start", "second start"]:
    start = time.perf_counter()
    index = Index(load_chunks("sections"), vector_cache_path())
    print(f"{run}: {index.stats} in {time.perf_counter() - start:.2f} s")"""),

md("## 8. Ask the same question two times\n\nThe first answer comes from the local model, the second from the answer cache."),
code("""answers = AnswerCache(CACHE_DIR / "answers.json")

for run in ["model", "cache"]:
    start = time.perf_counter()
    answer = ask(index, "How long until I get my money back?", answers=answers)
    print(f"{run}: {time.perf_counter() - start:.2f} s")
    print(answer)
    print()"""),

md("## 9. Ask the frontier model\n\nThis cell runs only if you entered an API key. Run it two times: the second time, the answer comes from the cache and costs nothing."),
code("""if os.environ.get("ANTHROPIC_API_KEY"):
    start = time.perf_counter()
    print(ask(index, "Can a school with 60 users pay by bank transfer, and what discount does it get?", hard=True, answers=answers))
    print(f"{time.perf_counter() - start:.2f} s")
else:
    print("Skipped: ANTHROPIC_API_KEY is not set.")"""),

md("""## 10. Clean up

Stop Ollama. To start again without the caches, delete the `.cache` folder.
When you are done, **stop the Workbench instance or the Colab runtime**
so that Google Cloud does not keep charging for it."""),
code("""if "ollama_process" in globals():
    ollama_process.terminate()
    print("Ollama stopped.")"""),
]

nb = nbf.v4.new_notebook(cells=cells, metadata={
    "kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"},
    "language_info": {"name": "python"},
})
# Fixed cell ids, so that a rebuild changes the file only when the cells change.
for i, cell in enumerate(nb.cells):
    cell.id = f"cell-{i:02d}"

nbf.write(nb, Path(__file__).parent / "ask_my_docs_cache_gcp.ipynb")
