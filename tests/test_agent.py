import copy
import json
from types import SimpleNamespace

import pytest

from src import agent
from src.agent import FORCE_FINAL, run_agent, summarize_result
from src.config import AGENT_MAX_TOKENS, AGENT_MODEL, AGENT_SYSTEM_PROMPT

HIT = {
    "id": "sea-2025:section:00001",
    "company": "Sea",
    "year": 2025,
    "pages": ["95"],
    "section": "Item 5 > Results",
    "is_table": False,
    "filing": "sea-2025",
}
SEARCH_OUTPUT = (
    "1 results for 'revenue' (company=Sea, year=2025)\n\n"
    "Result 1 [Sea, FY2025, p.95] | text | Item 5 > Results\n"
    "Total revenue was US$22,938,469 thousand."
)


def text_block(text):
    return SimpleNamespace(type="text", text=text)


def tool_block(block_id, name, args):
    return SimpleNamespace(type="tool_use", id=block_id, name=name, input=args)


def reply(*content, stop="end_turn", tokens=(100, 10)):
    usage = SimpleNamespace(input_tokens=tokens[0], output_tokens=tokens[1])
    return SimpleNamespace(content=list(content), stop_reason=stop, usage=usage)


def tool_reply(*blocks, tokens=(100, 10)):
    return reply(*blocks, stop="tool_use", tokens=tokens)


class FakeClient:
    """Plays back scripted replies and records a snapshot of every request."""

    def __init__(self, *replies):
        self.replies = list(replies)
        self.requests = []
        self.messages = SimpleNamespace(create=self._create)

    def _create(self, **kwargs):
        assert self.replies, "the agent made more calls than the test scripted"
        self.requests.append(copy.deepcopy(kwargs))
        return self.replies.pop(0)


@pytest.fixture(autouse=True)
def fake_search(monkeypatch):
    def search(query, company=None, year=None, *, seen=None):
        seen.append(HIT)
        return SEARCH_OUTPUT

    monkeypatch.setattr(agent, "search_reports", search)


def read_trace(path):
    return [json.loads(line) for line in open(path, encoding="utf-8")]


def test_answers_directly_when_no_tool_is_needed(tmp_path):
    client = FakeClient(reply(text_block("I don't know."), tokens=(120, 8)))
    result = run_agent("What is the weather?", "Q1", client=client, trace_dir=tmp_path)
    assert result["answer"] == "I don't know."
    assert (result["steps"], result["tool_calls"], result["hit_cap"]) == (1, 0, False)
    assert result["hits"] == []
    assert (result["input_tokens"], result["output_tokens"]) == (120, 8)


def test_request_carries_model_prompt_tools_and_question(tmp_path):
    client = FakeClient(reply(text_block("ok")))
    run_agent("How much?", "Q1", client=client, trace_dir=tmp_path)
    request = client.requests[0]
    assert request["model"] == AGENT_MODEL
    assert request["max_tokens"] == AGENT_MAX_TOKENS
    assert request["system"] == AGENT_SYSTEM_PROMPT
    assert [tool["name"] for tool in request["tools"]] == ["search_reports", "calculate"]
    assert request["messages"] == [{"role": "user", "content": "How much?"}]
    assert "tool_choice" not in request  # tools stay available on normal turns


def test_search_result_is_fed_back_and_hits_are_collected(tmp_path):
    client = FakeClient(
        tool_reply(
            text_block("Searching Sea."),
            tool_block("t1", "search_reports", {"query": "revenue", "company": "Sea"}),
            tokens=(100, 20),
        ),
        reply(text_block("US$22.9 billion [Sea, FY2025, p.95]"), tokens=(400, 30)),
    )
    result = run_agent("Sea revenue?", "Q1", client=client, trace_dir=tmp_path)
    assert result["answer"] == "US$22.9 billion [Sea, FY2025, p.95]"
    assert result["hits"] == [HIT]
    assert (result["steps"], result["tool_calls"]) == (2, 1)
    assert (result["input_tokens"], result["output_tokens"]) == (500, 50)
    # The second request holds the assistant turn, then the tool result for the same id.
    second = client.requests[1]["messages"]
    assert [m["role"] for m in second] == ["user", "assistant", "user"]
    assert second[2]["content"] == [
        {"type": "tool_result", "tool_use_id": "t1", "content": SEARCH_OUTPUT}
    ]


def test_calculate_is_executed_for_real(tmp_path):
    client = FakeClient(
        tool_reply(tool_block("t1", "calculate", {"expression": "(150 - 120) / 120 * 100"})),
        reply(text_block("25%")),
    )
    run_agent("Growth?", "Q1", client=client, trace_dir=tmp_path)
    tool_result = client.requests[1]["messages"][2]["content"][0]
    assert tool_result["content"] == "25"
    assert "is_error" not in tool_result


def test_parallel_tool_calls_all_get_results_in_one_user_turn(tmp_path):
    client = FakeClient(
        tool_reply(
            tool_block("a", "search_reports", {"query": "revenue", "company": "Sea"}),
            tool_block("b", "search_reports", {"query": "revenue", "company": "Grab"}),
        ),
        reply(text_block("done")),
    )
    result = run_agent("Compare", "Q1", client=client, trace_dir=tmp_path)
    results = client.requests[1]["messages"][2]["content"]
    assert [r["tool_use_id"] for r in results] == ["a", "b"]
    assert result["tool_calls"] == 2
    assert len(result["hits"]) == 2


def test_unknown_tool_and_bad_arguments_return_errors_and_the_loop_continues(tmp_path):
    client = FakeClient(
        tool_reply(
            tool_block("a", "browse_web", {"url": "x"}),
            tool_block("b", "search_reports", {"q": "revenue"}),  # wrong argument name
            tool_block("c", "calculate", {"expression": "1 / 0"}),
        ),
        reply(text_block("I don't know.")),
    )
    result = run_agent("Q", "Q1", client=client, trace_dir=tmp_path)
    a, b, c = client.requests[1]["messages"][2]["content"]
    assert a["is_error"]
    assert "unknown tool" in a["content"]
    assert b["is_error"]
    assert "bad arguments" in b["content"]
    assert c["is_error"]
    assert "zero" in c["content"]
    assert result["answer"] == "I don't know."


def test_step_cap_forces_a_final_answer_with_tools_switched_off(tmp_path):
    search = tool_block("t", "search_reports", {"query": "revenue"})
    client = FakeClient(
        tool_reply(search),
        tool_reply(search),
        reply(text_block("I don't know. Grab's figure was not found."), tokens=(900, 40)),
    )
    result = run_agent("Q", "Q1", client=client, max_steps=2, trace_dir=tmp_path)
    assert result["hit_cap"] is True
    assert result["steps"] == 3
    assert result["answer"] == "I don't know. Grab's figure was not found."
    assert len(client.requests) == 3
    assert "tool_choice" not in client.requests[0]
    assert "tool_choice" not in client.requests[1]
    final = client.requests[2]
    assert final["tool_choice"] == {"type": "none"}
    assert final["tools"]  # still defined, because the history contains tool blocks
    last_turn = final["messages"][-1]
    assert last_turn["role"] == "user"
    assert last_turn["content"][0]["type"] == "tool_result"  # tool results stay first
    assert last_turn["content"][-1] == {"type": "text", "text": FORCE_FINAL}


def test_answering_on_the_last_allowed_step_is_not_a_cap_hit(tmp_path):
    client = FakeClient(
        tool_reply(tool_block("t", "search_reports", {"query": "revenue"})),
        reply(text_block("answer")),
    )
    result = run_agent("Q", "Q1", client=client, max_steps=2, trace_dir=tmp_path)
    assert (result["steps"], result["hit_cap"]) == (2, False)


def test_trace_records_every_step_without_the_full_passages(tmp_path):
    client = FakeClient(
        tool_reply(
            text_block("Searching."),
            tool_block("t1", "search_reports", {"query": "revenue", "company": "Sea"}),
            tokens=(100, 20),
        ),
        reply(text_block("US$22.9 billion [Sea, FY2025, p.95]"), tokens=(400, 30)),
    )
    result = run_agent("Sea revenue?", "Q7", client=client, trace_dir=tmp_path)
    assert result["trace"] == str(tmp_path / "Q7.jsonl")
    records = read_trace(result["trace"])
    assert [r["event"] for r in records] == ["question", "step", "step", "final"]
    assert records[0]["question"] == "Sea revenue?"
    step1 = records[1]
    assert step1["text"] == "Searching."
    assert step1["usage"] == {"input_tokens": 100, "output_tokens": 20}
    assert step1["tool_calls"][0]["name"] == "search_reports"
    assert step1["tool_calls"][0]["input"] == {"query": "revenue", "company": "Sea"}
    assert "[Sea, FY2025, p.95]" in step1["tool_calls"][0]["result"]
    assert "Total revenue was" not in json.dumps(records)  # passages are not logged
    assert records[2]["tool_calls"] == []
    assert records[3]["answer"] == "US$22.9 billion [Sea, FY2025, p.95]"
    assert (records[3]["steps"], records[3]["input_tokens"]) == (2, 500)


def test_each_run_overwrites_its_trace(tmp_path):
    for _ in range(2):
        client = FakeClient(reply(text_block("a")))
        result = run_agent("Q", "Q1", client=client, trace_dir=tmp_path)
    assert [r["event"] for r in read_trace(result["trace"])] == ["question", "step", "final"]


def test_trace_dir_none_writes_nothing(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    result = run_agent("Q", "Q1", client=FakeClient(reply(text_block("a"))), trace_dir=None)
    assert result["trace"] is None
    assert list(tmp_path.iterdir()) == []


def test_summarize_result():
    assert summarize_result(SEARCH_OUTPUT) == (
        "1 results for 'revenue' (company=Sea, year=2025) >> "
        "Result 1 [Sea, FY2025, p.95] | text | Item 5 > Results"
    )
    assert summarize_result("25") == "25"
    assert len(summarize_result("Error: " + "x" * 1000)) == 300
