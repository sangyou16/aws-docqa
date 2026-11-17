#!/usr/bin/env python3
"""Retrieval eval: Hit@K over question -> expected-source pairs.

A question is a hit if any of the top-K passages comes from the expected doc.
Exits non-zero if Hit@K is below the threshold (--min, or env EVAL_MIN_HIT_AT_3).
"""
import argparse
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from app.corpus import get_retriever  # noqa: E402

QUESTIONS = Path(__file__).resolve().parent / "questions.json"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--k", type=int, default=3)
    ap.add_argument("--min", type=float, default=float(os.environ.get("EVAL_MIN_HIT_AT_3", "0.8")))
    args = ap.parse_args()

    retriever, pairs = get_retriever(), json.loads(QUESTIONS.read_text())
    hits = 0
    for pair in pairs:
        docs = [p.doc for p, _ in retriever.search(pair["question"], args.k)]
        ok = pair["source"] in docs
        hits += ok
        print(f"{'HIT ' if ok else 'MISS'}  {pair['question']}\n      expected={pair['source']} got={docs}")
    score = hits / len(pairs)
    print(f"\nHit@{args.k} = {hits}/{len(pairs)} = {score:.3f} (threshold {args.min:.3f})")
    if score < args.min:
        print("FAIL: below threshold")
        return 1
    print("PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
