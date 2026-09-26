"""Guardrails: checks in normal code around the model.

Input checks run before the model sees the question. Document checks run on
each chunk when the app loads the documents. Output checks run on the answer
before the user sees it.
"""

import re

import numpy as np

MAX_QUESTION_CHARS = 500

# Phrases that try to change the rules of the app. Each pattern is a
# regular expression, checked without case.
INJECTION_PATTERNS = [
    r"\b(ignore|disregard|forget|override)\b.{0,40}\b(instructions?|rules?|documents?|prompt|above|previous)\b",
    r"\b(system|hidden|secret) prompt\b",
    r"\byou are now\b",
    r"\b(pretend|act as|role-?play)\b",
    r"\b(jailbreak|developer mode|dan mode)\b",
    r"\bnote (for|to) the (ai|assistant|model|chatbot)\b",
    r"\b(ai|assistant|model|chatbot)\b.{0,20}\b(must|should) (tell|say|answer)\b",
    r"\btell every user\b",
]

EMAIL = re.compile(r"\b[\w.+-]+@[\w-]+\.[\w.-]+\b")
CARD = re.compile(r"\b(?:\d[ -]?){13,19}\b")
# Sentences that say "the documents do not answer this". They are not claims, so we do not check them.
REFUSAL = re.compile(r"i do not know|do(es)? not (contain|mention|say|include|state)|no information", re.IGNORECASE)
NUMBER = re.compile(r"\b\d+(?:[.,:]\d+)*\b")


def find_injection(text):
    """Return the first injection pattern that matches the text, or None."""
    for pattern in INJECTION_PATTERNS:
        if re.search(pattern, text, flags=re.IGNORECASE):
            return pattern
    return None


def luhn_ok(digits):
    """The checksum that all payment card numbers pass."""
    total = 0
    for i, d in enumerate(int(c) for c in reversed(digits)):
        if i % 2 == 1:
            d = d * 2 - 9 if d > 4 else d * 2
        total += d
    return total % 10 == 0


def redact(text):
    """Replace email addresses and card numbers with placeholders."""
    text = EMAIL.sub("[EMAIL]", text)

    def card(match):
        digits = re.sub(r"\D", "", match.group())
        return "[CARD]" if 13 <= len(digits) <= 19 and luhn_ok(digits) else match.group()

    return CARD.sub(card, text)


# Input guardrail
def check_input(question):
    """Return (question, problem). The question has private data removed.

    problem is None when the question can go to the model.
    """
    question = question.strip()
    if not question:
        return question, "The question is empty."
    if len(question) > MAX_QUESTION_CHARS:
        return question, f"The question is longer than {MAX_QUESTION_CHARS} characters."
    if find_injection(question):
        return question, "The question tries to change the rules of the app."
    return redact(question), None


# Document guardrail
def check_chunks(chunks):
    """Split the chunks into safe chunks and chunks that contain instructions for the model."""
    safe, blocked = [], []
    for chunk in chunks:
        (blocked if find_injection(chunk["text"]) else safe).append(chunk)
    return safe, blocked


# Output guardrails
def numbers_in(text):
    return {n.replace(",", "") for n in NUMBER.findall(text)}


def unsupported_numbers(answer, hits):
    """Numbers in the answer that are not in any of the chunks."""
    source = " ".join(chunk["text"] for chunk, _ in hits)
    return sorted(numbers_in(answer) - numbers_in(source))


def sentences(text):
    parts = re.split(r"(?<=[.!?])\s+|\n+", text)
    return [p.strip() for p in parts if len(p.split()) >= 3]


def unsupported_sentences(answer, hits, encoder, min_score=0.6):
    """Sentences in the answer that are not close to any sentence in the chunks."""
    claims = [s for s in sentences(answer) if not REFUSAL.search(s)]
    evidence = [s for chunk, _ in hits for s in sentences(chunk["text"])]
    if not claims or not evidence:
        return []
    c = encoder.encode(claims, normalize_embeddings=True)
    e = encoder.encode(evidence, normalize_embeddings=True)
    best = (c @ e.T).max(axis=1)
    return [(claim, float(score)) for claim, score in zip(claims, best) if score < min_score]


def check_output(answer, hits, encoder):
    """Return a list of problems. An empty list means that the answer passed."""
    problems = []
    numbers = unsupported_numbers(answer, hits)
    if numbers:
        problems.append(f"Numbers that are not in the documents: {', '.join(numbers)}")
    for claim, score in unsupported_sentences(answer, hits, encoder):
        problems.append(f"Not supported by the documents ({score:.2f}): {claim}")
    return problems


# Output guardrail with a model: the judge
JUDGE_PROMPT = (
    "You check answers. Read the documents and the answer.\n"
    "Reply with one word: YES if every fact in the answer is stated in the documents, "
    "NO if any fact is missing or different.\n\n"
    "Documents:\n{documents}\n\nQuestion: {question}\nAnswer: {answer}\n\n"
    "Every fact stated in the documents (YES or NO)?"
)


def judge_answer(question, answer, hits, chat):
    """Ask a model if the documents support the answer. Return True for yes.

    `chat` is a function that sends a prompt to a model and returns its text.
    """
    if REFUSAL.search(answer) and not unsupported_numbers(answer, hits):
        return True  # a refusal: nothing to check
    documents = "\n\n".join(chunk["text"] for chunk, _ in hits)
    reply = chat(JUDGE_PROMPT.format(documents=documents, question=question, answer=answer))
    return reply.strip().upper().startswith("YES")
