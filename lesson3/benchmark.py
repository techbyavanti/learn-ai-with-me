"""Measure where the start-up time goes, with and without the vector cache.

The six help pages are too small to show a difference, so this script also
makes a large set of pages: copies of the six pages with a different product
name in each title. The copies are for timing only, not for search quality.
"""

import argparse
import shutil
import tempfile
import time
from pathlib import Path

from app import DOCS_DIR, ENCODER_MODEL, LOCAL_MODEL, Index, ask, load_chunks
from cache import AnswerCache, VectorCache

QUESTIONS = [
    "How long until I get my money back?",
    "Is there a discount for schools?",
    "When is live chat open?",
]


def timed(fn):
    start = time.perf_counter()
    result = fn()
    return result, time.perf_counter() - start


def make_pages(folder, copies):
    """Write `copies` versions of each help page. Each version has its own title."""
    for path in sorted(DOCS_DIR.glob("*.md")):
        text = path.read_text()
        title, rest = text.split("\n", 1)
        for n in range(copies):
            (folder / f"{path.stem}_{n:04d}.md").write_text(f"{title} (product {n})\n{rest}")


def run(docs_dir, cache_path, get_encoder, label):
    chunks = load_chunks("sections", docs_dir)
    texts = [c["text"] for c in chunks]

    cache_path.unlink(missing_ok=True)
    (_, stats), cold = timed(lambda: VectorCache(cache_path).embed(get_encoder, ENCODER_MODEL, texts))
    assert stats["embedded"] == len(texts)
    (_, stats), warm = timed(lambda: VectorCache(cache_path).embed(get_encoder, ENCODER_MODEL, texts))
    assert stats["reused"] == len(texts)

    # Change one page: add a sentence to one section.
    first = sorted(Path(docs_dir).glob("*.md"))[0]
    text = first.read_text()
    heading_end = text.index("\n", text.index("\n## ") + 1)
    first.write_text(text[:heading_end] + "\nThis sentence is new." + text[heading_end:])
    texts = [c["text"] for c in load_chunks("sections", docs_dir)]
    (_, stats), edit = timed(lambda: VectorCache(cache_path).embed(get_encoder, ENCODER_MODEL, texts))

    size_mb = cache_path.stat().st_size / 1e6
    print(f"{label:<12} {len(texts):>7} {cold:>10.2f} {warm:>10.2f} {edit:>10.2f} {stats['embedded']:>9} {size_mb:>8.1f}")


def answer_timing(tmp):
    """Ask each question two times: the first answer comes from the model, the second from the cache."""
    index = Index(load_chunks("sections"))
    answers = AnswerCache(tmp / "answers.json")
    print(f"\nAnswers from {LOCAL_MODEL}, then from the answer cache:")
    for question in QUESTIONS:
        _, first = timed(lambda: ask(index, question, answers=answers))
        _, second = timed(lambda: ask(index, question, answers=answers))
        print(f"  {first:>5.2f} s -> {second:.3f} s  {question}")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--copies", type=int, default=200, help="Copies of each page for the large set.")
    parser.add_argument("--answers", action="store_true", help="Also time the answer cache (needs Ollama).")
    parser.add_argument("--device", default=None, help="cpu, cuda, or mps. Default: the fastest one.")
    args = parser.parse_args()

    def load():
        from sentence_transformers import SentenceTransformer

        return SentenceTransformer(ENCODER_MODEL, device=args.device)

    encoder, load_time = timed(load)
    print(f"Load the encoder (one time for each start): {load_time:.2f} s on {encoder.device}\n")

    print(f"{'Pages':<12} {'Chunks':>7} {'No cache':>10} {'Cache':>10} {'1 edit':>10} {'Embedded':>9} {'Cache MB':>8}")
    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        small = tmp / "small"
        shutil.copytree(DOCS_DIR, small)
        run(small, tmp / "small.npz", lambda: encoder, "6")

        large = tmp / "large"
        large.mkdir()
        make_pages(large, args.copies)
        run(large, tmp / "large.npz", lambda: encoder, f"{6 * args.copies:,}")
        print("\nTimes in seconds. '1 edit' = the start after one section of one page changed.")
        if args.answers:
            answer_timing(tmp)


if __name__ == "__main__":
    main()
