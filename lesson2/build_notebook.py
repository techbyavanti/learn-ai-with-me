"""Build the Google Cloud notebook for this lesson.

Run: python build_notebook.py   (needs: pip install nbformat)
The notebook is written without outputs. Edit the cells here, not in the .ipynb file.
"""

from pathlib import Path

import nbformat as nbf

md = nbf.v4.new_markdown_cell
code = nbf.v4.new_code_cell

cells = [
md("""# Ask My Docs on Google Cloud

This notebook runs the lesson 2 app from
[learn-ai-with-me](https://github.com/techbyavanti/learn-ai-with-me) on Google Cloud.
It works in **Vertex AI Workbench** and in **Colab Enterprise**.

Lesson 2 is about **chunking**: how to cut long documents into parts before you embed them.
The notebook compares four strategies on six help pages:

| Strategy | What it does |
|---|---|
| `whole` | One page is one chunk |
| `fixed` | A chunk every 60 words |
| `overlap` | A chunk every 40 words, 60 words long (20 words overlap) |
| `sections` | Cut at headings, keep paragraphs together, add the heading to each chunk |

**Machine:** 4 vCPUs and 16 GB RAM is enough (for example `e2-standard-4`).

Run the cells from top to bottom."""),

md("## 1. Get the code\n\nIf `app.py` is not in the current folder, this cell clones the repository."),
code("""import os
import subprocess

REPO = "https://github.com/techbyavanti/learn-ai-with-me.git"

if not os.path.exists("app.py"):
    if not os.path.exists("learn-ai-with-me"):
        subprocess.run(["git", "clone", "--depth", "1", REPO], check=True)
    os.chdir("learn-ai-with-me/lesson2")

print("Working folder:", os.getcwd())
print(sorted(os.listdir(".")))"""),

md("## 2. Install the Python packages"),
code("%pip install -q -r requirements.txt"),

md("""## 3. Install and start Ollama

Ollama runs the local, open weight model. This cell installs it on Linux
(Workbench and Colab Enterprise use Linux) and skips the install if Ollama is already there."""),
code("""import shutil

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

md("## 5. Compare the chunking strategies\n\nThe first run downloads the encoder."),
code("""from app import Index, ask, load_chunks
from eval_chunking import TESTS, hit_rate, words_sent

print(f"{'Strategy':<10} {'Chunks':>6} {'Hit rate':>9} {'Words sent':>11}")
indexes = {}
for name in ["whole", "fixed", "overlap", "sections"]:
    indexes[name] = Index(load_chunks(name))
    rate = hit_rate(indexes[name], TESTS)
    print(f"{name:<10} {len(indexes[name].chunks):>6} {rate:>9.0%} {words_sent(indexes[name], TESTS):>11.0f}")"""),

md("## 6. See the search results for one question"),
code("""question = "How long until I get my money back?"

for name, index in indexes.items():
    print(f"== {name}")
    for chunk, score in index.search(question):
        preview = " ".join(chunk["text"].split())[:80]
        print(f"  [{score:.2f}] {chunk['source']}: {preview}...")"""),

md("## 7. Ask the local model"),
code("""print(ask(indexes["sections"], "How long until I get my money back?"))"""),
code("""print(ask(indexes["whole"], "How long until I get my money back?"))"""),
code("""print(ask(indexes["sections"], "What is the capital of France?"))"""),

md("## 8. Ask the frontier model\n\nThis cell runs only if you entered an API key."),
code("""if os.environ.get("ANTHROPIC_API_KEY"):
    print(ask(indexes["sections"], "Can a school with 60 users pay by bank transfer, and what discount does it get?", hard=True))
else:
    print("Skipped: ANTHROPIC_API_KEY is not set.")"""),

md("""## 9. Use your own documents

Upload your `.md` files to a folder (for example `my_docs`), then set `MY_DOCS` below.
Use headings (`## Heading`) in your files, so that the `sections` strategy can cut at them."""),
code("""MY_DOCS = "docs"  # change to your folder

my_index = Index(load_chunks("sections", MY_DOCS))
print(len(my_index.chunks), "chunks")
print(ask(my_index, "How do I invite a person to my team?"))"""),

md("""## 10. Clean up

Stop Ollama. When you are done, **stop the Workbench instance or the Colab runtime**
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

nbf.write(nb, Path(__file__).parent / "ask_my_docs_gcp.ipynb")
