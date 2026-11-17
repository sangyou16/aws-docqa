from app.bm25 import BM25Index, tokenize


def test_tokenize_lowercases_and_drops_stopwords():
    assert tokenize("What is the IAM Role?") == ["iam", "role"]


def test_rarer_term_ranks_higher():
    idx = BM25Index(["cat dog", "cat bird", "cat fish"])
    assert idx.search("cat fish")[0][0] == 2


def test_no_match_returns_empty():
    assert BM25Index(["alpha beta"]).search("gamma") == []
