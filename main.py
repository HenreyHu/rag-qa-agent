"""Ask a question about the Sea and Grab annual reports from the command line.

    python main.py "Whose revenue grew faster in FY2025, Sea or Grab?"
    python main.py "What was Sea's total revenue in 2025?" --mode rag --company Sea --year 2025
    python main.py "..." --hybrid --trace

The default is the agent (it searches as many times as it needs and does the arithmetic with a
tool). --mode rag is the single-retrieval baseline, kept for comparison.
"""

import argparse
import os
import sys


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Ask a question about the annual reports.")
    parser.add_argument("question")
    parser.add_argument("--mode", choices=("agent", "rag"), default="agent")
    parser.add_argument(
        "--hybrid", action="store_true", help="agent only: keyword + vector search (BM25 + RRF)"
    )
    parser.add_argument("--trace", action="store_true", help="agent only: print each step")
    parser.add_argument("--company", help="rag only: Sea or Grab")
    parser.add_argument("--year", type=int, help="rag only: fiscal year, e.g. 2025")
    parser.add_argument("--k", type=int, default=5, help="rag only: chunks to retrieve")
    return parser


def ask(args: argparse.Namespace) -> None:
    # Imported here because src.config reads AGENT_SEARCH_MODE when it is first imported.
    from src.retrieve import citation

    if args.mode == "rag":
        from src.rag import answer

        result = answer(args.question, args.k, {"company": args.company, "year": args.year})
        print(result["answer"])
        print(f"\n{result['input_tokens']} in / {result['output_tokens']} out tokens")
    else:
        from src.agent import run_agent

        result = run_agent(args.question, "cli")
        print(result["answer"])
        print(
            f"\n{result['steps']} model turns, {result['tool_calls']} tool calls, "
            f"{result['input_tokens']} in / {result['output_tokens']} out tokens, "
            f"{result['seconds']}s" + (" (hit the step cap)" if result["hit_cap"] else "")
        )
        if args.trace:
            import json
            from pathlib import Path

            from eval.show_trace import show

            lines = Path(result["trace"]).read_text(encoding="utf-8").splitlines()
            print()
            show([json.loads(line) for line in lines])
    print("Retrieved:", " ".join(dict.fromkeys(citation(hit) for hit in result["hits"])))


def main(argv: list[str] | None = None) -> None:
    args = build_parser().parse_args(argv)
    if args.hybrid:
        os.environ["AGENT_SEARCH_MODE"] = "hybrid"  # must be set before src.config is imported
    from src.config import utf8_stdout

    utf8_stdout()
    ask(args)


if __name__ == "__main__":
    main(sys.argv[1:])
