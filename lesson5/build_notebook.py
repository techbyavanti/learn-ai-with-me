"""Build the Google Cloud notebook for this lesson.

Run: python build_notebook.py   (needs: pip install nbformat)
The notebook is written without outputs. Edit the cells here, not in the .ipynb file.
"""

from pathlib import Path

import nbformat as nbf

md = nbf.v4.new_markdown_cell
code = nbf.v4.new_code_cell

cells = [
md("""# Ask My Docs with an Agent Loop on Google Cloud

This notebook runs the lesson 5 app from
[learn-ai-with-me](https://github.com/techbyavanti/learn-ai-with-me) on Google Cloud.
It works in **Vertex AI Workbench** and in **Colab Enterprise**.

Lesson 5 is about **agent loops**: the model decides when to search, when to calculate,
and when to answer. Rules and limits in code keep the loop safe:

| Rule or limit | Value |
|---|---|
| Search before you calculate or answer | enforced in code |
| Numbers in the answer must come from a search, the calculator, or the question | checked before the loop accepts an answer |
| Model calls / searches / answers sent back | 6 / 4 / 2 |

**Machine:** 4 vCPUs and 16 GB RAM is enough for `llama3.2`. For `qwen2.5:7b-instruct`,
a GPU (for example an NVIDIA T4) makes the agent much faster.

Run the cells from top to bottom."""),

md("## 1. Get the code\n\nIf `app.py` is not in the current folder, this cell clones the repository."),
code("""import os
import subprocess

REPO = "https://github.com/techbyavanti/learn-ai-with-me.git"

if not os.path.exists("app.py"):
    if not os.path.exists("learn-ai-with-me"):
        subprocess.run(["git", "clone", "--depth", "1", REPO], check=True)
    os.chdir("learn-ai-with-me/lesson5")

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

md("## 5. The calculator\n\nThe calculator allows only numbers and + - * /. It refuses anything that could run code."),
code("""subprocess.run([sys.executable, "test_tools.py"], check=True)"""),

md("## 6. Watch the agent work\n\nThe first run downloads the encoder."),
code("""from app import Index, ask, ask_agent, load_chunks

index = Index(load_chunks("sections"))
question = "For 5 users, how much do we save in one year with the yearly plan instead of the monthly plan?"

guard = []
answer, result = ask_agent(index, question, guard=guard)
for step in result.steps:
    print("STEP", step)
print(f"({result.model_calls} model calls, {result.retries} sent back)")
for finding in guard:
    print("GUARD", finding)
print("ANSWER:", answer)"""),

md("## 7. The same question with one search (lesson 4)"),
code("""guard = []
print(ask(index, question, guard=guard))
for finding in guard:
    print("GUARD", finding)"""),

md("""## 8. A second model (optional)

Agents need a model that plans well. `qwen2.5:7b-instruct` (4.7 GB) is better at tool use
than `llama3.2` (2 GB). This cell downloads it and asks the same question."""),
code("""SECOND_MODEL = "qwen2.5:7b-instruct"
subprocess.run(["ollama", "pull", SECOND_MODEL], check=True)

guard = []
answer, result = ask_agent(index, question, guard=guard, model=SECOND_MODEL)
for step in result.steps:
    print("STEP", step)
print("ANSWER:", answer)"""),

md("""## 9. The agent eval

12 questions (8 need more than one step), one search against the agent. This takes some
minutes. Add `"--models", "llama3.2", "qwen2.5:7b-instruct"` to compare both models, and
`"--runs", "3"` for more stable numbers."""),
code("""subprocess.run([sys.executable, "eval_agent.py", "--models", LOCAL_MODEL], check=True)"""),

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

nbf.write(nb, Path(__file__).parent / "ask_my_docs_agent_gcp.ipynb")
