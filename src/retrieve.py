"""Vector search over the filing collections.

Example:
    python -m src.retrieve "What was Sea's total revenue in 2025?" --company Sea --year 2025
"""

import argparse
import textwrap
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


def search(
    query: str, k: int = 5, filters: dict | None = None, strategy: str = "section"
) -> list[dict]:
    """The top-k chunks for a query, optionally filtered on metadata such as company or year."""
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
    parser.add_argument("--company", help="Sea or Grab")
    parser.add_argument("--year", type=int, help="fiscal year of the report, e.g. 2025")
    args = parser.parse_args()

    filters = {"company": args.company, "year": args.year}
    for rank, hit in enumerate(search(args.query, args.k, filters, args.strategy), start=1):
        kind = "table" if hit["is_table"] else "text"
        print(f"{rank}. {citation(hit)}  score {hit['score']:.3f}  {kind}")
        print(f"   {hit['section']}")
        body = hit["text"].split("\n", 1)[1]
        print(textwrap.indent(textwrap.shorten(body, 320, placeholder=" ..."), "   "))
        print()


if __name__ == "__main__":
    main()
