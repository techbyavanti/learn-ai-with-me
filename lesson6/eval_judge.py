"""Can you trust a judge model? Compare its verdicts with answers that I labeled by hand.

evals/labeled_answers.jsonl has answers with my label: "correct" or "wrong".
The judge (the prompt from lesson 4) reads the same documents as the app and says YES or NO.

    python eval_judge.py --models llama3.2:3b qwen2.5:7b-instruct
"""

import argparse
import json
from pathlib import Path

import ollama

from app import Index, load_chunks
from guardrails import judge_answer

LABELS = Path(__file__).parent / "evals" / "labeled_answers.jsonl"


def make_judge(model):
    def chat(prompt):
        response = ollama.chat(model=model, messages=[{"role": "user", "content": prompt}],
                               options={"temperature": 0})
        return response["message"]["content"]
    return chat


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--models", nargs="+", default=["llama3.2:3b"])
    parser.add_argument("-v", "--verbose", action="store_true", help="Print every disagreement.")
    args = parser.parse_args()

    rows = [json.loads(line) for line in LABELS.read_text().splitlines() if line.strip()]
    index = Index(load_chunks("sections"))
    n_correct = sum(r["label"] == "correct" for r in rows)
    n_wrong = len(rows) - n_correct
    print(f"{len(rows)} labeled answers: {n_correct} correct, {n_wrong} wrong\n")
    print(f"{'Judge':<22} {'Agrees with me':>15} {'Wrong answers caught':>21} {'Correct answers blocked':>24}")
    for model in args.models:
        judge = make_judge(model)
        agree = caught = blocked = 0
        misses = []
        for r in rows:
            says_ok = judge_answer(r["question"], r["answer"], index.search(r["question"]), judge)
            if says_ok == (r["label"] == "correct"):
                agree += 1
            else:
                misses.append(r)
            if r["label"] == "wrong" and not says_ok:
                caught += 1
            if r["label"] == "correct" and not says_ok:
                blocked += 1
        print(f"{model:<22} {agree:>8}/{len(rows):<6} {caught:>14}/{n_wrong:<6} {blocked:>17}/{n_correct:<6}")
        if args.verbose:
            for r in misses:
                verdict = "blocked" if r["label"] == "correct" else "passed"
                print(f"    {verdict:<8} ({r['note']}) {r['answer'][:90]}")


if __name__ == "__main__":
    main()
