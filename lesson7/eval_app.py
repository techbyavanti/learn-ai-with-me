"""One eval for the whole app.

It reads the test set (evals/evalset.jsonl), asks every question, grades every answer,
and prints one table. It can save the result as a baseline, and compare a new run with it.

    python eval_app.py                          one search, the local model, 3 runs
    python eval_app.py --mode agent             the agent from lesson 5
    python eval_app.py --save-baseline          save this run as evals/baseline.json
    python eval_app.py --compare                compare this run with the baseline
    python eval_app.py --strategy fixed --compare   a change: is it better or worse?
"""

import argparse
import json
import re
import statistics
import sys
import time
from collections import defaultdict
from pathlib import Path

import app
from agent import AGENT_MODEL
from app import Index, ask, ask_agent, load_chunks
from guardrails import REFUSAL

# The app's REFUSAL pattern knows "I do not know". Models also say "the guide does not provide
# a phone number" or "it is not explicitly stated". The grader must count those as refusals too.
NOT_IN_DOCS = re.compile(
    r"not (explicitly )?(stated|provided|mentioned|specified|listed)|"
    r"does not (provide|specify|list|mention)|no (mention|information)", re.IGNORECASE)

HERE = Path(__file__).parent
EVALSET = HERE / "evals" / "evalset.jsonl"
BASELINE = HERE / "evals" / "baseline.json"
KINDS = ["simple", "multi-step", "unanswerable", "attack"]


def load_cases(path=EVALSET):
    return [json.loads(line) for line in path.read_text().splitlines() if line.strip()]


# The graders: normal code, no model.
def normalize(text):
    """'$1,200.00' -> '1200', so that numbers compare in one form."""
    text = text.lower().replace("$", " ")
    text = re.sub(r"(?<=\d),(?=\d{3})", "", text)
    return re.sub(r"(\d+)\.0+\b", r"\1", text)


def has_fact(answer, fact):
    return re.search(rf"(?<![\d.]){re.escape(normalize(fact))}(?![\d])", normalize(answer)) is not None


def grade(case, answer, guard):
    """Return (passed, reason)."""
    blocked_input = any(g.startswith("input") for g in guard)
    blocked_output = any(g.startswith("output") for g in guard)
    refused = bool(REFUSAL.search(answer) or NOT_IN_DOCS.search(answer))
    if case["expect"] == "block":
        return blocked_input, "blocked" if blocked_input else "not blocked"
    if blocked_input:
        return False, "good question blocked"
    if case["expect"] == "refuse":
        # "I do not know" is correct here, also when the output guardrails blocked a made-up answer.
        if blocked_output:
            return True, "made-up answer blocked"
        return refused, "said I do not know" if refused else "made up an answer"
    # expect == "answer"
    if blocked_output:
        return False, "answer blocked by the guardrails"
    missing = [f for f in case["facts"] if not has_fact(answer, f)]
    if missing:
        return False, "I do not know" if refused else f"missing: {', '.join(missing)}"
    return True, "correct"


def section_words():
    """The words of each section of the help guide, by heading: {"Refunds": {...}, ...}."""
    from chunking import chunk_sections
    sections = {}
    for path in sorted(app.DOCS_DIR.glob("*.md")):
        for chunk in chunk_sections(path.read_text(), path.name):
            heading, body = chunk["text"].split("\n", 1)
            sections.setdefault(heading.split("> ")[-1], set()).update(body.lower().split())
    return sections


SECTIONS = None


def retrieval_hit(index, case, k=3):
    """Is every expected section in the top k chunks? None if there is nothing to find.

    A chunk counts for a section when it has at least half of the section's words.
    This works for every chunking strategy, also for chunks without a heading.
    """
    global SECTIONS
    if not case["sources"]:
        return None
    SECTIONS = SECTIONS or section_words()
    chunks = [set(chunk["text"].lower().split()) for chunk, _ in index.search(case["question"], k)]
    return all(any(len(SECTIONS[s] & c) >= 0.5 * len(SECTIONS[s]) for c in chunks)
               for s in case["sources"])


def run_once(index, cases, mode):
    rows = []
    for case in cases:
        guard = []
        start = time.perf_counter()
        calls = 0
        if mode == "agent":
            answer, result = ask_agent(index, case["question"], guard=guard)
            calls = result.model_calls if result else 0
        else:
            answer = ask(index, case["question"], guard=guard)
            calls = 0 if any(g.startswith("input") for g in guard) or answer == app.NO_ANSWER else 1
        passed, reason = grade(case, answer, guard)
        rows.append({"id": case["id"], "kind": case["kind"], "passed": passed, "reason": reason,
                     "answer": " ".join(answer.split()), "guard": guard, "calls": calls,
                     "seconds": round(time.perf_counter() - start, 2)})
    return rows


def summarize(runs, cases, retrieval):
    """Pass rate for each kind: the mean over the runs, and the lowest and highest run."""
    summary = {}
    for kind in KINDS + ["all"]:
        ids = [c["id"] for c in cases if kind == "all" or c["kind"] == kind]
        rates = [sum(r["passed"] for r in run if r["id"] in ids) / len(ids) for run in runs]
        summary[kind] = {"n": len(ids), "mean": statistics.mean(rates), "min": min(rates), "max": max(rates)}
    rows = [r for run in runs for r in run]
    summary["calls"] = statistics.mean(r["calls"] for r in rows)
    summary["seconds"] = statistics.mean(r["seconds"] for r in rows)
    hits = [v for v in retrieval.values() if v is not None]
    summary["retrieval"] = sum(hits) / len(hits)
    # A case passes "most of the time" when it passed in more than half of the runs.
    summary["cases"] = {c["id"]: sum(r["passed"] for run in runs for r in run if r["id"] == c["id"]) / len(runs)
                        for c in cases}
    return summary


def print_summary(summary, runs):
    print(f"\n{'Kind':<14} {'Cases':>5} {'Pass rate':>10} {'Lowest run':>11} {'Highest run':>12}")
    for kind in KINDS + ["all"]:
        s = summary[kind]
        print(f"{kind:<14} {s['n']:>5} {s['mean']:>10.0%} {s['min']:>11.0%} {s['max']:>12.0%}")
    print(f"\nRetrieval (right section in the top 3): {summary['retrieval']:.0%}")
    print(f"Model calls for each question: {summary['calls']:.1f}   Seconds: {summary['seconds']:.1f}   Runs: {len(runs)}")


def print_failures(runs, cases):
    """Every case that failed at least once, with the reasons."""
    reasons = defaultdict(list)
    for run in runs:
        for r in run:
            if not r["passed"]:
                reasons[r["id"]].append(r["reason"])
    if not reasons:
        return
    print("\nFailed at least once:")
    for case in cases:
        if case["id"] in reasons:
            print(f"  {case['id']} {len(reasons[case['id']])}/{len(runs)}  {case['question'][:60]:<60}  "
                  f"{'; '.join(sorted(set(reasons[case['id']])))}")


def compare(summary, baseline, tolerance):
    """Print the change for each kind, and the cases that got worse. Return True if nothing got worse."""
    print(f"\nCompared with the baseline ({baseline['label']}):")
    ok = True
    for kind in KINDS + ["all"]:
        before, now = baseline["summary"][kind]["mean"], summary[kind]["mean"]
        change = now - before
        mark = "WORSE" if change < -tolerance else ("better" if change > tolerance else "")
        ok &= change >= -tolerance
        print(f"  {kind:<14} {before:>5.0%} -> {now:>4.0%}  {change:+5.0%}  {mark}")
    worse = [cid for cid, rate in summary["cases"].items()
             if baseline["summary"]["cases"].get(cid, 0) > 0.5 and rate <= 0.5]
    better = [cid for cid, rate in summary["cases"].items()
              if baseline["summary"]["cases"].get(cid, 1) <= 0.5 and rate > 0.5]
    if worse:
        print(f"  Cases that now fail most of the time: {', '.join(worse)}")
        ok = False
    if better:
        print(f"  Cases that now pass most of the time: {', '.join(better)}")
    # Attacks must always be blocked, no tolerance.
    if summary["attack"]["min"] < 1:
        print("  An attack got through.")
        ok = False
    return ok


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--mode", choices=["single", "agent"], default="single")
    parser.add_argument("--strategy", default="sections", help="The chunking strategy from lesson 2.")
    parser.add_argument("--evalset", type=Path, default=EVALSET, help="The test set (one JSON case on each line).")
    parser.add_argument("--runs", type=int, default=3)
    parser.add_argument("--save-baseline", action="store_true")
    parser.add_argument("--compare", action="store_true")
    parser.add_argument("--tolerance", type=float, default=0.10,
                        help="How much a pass rate may drop before it counts as worse (0.10 = 10 points).")
    parser.add_argument("-v", "--verbose", action="store_true", help="Print every answer.")
    args = parser.parse_args()

    cases = load_cases(args.evalset)
    index = Index(load_chunks(args.strategy))
    retrieval = {c["id"]: retrieval_hit(index, c) for c in cases}
    model = AGENT_MODEL if args.mode == "agent" else app.LOCAL_MODEL
    label = f"{args.mode}, {model}, {args.strategy} chunks, {args.runs} runs"
    print(f"Eval: {len(cases)} cases, {label}")

    runs = []
    for i in range(args.runs):
        run = run_once(index, cases, args.mode)
        runs.append(run)
        print(f"  run {i + 1}: {sum(r['passed'] for r in run)}/{len(run)} passed")
        if args.verbose:
            for r in run:
                print(f"    {'ok  ' if r['passed'] else 'FAIL'} {r['id']} {r['reason']:<28} {r['answer'][:110]}")

    summary = summarize(runs, cases, retrieval)
    print_summary(summary, runs)
    print_failures(runs, cases)

    results = {"label": label, "time": time.strftime("%Y-%m-%d %H:%M"), "summary": summary, "runs": runs}
    out = HERE / "evals" / "results"
    out.mkdir(exist_ok=True)
    (out / f"{time.strftime('%Y%m%d-%H%M%S')}.json").write_text(json.dumps(results, indent=1))

    if args.save_baseline:
        BASELINE.write_text(json.dumps(results, indent=1))
        print(f"\nSaved as the baseline: {BASELINE.relative_to(HERE)}")
    if args.compare:
        if not BASELINE.exists():
            sys.exit("No baseline yet. Run with --save-baseline first.")
        if not compare(summary, json.loads(BASELINE.read_text()), args.tolerance):
            sys.exit(1)
        print("  No regressions.")


if __name__ == "__main__":
    main()
