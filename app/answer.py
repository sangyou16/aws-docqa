"""Answer construction: extractive by default, optional Amazon Bedrock summary."""
import os
import re

from app.bm25 import tokenize
from app.corpus import Passage

NO_ANSWER = "I couldn't find anything relevant in the indexed documents."


def bedrock_enabled() -> bool:
    return os.environ.get("ENABLE_BEDROCK", "false").lower() == "true"


def extractive_answer(query: str, hits: list[tuple[Passage, float]]) -> tuple[str, list[Passage]]:
    """Pick the best-matching sentence from each hit; cite exactly the passages used."""
    terms = set(tokenize(query))
    parts, used = [], []
    for passage, _ in hits:
        sentences = re.split(r"(?<=[.!?])\s+", passage.text)
        best = max(sentences, key=lambda s: len(terms & set(tokenize(s))))
        used.append(passage)
        parts.append(f"{best} [{len(used)}]")
    return (" ".join(parts) if parts else NO_ANSWER), used


def bedrock_answer(query: str, passages: list[Passage]) -> str:
    import boto3  # imported lazily: only needed when the flag is on

    context = "\n\n".join(f"[{i}] {p.text}" for i, p in enumerate(passages, 1))
    prompt = (
        "Answer the question using ONLY the numbered passages. Cite passages like [1]. "
        "If they don't contain the answer, say so.\n\n"
        f"Passages:\n{context}\n\nQuestion: {query}"
    )
    client = boto3.client("bedrock-runtime")
    resp = client.converse(
        modelId=os.environ["BEDROCK_MODEL_ID"],
        messages=[{"role": "user", "content": [{"text": prompt}]}],
        inferenceConfig={"maxTokens": 400, "temperature": 0.0},
    )
    return resp["output"]["message"]["content"][0]["text"]
