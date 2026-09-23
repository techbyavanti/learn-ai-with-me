"""Ask My Notes: a small RAG app.

An encoder finds the correct notes. A decoder writes the answer from them.
A router sends the prompt to a local model or to a frontier model.
"""

import argparse
import os
import sys

import numpy as np
from sentence_transformers import SentenceTransformer

from notes import NOTES

ENCODER_MODEL = "all-MiniLM-L6-v2"
LOCAL_MODEL = os.environ.get("LOCAL_MODEL", "llama3.2")
FRONTIER_MODEL = os.environ.get("FRONTIER_MODEL", "claude-sonnet-5")
MIN_SCORE = 0.3  # start value; change it for your data

# Step 1: embed the notes (one time for each set of notes)
encoder = SentenceTransformer(ENCODER_MODEL)
note_vectors = encoder.encode(NOTES, normalize_embeddings=True)


# Step 2: search the notes
def search(question, k=3):
    """Return the k closest notes as (text, score) pairs."""
    q = encoder.encode([question], normalize_embeddings=True)[0]
    scores = note_vectors @ q
    top = np.argsort(scores)[::-1][:k]
    return [(NOTES[i], float(scores[i])) for i in top]


# Step 3: write the answer with a decoder
def build_prompt(question, hits):
    context = "\n".join(f"- {text}" for text, _ in hits)
    return (
        "Answer the question with only the notes below.\n"
        "If the notes do not contain the answer, say: I do not know.\n\n"
        f"Notes:\n{context}\n\nQuestion: {question}"
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
def ask(question, hard=False):
    hits = search(question)
    if hits[0][1] < MIN_SCORE:
        return "I do not know. No note matches this question."
    prompt = build_prompt(question, hits)
    if hard:
        return answer_frontier(prompt)
    return answer_local(prompt)


def main():
    parser = argparse.ArgumentParser(description="Ask questions about your notes.")
    parser.add_argument("question", nargs="?", help="The question. Leave empty for chat mode.")
    parser.add_argument("--hard", action="store_true", help="Use the frontier model.")
    parser.add_argument("--show-search", action="store_true", help="Show the search results.")
    args = parser.parse_args()

    def run(question):
        if args.show_search:
            for text, score in search(question):
                print(f"  [{score:.2f}] {text}")
        print(ask(question, hard=args.hard))

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
