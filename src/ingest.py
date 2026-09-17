"""Parse, chunk, embed and store the pinned filings, with one Chroma collection per strategy.

Examples:
    python -m src.ingest                          # rebuild both collections
    python -m src.ingest --dry-run                # parse and chunk only; see data/processed/
    python -m src.ingest --dry-run --only sea-2025
"""

import argparse
import json
import statistics
import time
from collections.abc import Iterable
from dataclasses import asdict
from pathlib import Path

from src.chunking import Chunk, chunk_fixed, chunk_sections, chunk_tables
from src.config import (
    BODY_TOKENS,
    COLLECTIONS,
    EMBED_MODEL,
    MAX_MODEL_TOKENS,
    OVERLAP_TOKENS,
    PROCESSED_DIR,
    STRATEGIES,
    Filing,
    format_table,
    load_filings,
    utf8_stdout,
)
from src.embedding import embed_documents
from src.parse_filing import parse_html
from src.retrieve import get_client

CHUNKERS = {"fixed": chunk_fixed, "section": chunk_sections}


def write_jsonl(path: Path, records: Iterable[dict]) -> None:
    with path.open("w", encoding="utf-8", newline="\n") as f:
        for record in records:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")


def chunk_filing(
    filing: Filing, strategies: tuple[str, ...]
) -> tuple[dict[str, list[Chunk]], dict]:
    start = time.perf_counter()
    blocks, parse_stats = parse_html(filing.path.read_bytes())
    parse_seconds = time.perf_counter() - start
    write_jsonl(PROCESSED_DIR / f"{filing.key}_blocks.jsonl", (asdict(b) for b in blocks))

    tables = chunk_tables(blocks, filing)
    chunks = {s: CHUNKERS[s](blocks, filing) + tables for s in strategies}
    for strategy, strategy_chunks in chunks.items():
        write_jsonl(
            PROCESSED_DIR / f"{filing.key}_chunks_{strategy}.jsonl",
            ({"id": c.id, "text": c.text, **c.metadata()} for c in strategy_chunks),
        )

    labels = {b.page_seq: b.page for b in blocks}
    stats = {
        "pages": len(labels),
        "unlabeled_pages": sum(label.startswith("s") for label in labels.values()),
        "blocks": len(blocks),
        "tables": parse_stats["tables"],
        "table_chunks": len(tables),
        **{f"{s}_chunks": len(c) - len(tables) for s, c in chunks.items()},
        "parse_seconds": round(parse_seconds, 2),
    }
    return chunks, stats


def token_summary(chunks: list[Chunk]) -> dict:
    tokens = sorted(c.n_tokens for c in chunks)
    return {
        "chunks": len(chunks),
        "median_tokens": int(statistics.median(tokens)),
        "p95_tokens": tokens[int(0.95 * (len(tokens) - 1))],
        "max_tokens": tokens[-1],
    }


def store(strategy: str, chunks: list[Chunk], vectors: dict[str, list[float]]) -> int:
    client = get_client()
    name = COLLECTIONS[strategy]
    if name in {c.name for c in client.list_collections()}:
        # Rebuild from scratch: Chroma silently ignores ids that already exist.
        client.delete_collection(name)
    collection = client.create_collection(
        name,
        configuration={"hnsw": {"space": "cosine"}},
        # Vectors are computed by bge here; Chroma must never embed text with its default model.
        embedding_function=None,
        metadata={
            "embed_model": EMBED_MODEL,
            "strategy": strategy,
            "body_tokens": BODY_TOKENS,
            "overlap_tokens": OVERLAP_TOKENS if strategy == "fixed" else 0,
        },
    )
    batch_size = client.get_max_batch_size()
    for i in range(0, len(chunks), batch_size):
        batch = chunks[i : i + batch_size]
        collection.add(
            ids=[c.id for c in batch],
            embeddings=[vectors[c.text] for c in batch],
            documents=[c.text for c in batch],
            metadatas=[c.metadata() for c in batch],
        )
    return collection.count()


def main() -> None:
    utf8_stdout()
    parser = argparse.ArgumentParser(description="Build the vector store from the pinned filings.")
    parser.add_argument("--strategy", choices=[*STRATEGIES, "both"], default="both")
    parser.add_argument("--dry-run", action="store_true", help="parse and chunk only")
    parser.add_argument(
        "--only", metavar="FILING", help="one filing, e.g. sea-2025 (dry runs only)"
    )
    args = parser.parse_args()
    if args.only and not args.dry_run:
        parser.error("--only would leave the collections half-built, so it needs --dry-run")

    strategies = STRATEGIES if args.strategy == "both" else (args.strategy,)
    filings = [f for f in load_filings() if args.only in (None, f.key)]
    if not filings:
        parser.error(f"no pinned filing named {args.only!r}")
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)

    all_chunks: dict[str, list[Chunk]] = {s: [] for s in strategies}
    stats: dict = {"filings": {}}
    for filing in filings:
        chunks, stats["filings"][filing.key] = chunk_filing(filing, strategies)
        for strategy in strategies:
            all_chunks[strategy] += chunks[strategy]
    filing_rows = [[key, *values.values()] for key, values in stats["filings"].items()]
    first = next(iter(stats["filings"].values()))
    print(format_table(["filing", *first], filing_rows), end="\n\n")

    for strategy, chunks in all_chunks.items():
        too_long = [c.id for c in chunks if c.n_tokens > MAX_MODEL_TOKENS]
        if too_long:
            raise SystemExit(
                f"{len(too_long)} chunks exceed {MAX_MODEL_TOKENS} tokens: {too_long[:5]}"
            )
        stats[strategy] = token_summary(chunks)

    if not args.dry_run:
        # Table chunks are shared by both collections, so each distinct text is embedded once.
        texts = list(dict.fromkeys(c.text for chunks in all_chunks.values() for c in chunks))
        print(f"Embedding {len(texts):,} distinct chunks with {EMBED_MODEL} ...")
        start = time.perf_counter()
        vectors = dict(zip(texts, embed_documents(texts, show_progress=True), strict=True))
        stats["embedding"] = {"texts": len(texts), "seconds": round(time.perf_counter() - start, 1)}
        for strategy, chunks in all_chunks.items():
            stats[strategy]["stored"] = store(strategy, chunks, vectors)

    summary_rows = [[s, *stats[s].values()] for s in strategies]
    print(format_table(["collection", *stats[strategies[0]]], summary_rows))
    if "embedding" in stats:
        print(
            f"\nEmbedded {stats['embedding']['texts']:,} texts in {stats['embedding']['seconds']}s"
        )
    if not args.only:
        stats_path = PROCESSED_DIR / "ingest_stats.json"
        stats_path.write_text(json.dumps(stats, indent=2) + "\n", encoding="utf-8", newline="\n")


if __name__ == "__main__":
    main()
