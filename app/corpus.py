"""Loads text documents from data/docs and splits them into paragraph passages.

File format: header lines ("Title: ...", "Source: ..."), a blank line, then body
paragraphs separated by blank lines. Each paragraph is one passage.
"""
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

from app.bm25 import BM25Index

DOCS_DIR = Path(__file__).resolve().parent.parent / "data" / "docs"


@dataclass(frozen=True)
class Passage:
    id: str      # "<doc-slug>#<n>"
    doc: str     # doc slug (filename without .txt)
    title: str
    source: str  # URL of the original public page
    text: str


def load_passages(docs_dir: Path = DOCS_DIR) -> list[Passage]:
    passages = []
    for path in sorted(docs_dir.glob("*.txt")):
        head, _, body = path.read_text(encoding="utf-8").partition("\n\n")
        meta = dict(line.split(": ", 1) for line in head.splitlines() if ": " in line)
        paras = [p.strip() for p in body.split("\n\n") if p.strip()]
        for n, text in enumerate(paras, 1):
            passages.append(Passage(f"{path.stem}#{n}", path.stem, meta.get("Title", path.stem),
                                    meta.get("Source", ""), " ".join(text.split())))
    return passages


class Retriever:
    def __init__(self, passages: list[Passage]):
        self.passages = passages
        self.index = BM25Index([f"{p.title} {p.text}" for p in passages])

    def search(self, query: str, k: int = 3) -> list[tuple[Passage, float]]:
        return [(self.passages[i], s) for i, s in self.index.search(query, k)]


@lru_cache(maxsize=1)
def get_retriever() -> Retriever:
    return Retriever(load_passages())
