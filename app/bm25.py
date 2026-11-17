"""Minimal BM25 (Okapi) keyword index. Pure Python, no dependencies."""
import math
import re
from collections import Counter

STOPWORDS = frozenset(
    "a an and are as at be by can do does for from how i in is it of on or that the "
    "this to was what when where which who why with you your should".split()
)


def tokenize(text: str) -> list[str]:
    return [t for t in re.findall(r"[a-z0-9]+", text.lower()) if t not in STOPWORDS]


class BM25Index:
    def __init__(self, texts: list[str], k1: float = 1.5, b: float = 0.75):
        self.k1, self.b = k1, b
        self.docs = [Counter(tokenize(t)) for t in texts]
        self.lengths = [sum(d.values()) for d in self.docs]
        self.avg_len = (sum(self.lengths) / len(self.lengths)) if self.docs else 0.0
        df = Counter(term for d in self.docs for term in d)
        n = len(self.docs)
        # "+1" inside the log keeps IDF non-negative for very common terms.
        self.idf = {t: math.log(1 + (n - f + 0.5) / (f + 0.5)) for t, f in df.items()}

    def score(self, query_terms: list[str], i: int) -> float:
        tf, norm = self.docs[i], 1 - self.b + self.b * self.lengths[i] / (self.avg_len or 1)
        total = 0.0
        for t in query_terms:
            f = tf.get(t, 0)
            if f:
                total += self.idf[t] * f * (self.k1 + 1) / (f + self.k1 * norm)
        return total

    def search(self, query: str, k: int = 3) -> list[tuple[int, float]]:
        terms = tokenize(query)
        scored = [(i, self.score(terms, i)) for i in range(len(self.docs))]
        scored = [s for s in scored if s[1] > 0]
        scored.sort(key=lambda s: s[1], reverse=True)
        return scored[:k]
