"""Send many questions to the service at the same time, and measure the waiting time.

Start the service first (uvicorn server:app --port 8000), then:
    python load_test.py --users 1 4 8
    python load_test.py --users 8 --repeat      (the same questions again: answers from the cache)
"""

import argparse
import json
import statistics
import time
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor

QUESTIONS = [
    "How long until I get my money back?",
    "Is there a discount for schools?",
    "What happens if my card payment fails?",
    "How much is the yearly plan?",
    "Can I pay by bank transfer?",
    "How long is a password reset link valid?",
    "Which identity providers work with SSO?",
    "When does a session end on its own?",
    "Can I restore a project that I deleted?",
    "How often do you back up my data?",
    "Can I keep my data in the United States?",
    "When is live chat open?",
    "Is there parking at the office?",
    "How fast do you reply on the paid plan?",
    "Does the phone app work without internet?",
    "How long is an invitation valid?",
]


def ask(url, question, mode):
    body = json.dumps({"question": question, "mode": mode}).encode()
    request = urllib.request.Request(f"{url}/ask", data=body,
                                     headers={"Content-Type": "application/json"})
    start = time.perf_counter()
    try:
        with urllib.request.urlopen(request, timeout=300) as response:
            data = json.load(response)
            status = "cached" if data.get("cached") else "ok"
    except urllib.error.HTTPError as e:
        status = "busy" if e.code == 503 else f"error {e.code}"
    except OSError as e:
        status = f"error {e}"
    return time.perf_counter() - start, status


def run(url, users, questions, mode):
    """All questions, with `users` of them in progress at the same time."""
    start = time.perf_counter()
    with ThreadPoolExecutor(max_workers=users) as pool:
        results = list(pool.map(lambda q: ask(url, q, mode), questions))
    total = time.perf_counter() - start
    times = sorted(t for t, _ in results)
    statuses = [s for _, s in results]
    p95 = times[max(0, round(0.95 * len(times)) - 1)]
    print(f"{users:>5} {mode:<7} {len(questions):>9} {statistics.median(times):>9.2f} {p95:>8.2f} "
          f"{times[-1]:>8.2f} {len(questions) / total:>12.2f} "
          f"{statuses.count('busy') + sum(s.startswith('error') for s in statuses):>7}")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--url", default="http://localhost:8000")
    parser.add_argument("--users", type=int, nargs="+", default=[1, 4, 8])
    parser.add_argument("--mode", default="single", choices=["single", "agent"])
    parser.add_argument("--repeat", action="store_true", help="Ask each question two times: the second from the cache.")
    parser.add_argument("--suffix", default="", help="Text added to each question, so that no answer comes from the cache.")
    args = parser.parse_args()

    with urllib.request.urlopen(f"{args.url}/health", timeout=10) as response:
        print("Service:", json.load(response))
    print(f"\n{'Users':>5} {'Mode':<7} {'Questions':>9} {'Median s':>9} {'p95 s':>8} {'Max s':>8} "
          f"{'Questions/s':>12} {'Failed':>7}")
    for users in args.users:
        suffix = args.suffix or ("" if args.repeat else f" (test {users}-{time.time():.0f})")
        questions = [q + suffix for q in QUESTIONS]
        run(args.url, users, questions, args.mode)
    print("\nMedian, p95, and Max = the waiting time of one person. Questions/s = all people together."
          "\nFailed = 'busy' (503) or an error.")


if __name__ == "__main__":
    main()
