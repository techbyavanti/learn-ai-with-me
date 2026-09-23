"""Step 5: test the search part.

Each test has a question and the index of the correct note in NOTES.
Write the questions in different words from the notes.
"""

from app import search
from notes import NOTES

TESTS = [
    ("When does the office close?", 0),
    ("I forgot my password", 1),
    ("How long do refunds take?", 2),
    ("How much is the paid plan?", 4),
    ("Can I download my data?", 5),
    ("Can I get a deleted project back?", 7),
]


def retrieval_hit_rate(tests, k=3):
    found = 0
    for question, note_id in tests:
        texts = [text for text, _ in search(question, k)]
        if NOTES[note_id] in texts:
            found += 1
        else:
            print(f"MISS: {question!r}")
    return found / len(tests)


if __name__ == "__main__":
    print(f"Retrieval hit rate: {retrieval_hit_rate(TESTS):.0%}")
