"""Ask My Docs as a web service.

The service loads everything one time when it starts: the documents, the vectors, the
encoder, and the model. Then it answers questions from many people.

Start it:  uvicorn server:app --port 8000
Ask:       curl -s localhost:8000/ask -H 'Content-Type: application/json' \
                -d '{"question": "How long until I get my money back?"}'
Open:      http://localhost:8000 in a browser
"""

import os
import threading
import time
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from pydantic import BaseModel

import app as core
from agent import AGENT_MODEL
from cache import AnswerCache, make_key

# At most this many questions work with the model at the same time. The others wait in line.
MAX_BUSY = int(os.environ.get("MAX_BUSY", "2"))
# A question that waits longer than this gets "busy, try again" (HTTP 503).
QUEUE_TIMEOUT = float(os.environ.get("QUEUE_TIMEOUT", "60"))

state = {}
model_slots = threading.BoundedSemaphore(MAX_BUSY)
encoder_lock = threading.Lock()
answers_lock = threading.Lock()
served_lock = threading.Lock()


class LockedEncoder:
    """The encoder, used by one request at a time."""

    def __init__(self, encoder):
        self.encoder = encoder

    def encode(self, *args, **kwargs):
        with encoder_lock:
            return self.encoder.encode(*args, **kwargs)


class LockedAnswerCache(AnswerCache):
    """The answer cache, written by one request at a time."""

    def get(self, model, prompt):
        with answers_lock:
            return super().get(model, prompt)

    def put(self, model, prompt, answer):
        with answers_lock:
            super().put(model, prompt, answer)


@asynccontextmanager
async def lifespan(_):
    """Load everything one time, before the first request."""
    start = time.perf_counter()
    core._encoder = LockedEncoder(core.get_encoder())
    chunks = core.load_chunks("sections", report=True)
    index = core.Index(chunks, core.vector_cache_path())
    answers = LockedAnswerCache(core.CACHE_DIR / "answers.json")
    warm_up_model()
    state.update(
        index=index,
        answers=answers,
        # A fingerprint of all chunks: when a document changes, old agent answers do not match.
        docs_key=make_key(*[c["text"] for c in chunks]),
        started=time.time(),
        load_seconds=time.perf_counter() - start,
        served=0,
    )
    print(f"Ready: {len(chunks)} chunks, loaded in {state['load_seconds']:.1f} s")
    yield


def warm_up_model():
    """Ask the model one short question, so that Ollama loads it into memory now."""
    try:
        import ollama

        ollama.chat(model=AGENT_MODEL, messages=[{"role": "user", "content": "Hi"}],
                    options={"num_predict": 1}, keep_alive="30m")
    except Exception as e:  # the service still starts; the first question will be slower
        print(f"Could not warm up the model: {e}")


app = FastAPI(title="Ask My Docs", lifespan=lifespan)


class Question(BaseModel):
    question: str
    mode: str = "agent"  # "agent" or "single"
    steps: bool = False  # return the steps of the agent


@app.get("/health")
def health():
    """For monitoring: is the service up, and what did it load?"""
    return {
        "status": "ok",
        "chunks": len(state["index"].chunks),
        "model": core.LOCAL_MODEL,
        "agent_model": AGENT_MODEL,
        "max_busy": MAX_BUSY,
        "load_seconds": round(state["load_seconds"], 1),
        "uptime_seconds": round(time.time() - state["started"]),
        "questions_served": state["served"],
    }


@app.post("/ask")
def ask(q: Question):
    """Answer one question. FastAPI runs this in a thread, so many questions can arrive at once."""
    if q.mode not in ("agent", "single"):
        raise HTTPException(400, "mode must be 'agent' or 'single'")
    start = time.perf_counter()
    index, answers = state["index"], state["answers"]
    guard, steps, cached = [], [], False

    # The agent's answers go in the answer cache too, with the documents fingerprint in the key.
    agent_key = f"agent\n{state['docs_key']}\n{q.question.strip()}"
    if q.mode == "agent":
        saved = answers.get(AGENT_MODEL, agent_key)
        if saved is not None:
            count_served()
            return _reply(q, saved, guard, steps, start, cached=True)

    if not model_slots.acquire(timeout=QUEUE_TIMEOUT):
        raise HTTPException(503, "The service is busy. Please try again in a moment.")
    try:
        if q.mode == "single":
            answer = core.ask(index, q.question, answers=answers, guard=guard)
        else:
            answer, result = core.ask_agent(index, q.question, guard=guard)
            steps = result.steps if result else []
            if result and result.stop_reason == "answered" and not guard:
                answers.put(AGENT_MODEL, agent_key, answer)
    finally:
        model_slots.release()
    count_served()
    return _reply(q, answer, guard, steps, start, cached)


def count_served():
    with served_lock:
        state["served"] += 1


def _reply(q, answer, guard, steps, start, cached):
    reply = {"answer": answer, "mode": q.mode, "cached": cached, "guard": guard,
             "seconds": round(time.perf_counter() - start, 2)}
    if q.steps:
        reply["steps"] = steps
    return reply


@app.get("/", response_class=HTMLResponse)
def page():
    """A small page to ask questions in the browser."""
    return PAGE


PAGE = """<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>Ask My Docs</title>
<style>
  body { font-family: system-ui, sans-serif; max-width: 640px; margin: 40px auto; padding: 0 16px; }
  textarea { width: 100%; height: 80px; font: inherit; padding: 8px; box-sizing: border-box; }
  button { font: inherit; padding: 8px 16px; margin-top: 8px; }
  #answer { white-space: pre-wrap; margin-top: 24px; }
  .meta { color: #666; font-size: 0.9em; }
</style></head>
<body>
<h1>Ask My Docs</h1>
<textarea id="q" maxlength="500">How long until I get my money back?</textarea>
<label><input type="checkbox" id="agent" checked> Use the agent (search more than once, calculate)</label><br>
<button onclick="ask()">Ask</button>
<div id="answer"></div>
<script>
async function ask() {
  const out = document.getElementById("answer");
  out.textContent = "Thinking...";
  const mode = document.getElementById("agent").checked ? "agent" : "single";
  const r = await fetch("/ask", {method: "POST", headers: {"Content-Type": "application/json"},
    body: JSON.stringify({question: document.getElementById("q").value, mode, steps: true})});
  const data = await r.json();
  if (!r.ok) { out.textContent = data.detail || "Error"; return; }
  const steps = (data.steps || []).map(s => "- " + s).join("\\n");
  out.innerHTML = "";
  out.append(data.answer);
  const meta = document.createElement("p");
  meta.className = "meta";
  meta.textContent = `${data.seconds} s${data.cached ? " (from the cache)" : ""}` + (steps ? "\\n" + steps : "");
  out.append(meta);
}
</script>
</body></html>
"""
