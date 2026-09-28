"""Three ways to cut a document into chunks.

Each function takes the text of one document and returns a list of chunks.
Each chunk is a dict with the text to embed and the name of its source.
"""

import re


def chunk_whole(text, source):
    """No chunking: the whole document is one chunk."""
    return [{"text": text, "source": source}]


def chunk_fixed(text, source, size=60, overlap=0):
    """Cut the text into pieces of `size` words.

    Each piece starts `size - overlap` words after the previous piece,
    so that neighbor pieces share `overlap` words.
    """
    words = text.split()
    step = size - overlap
    chunks = []
    for start in range(0, len(words), step):
        piece = words[start:start + size]
        chunks.append({"text": " ".join(piece), "source": source})
        if start + size >= len(words):
            break
    return chunks


def chunk_sections(text, source, max_words=120):
    """Cut the text at its headings, and keep paragraphs together.

    Each chunk starts with the document title and the section heading,
    so that the chunk keeps its context. A long section is cut between
    paragraphs, never inside a paragraph.
    """
    title = ""
    chunks = []
    for block in re.split(r"\n(?=## )", text.strip()):
        lines = block.strip().splitlines()
        if lines[0].startswith("# "):
            title = lines[0][2:].strip()
            continue  # the intro under the title has no facts to find
        heading = lines[0].lstrip("# ").strip()
        prefix = f"{title} > {heading}\n"
        paragraphs = [p.strip() for p in "\n".join(lines[1:]).split("\n\n") if p.strip()]

        current = []
        for paragraph in paragraphs:
            paragraph = " ".join(paragraph.split())
            if current and len(" ".join(current + [paragraph]).split()) > max_words:
                chunks.append({"text": prefix + "\n".join(current), "source": source})
                current = []
            current.append(paragraph)
        if current:
            chunks.append({"text": prefix + "\n".join(current), "source": source})
    return chunks


STRATEGIES = {
    "whole": chunk_whole,
    "fixed": chunk_fixed,
    "overlap": lambda text, source: chunk_fixed(text, source, overlap=20),
    "sections": chunk_sections,
}
