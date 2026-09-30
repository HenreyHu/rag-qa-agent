"""Basic RAG: retrieve the top-k chunks, then ask Claude to answer only from them.

Example:
    python -m src.rag "What was Sea's total revenue in 2025?" --company Sea --year 2025
"""

import argparse
from functools import cache

import anthropic

from src.config import (
    ANSWER_MAX_TOKENS,
    ANSWER_MODEL,
    STRATEGIES,
    SYSTEM_PROMPT,
    load_env,
    utf8_stdout,
)
from src.retrieve import citation, search


@cache
def get_client() -> anthropic.Anthropic:
    load_env()  # puts ANTHROPIC_API_KEY from .env into the environment
    return anthropic.Anthropic()


def build_context(hits: list[dict]) -> str:
    """Each chunk is headed by the exact citation string, so the model can copy it verbatim."""
    return "\n\n".join(f"{citation(hit)}\n{hit['text']}" for hit in hits)


def answer(
    question: str, k: int = 5, filters: dict | None = None, strategy: str = "section"
) -> dict:
    """Answer a question from the top-k chunks. Returns the answer text and the chunks it saw.

    The hits are returned so the eval can check whether each cited page was actually retrieved.
    """
    hits = search(question, k, filters, strategy)
    response = get_client().messages.create(
        model=ANSWER_MODEL,
        max_tokens=ANSWER_MAX_TOKENS,
        system=SYSTEM_PROMPT,
        messages=[
            {
                "role": "user",
                "content": f"Context:\n\n{build_context(hits)}\n\nQuestion: {question}",
            }
        ],
    )
    text = "".join(block.text for block in response.content if block.type == "text")
    return {"question": question, "answer": text.strip(), "hits": hits}


def main() -> None:
    utf8_stdout()
    parser = argparse.ArgumentParser(description="Ask a question about the annual reports.")
    parser.add_argument("question")
    parser.add_argument("--k", type=int, default=5)
    parser.add_argument("--strategy", choices=STRATEGIES, default="section")
    parser.add_argument("--company", help="Sea or Grab")
    parser.add_argument("--year", type=int, help="fiscal year of the report, e.g. 2025")
    args = parser.parse_args()

    result = answer(
        args.question, args.k, {"company": args.company, "year": args.year}, args.strategy
    )
    print(result["answer"])
    print("\nRetrieved:", " ".join(citation(hit) for hit in result["hits"]))


if __name__ == "__main__":
    main()
