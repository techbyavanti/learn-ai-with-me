"""Two small caches for the RAG app.

VectorCache saves one vector for each chunk, so the app embeds a chunk only
one time. AnswerCache saves the answer for each prompt, so the app calls the
model only one time for the same question and the same chunks.
"""

import hashlib
import json
from pathlib import Path

import numpy as np


def make_key(*parts):
    """A short fingerprint of the parts. The same parts always give the same key."""
    return hashlib.sha256("\n".join(parts).encode("utf-8")).hexdigest()[:16]


class VectorCache:
    """Vectors on disk, one row for each chunk key."""

    def __init__(self, path):
        self.path = Path(path)
        self.vectors = {}
        if self.path.exists():
            data = np.load(self.path)
            self.vectors = dict(zip(data["keys"], data["vectors"]))

    def embed(self, get_encoder, encoder_name, texts):
        """Return one vector for each text. Embed only the texts that are not in the cache.

        `get_encoder` is a function, so that we load the encoder only when a text is missing.
        """
        keys = [make_key(encoder_name, text) for text in texts]
        missing = [i for i, key in enumerate(keys) if key not in self.vectors]
        if missing:
            new = get_encoder().encode([texts[i] for i in missing], normalize_embeddings=True)
            for i, vector in zip(missing, new):
                self.vectors[keys[i]] = vector
        # Keep only the chunks that exist now, so that old chunks do not fill the disk.
        self.vectors = {key: self.vectors[key] for key in keys}
        self.save()
        stats = {"reused": len(texts) - len(missing), "embedded": len(missing)}
        return np.array([self.vectors[key] for key in keys]), stats

    def save(self):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        keys = list(self.vectors)
        vectors = np.array([self.vectors[k] for k in keys]) if keys else np.zeros((0, 0))
        np.savez(self.path, keys=np.array(keys), vectors=vectors)


class AnswerCache:
    """Answers on disk, one for each (model, prompt) pair."""

    def __init__(self, path):
        self.path = Path(path)
        self.answers = json.loads(self.path.read_text()) if self.path.exists() else {}

    def get(self, model, prompt):
        return self.answers.get(make_key(model, prompt))

    def put(self, model, prompt, answer):
        self.answers[make_key(model, prompt)] = answer
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps(self.answers, indent=1))
