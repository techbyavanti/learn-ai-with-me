"""Build the Google Cloud notebook for this lesson.

Run: python build_notebook.py   (needs: pip install nbformat)
The notebook is written without outputs. Edit the cells here, not in the .ipynb file.
"""

from pathlib import Path

import nbformat as nbf

md = nbf.v4.new_markdown_cell
code = nbf.v4.new_code_cell

cells = [
md("""# Ask My Docs as a Web App on Google Cloud

This notebook runs the lesson 7 web app from
[learn-ai-with-me](https://github.com/techbyavanti/learn-ai-with-me) on Google Cloud.
It works in **Vertex AI Workbench** and in **Colab Enterprise**.

Lesson 7 turns the script into a **web app**: one process loads the documents, the encoder,
and the model one time, then answers questions from many people.

| Endpoint | What it does |
|---|---|
| `POST /ask` | Answers a question (`mode`: `agent` or `single`) |
| `GET /health` | Says that the service is up, and what it loaded |
| `GET /` | A small web page to ask questions |

**Machine:** 4 vCPUs and 16 GB RAM is enough. A GPU makes the model (and the load test) faster.

Run the cells from top to bottom."""),

md("## 1. Get the code\n\nIf `app.py` is not in the current folder, this cell clones the repository."),
code("""import os
import subprocess

REPO = "https://github.com/techbyavanti/learn-ai-with-me.git"

if not os.path.exists("app.py"):
    if not os.path.exists("learn-ai-with-me"):
        subprocess.run(["git", "clone", "--depth", "1", REPO], check=True)
    os.chdir("learn-ai-with-me/lesson7")

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

md("## 5. Start the service\n\nThe service runs in the background on a free port. The first start downloads the encoder."),
code("""import json
import socket
import time
import urllib.request

# Pick a free port, so that the service does not collide with another program.
with socket.socket() as s:
    s.bind(("localhost", 0))
    PORT = s.getsockname()[1]
URL = f"http://localhost:{PORT}"

server_log = open("server.log", "w")
server = subprocess.Popen([sys.executable, "-m", "uvicorn", "server:app", "--port", str(PORT)],
                          stdout=server_log, stderr=subprocess.STDOUT)
for _ in range(180):
    if server.poll() is not None:
        raise RuntimeError("The service stopped:\\n" + open("server.log").read())
    try:
        urllib.request.urlopen(f"{URL}/health", timeout=2)
        break
    except OSError:
        time.sleep(1)
print("Service on", URL)
print([line for line in open("server.log").read().splitlines() if "Ready" in line])"""),

md("## 6. Health check"),
code("""print(json.load(urllib.request.urlopen(f"{URL}/health")))"""),

md("## 7. Ask a question"),
code("""def ask(question, mode="single", steps=False):
    body = json.dumps({"question": question, "mode": mode, "steps": steps}).encode()
    request = urllib.request.Request(f"{URL}/ask", data=body,
                                     headers={"Content-Type": "application/json"})
    return json.load(urllib.request.urlopen(request, timeout=300))

print(ask("How long until I get my money back?"))
print(ask("For 5 users, how much do we save in one year with the yearly plan instead of the monthly plan?",
          mode="agent", steps=True))"""),

md("## 8. The load test\n\n16 questions with 1, 4, and 8 people asking at the same time."),
code("""subprocess.run([sys.executable, "load_test.py", "--url", URL, "--users", "1", "4", "8"], check=True)"""),

md("## 9. The same questions again (from the cache)"),
code("""subprocess.run([sys.executable, "load_test.py", "--url", URL, "--users", "8",
                "--repeat", "--suffix", " (warm)"], check=True)
subprocess.run([sys.executable, "load_test.py", "--url", URL, "--users", "8",
                "--repeat", "--suffix", " (warm)"], check=True)"""),

md("""## 10. Clean up

Stop Ollama. To start again without the caches, delete the `.cache` folder.
When you are done, **stop the Workbench instance or the Colab runtime**
so that Google Cloud does not keep charging for it."""),
code("""if "server" in globals():
    server.terminate()
    print("Service stopped.")
if "ollama_process" in globals():
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

nbf.write(nb, Path(__file__).parent / "ask_my_docs_app_gcp.ipynb")
