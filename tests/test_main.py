import main


def test_defaults_to_the_agent():
    args = main.build_parser().parse_args(["What was Sea's revenue?"])
    assert args.mode == "agent"
    assert not args.vector


def test_agent_mode_prints_answer_cost_and_retrieved_pages(monkeypatch, capsys):
    fake = {
        "answer": "US$16.8 billion [Sea, FY2025, p.80]",
        "hits": [{"company": "Sea", "year": 2025, "page": "80"}] * 2,
        "steps": 2,
        "tool_calls": 1,
        "hit_cap": False,
        "input_tokens": 100,
        "output_tokens": 20,
        "seconds": 1.5,
        "trace": None,
    }
    monkeypatch.setattr("src.agent.run_agent", lambda question, qid=None: fake)
    monkeypatch.setattr("src.retrieve.citation", lambda hit: "[Sea, FY2025, p.80]")

    main.ask(main.build_parser().parse_args(["q"]))

    out = capsys.readouterr().out
    assert "US$16.8 billion" in out
    assert "2 model turns, 1 tool calls" in out
    assert out.count("[Sea, FY2025, p.80]") == 2  # once in the answer, once in Retrieved (deduped)


def test_vector_flag_sets_the_search_mode(monkeypatch):
    monkeypatch.delenv("AGENT_SEARCH_MODE", raising=False)
    monkeypatch.setattr(main, "ask", lambda args: None)
    main.main(["q", "--vector"])
    assert main.os.environ["AGENT_SEARCH_MODE"] == "vector"
    monkeypatch.delenv("AGENT_SEARCH_MODE")
