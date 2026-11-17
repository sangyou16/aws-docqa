import json
import logging

import pytest
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_health():
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"
    assert r.json()["passages"] > 0


def test_search_returns_sources():
    r = client.post("/search", json={"query": "least privilege IAM roles", "top_k": 3})
    assert r.status_code == 200
    results = r.json()["results"]
    assert 1 <= len(results) <= 3
    for p in results:
        assert p["source"].startswith("https://")
        assert p["score"] > 0
    assert results[0]["id"].startswith("sec-identity-and-access-management#")
    scores = [p["score"] for p in results]
    assert scores == sorted(scores, reverse=True)


def test_ask_cites_only_retrieved_passages():
    q = {"query": "how should retries handle failures", "top_k": 3}
    retrieved = {p["id"] for p in client.post("/search", json=q).json()["results"]}
    r = client.post("/ask", json=q)
    assert r.status_code == 200
    body = r.json()
    assert body["mode"] == "extractive"
    cited = {c["id"] for c in body["citations"]}
    assert cited and cited <= retrieved
    for n in range(1, len(body["citations"]) + 1):
        assert f"[{n}]" in body["answer"]


def test_ask_with_no_matches_returns_no_citations():
    r = client.post("/ask", json={"query": "zzzz qqqq"})
    assert r.status_code == 200
    assert r.json()["citations"] == []


@pytest.mark.parametrize("path,payload", [
    ("/search", {}),                                  # missing query
    ("/search", {"query": ""}),                       # too short
    ("/search", {"query": "backup", "top_k": 0}),     # top_k out of range
    ("/search", {"query": "backup", "top_k": 99}),
    ("/ask", {"query": "x" * 501}),                   # too long
    ("/ask", {"query": "backup", "top_k": "many"}),   # wrong type
])
def test_bad_input_returns_422(path, payload):
    assert client.post(path, json=payload).status_code == 422


def test_use_llm_rejected_when_bedrock_disabled(monkeypatch):
    monkeypatch.delenv("ENABLE_BEDROCK", raising=False)
    r = client.post("/ask", json={"query": "backups", "use_llm": True})
    assert r.status_code == 400


def test_bedrock_failure_falls_back_to_extractive(monkeypatch):
    monkeypatch.setenv("ENABLE_BEDROCK", "true")
    def boom(*_):
        raise RuntimeError("no network")
    monkeypatch.setattr("app.main.bedrock_answer", boom)
    r = client.post("/ask", json={"query": "backups", "use_llm": True})
    assert r.status_code == 200
    assert r.json()["mode"] == "extractive"


def test_request_is_logged_as_json(capsys):
    client.post("/search", json={"query": "encryption at rest"})
    line = [l for l in capsys.readouterr().out.splitlines() if l.startswith("{")][-1]
    log = json.loads(line)
    assert log["endpoint"] == "/search"
    assert log["result_count"] >= 1
    assert log["error"] is None
    assert isinstance(log["latency_ms"], float)
    assert log["request_id"]


def test_validation_error_is_logged(capsys):
    client.post("/search", json={})
    log = json.loads([l for l in capsys.readouterr().out.splitlines() if l.startswith("{")][-1])
    assert log["status"] == 422 and log["error"] == "http_422"
