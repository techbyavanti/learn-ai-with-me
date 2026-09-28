"""Check the calculator: correct results, and no way to run code.

Run: python test_tools.py
"""

from tools import calculate, format_number

GOOD = [
    ("30 * 12 * 0.5", "180"),
    ("10 * 10 * 12", "1200"),
    ("(12 - 10) * 5 * 12", "120"),
    ("30 - 10", "20"),
    ("8 x 10 x 12 x 0.5", "480"),
    ("1,200 / 12", "100"),
    ("-5 + 2", "-3"),
]

BAD = [
    "__import__('os').system('ls')",
    "open('secret.txt').read()",
    "2 ** 1000000",
    "abs(-3)",
    "a + 1",
    "1 / 0",
    "9" * 101,
]


def main():
    failed = 0
    for expression, want in GOOD:
        got = format_number(calculate(expression))
        ok = got == want
        failed += not ok
        print(f"{'ok' if ok else 'FAIL':<4} {expression} = {got}")
    for expression in BAD:
        try:
            calculate(expression)
            print(f"FAIL {expression[:40]} was allowed")
            failed += 1
        except (ValueError, SyntaxError, ZeroDivisionError) as e:
            print(f"ok   refused: {expression[:40]} ({type(e).__name__})")
    if failed:
        raise SystemExit(f"{failed} calculator checks failed.")
    print("All calculator checks passed.")


if __name__ == "__main__":
    main()
