"""Print an agent trace in readable form.

Example:
    python -m eval.show_trace C01
"""

import argparse
import json

from src.config import RESULTS_DIR, utf8_stdout


def show(records: list[dict]) -> None:
    for record in records:
        if record["event"] == "question":
            print(f"QUESTION: {record['question']}")
            print(f"(model {record['model']}, up to {record['max_steps']} steps)\n")
        elif record["event"] == "step":
            label = "FORCED FINAL" if record["forced"] else f"STEP {record['step']}"
            usage = record["usage"]
            print(
                f"--- {label}  ({usage['input_tokens']} in / {usage['output_tokens']} out, "
                f"{record['seconds']}s)"
            )
            if record["text"]:
                print(f"  says: {record['text']}")
            for call in record["tool_calls"]:
                args = ", ".join(f"{key}={value!r}" for key, value in call["input"].items())
                print(f"  CALL {call['name']}({args})")
                head, _, headers = call["result"].partition(" >> ")
                print(f"    -> {head}")
                for line in filter(None, headers.split(" ; ")):
                    print(f"       {line}")
        elif record["event"] == "final":
            print(f"\nFINAL ANSWER:\n{record['answer']}\n")
            print(
                f"{record['steps']} model turns, {record['tool_calls']} tool calls, "
                f"{record['input_tokens']} in / {record['output_tokens']} out tokens, "
                f"{record['seconds']}s, hit step cap: {record['hit_cap']}"
            )


def main() -> None:
    utf8_stdout()
    parser = argparse.ArgumentParser(description="Show an agent trace.")
    parser.add_argument("qid", help="trace name, e.g. C01 (reads eval/results/traces/C01.jsonl)")
    args = parser.parse_args()
    path = RESULTS_DIR / "traces" / f"{args.qid}.jsonl"
    with path.open(encoding="utf-8") as handle:
        show([json.loads(line) for line in handle])


if __name__ == "__main__":
    main()
