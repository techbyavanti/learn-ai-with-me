"""Ask My Docs, with caching.

This is the lesson 2 app with two caches. The vector cache saves the vector of
each chunk, so the app embeds only new or changed chunks. The answer cache
saves each answer, so the same question with the same chunks does not call the
model again.
"""

import argparse
import os
import sys
import time
from pathlib import Path

import numpy as np

from cache import AnswerCache, VectorCache, make_key
from chunking import STRATEGIES

ENCODER_MODEL = "all-MiniLM-L6-v2"
LOCAL_MODEL = os.environ.get("LOCAL_MODEL", "llama3.2")
FRONTIER_MODEL = os.environ.get("FRONTIER_MODEL", "claude-sonnet-5")
MIN_SCORE = 0.3  # start value; change it for your data
HERE = Path(__file__).parent
DOCS_DIR = HERE / "docs"
CACHE_DIR = HERE / ".cache"

_encoder = None


def get_encoder():
    """Load the encoder the first time that we need it."""
    global _encoder
    if _encoder is None:
        from sentence_transformers import SentenceTransformer

        _encoder = SentenceTransformer(ENCODER_MODEL)
    return _encoder


# Step 1: load the documents and cut them into chunks
def load_chunks(strategy="sections", docs_dir=DOCS_DIR):
    chunker = STRATEGIES[strategy]
    chunks = []
    for path in sorted(Path(docs_dir).glob("*.md")):
        chunks.extend(chunker(path.read_text(), path.name))
    return chunks


# Step 2: embed the chunks (with the vector cache) and search them
def vector_cache_path(docs_dir=DOCS_DIR):
    """One cache file for each docs folder, so that two folders do not remove each other's vectors."""
    return CACHE_DIR / f"vectors-{make_key(str(Path(docs_dir).resolve()))}.npz"


class Index:
    def __init__(self, chunks, cache_path=None):
        """Embed the chunks. With a cache_path, reuse the vectors that are saved there."""
        self.chunks = chunks
        texts = [c["text"] for c in chunks]
        if cache_path:
            cache = VectorCache(cache_path)
            self.vectors, self.stats = cache.embed(get_encoder, ENCODER_MODEL, texts)
        else:
            self.vectors = get_encoder().encode(texts, normalize_embeddings=True)
            self.stats = {"reused": 0, "embedded": len(texts)}

    def search(self, question, k=3):
        """Return the k closest chunks as (chunk, score) pairs."""
        q = get_encoder().encode([question], normalize_embeddings=True)[0]
        scores = self.vectors @ q
        top = np.argsort(scores)[::-1][:k]
        return [(self.chunks[i], float(scores[i])) for i in top]


# Step 3: write the answer with a decoder (the same as lesson 2)
def build_prompt(question, hits):
    context = "\n\n".join(f"[{chunk['source']}]\n{chunk['text']}" for chunk, _ in hits)
    return (
        "Answer the question with only the documents below.\n"
        "If the documents do not contain the answer, say: I do not know.\n\n"
        f"Documents:\n{context}\n\nQuestion: {question}"
    )


def answer_local(prompt):
    """Use the open weight model through Ollama."""
    import ollama

    try:
        response = ollama.chat(
            model=LOCAL_MODEL,
            messages=[{"role": "user", "content": prompt}],
        )
    except ollama.ResponseError as e:
        if e.status_code == 404:
            sys.exit(
                f"Error: the Ollama model '{LOCAL_MODEL}' is not installed.\n"
                f"Run 'ollama pull {LOCAL_MODEL}', or set LOCAL_MODEL to a model "
                "from 'ollama list'."
            )
        raise
    except ConnectionError:
        sys.exit("Error: cannot connect to Ollama. Start it with 'ollama serve'.")
    return response["message"]["content"]


_client = None


def answer_frontier(prompt):
    """Use the frontier model through the Anthropic API."""
    global _client
    if _client is None:
        import anthropic

        if not os.environ.get("ANTHROPIC_API_KEY"):
            sys.exit("Error: --hard needs the ANTHROPIC_API_KEY environment variable.")
        _client = anthropic.Anthropic()  # reads ANTHROPIC_API_KEY
    response = _client.messages.create(
        model=FRONTIER_MODEL,
        max_tokens=500,
        messages=[{"role": "user", "content": prompt}],
    )
    return response.content[0].text


# Step 4: connect the parts (with the answer cache)
def ask(index, question, hard=False, answers=None):
    hits = index.search(question)
    if hits[0][1] < MIN_SCORE:
        return "I do not know. No document matches this question."
    prompt = build_prompt(question, hits)
    model = FRONTIER_MODEL if hard else LOCAL_MODEL
    if answers is not None:
        saved = answers.get(model, prompt)
        if saved is not None:
            return saved
    answer = answer_frontier(prompt) if hard else answer_local(prompt)
    if answers is not None:
        answers.put(model, prompt, answer)
    return answer


def main():
    parser = argparse.ArgumentParser(description="Ask questions about your documents.")
    parser.add_argument("question", nargs="?", help="The question. Leave empty for chat mode.")
    parser.add_argument("--strategy", choices=STRATEGIES, default="sections",
                        help="How to cut the documents into chunks (default: sections).")
    parser.add_argument("--docs", default=DOCS_DIR, help="Folder with .md documents.")
    parser.add_argument("--hard", action="store_true", help="Use the frontier model.")
    parser.add_argument("--show-search", action="store_true", help="Show the search results.")
    parser.add_argument("--no-cache", action="store_true", help="Do not read or write the caches.")
    args = parser.parse_args()

    start = time.perf_counter()
    cache_path = None if args.no_cache else vector_cache_path(args.docs)
    index = Index(load_chunks(args.strategy, args.docs), cache_path)
    answers = None if args.no_cache else AnswerCache(CACHE_DIR / "answers.json")
    get_encoder()  # the questions need the encoder, even when all the chunks come from the cache
    print(f"{len(index.chunks)} chunks: {index.stats['reused']} from the cache, "
          f"{index.stats['embedded']} embedded. Ready in {time.perf_counter() - start:.1f} s.")

    def run(question):
        if args.show_search:
            for chunk, score in index.search(question):
                preview = " ".join(chunk["text"].split())[:90]
                print(f"  [{score:.2f}] {chunk['source']}: {preview}...")
        start = time.perf_counter()
        answer = ask(index, question, hard=args.hard, answers=answers)
        print(answer)
        print(f"({time.perf_counter() - start:.2f} s)")

    if args.question:
        run(args.question)
        return

    print("Ask a question. Type 'exit' to stop.")
    while True:
        try:
            question = input("\n> ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            break
        if question.lower() in {"exit", "quit"}:
            break
        if question:
            run(question)


if __name__ == "__main__":
    main()
