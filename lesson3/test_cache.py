"""Check that the caches embed again exactly when they must.

Run: python test_cache.py
"""

import shutil
import tempfile
from pathlib import Path

from app import DOCS_DIR, ENCODER_MODEL, get_encoder, load_chunks
from cache import AnswerCache, VectorCache


def embed(cache_path, docs, strategy="sections", encoder_name=ENCODER_MODEL):
    texts = [c["text"] for c in load_chunks(strategy, docs)]
    _, stats = VectorCache(cache_path).embed(get_encoder, encoder_name, texts)
    return stats


def check(name, stats, embedded):
    status = "ok" if stats["embedded"] == embedded else "FAIL"
    print(f"{status:<4} {name:<38} reused {stats['reused']:>3}, embedded {stats['embedded']:>3}")
    return status == "ok"


def main():
    results = []
    with tempfile.TemporaryDirectory() as tmp:
        docs = Path(tmp) / "docs"
        shutil.copytree(DOCS_DIR, docs)
        cache = Path(tmp) / "vectors.npz"
        total = len(load_chunks("sections", docs))

        results.append(check("first start", embed(cache, docs), total))
        results.append(check("second start, nothing changed", embed(cache, docs), 0))

        billing = docs / "billing.md"
        billing.write_text(billing.read_text().replace("5 to 7", "3 to 5"))
        results.append(check("one fact changed in one page", embed(cache, docs), 1))

        (docs / "new.md").write_text("# New page\n\n## Holidays\n\nWe close on 24 December.\n")
        results.append(check("one new page", embed(cache, docs), 1))

        (docs / "new.md").unlink()
        results.append(check("one page deleted", embed(cache, docs), 0))

        results.append(check("other chunking (fixed)", embed(cache, docs, "fixed"),
                             len(load_chunks("fixed", docs))))
        results.append(check("other encoder name", embed(cache, docs, encoder_name="other-encoder"),
                             total))

        answers = AnswerCache(Path(tmp) / "answers.json")
        answers.put("llama3.2", "prompt A", "answer A")
        same = answers.get("llama3.2", "prompt A") == "answer A"
        other_model = answers.get("claude-sonnet-5", "prompt A") is None
        other_prompt = answers.get("llama3.2", "prompt B") is None
        ok = same and other_model and other_prompt
        print(f"{'ok' if ok else 'FAIL':<4} answer cache: same prompt hits, other model or prompt misses")
        results.append(ok)

    if not all(results):
        raise SystemExit("Some cache checks failed.")
    print("All cache checks passed.")


if __name__ == "__main__":
    main()
