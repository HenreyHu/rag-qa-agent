import pytest

from src.tools import calculate


@pytest.mark.parametrize(
    ("expression", "expected"),
    [
        ("(150 - 120) / 120 * 100", "25"),  # growth rate in percent
        ("(6419467 - 5000000) / 5000000", "0.283893"),  # growth rate as a fraction
        ("1 / 3", "0.333333"),  # ratio, rounded to 6 places
        ("2 ** 3 + 1", "9"),
        ("-5 + 10", "5"),
        ("(1 + 0.5) ** 2", "2.25"),  # compounding
        ("4,158,920 / 1,000", "4158.92"),  # thousands separators as printed in the filings
        ("  7 * 6  ", "42"),
    ],
)
def test_valid_expressions(expression, expected):
    assert calculate(expression) == expected


@pytest.mark.parametrize("expression", ["1 / 0", "5 / (3 - 3)", "0 ** -1"])
def test_division_by_zero_returns_an_error(expression):
    result = calculate(expression)
    assert result.startswith("Error:")
    assert "zero" in result


@pytest.mark.parametrize(
    "expression",
    [
        "__import__('os').system('echo hi')",
        "open('data/raw/x')",
        "().__class__.__bases__",
        "[x for x in range(3)]",
        "lambda: 1",
        "x + 1",
        "'a' * 3",
        "True + 1",
    ],
)
def test_injection_attempts_are_rejected(expression):
    assert calculate(expression).startswith("Error:")


@pytest.mark.parametrize(
    "expression", ["", "   ", "what is the growth rate", "2 +", "10%", "(1 + 2", "1 2"]
)
def test_garbage_returns_an_error_and_never_raises(expression):
    assert calculate(expression).startswith("Error:")


@pytest.mark.parametrize(
    "expression", ["9 ** 9 ** 9", "10 ** 200", "1e308 * 10", "(-8) ** (1/3)", "1" * 500]
)
def test_limits_return_an_error(expression):
    assert calculate(expression).startswith("Error:")


def test_error_message_tells_the_model_how_to_retry():
    assert "for example" in calculate("10%")