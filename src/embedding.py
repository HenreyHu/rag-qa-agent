"""The embedding model (BAAI/bge-small-en-v1.5) and its tokenizer."""

from functools import cache

from tokenizers import Encoding, Tokenizer

from src.config import EMBED_MODEL, QUERY_PROMPT


@cache
def get_tokenizer() -> Tokenizer:
    tokenizer = Tokenizer.from_pretrained(EMBED_MODEL)
    # The shipped tokenizer.json truncates at 512 tokens; budgets need the untruncated length.
    tokenizer.no_truncation()
    tokenizer.no_padding()
    return tokenizer


def tokenize(text: str) -> Encoding:
    """Tokens without [CLS]/[SEP], with character offsets and word ids for clean cut points."""
    return get_tokenizer().encode(text, add_special_tokens=False)


def count_tokens(text: str, special_tokens: bool = False) -> int:
    return len(get_tokenizer().encode(text, add_special_tokens=special_tokens).ids)


@cache
def get_model():
    # Imported here so that parsing, chunking and their tests don't have to load torch.
    from sentence_transformers import SentenceTransformer

    # The model's own config defines no prompts, so encode_query() would otherwise add nothing.
    return SentenceTransformer(EMBED_MODEL, prompts={"query": QUERY_PROMPT})


def embed_documents(
    texts: list[str], batch_size: int = 32, show_progress: bool = False
) -> list[list[float]]:
    vectors = get_model().encode_document(
        texts,
        batch_size=batch_size,
        normalize_embeddings=True,
        show_progress_bar=show_progress,
    )
    return vectors.tolist()


def embed_query(query: str) -> list[float]:
    return get_model().encode_query(query, normalize_embeddings=True).tolist()
