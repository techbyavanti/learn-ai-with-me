"""Compare the chunking strategies with a small retrieval eval.

Each test has a question and a short phrase from the answer. A test passes
when one of the top k chunks contains the whole phrase. A chunk that has only
half of the answer does not help the decoder, so it does not pass.
"""

from app import Index, encoder, load_chunks
from chunking import STRATEGIES

TESTS = [
    ("How long until I get my money back?", "This takes 5 to 7 business days"),
    ("Is there a discount for schools?", "discount of 50 percent"),
    ("What happens if my card payment fails?", "we try again after 3 days and after 7 days"),
    ("How much is the yearly plan?", "the price is 10 dollars for each user"),
    ("Can I pay by bank transfer?", "Customers on the yearly plan can also pay by bank transfer"),
    ("How long is a password reset link valid?", "The link is valid for one hour"),
    ("Which identity providers work with SSO?", "Okta, Microsoft Entra ID, and Google Workspace"),
    ("When does a session end on its own?", "after 30 days without activity"),
    ("Can I restore a project that I deleted?", "open the Trash and select 'Restore'"),
    ("How often do you back up my data?", "every 6 hours"),
    ("Can I keep my data in the United States?", "select a data center in the United States"),
    ("When is live chat open?", "from 9:00 to 17:00 Central European Time"),
    ("Is there parking at the office?", "public parking garage next to the building"),
    ("How fast do you reply on the paid plan?", "we reply to them in 4 hours"),
    ("Does the phone app work without internet?", "without an internet connection"),
    ("How long is an invitation valid?", "Invitations are valid for 7 days"),
]


def flat(text):
    return " ".join(text.split())


def hit_rate(index, tests, k=3, verbose=False):
    found = 0
    for question, phrase in tests:
        texts = [flat(chunk["text"]) for chunk, _ in index.search(question, k)]
        if any(phrase in text for text in texts):
            found += 1
        elif verbose:
            print(f"  MISS: {question!r}")
    return found / len(tests)


def words_sent(index, tests, k=3):
    """The average number of words that go to the decoder for each question."""
    total = 0
    for question, _ in tests:
        total += sum(len(chunk["text"].split()) for chunk, _ in index.search(question, k))
    return total / len(tests)


if __name__ == "__main__":
    import sys

    verbose = "-v" in sys.argv
    print(f"Encoder reads at most {encoder.max_seq_length} tokens of each chunk.\n")
    print(f"{'Strategy':<10} {'Chunks':>6} {'Hit rate':>9} {'Words sent':>11}")
    for name in STRATEGIES:
        index = Index(load_chunks(name))
        rate = hit_rate(index, TESTS, verbose=verbose)
        print(f"{name:<10} {len(index.chunks):>6} {rate:>9.0%} {words_sent(index, TESTS):>11.0f}")
