#!/usr/bin/env python3
"""Replace the seed notes in data/docs with the text of the real public pages.

Each data/docs/<slug>.txt names its page in a "Source:" line, so the URL list lives
in the corpus itself. Standard library only. Run from a machine with internet access:

    python scripts/fetch_corpus.py            # fetch all
    python scripts/fetch_corpus.py --dry-run  # just list URLs

After fetching, re-run the eval (python eval/run_eval.py); question wording may need tuning.
"""
import argparse
import sys
import urllib.request
from html.parser import HTMLParser
from pathlib import Path

DOCS = Path(__file__).resolve().parent.parent / "data" / "docs"


class ParagraphParser(HTMLParser):
    """Collects text of <p> and <li> elements inside the page's main content."""

    def __init__(self):
        super().__init__()
        self.paras, self._buf, self._depth, self._in_main = [], [], 0, False

    def handle_starttag(self, tag, attrs):
        if tag == "main" or dict(attrs).get("id") == "main-col-body":
            self._in_main = True
        if self._in_main and tag in ("p", "li"):
            self._depth += 1

    def handle_endtag(self, tag):
        if self._in_main and tag in ("p", "li") and self._depth:
            self._depth -= 1
            text = " ".join("".join(self._buf).split())
            if len(text) > 40:
                self.paras.append(text)
            self._buf = []

    def handle_data(self, data):
        if self._depth:
            self._buf.append(data)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()
    failed = 0
    for path in sorted(DOCS.glob("*.txt")):
        head = path.read_text(encoding="utf-8").partition("\n\n")[0]
        meta = dict(l.split(": ", 1) for l in head.splitlines() if ": " in l)
        url = meta["Source"]
        if args.dry_run:
            print(path.stem, url)
            continue
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "docqa-corpus-fetch/1.0"})
            html = urllib.request.urlopen(req, timeout=20).read().decode("utf-8", "replace")
        except Exception as exc:
            print(f"FAIL {path.stem}: {exc}", file=sys.stderr)
            failed += 1
            continue
        parser = ParagraphParser()
        parser.feed(html)
        if not parser.paras:
            print(f"FAIL {path.stem}: no paragraphs found", file=sys.stderr)
            failed += 1
            continue
        path.write_text(f"Title: {meta['Title']}\nSource: {url}\n\n" + "\n\n".join(parser.paras) + "\n",
                        encoding="utf-8")
        print(f"ok   {path.stem}: {len(parser.paras)} paragraphs")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
