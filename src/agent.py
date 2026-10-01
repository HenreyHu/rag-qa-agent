"""The agent: a Claude tool-use loop over the search and calculate tools.

Basic RAG (src/rag.py) retrieves once and answers. Here the model decides what to search for,
reads the results, searches again if they are weak, uses a tool for arithmetic, and answers when
it has the evidence. The search and calculation logic lives in src/tools.py; this file is only
the loop, the step cap and the trace.

Example:
    python -m src.agent "Whose revenue grew faster in FY2025, Sea or Grab?" --qid demo
"""

import argparse
import json
import time
from pathlib import Path

from src.config import (
    AGENT_MAX_STEPS,
    AGENT_MAX_TOKENS,
    AGENT_MODEL,
    AGENT_SYSTEM_PROMPT,
    RESULTS_DIR,
    utf8_stdout,
)
from src.rag import get_client
from src.retrieve import citation
from src.tools import calculate, search_reports, tool_schemas

TRACE_DIR = RESULTS_DIR / "traces"

# Added as the last block of the final user turn when the step cap is reached.
FORCE_FINAL = (
    "You have used all your steps. Answer now from the evidence already retrieved, citing "
    '[Company, FYyear, p.X]. If it is not enough, say "I don\'t know" and say what is missing. '
    "Do not call any tool."
)


def summarize_result(output: str) -> str:
    """A short trace entry: for a search, the query line plus each result's citation and section.

    The full passages are not logged. They are large, and the citation and section are enough to
    see whether the agent got the right pages.
    """
    lines = output.splitlines()
    headers = [line for line in lines if line.startswith("Result ")]
    if headers:
        return f"{lines[0]} >> " + " ; ".join(headers)
    return output[:300]


def run_tool(name: str, args: dict, seen: list) -> str:
    """Run one tool call. Mistakes by the model come back as "Error: ..." text, never exceptions."""
    try:
        if name == "search_reports":
            return search_reports(**args, seen=seen)
        if name == "calculate":
            return calculate(**args)
    except TypeError as exc:  # a missing or unexpected argument name
        return f"Error: bad arguments for {name}: {exc}"
    return f"Error: unknown tool {name!r}. Use search_reports or calculate."


def _text(response) -> str:
    return "".join(block.text for block in response.content if block.type == "text").strip()


def _log(path: Path | None, record: dict) -> None:
    if path is None:
        return
    # Written after every step, so a crash mid-run still leaves the steps so far.
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(record, ensure_ascii=False) + "\n")


def run_agent(
    question: str,
    qid: str | None = None,
    *,
    client=None,
    max_steps: int = AGENT_MAX_STEPS,
    trace_dir: Path | None = TRACE_DIR,
) -> dict:
    """Answer a question with the tool-use loop.

    Returns the same keys as rag.answer() (question, answer, hits) so the answer eval can score
    it unchanged, plus steps, tool_calls, hit_cap, token totals, seconds and the trace path.
    `hits` is every chunk the agent saw, which the citation check needs.
    """
    client = client or get_client()
    tools = tool_schemas()

    trace_path = None
    if trace_dir is not None:
        Path(trace_dir).mkdir(parents=True, exist_ok=True)
        trace_path = Path(trace_dir) / f"{qid or 'adhoc'}.jsonl"
        trace_path.write_text("", encoding="utf-8")  # one run per file
    _log(
        trace_path,
        {"event": "question", "question": question, "model": AGENT_MODEL, "max_steps": max_steps},
    )

    messages = [{"role": "user", "content": question}]
    seen: list[dict] = []
    totals = {"input_tokens": 0, "output_tokens": 0}
    tool_calls = 0
    hit_cap = False
    started = time.perf_counter()

    # Passes 1..max_steps are normal turns. If the model is still calling tools after that, one
    # more pass is made with tools switched off, so there is always a final answer.
    for step in range(1, max_steps + 2):
        force = step > max_steps
        if force:
            hit_cap = True
            # The last message is the user turn holding the tool results; add the instruction to it.
            messages[-1]["content"].append({"type": "text", "text": FORCE_FINAL})
        began = time.perf_counter()
        response = client.messages.create(
            model=AGENT_MODEL,
            max_tokens=AGENT_MAX_TOKENS,
            system=AGENT_SYSTEM_PROMPT,
            tools=tools,  # the API requires tools whenever the history holds tool blocks
            messages=messages,
            **({"tool_choice": {"type": "none"}} if force else {}),
        )
        totals["input_tokens"] += response.usage.input_tokens
        totals["output_tokens"] += response.usage.output_tokens
        text = _text(response)
        calls = [block for block in response.content if block.type == "tool_use"]
        record = {
            "event": "step",
            "step": step,
            "forced": force,
            "stop_reason": response.stop_reason,
            "text": text,
            "usage": {
                "input_tokens": response.usage.input_tokens,
                "output_tokens": response.usage.output_tokens,
            },
            "seconds": round(time.perf_counter() - began, 2),
            "tool_calls": [],
        }
        messages.append({"role": "assistant", "content": response.content})

        if force or not calls:
            _log(trace_path, record)
            answer = text
            break

        results = []
        for block in calls:
            output = run_tool(block.name, block.input, seen)
            tool_calls += 1
            result = {"type": "tool_result", "tool_use_id": block.id, "content": output}
            if output.startswith("Error:"):
                result["is_error"] = True
            results.append(result)
            record["tool_calls"].append(
                {"name": block.name, "input": block.input, "result": summarize_result(output)}
            )
        _log(trace_path, record)
        messages.append({"role": "user", "content": results})

    seconds = round(time.perf_counter() - started, 2)
    summary = {
        "steps": step,
        "tool_calls": tool_calls,
        "hit_cap": hit_cap,
        **totals,
        "seconds": seconds,
    }
    _log(trace_path, {"event": "final", "answer": answer, **summary})
    return {
        "question": question,
        "answer": answer,
        "hits": seen,
        **summary,
        "trace": str(trace_path) if trace_path else None,
    }


def main() -> None:
    utf8_stdout()
    parser = argparse.ArgumentParser(description="Ask the agent a question about the reports.")
    parser.add_argument("question")
    parser.add_argument("--qid", help="names the trace file, e.g. C03")
    args = parser.parse_args()

    result = run_agent(args.question, args.qid)
    print(result["answer"])
    print(
        f"\n{result['steps']} model turns, {result['tool_calls']} tool calls, "
        f"{result['input_tokens']} in / {result['output_tokens']} out tokens, "
        f"{result['seconds']}s" + (" (hit the step cap)" if result["hit_cap"] else "")
    )
    print("Retrieved:", " ".join(dict.fromkeys(citation(hit) for hit in result["hits"])))
    print("Trace:", result["trace"])


if __name__ == "__main__":
    main()
