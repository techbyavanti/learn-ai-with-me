"""Ask My Docs: the lesson 1 app, now for long documents.

The app cuts each document into chunks, embeds the chunks, and searches them.
The rest is the same as lesson 1: a decoder writes the answer from the chunks,
and a router sends the prompt to a local model or to a frontier model.
"""

import argparse
import os
import sys
from pathlib import Path

import numpy as np
from sentence_transformers import SentenceTransformer

from chunking import STRATEGIES

ENCODER_MODEL = "all-MiniLM-L6-v2"
LOCAL_MODEL = os.environ.get("LOCAL_MODEL", "llama3.2")
FRONTIER_MODEL = os.environ.get("FRONTIER_MODEL", "claude-sonnet-5")
MIN_SCORE = 0.3  # start value; change it for your data
DOCS_DIR = Path(__file__).parent / "docs"

encoder = SentenceTransformer(ENCODER_MODEL)


# Step 1: load the documents and cut them into chunks
def load_chunks(strategy="sections", docs_dir=DOCS_DIR):
    chunker = STRATEGIES[strategy]
    chunks = []
    for path in sorted(Path(docs_dir).glob("*.md")):
        chunks.extend(chunker(path.read_text(), path.name))
    return chunks


# Step 2: embed the chunks and search them
class Index:
    def __init__(self, chunks):
        self.chunks = chunks
        self.vectors = encoder.encode([c["text"] for c in chunks], normalize_embeddings=True)

    def search(self, question, k=3):
        """Return the k closest chunks as (chunk, score) pairs."""
        q = encoder.encode([question], normalize_embeddings=True)[0]
        scores = self.vectors @ q
        top = np.argsort(scores)[::-1][:k]
        return [(self.chunks[i], float(scores[i])) for i in top]


# Step 3: write the answer with a decoder (the same as lesson 1)
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


# Step 4: connect the parts
def ask(index, question, hard=False):
    hits = index.search(question)
    if hits[0][1] < MIN_SCORE:
        return "I do not know. No document matches this question."
    prompt = build_prompt(question, hits)
    if hard:
        return answer_frontier(prompt)
    return answer_local(prompt)


def main():
    parser = argparse.ArgumentParser(description="Ask questions about your documents.")
    parser.add_argument("question", nargs="?", help="The question. Leave empty for chat mode.")
    parser.add_argument("--strategy", choices=STRATEGIES, default="sections",
                        help="How to cut the documents into chunks (default: sections).")
    parser.add_argument("--docs", default=DOCS_DIR, help="Folder with .md documents.")
    parser.add_argument("--hard", action="store_true", help="Use the frontier model.")
    parser.add_argument("--show-search", action="store_true", help="Show the search results.")
    args = parser.parse_args()

    index = Index(load_chunks(args.strategy, args.docs))
    print(f"{len(index.chunks)} chunks ({args.strategy})")

    def run(question):
        if args.show_search:
            for chunk, score in index.search(question):
                preview = " ".join(chunk["text"].split())[:90]
                print(f"  [{score:.2f}] {chunk['source']}: {preview}...")
        print(ask(index, question, hard=args.hard))

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
