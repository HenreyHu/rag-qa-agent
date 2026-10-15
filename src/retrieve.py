"""Vector search over the filing collections.

Example:
    python -m src.retrieve "What was Sea's total revenue in 2025?" --company Sea --year 2025
"""

import argparse
import math
import re
import textwrap
from collections import Counter
from functools import cache

import chromadb
from chromadb.config import Settings

from src.config import (
    CHROMA_DIR,
    COLLECTIONS,
    EMBED_MODEL,
    STRATEGIES,
    find_company,
    utf8_stdout,
)
from src.embedding import embed_query


@cache
def get_client() -> chromadb.ClientAPI:
    return chromadb.PersistentClient(
        path=str(CHROMA_DIR), settings=Settings(anonymized_telemetry=False)
    )


@cache
def get_collection(strategy: str) -> chromadb.Collection:
    collection = get_client().get_collection(COLLECTIONS[strategy], embedding_function=None)
    built_with = (collection.metadata or {}).get("embed_model")
    # Vectors from different models live in different spaces; mixing them fails silently.
    if built_with != EMBED_MODEL:
        raise RuntimeError(
            f"{collection.name} was built with {built_with!r} but queries use {EMBED_MODEL!r}; "
            "re-run `python -m src.ingest`."
        )
    return collection


def to_where(filters: dict | None) -> dict | None:
    """A Chroma where clause: list values become $in, and several keys are joined with $and."""
    clauses = [
        {key: {"$in": list(value)} if isinstance(value, list | tuple | set) else value}
        for key, value in (filters or {}).items()
        if value is not None
    ]
    if not clauses:
        return None
    # Chroma rejects a where dict with more than one key, so combine conditions explicitly.
    return clauses[0] if len(clauses) == 1 else {"$and": clauses}


def _canonical_companies(value):
    if isinstance(value, str):
        return find_company(value).short_name
    if isinstance(value, list | tuple | set):
        return [find_company(v).short_name for v in value]
    return value


SEARCH_MODES = ("vector", "hybrid")
RRF_K = 60  # the usual reciprocal-rank-fusion constant: it damps the gap between top ranks
CANDIDATES = 50  # each ranking contributes its top 50 chunks to the fusion
_WORD = re.compile(r"[a-z0-9]+")


def tokenize(text: str) -> list[str]:
    return _WORD.findall(text.lower())


def _matches(metadata: dict, filters: dict) -> bool:
    def ok(key, wanted):
        if wanted is None:
            return True
        value = metadata.get(key)
        return value in wanted if isinstance(wanted, list | tuple | set) else value == wanted

    return all(ok(key, wanted) for key, wanted in filters.items())


class Bm25Index:
    """Okapi BM25 over every chunk of one collection, so exact words (line items, names) count.

    Vector search blurs rare exact words into a topic; BM25 rewards them, which is why the two
    are mixed. There are only about 2,400 chunks, so scanning them is fast and needs no library.
    """

    def __init__(self, ids, texts, metadatas, k1: float = 1.5, b: float = 0.75):
        self.ids, self.texts, self.metadatas = ids, texts, metadatas
        self.k1, self.b = k1, b
        self.counts = [Counter(tokenize(text)) for text in texts]
        self.lengths = [sum(c.values()) for c in self.counts]
        self.average = sum(self.lengths) / len(self.lengths)
        document_frequency = Counter()
        for c in self.counts:
            document_frequency.update(c.keys())
        n = len(texts)
        self.idf = {
            term: math.log(1 + (n - df + 0.5) / (df + 0.5))
            for term, df in document_frequency.items()
        }

    def top(self, query: str, n: int, filters: dict) -> list[dict]:
        terms = [t for t in dict.fromkeys(tokenize(query)) if t in self.idf]
        scored = []
        for i, counts in enumerate(self.counts):
            if not _matches(self.metadatas[i], filters):
                continue
            norm = self.k1 * (1 - self.b + self.b * self.lengths[i] / self.average)
            score = sum(
                self.idf[t] * counts[t] * (self.k1 + 1) / (counts[t] + norm)
                for t in terms
                if counts[t]
            )
            if score > 0:
                scored.append((score, i))
        scored.sort(reverse=True)
        return [
            {"id": self.ids[i], "score": score, "text": self.texts[i], **self.metadatas[i]}
            for score, i in scored[:n]
        ]


@cache
def get_bm25(strategy: str) -> Bm25Index:
    data = get_collection(strategy).get(include=["documents", "metadatas"])
    return Bm25Index(data["ids"], data["documents"], data["metadatas"])


def hybrid_search(
    query: str, k: int, filters: dict | None = None, strategy: str = "section"
) -> list[dict]:
    """Vector and BM25 rankings fused with reciprocal rank fusion (score = sum of 1/(60 + rank)).

    Rank-based fusion avoids having to scale cosine similarity and BM25 scores onto one range.
    """
    filters = dict(filters or {})
    if "company" in filters:
        filters["company"] = _canonical_companies(filters["company"])
    rankings = [
        search(query, CANDIDATES, filters, strategy),
        get_bm25(strategy).top(query, CANDIDATES, filters),
    ]
    fused: dict[str, dict] = {}
    for ranking in rankings:
        for rank, hit in enumerate(ranking, start=1):
            entry = fused.setdefault(hit["id"], {"hit": hit, "score": 0.0})
            entry["score"] += 1 / (RRF_K + rank)
    best = sorted(fused.values(), key=lambda entry: entry["score"], reverse=True)[:k]
    return [{**entry["hit"], "score": entry["score"]} for entry in best]


def search(
    query: str,
    k: int = 5,
    filters: dict | None = None,
    strategy: str = "section",
    mode: str = "vector",
) -> list[dict]:
    """The top-k chunks for a query, optionally filtered on metadata such as company or year.

    mode "hybrid" mixes in keyword (BM25) matches; "vector" is the embedding search alone.
    """
    if mode == "hybrid":
        return hybrid_search(query, k, filters, strategy)
    filters = dict(filters or {})
    if "company" in filters:
        filters["company"] = _canonical_companies(filters["company"])
    result = get_collection(strategy).query(
        query_embeddings=[embed_query(query)],
        n_results=k,
        where=to_where(filters),
        include=["documents", "metadatas", "distances"],
    )
    return [
        {"id": chunk_id, "score": 1 - distance, "text": text, **metadata}
        for chunk_id, text, metadata, distance in zip(
            result["ids"][0],
            result["documents"][0],
            result["metadatas"][0],
            result["distances"][0],
            strict=True,
        )
    ]


def citation(hit: dict) -> str:
    return f"[{hit['company']}, FY{hit['year']}, p.{', '.join(hit['pages'])}]"


def main() -> None:
    utf8_stdout()
    parser = argparse.ArgumentParser(description="Search the annual reports.")
    parser.add_argument("query")
    parser.add_argument("--k", type=int, default=5)
    parser.add_argument("--strategy", choices=STRATEGIES, default="section")
    parser.add_argument("--mode", choices=SEARCH_MODES, default="vector")
    parser.add_argument("--company", help="Sea or Grab")
    parser.add_argument("--year", type=int, help="fiscal year of the report, e.g. 2025")
    args = parser.parse_args()

    filters = {"company": args.company, "year": args.year}
    hits = search(args.query, args.k, filters, args.strategy, args.mode)
    for rank, hit in enumerate(hits, start=1):
        kind = "table" if hit["is_table"] else "text"
        print(f"{rank}. {citation(hit)}  score {hit['score']:.3f}  {kind}")
        print(f"   {hit['section']}")
        body = hit["text"].split("\n", 1)[1]
        print(textwrap.indent(textwrap.shorten(body, 320, placeholder=" ..."), "   "))
        print()


if __name__ == "__main__":
    main()
