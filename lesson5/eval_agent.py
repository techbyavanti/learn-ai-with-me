"""Compare one search (lesson 4) with the agent loop, on questions that need more than one step.

A test passes when the answer gets through the guardrails AND contains every expected
number or phrase. The script also counts model calls and time.

Run: python eval_agent.py                                  (the local model, 1 run)
     python eval_agent.py --models llama3.2:3b qwen2.5:7b-instruct --runs 3
"""

import argparse
import re
import time
from collections import defaultdict

import app
from app import Index, ask, ask_agent, load_chunks

# (question, expected parts of the answer, kind)
TESTS = [
    ("How much do 10 users pay for one year on the yearly plan?", ["1200"], "multi-step"),
    ("A school has 30 users on the monthly paid plan. How much does it pay each month "
     "after the school discount?", ["180"], "multi-step"),
    ("We have 25 users on the paid plan. Can we use single sign-on, and how much do we pay "
     "each month?", ["300"], "multi-step"),
    ("How much does a nonprofit with 8 users pay for one year on the yearly plan?", ["480"], "multi-step"),
    ("I deleted a project 10 days ago. How many days do I have left to restore it?", ["20"], "multi-step"),
    ("For 5 users, how much do we save in one year with the yearly plan instead of the "
     "monthly plan?", ["120"], "multi-step"),
    ("We have 15 users on the paid plan. Can we use single sign-on?", ["20"], "multi-step"),
    ("My card payment failed. How many times do you try again, and what happens if the "
     "last try fails?", ["free plan"], "multi-step"),
    ("How long until I get my money back?", ["5 to 7"], "simple"),
    ("When is live chat open?", ["9:00"], "simple"),
    ("How long is an invitation valid?", ["7 days"], "simple"),
    ("Is there a discount for schools?", ["50"], "simple"),
]


def normalize(text):
    """'$1,200.00' -> '1200' so that numbers compare in one form."""
    text = text.lower().replace("$", " ").replace("€", " ")
    text = re.sub(r"(?<=\d),(?=\d{3})", "", text)
    return re.sub(r"(\d+)\.0+\b", r"\1", text)


def passed(answer, expected):
    text = normalize(answer)
    return all(re.search(rf"(?<![\d.]){re.escape(normalize(e))}(?![\d])", text) for e in expected)


def run(index, model, mode, question):
    """Return (answer, blocked, model_calls, seconds)."""
    guard = []
    start = time.perf_counter()
    if mode == "single":
        app.LOCAL_MODEL = model
        answer = ask(index, question, guard=guard)
        calls = 1 if not guard or not guard[0].startswith("input") else 0
    else:
        answer, result = ask_agent(index, question, guard=guard, model=model)
        calls = result.model_calls if result else 0
    return answer, bool(guard), calls, time.perf_counter() - start


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--models", nargs="+", default=[app.LOCAL_MODEL])
    parser.add_argument("--runs", type=int, default=1)
    parser.add_argument("-v", "--verbose", action="store_true", help="Print every answer.")
    args = parser.parse_args()

    index = Index(load_chunks("sections"))
    rows = []
    for model in args.models:
        for mode in ["single", "agent"]:
            stats = defaultdict(lambda: defaultdict(float))
            for _ in range(args.runs):
                for question, expected, kind in TESTS:
                    answer, blocked, calls, seconds = run(index, model, mode, question)
                    ok = passed(answer, expected) and not blocked
                    for group in (kind, "all"):
                        s = stats[group]
                        s["n"] += 1
                        s["ok"] += ok
                        s["blocked"] += blocked
                        s["calls"] += calls
                        s["seconds"] += seconds
                    if args.verbose:
                        mark = "ok  " if ok else ("BLCK" if blocked else "FAIL")
                        print(f"[{model} {mode}] {mark} {question}\n      {' '.join(answer.split())[:200]}")
            rows.append((model, mode, stats))

    print(f"\n{'Model':<22} {'Mode':<7} {'Multi-step':>11} {'Simple':>8} {'Blocked':>8} {'Other':>7} "
          f"{'Calls':>6} {'Seconds':>8}")
    for model, mode, stats in rows:
        m, s, a = stats["multi-step"], stats["simple"], stats["all"]
        other = int(a["n"] - a["ok"] - a["blocked"])
        print(f"{model:<22} {mode:<7} {int(m['ok']):>4}/{int(m['n']):<6} {int(s['ok']):>3}/{int(s['n']):<4} "
              f"{int(a['blocked']):>4}/{int(a['n']):<3} {other:>3}/{int(a['n']):<3} "
              f"{a['calls'] / a['n']:>6.1f} {a['seconds'] / a['n']:>8.1f}")
    print("\nMulti-step and Simple = correct answers. Blocked = stopped by the output guardrails "
          "(the user gets 'I do not know').\nOther = the answer got to the user, but it is wrong, "
          "incomplete, or 'I do not know'.\nCalls and Seconds = average for each question.")


if __name__ == "__main__":
    main()
